"""agent/tools.py - the tool surface the agent may call.

Design
------
Every capability is a `Tool`: a name, a JSON-schema the model fills in, and a
callable. The registry is the single source of truth for what Stella can do,
which means three things fall out for free:

* the model sees exactly the tools that exist (no hallucinated names)
* permissions are enforced in one place (`requires` + `allow_destructive`)
* adding a capability is one decorator, not edits across the codebase

Safety
------
Anything that writes to disk, shells out, or reaches the network is marked
destructive and must be explicitly allowed by the caller. The agent cannot
widen its own permissions - `Registry.allowed` is injected from the host and
never derived from model output.

Honesty
-------
Every tool result carries an honesty status:

* ``done``     - the action completed and was verified (or is self-evident)
* ``unverified`` - the action was attempted but could not be confirmed
* ``failed``     - the action could not be performed

This matches the principle from Stella's design: "It says what it checked,
not what it assumed." Tools must never claim success they did not observe.
"""

from __future__ import annotations

import inspect
import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from core.tool_policy import PolicyDecision
from core.tool_policy import evaluate as evaluate_tool_policy


def _audit_tool_call(
    tool_name: str,
    target: str,
    activity: str,
    rule: str,
    ok: bool,
    reason: str = "",
    tool: "Tool | None" = None,
) -> None:
    """Best-effort audit row: a failure to log never fails the call itself."""
    try:
        from core import audit

        audit.record(
            "agent",
            tool_name,
            target or "-",
            "permitted" if ok else "refused",
            activity=activity,
            rule=rule,
            extra={
                "reason": reason,
                "destructive": bool(tool.destructive) if tool else False,
                "requires": list(tool.requires) if tool else [],
            },
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Honesty levels for tool results
# ---------------------------------------------------------------------------

class Honesty(str):
    """How much trust a tool result deserves.

    ``done``      - the action completed and was observed to succeed
    ``unverified``- the action was attempted but the result could not be
                    confirmed (e.g., a file write that returned success but
                    the file wasn't re-read to confirm)
    ``failed``    - the action could not be performed at all
    ``ask``       - nothing was done, because doing it would have been a guess
    ``started``   - the action is under way; the outcome follows separately

    See `agent/outcome.py` for what each word may be spoken as.
    """
    DONE = "done"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    ASK = "ask"
    STARTED = "started"

    @classmethod
    def from_bool(cls, ok: bool) -> "Honesty":
        return cls.DONE if ok else cls.FAILED


# ---------------------------------------------------------------------------
# Tool result
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    """Uniform tool outcome.

    ``ok`` false means the loop should reconsider. ``honesty`` tells the
    model how much to trust the outcome: ``done`` means the action was
    confirmed, ``unverified`` means it was attempted but not confirmed,
    ``failed`` means it did not happen.
    """

    ok: bool
    output: str = ""
    data: Any = None
    error: str = ""
    honesty: Honesty = Honesty.DONE

    def as_message(self) -> str:
        if self.ok:
            return self.output
        return f"ERROR: {self.error or 'tool failed'}"

    @property
    def is_confirmed(self) -> bool:
        """True only if the outcome was confirmed (honesty == done)."""
        return self.ok and self.honesty == Honesty.DONE


# ---------------------------------------------------------------------------
# Tool declaration
# ---------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., ToolResult]
    requires: tuple[str, ...] = ()
    destructive: bool = False
    # Self-describing metadata (mark-LVI pattern): every skill declares its
    # own TOOL dict. These fields let the model understand *why* a tool
    # exists and what it costs, not just what it does.
    category: str = "general"
    cost_tier: int = 1          # 1 = cheap/free, 2 = moderate, 3 = expensive
    requires_confirmation: bool = False
    read_only: bool = True
    # Activity class gating by core/tool_policy.py: passive | dns | active |
    # destructive. Passive work never opens a connection to a target.
    activity: str = "passive"
    # Short description for models on a tight tool budget (agent/tool_budget).
    brief: str = ""

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_tool_dict(self) -> dict:
        """Self-describing tool dict (mark-LVI pattern).

        Returns a complete description that can be shown to the model or
        stored in a skill manifest, including honesty metadata hints.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "category": self.category,
            "cost_tier": self.cost_tier,
            "requires_confirmation": self.requires_confirmation,
            "read_only": self.read_only,
            "requires": list(self.requires),
            "destructive": self.destructive,
            "activity": self.activity,
        }

class Registry:
    """Holds tools and decides what a given caller may run."""

    def __init__(self, allowed: Iterable[str] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        # None means "no gating" (used by tests and by trusted local callers).
        self.allowed: set[str] | None = None if allowed is None else set(allowed)
        self.actor = "agent"

    # -- registration -------------------------------------------------------

    def tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        requires: tuple[str, ...] = (),
        destructive: bool = False,
        activity: str = "passive",
        brief: str = "",
    ):
        def wrap(fn: Callable[..., ToolResult]) -> Callable[..., ToolResult]:
            self.register(
                Tool(
                    name, description, parameters, fn, requires, destructive,
                    activity=activity, brief=brief,
                )
            )
            return fn

        return wrap

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    # -- queries ------------------------------------------------------------

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self):
        return iter(self._tools.values())

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def permitted(self, name: str) -> bool:
        if name not in self._tools:
            return False
        if self.allowed is None:
            return True
        return name in self.allowed

    def schemas(self) -> list[dict]:
        """OpenAI-style tool schemas for the tools this caller may use."""
        return [t.schema() for t in self._tools.values() if self.permitted(t.name)]

    # -- policy gate --------------------------------------------------------

    _audit = staticmethod(_audit_tool_call)

    @staticmethod
    def _target_of(tool: Tool, kwargs: dict) -> str:
        for key in ("target", "scope", "host", "domain", "ip", "url", "path", "command"):
            value = kwargs.get(key)
            if value:
                return str(value)[:200]
        return ""

    def policy_check(self, name: str, args: dict | None = None) -> PolicyDecision:
        """The policy verdict for a call, without running it."""
        tool = self._tools.get(name)
        if tool is None:
            return PolicyDecision(
                allowed=False, rule="unknown-tool", reason=f"unknown tool '{name}'")
        kwargs = dict(args or {})
        return evaluate_tool_policy(
            name, tool.activity, self._target_of(tool, kwargs), actor=self.actor)

    # -- execution ----------------------------------------------------------

    def run(self, name: str, args: dict | None = None) -> ToolResult:
        """Execute a tool with permission, policy and audit guarantees."""
        tool = self._tools.get(name)
        if tool is None:
            self._audit(name, args or "", "", "unknown-tool", ok=False, tool=tool)
            return ToolResult(ok=False, error=f"unknown tool '{name}'")
        if not self.permitted(name):
            self._audit(name, args or "", "", "not-enabled", ok=False, tool=tool)
            return ToolResult(
                ok=False,
                error=f"tool '{name}' is not enabled for this session",
            )

        kwargs = dict(args or {})
        target = self._target_of(tool, kwargs)

        decision = evaluate_tool_policy(
            name, tool.activity, target, actor=self.actor)
        if not decision.allowed:
            approved = False
            try:
                from core.approvals import is_approved

                approved = is_approved(
                    self.actor, name, tool.activity, target)
            except Exception:
                approved = False
            if not approved:
                self._audit(
                    name, target, decision.activity, decision.rule, ok=False,
                    reason=decision.reason, tool=tool)
                return ToolResult(
                    ok=False,
                    error=(
                        f"Refused by tool policy '{decision.rule}': {decision.reason} "
                        "Add an allow rule in config/tool_policy.json naming this tool "
                        "and target, or grant a standing approval from Settings."
                    ),
                    honesty=Honesty.ASK,
                )

        self._audit(
            name, target, decision.activity, decision.rule, ok=True,
            reason="permitted; running", tool=tool)

        try:
            kwargs = dict(args or {})
            sig = inspect.signature(tool.handler)
            # Drop anything the handler does not accept: models routinely
            # include extra keys, and a TypeError here would waste a turn.
            kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            started = time.time()
            result = tool.handler(**kwargs)
            if not isinstance(result, ToolResult):
                result = ToolResult(ok=True, output=str(result))
            result.output = (result.output or "")[:8000]
            result.data = {"elapsed": round(time.time() - started, 3), **(
                result.data if isinstance(result.data, dict) else {})}

            # Honesty inference: if the tool handler didn't set honesty,
            # infer it from the tool's properties and outcome.
            if result.honesty == Honesty.DONE and not result.ok:
                result.honesty = Honesty.FAILED
            elif result.ok and result.honesty == Honesty.DONE:
                # Destructive or network actions are "unverified" unless the
                # handler explicitly confirmed them.
                if tool.destructive or not tool.read_only:
                    result.honesty = Honesty.UNVERIFIED

            return result
        except TypeError as exc:
            return ToolResult(ok=False, error=f"bad arguments for '{name}': {exc}",
                              honesty=Honesty.FAILED)
        except Exception as exc:  # noqa: BLE001 - surfaced back to the model
            return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}",
                              honesty=Honesty.FAILED)


# ---------------------------------------------------------------------------
# Built-in tool suite
# ---------------------------------------------------------------------------

_SAFE_ROOT: Path | None = None


def set_workspace_root(root: str | Path | None) -> None:
    """Confine filesystem tools to a root directory.

    Called by the host at startup. Passing None disables the confinement,
    which is only appropriate when the user has explicitly asked for
    unrestricted access.
    """
    global _SAFE_ROOT
    _SAFE_ROOT = Path(root).expanduser().resolve() if root else None


def _resolve_in_workspace(path: str) -> Path:
    """Resolve `path`, refusing anything outside the workspace root."""
    p = Path(path).expanduser()
    p = p if p.is_absolute() else (_SAFE_ROOT or Path.cwd()) / p
    p = p.resolve()
    if _SAFE_ROOT is not None:
        root = _SAFE_ROOT
        try:
            p.relative_to(root)
        except ValueError:
            raise PermissionError(
                f"path {p} is outside the workspace ({root}); "
                "write access is confined to the workspace"
            ) from None
    return p


def build_default_registry(workspace: str | Path | None = None,
                           include_legacy: bool = True) -> Registry:
    """The standard tool suite Stella ships with.

    Two layers in one registry:

    * the core tools below (filesystem, shell, memory, reasoning) - these are
      sandboxed by the workspace root and always available
    * the legacy catalogue from `agent.tool_catalogue` - the 41 real
      capabilities (PDF, browser, Spotify, smart home, ...). They are wrapped,
      not rewritten, and carry capability tags used for consent.
    """
    reg = Registry()

    if workspace is not None:
        set_workspace_root(workspace)

    if include_legacy:
        try:
            from agent.tool_catalogue import register_legacy
            added = register_legacy(reg)
            logger_count = f" (+{added} capability tools)"
        except Exception as exc:  # noqa: BLE001 - never block on the catalogue
            logger_count = f" (capability tools unavailable: {exc})"
    else:
        logger_count = ""
    print(f"[agent] tool registry: {len(reg)} tools{logger_count}")

    # ---- filesystem -------------------------------------------------------

    @reg.tool(
        "read_file",
        "Read a UTF-8 text file. Returns the content, optionally a line range.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File to read."},
                "start_line": {"type": "integer", "description": "1-based first line."},
                "max_lines": {"type": "integer", "description": "How many lines."},
            },
            "required": ["path"],
        },
    )
    def read_file(path: str, start_line: int = 1, max_lines: int = 400) -> ToolResult:
        p = _resolve_in_workspace(path)
        if not p.is_file():
            return ToolResult(ok=False, error=f"not a file: {p}")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        chunk = lines[max(0, start_line - 1): start_line - 1 + max_lines]
        return ToolResult(
            ok=True,
            output="\n".join(chunk) or "(empty)",
            data={"path": str(p), "lines": len(lines)},
        )

    @reg.tool(
        "write_file",
        "Create or overwrite a text file. Overwrites the whole file.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "append": {"type": "boolean", "description": "Append instead of overwrite."},
            },
            "required": ["path", "content"],
        },
        requires=("files",),
        destructive=True,
        activity="destructive",
        brief="Write or append a text file in the workspace.",
    )
    def write_file(path: str, content: str, append: bool = False) -> ToolResult:
        p = _resolve_in_workspace(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if append:
            with p.open("a", encoding="utf-8") as fh:
                fh.write(content)
        else:
            p.write_text(content, encoding="utf-8")
        return ToolResult(ok=True, output=f"wrote {len(content)} chars -> {p}",
                          data={"path": str(p)})

    @reg.tool(
        "list_dir",
        "List files and folders in a directory.",
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    )
    def list_dir(path: str = ".") -> ToolResult:
        p = _resolve_in_workspace(path)
        if not p.is_dir():
            return ToolResult(ok=False, error=f"not a directory: {p}")
        rows = []
        for child in sorted(p.iterdir(), key=lambda c: (c.is_file(), c.name))[:500]:
            kind = "d" if child.is_dir() else "f"
            size = child.stat().st_size if child.is_file() else 0
            rows.append(f"{kind} {size:>10} {child.name}")
        return ToolResult(ok=True, output="\n".join(rows) or "(empty)",
                          data={"count": len(rows)})

    @reg.tool(
        "search_text",
        "Regex search across files under a directory.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string"},
                "glob": {"type": "string", "description": "e.g. *.py"},
                "max_hits": {"type": "integer"},
            },
            "required": ["path", "pattern"],
        },
    )
    def search_text(path: str, pattern: str, glob: str = "*", max_hits: int = 60) -> ToolResult:
        import re
        root = _resolve_in_workspace(path)
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            return ToolResult(ok=False, error=f"bad regex: {exc}")
        if not root.is_dir():
            return ToolResult(ok=False, error=f"not a directory: {root}")
        hits, scanned = [], 0
        for f in root.rglob(glob):
            if not f.is_file() or f.stat().st_size > 2_000_000:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            scanned += 1
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append(f"{f}:{i}: {line.strip()[:200]}")
                    if len(hits) >= max_hits:
                        return ToolResult(ok=True, output="\n".join(hits),
                                          data={"scanned": scanned, "truncated": True})
        return ToolResult(ok=True, output="\n".join(hits) or "(no matches)",
                          data={"scanned": scanned, "hits": len(hits)})

    # ---- shell ------------------------------------------------------------

    @reg.tool(
        "run_command",
        "Run a shell command in the workspace. Returns stdout+stderr.",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_s": {"type": "integer"},
            },
            "required": ["command"],
        },
        requires=("shell",),
        destructive=True,
        activity="active",
        brief="Run one shell command in the workspace and return its output.",
    )
    def run_command(command: str, timeout_s: int = 60) -> ToolResult:
        cwd = str(_SAFE_ROOT or Path.cwd())
        try:
            proc = subprocess.run(
                command, shell=True, cwd=cwd, capture_output=True,
                text=True, timeout=max(1, min(timeout_s, 300)),
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, error=f"timed out after {timeout_s}s")
        body = (proc.stdout or "") + (proc.stderr or "")
        return ToolResult(
            ok=proc.returncode == 0,
            output=body[:8000] or "(no output)",
            error=f"exit code {proc.returncode}" if proc.returncode else "",
            data={"returncode": proc.returncode},
        )

    # ---- memory -----------------------------------------------------------

    @reg.tool(
        "remember",
        "Store a durable fact for later sessions.",
        {
            "type": "object",
            "properties": {
                "fact": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["fact"],
        },
        requires=("memory",),
    )
    def remember(fact: str, tags: list[str] | None = None) -> ToolResult:
        from agent.memory import remember as _remember
        return _remember(fact, tags)

    @reg.tool(
        "recall",
        "Search stored memories. Use before assuming you do not know something.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    )
    def recall(query: str, limit: int = 8) -> ToolResult:
        from agent.memory import recall as _recall
        return _recall(query, limit)

    @reg.tool(
        "write_note",
        "Write a markdown note to the Memory Vault folder. Returns the file path.",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Note title (used as filename)."},
                "content": {"type": "string", "description": "Note body in markdown."},
                "folder": {"type": "string", "description": "Optional subfolder within the vault."},
            },
            "required": ["title", "content"],
        },
        requires=("memory",),
        destructive=True,
        activity="destructive",
        brief="Write a markdown note into the Memory Vault.",
    )
    def write_note(title: str, content: str, folder: str = "") -> ToolResult:
        import re as _re
        from pathlib import Path as _Path
        # Determine vault root from settings or default to ~/Stella/notes
        vault_root = _Path.home() / "Stella" / "notes"
        try:
            import json as _json
            from core.user_paths import get_user_data_dir
            settings_path = _Path(get_user_data_dir()) / "config" / "app_settings.json"
            if settings_path.exists():
                s = _json.loads(settings_path.read_text(encoding="utf-8-sig"))
                if not isinstance(s, dict):
                    s = {}
                configured = s.get("vault_path") or s.get("memory_vault_folder")
                if configured and s.get("vault_enabled", True):
                    vault_root = _Path(configured)
        except Exception:
            pass
        if folder:
            vault_root = vault_root / folder
        vault_root.mkdir(parents=True, exist_ok=True)
        # Sanitize title for filename
        safe = _re.sub(r'[<>:"/\\|?*]', "_", title).strip() or "untitled"
        path = vault_root / f"{safe}.md"
        # Avoid overwriting — append counter
        counter = 1
        while path.exists():
            path = vault_root / f"{safe}_{counter}.md"
            counter += 1
        path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
        return ToolResult(ok=True, output=f"Note written: {path}", data={"path": str(path)})

    # ---- time / environment ------------------------------------------------

    @reg.tool(
        "current_time",
        "Current local date and time. Use before any date arithmetic.",
        {"type": "object", "properties": {}},
    )
    def current_time() -> ToolResult:
        import datetime
        now = datetime.datetime.now().astimezone()
        return ToolResult(ok=True, output=now.strftime("%Y-%m-%d %H:%M:%S %Z (%A)"))

    @reg.tool(
        "system_info",
        "Report platform, python version, and workspace location.",
        {"type": "object", "properties": {}},
    )
    def system_info() -> ToolResult:
        import platform
        import sys
        return ToolResult(
            ok=True,
            output=(f"platform={platform.platform()}\n"
                    f"python={sys.version.split()[0]}\n"
                    f"cwd={Path.cwd()}\nworkspace={_SAFE_ROOT or '(unrestricted)'}"),
        )

    @reg.tool(
        "calculate",
        "Evaluate an arithmetic expression exactly. Prefer this over mental math.",
        {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    )
    def calculate(expression: str) -> ToolResult:
        # Deliberately narrow: no names, no attribute access, no builtins.
        allowed = set("0123456789+-*/().%^ ")
        if not set(expression) <= allowed:
            return ToolResult(ok=False, error="only digits and + - * / ( ) . % ^ allowed")
        try:
            return ToolResult(ok=True, output=str(eval(expression, {"__builtins__": {}}, {})))
        except Exception as exc:
            return ToolResult(ok=False, error=f"cannot evaluate: {exc}")

    @reg.tool(
        "todo",
        "Record or update the step-by-step plan for the current task.",
        {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "description": "Full list of steps, each short.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "string"},
                            "status": {"type": "string", "enum": ["pending", "doing", "done", "failed"]},
                        },
                        "required": ["step"],
                    },
                },
                "note": {"type": "string", "description": "Why the plan changed, if it did."},
            },
            "required": ["steps"],
        },
    )
    def todo(steps: list, note: str = "") -> ToolResult:
        from agent.scratchpad import write_plan
        return write_plan(steps, note)

    # ---- device automation (Needle, rootless, reversible) --------------------
    # These give the model the same activate/scan/run/revert cycle the Settings
    # page exposes manually, as callable tools. Needle routes tool-call turns
    # here; the confidence gate decides whether its call is trusted.

    @reg.tool(
        "device_scan",
        "Rootlessly read the whole device (screens, controls, permissions, "
        "processes, network) into device_state.json. Parses every detail needed "
        "to drive the device exactly, without opening Settings.",
        {
            "type": "object",
            "properties": {
                "device": {"type": "string",
                           "description": "Device id or address (e.g. 192.168.1.50, this-pc)."},
            },
            "required": ["device"],
        },
    )
    def device_scan(device: str) -> ToolResult:
        from agent import device_automation as da
        state, err = da.scan_device(device)
        if err is not None:
            return ToolResult(ok=False, error=err)
        try:
            da.save_state(state)
        except Exception as exc:  # never fail a scan on persistence
            state.setdefault("errors", []).append({"at": "save", "error": str(exc)})
        return ToolResult(
            ok=True,
            output=(f"scanned {state.get('device')} ({state.get('platform')}): "
                    f"{len(state.get('screens', []))} screens, "
                    f"{len(state.get('controls', []))} controls, "
                    f"{len(state.get('permissions', []))} permission groups, "
                    f"{len(state.get('processes', []))} process groups, "
                    f"{len(state.get('network', []))} network groups"),
            data=state,
        )

    @reg.tool(
        "device_revert",
        "Deactivate a device automation session, reversing every change the "
        "activation made, in reverse order, at the same access level. The "
        "device returns to exactly how it was before activation.",
        {
            "type": "object",
            "properties": {
                "device": {"type": "string", "description": "Device to roll back."},
                "goal": {"type": "string",
                         "description": "What was automated, for the audit log."},
            },
            "required": ["device"],
        },
        destructive=True,
        activity="destructive",
        brief="Reverse every change a device automation session made.",
    )
    def device_revert(device: str, goal: str = "") -> ToolResult:
        from agent import device_automation as da
        try:
            state = da.load_state()
        except Exception as exc:
            return ToolResult(ok=False, error=f"cannot read device state: {exc}")
        try:
            activation = da.activate(device, "stella", state)
        except Exception as exc:
            return ToolResult(ok=False, error=f"cannot build activation for {device}: {exc}")
        summary = activation.revert()
        line = (f"reverted {summary.get('reverted', 0)} step(s) on {device} "
                f"({summary.get('failed', 0)} failed)")
        if goal:
            line += f" for goal: {goal[:120]}"
        if summary.get("failed"):
            return ToolResult(ok=False, error=line, data=summary)
        return ToolResult(ok=True, output=line, data=summary)

    # ---- image generation (pocketstrike pattern) ------------------------
    # Image generation via local model (llama.cpp/Ollama with vision) or
    # external image generation API. Honest about what it can produce.
    @reg.tool(
        "generate_image",
        "Generate an image from a text prompt. Uses a local image model if "
        "available (Ollama/LM Studio with vision), otherwise reports that "
        "image generation is not available on this device. The returned "
        "image path can be used in subsequent messages.",
        {
            "type": "object",
            "properties": {
                "prompt": {"type": "string",
                           "description": "Description of the image to generate."},
                "width": {"type": "integer",
                          "description": "Image width in pixels (default 512)."},
                "height": {"type": "integer",
                           "description": "Image height in pixels (default 512)."},
            },
            "required": ["prompt"],
        },
        requires=("files",),
        destructive=False,
    )
    def generate_image(prompt: str, width: int = 512, height: int = 512) -> ToolResult:
        """Generate an image from a text prompt.

        Tries a local image model first (Ollama/LM Studio with vision
        capability), then falls back to reporting unavailability. Never
        fabricates an image that wasn't actually generated.
        """
        import json
        import urllib.request

        # Try local image model first (Ollama/LM Studio with vision support)
        try:
            from core.providers import registry

            endpoint = registry.image_generation_endpoint()
            base_url = endpoint["base_url"]
            api_key = endpoint["api_key"]
        except Exception:
            base_url = ""
            api_key = ""

        if base_url:
            try:
                payload = {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                }
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                req = urllib.request.Request(
                    base_url.rstrip("/") + "/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode())
                        image_path = data.get("image_path", "")
                        if image_path and Path(image_path).exists():
                            return ToolResult(
                                ok=True,
                                output=f"Image generated: {image_path}",
                                data={"path": image_path, "prompt": prompt},
                                honesty=Honesty.DONE,
                            )
            except Exception:
                pass  # Fall through to "not available"

        return ToolResult(
            ok=False,
            error="Image generation not available on this device. "
                  "Configure an image generation endpoint in Settings, "
                  "or use a local model with vision capabilities.",
            honesty=Honesty.FAILED,
        )

    return reg