"""agent/tool_catalogue.py - the legacy tool library, made addressable.

Why this exists
---------------
`agent/executor.py::_call_tool` has always been the real tool surface: 41
capabilities (PDF, Word, browser, Spotify, calendar, smart-home, globe,
uploads, code, self-healing...). But it is an `if/elif` chain reachable only
from the Gemini planner, so it has none of the properties a modern agent needs:

* no JSON schemas, so an OpenAI-compatible backend (our local K2) cannot
  discover or call it at all
* no permission gating - any step may invoke anything
* no capability labels for the user-facing consent screen

This module keeps `_call_tool` as the single implementation (Option 1: wrap,
don't rewrite) and registers each tool as a `Tool` in the registry. The
schemas are transcribed from the planner's own tool contract so the two
descriptions cannot silently drift.

Consequences of wrapping rather than rewriting: the `if/elif` chain stays as
the implementation detail underneath, which is ugly, but no working tool
changes behaviour.
"""

from __future__ import annotations

from typing import Any

from agent.tools import Registry, ToolResult

# --------------------------------------------------------------------------
# Capability groups drive the consent UI. A group is what the user grants or
# declines; individual tools inherit it.
# --------------------------------------------------------------------------
CAPABILITY = {
    "web": "network",
    "info": "network",
    "files": "files",
    "docs": "files",
    "system": "system",
    "media": "media",
    "social": "network",
    "home": "home",
    "dev": "dev",
    "self": "internal",
    "phone": "device",
}


def _s(t: str, **kw) -> dict:
    """Shorthand for a JSON-schema string property."""
    return {"type": "string", **kw}


def _e(*values: str, **kw) -> dict:
    """Shorthand for a string with an enum."""
    return {"type": "string", "enum": list(values), **kw}


def _b(t: str = "boolean", **kw) -> dict:
    return {"type": t, **kw}


def _obj(**props) -> dict:
    """The *properties map* for a tool, not a full schema.

    `_make_tool` wraps this as {"type": "object", "properties": ...}, so
    returning a nested schema here would double-nest it - and llama.cpp's
    template parser rejects that, because `required` would then name keys that
    do not exist under `properties`.
    """
    return dict(props)


def _req(*names: str) -> list:
    return list(names)


# (name, capability, description, properties, required, destructive)
TOOLS: list[tuple] = [
    # ---- documents -----------------------------------------------------
    ("pdf_document", "docs",
     "Create or convert a PDF document.",
     _obj(action=_e("create", "convert", "create_letter"), title=_s("Clear title"),
          subtitle=_s("Brief subtitle"), content=_s("Full report text"),
          output_path=_s("Folder or .pdf path"), auto_open=_b()), _req("title", "content"), True),
    ("word_document", "docs",
     "Create or convert a Word (.docx) document.",
     _obj(action=_e("create", "convert"), title=_s("Title"), content=_s("Body text"),
          output_path=_s("Output folder or path")), _req("title", "content"), True),
    ("presentation_builder", "docs",
     "Build a presentation / slide deck on a topic.",
     _obj(topic=_s("Topic or title"),
          theme=_e("corporate", "neon", "luxury", "academic", "sunset", "creative")),
     _req("topic"), True),
    ("spreadsheet_builder", "docs",
     "Build a spreadsheet, workbook, tracker or budget sheet.",
     _obj(topic=_s("Purpose of the sheet")), _req("topic"), True),

    # ---- information ----------------------------------------------------
    ("web_search", "web",
     "Search the web for information, research or current data.",
     _obj(query=_s("Clear, focused search query"), mode=_e("search", "compare"),
          items={"type": "array", "items": {"type": "string"}}, aspect=_s("Aspect to compare")),
     _req("query"), False),
    ("weather_report", "info", "Current weather for a city.",
     _obj(city=_s("City name")), _req("city"), False),
    ("flight_finder", "info", "Flights between two cities on a date.",
     _obj(origin=_s("Origin"), destination=_s("Destination"), date=_s("YYYY-MM-DD")),
     _req("origin", "destination", "date"), False),
    ("daily_briefing", "info", "Morning news briefing.",
     _obj(category=_e("all", "tech", "world")), [], False),
    ("youtube_video", "media", "Play, summarize or show trending YouTube video.",
     _obj(action=_e("play", "summarize", "trending"), query=_s("Search query")),
     _req("action"), False),

    # ---- files ----------------------------------------------------------
    ("file_controller", "files",
     "Read, write, list, move, copy or delete files.",
     _obj(action=_e("write", "create_file", "read", "list", "delete", "move", "copy",
                    "find", "disk_usage", "largest"),
          path=_s('Path; use "desktop" for the Desktop folder'),
          name=_s("Filename"), content=_s("File content")),
     _req("action"), True),
    ("cmd_control", "system", "Run a system command or open a file.",
     _obj(task=_s("Natural-language description of what to do"), visible=_b()),
     _req("task"), True),

    # ---- system ---------------------------------------------------------
    ("computer_control", "system",
     "Type, click, hotkey or scroll on the desktop.",
     _obj(action=_e("type", "click", "hotkey", "press", "scroll", "screenshot",
                    "screen_find", "screen_click"),
          text=_s("Text to type"), x={"type": "integer"}, y={"type": "integer"},
          keys=_s('e.g. "ctrl+c"'), key=_s("Key name"), direction=_e("up", "down"),
          description=_s("Natural-language screen target")),
     _req("action"), True),
    ("computer_settings", "system", "Change a system or desktop setting.",
     _obj(action=_s("Setting name"), description=_s("What to change"), value=_s("New value")),
     _req("action", "description"), True),
    ("desktop_control", "system",
     "Wallpaper, file organization, preview, clean, undo.",
     _obj(action=_e("wallpaper", "organize", "preview", "clean", "undo", "list", "task"),
          path=_s("Path"), task=_s("Task description")), _req("action"), True),
    ("smart_organizer", "files", "Organise, dedupe or archive files by type or date.",
     _obj(action=_e("preview", "organize", "undo", "find_duplicates",
                    "clean_empty_folders", "archive_old"),
          target=_s("Folder to organise"), mode=_e("by_type", "by_date"),
          days={"type": "integer"}), _req("action"), True),
    ("system_diagnostics", "system", "Check RAM, CPU, battery, disk or brightness.",
     _obj(action=_e("status", "ram_hogs", "cpu_hogs", "kill", "brightness",
                    "battery", "disk"),
          target=_s("Process name or PID"), level={"type": "number"},
          monitor=_s("Monitor target"), relative=_b(), limit={"type": "integer"}),
     _req("action"), False),
    ("kill_process", "system", "Terminate a running process.",
     _obj(name=_s("Process name or PID")), _req("name"), True),
    ("open_app", "system", "Launch an application by name.",
     _obj(app_name=_s("Application name")), _req("app_name"), False),
    ("send_message", "social", "Send a direct message or upload media.",
     _obj(receiver=_s("Recipient"), message_text=_s("Message or caption"),
          platform=_s("Platform"), mode=_e("dm", "upload"), media_path=_s("Media path")),
     _req("platform"), True),
    ("reminder", "home", "Set a reminder for a date and time.",
     _obj(date=_s("YYYY-MM-DD"), time=_s("HH:MM"), message=_s("Reminder text")),
     _req("date", "time", "message"), True),
    ("calendar_scheduler", "home", "Add, list or delete calendar events.",
     _obj(action=_e("add_event", "list_events", "check_day", "delete_event",
                    "get_upcoming", "export_ics"),
          title=_s("Event title"), date=_s('YYYY-MM-DD or "today"/"tomorrow"'),
          time=_s("HH:MM"), duration_minutes={"type": "number"},
          location=_s("Location")), _req("action"), True),
    ("spotify_controller", "media", "Control Spotify playback, volume and devices.",
     _obj(action=_e("play", "pause", "toggle", "next", "previous", "volume_up",
                    "volume_down", "set_volume", "search_play", "open_spotify",
                    "get_now_playing", "get_playlists", "get_queue", "get_devices",
                    "auth"),
          query=_s("Song or artist"), volume={"type": "number"},
          device_id=_s("Spotify Connect device")), _req("action"), False),
    ("call_screening", "phone", "Screen or manage an incoming call.",
     _obj(action=_e("start", "take_over", "hang_up"), caller=_s("Caller name"),
          app=_s("Calling app")), _req("action"), True),
    ("mobile_autopilot", "phone", "Run a multi-step workflow on the paired phone.",
     _obj(instruction=_s("What to do on the phone"), target=_s("Device name")),
     _req("instruction"), True),

    # ---- browser / vision ----------------------------------------------
    ("browser_control", "web",
     "Drive a real browser: navigate, click, type, fill forms, screenshot.",
     _obj(action=_e("go_to", "search", "click", "hover", "type", "press", "scroll",
                    "fill_form", "snapshot", "find", "evaluate", "screenshot",
                    "tabs", "wait_for", "select_option", "upload", "close"),
          url=_s("URL"), query=_s("Search query or text to find"), text=_s("Text"),
          selector=_s("CSS selector"), element=_s("Element ref from snapshot"),
          fields={"type": "object"}, direction=_e("up", "down"), key=_s("Key name"),
          expression=_s("JavaScript expression"), path=_s("File path")),
     _req("action"), True),
    ("screen_process", "media", "Analyse the screen or camera feed.",
     _obj(text=_s("What to analyse or ask"), angle=_e("screen", "camera")),
     _req("text"), False),

    # ---- workspace / code ------------------------------------------------
    ("google_workspace", "web", "Gmail, Calendar and Google Drive.",
     _obj(service=_e("gmail", "calendar", "drive"),
          action=_e("list", "read", "send", "unread", "search", "create",
                    "delete", "upload"),
          query=_s("Search query"), message_id=_s("Email id"), to=_s("Recipient"),
          subject=_s("Subject"), body=_s("Body"), title=_s("Calendar title"),
          date=_s('YYYY-MM-DD or "today"/"tomorrow"'), time=_s("HH:MM"),
          duration_minutes={"type": "number"}, filename=_s("Drive filename"),
          path=_s("Upload path")), _req("service", "action"), True),
    ("claude_code", "dev",
     "Write, edit or run code and projects. Use for all developer work.",
     _obj(description=_s("What to build or change"), workspace_path=_s("Project root")),
     _req("description"), True),
    ("geospatial_globe", "info",
     "Interactive globe: routes, weather, flights, ISS, earthquakes, radar.",
     _obj(action=_e("open", "route", "drive", "location", "fly_to", "weather",
                    "flights", "iss", "earthquakes", "nearby", "radar"),
          origin=_s("Origin"), destination=_s("Destination"),
          location=_s("Place"), query=_s("What to find")), _req("action"), False),

    # ---- games -----------------------------------------------------------
    ("game_updater", "media", "Install, update or list games on Steam/Epic.",
     _obj(action=_e("update", "install", "list", "download_status", "schedule"),
          platform=_e("steam", "epic", "both"), game_name=_s("Game name"),
          app_id=_s("App id"), shutdown_when_done=_b()), _req("action"), True),
    ("upload_video", "social", "Upload a video to a social platform.",
     _obj(media_path=_s("Path to video"), platform=_s("Platform"),
          caption=_s("Caption")), _req("media_path", "platform"), True),

    # ---- self-improvement -------------------------------------------------
    ("auto_heal", "self",
     "Diagnose and repair an error, or undo a previous patch.",
     _obj(action=_e("status", "heal", "history", "rollback", "learn_rule", "list_rules"),
          error_traceback=_s("Traceback or error"), rule_text=_s("Rule to remember"),
          category=_e("general", "formatting", "workflow", "habit"),
          patch_id=_s("Patch id")), _req("action"), True),
    ("skill_forge", "self",
     "Synthesise, sandbox-test and hot-load a brand new capability. Use when no "
     "existing tool can do the job.",
     _obj(action=_e("forge", "list"), goal=_s("Capability needed"),
          skill_name=_s("Name for the new skill")), _req("action"), True),
    ("dynamic_skill", "self", "List or run a previously forged skill.",
     _obj(action=_e("list", "run"), skill_name=_s("Skill name"),
          arguments={"type": "object"}), _req("action"), True),
    ("rollback", "self", "Undo a previously applied patch.",
     _obj(patch_id=_s("Patch id")), [], True),
    ("circuit_assembler", "dev", "Design safe wiring and show a circuit schematic.",
     _obj(action=_e("assemble_components", "analyze_screen", "show_schematic"),
          components=_s("Components"), query=_s("Question")), _req("action"), False),
    ("ram_hogs", "system", "Processes using the most memory.",
     _obj(limit={"type": "integer"}), [], False),
    ("code_helper", "dev", "Explain, write or debug a snippet of code.",
     _obj(description=_s("What you need"), language=_s("Language")), _req("description"), False),
]


def describe() -> list[dict]:
    """Catalogue entries, for docs and for the consent UI."""
    out = []
    for name, cap, desc, props, req, destructive in TOOLS:
        out.append({
            "name": name, "capability": cap, "description": desc,
            "parameters": props, "required": req, "destructive": destructive,
        })
    return out


def register_legacy(registry: Registry) -> int:
    """Register every legacy tool against `executor._call_tool`.

    The adapter deliberately accepts **any** parameters and forwards them
    verbatim: `_call_tool` already validates and dispatches per tool, and
    re-implementing its argument handling here would be exactly the
    duplication this refactor exists to avoid.
    """
    from agent.executor import _call_tool

    registered = 0
    for name, cap, desc, props, req, destructive in TOOLS:
        if name in registry:
            continue

        def make_handler(tool_name: str):
            def handler(**params) -> ToolResult:
                try:
                    output = _call_tool(tool_name, params, None, None)
                except ModuleNotFoundError as exc:
                    # Optional dependency (playwright, mediapipe, ...) absent.
                    return ToolResult(
                        ok=False,
                        error=f"'{tool_name}' needs an optional package that is "
                              f"not installed: {exc}",
                    )
                except Exception as exc:  # noqa: BLE001
                    return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")
                text = output if isinstance(output, str) else str(output)
                # A tool that returns empty text did not really do anything.
                if not text.strip():
                    return ToolResult(ok=False, error=f"'{tool_name}' returned nothing")
                return ToolResult(ok=True, output=text)
            return handler

        registry.register(_make_tool(name, cap, desc, props, req, destructive,
                                     make_handler(name)))
        registered += 1
    return registered


def _make_tool(name: str, capability: str, description: str, properties: dict,
               required: list, destructive: bool, handler) -> Any:
    from agent.tools import Tool
    return Tool(
        name=name,
        description=description,
        parameters={"type": "object", "properties": properties, "required": required},
        handler=handler,
        requires=(CAPABILITY.get(capability, "system"),),
        destructive=destructive,
    )