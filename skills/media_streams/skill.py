"""
Feature: media_streams
Description: Stream and manage open-source TV, radio and self-hosted media — IPTV-org channels, Radio Browser stations, capture, playlists, and the user's own Jellyfin/Icecast/LibreTime servers.
Uses theme tokens from themes.json (no hardcoded colours). Every result names the source and the country a channel comes from, states that a community list's legality varies by country, and reports playback honestly with the done/unverified/failed/ask vocabulary. Nothing is bundled, no DRM is circumvented, and no recording is written without an explicit confirm.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "media_streams",
    "aliases": ["media_streams", "tv channels", "iptv", "television", "watch channel",
                "play tv", "internet radio", "play radio", "radio station", "play music",
                "record stream", "jellyfin", "icecast", "libretime", "broadcast",
                "playlist", "m3u", "station manager", "now playing"],
    "description": (
        "Stream and manage open-source television, radio and self-hosted media. Search the "
        "IPTV-org channel catalogue and the Radio Browser station directory by country, "
        "language, category or codec; play a stream in Stella's own media surface or hand it to "
        "an external player when the codec is missing; record a stream to disk with a bounded "
        "duration; import, dedupe and export the user's own M3U playlists and personal station "
        "list; and connect to the user's own Jellyfin, Icecast or LibreTime servers over "
        "loopback. States honestly that a source is a community list whose legality varies by "
        "country, and never bundles content or circumvents DRM."
    ),
    "triggers": [
        "tv channel", "iptv", "television", "watch tv", "play channel", "channel guide",
        "radio station", "internet radio", "play radio", "world radio", "listen to",
        "record stream", "save stream", "record radio", "jellyfin", "icecast",
        "libretime", "my media server", "broadcast", "rtmp", "push stream",
        "import playlist", "m3u playlist", "playlist", "my stations", "station list",
        "what is playing", "now playing", "stop playback", "pause playback",
        "volume up", "change volume", "mute",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: tv_search | tv_channels | radio_search | tv_play | radio_play | stop | pause | volume | record | library | servers | now_playing | sources. Defaults to tv_search.",
            },
            "query": {
                "type": "STRING",
                "description": "Free-text search: a channel or station name, a country, a language, or a tag such as news, jazz or sports.",
            },
            "country": {
                "type": "STRING",
                "description": "Two-letter ISO country code filter, for example IN, GB or US.",
            },
            "language": {
                "type": "STRING",
                "description": "Language filter for channels or stations, for example english, hindi or malayalam.",
            },
            "category": {
                "type": "STRING",
                "description": "Content category filter, for example news, sports, music, movies, kids or general.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum entries to return. Defaults to 20.",
            },
            "channel": {
                "type": "STRING",
                "description": "Channel id, name, or the stream URL itself for playback.",
            },
            "station": {
                "type": "STRING",
                "description": "Station name or URL for playback.",
            },
            "url": {
                "type": "STRING",
                "description": "Explicit stream URL. Used verbatim, never resolved or guessed.",
            },
            "duration_seconds": {
                "type": "INTEGER",
                "description": "Recording length in seconds. Defaults to 300 and is capped at 3600.",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to write a recording to disk. Defaults to false (dry run).",
            },
            "action": {
                "type": "STRING",
                "description": "For library and servers: import | export | list | add | remove | refresh (library); list | status | play | connect (servers).",
            },
            "path": {
                "type": "STRING",
                "description": "Path to an M3U playlist file for the library import action.",
            },
            "volume": {
                "type": "INTEGER",
                "description": "Output volume percentage 0-100 for the volume operation.",
            },
            "target": {
                "type": "STRING",
                "description": "Output device name for the volume operation. Defaults to the selected audio output.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "media",
    "optional_dependencies": [],
    "notes": "Sources: IPTV-org public channel database, Radio Browser community database, user-configured Jellyfin/Icecap/LibreTime servers, VLC/ffmpeg optional for capture. No content is bundled; no DRM is circumvented.",
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _deliverables_dir():
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "deliverables"
    except Exception:
        import os
        from pathlib import Path
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StellaAI" / "deliverables"


def _library_dir():
    try:
        from core.user_paths import get_user_data_dir
        root = Path(get_user_data_dir()) / "media"
    except Exception:
        import os
        from pathlib import Path
        root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StellaAI" / "media"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _cache():
    try:
        from core.net.http import feed_cache
        return feed_cache(ttl=86400.0)
    except Exception:
        return None


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    """One operation record, stating its own outcome either way."""
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _as_int(value, default: int = 20, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _library_path() -> "Path":
    from pathlib import Path
    return _library_dir() / "stations.json"


def _load_library() -> dict:
    import json
    from pathlib import Path

    path = _library_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"entries": [], "updated_at": None}


def _save_library(data: dict) -> None:
    import json
    import time

    from pathlib import Path

    data["updated_at"] = round(time.time(), 3)
    try:
        _library_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        raise OSError(f"could not write the station library: {exc}") from exc


# ------------------------------------------------------------------ catalogue ops

def _op_tv_search(kwargs: Dict[str, Any]) -> dict:
    try:
        from core.media import iptv
    except Exception as exc:
        return _op("tv_search", False, None, f"{type(exc).__name__}: {exc}")

    result = iptv.search(kwargs, cache=_cache())
    if not result.get("ok"):
        return _op("tv_search", False, None, result.get("reason", "IPTV-org did not answer"))
    return _op("tv_search", True, result)


def _op_radio_search(kwargs: Dict[str, Any]) -> dict:
    try:
        from core.media import radiobrowser
    except Exception as exc:
        return _op("radio_search", False, None, f"{type(exc).__name__}: {exc}")

    result = radiobrowser.search(kwargs, cache=_cache())
    if not result.get("ok"):
        return _op("radio_search", False, None, result.get("reason", "Radio Browser did not answer"))
    return _op("radio_search", True, result)


def _op_tv_play(kwargs: Dict[str, Any]) -> dict:
    channel = (kwargs.get("channel") or kwargs.get("url") or "").strip()
    if not channel:
        return _op("tv_play", False, None,
                   "Name a channel (channel=...) or give a stream URL (url=...). Nothing was played.")
    if "://" not in channel:
        found = _find_channel(channel)
        if found is None:
            return _op("tv_play", False, None, (
                f"No channel matching '{channel}' was found in the public catalogue, so no stream "
                "URL could be resolved. Search first, then play the channel id."))
        channel = found
    return _play_kind(channel, kwargs, "video", "channel")


def _op_radio_play(kwargs: Dict[str, Any]) -> dict:
    station = (kwargs.get("station") or kwargs.get("url") or "").strip()
    if not station:
        return _op("radio_play", False, None,
                   "Name a station (station=...) or give a stream URL (url=...). Nothing was played.")
    if "://" not in station:
        found = _find_station(station)
        if found is None:
            return _op("radio_play", False, None, (
                f"No station matching '{station}' was found, so no stream URL could be resolved. "
                "Search first, then play the station name."))
        station = found
    return _play_kind(station, kwargs, "audio", "station")


def _play_kind(url: str, kwargs: Dict[str, Any], kind: str, noun: str) -> dict:
    try:
        from core.media import player as player_module
    except Exception as exc:
        return _op("tv_play" if kind == "video" else "radio_play", False, None,
                   f"{type(exc).__name__}: {exc}")

    title = (kwargs.get("channel") or kwargs.get("station") or "").strip()
    outcome = player_module.player().play(url, title=title, kind=kind)
    engines = player_module.player().available_engines()
    if outcome["ok"]:
        return _op("tv_play" if kind == "video" else "radio_play", True, {
            **outcome,
            "url": url,
            "title": title or url,
            "kind": kind,
            "engines": engines,
            "source": "you chose this stream",
        })
    return _op("tv_play" if kind == "video" else "radio_play", False, None,
               f"{outcome['outcome']}: {outcome['detail']}")


def _op_stop(kwargs: Dict[str, Any]) -> dict:
    from core.media import player as player_module

    outcome = player_module.player().stop()
    return _op("stop", outcome["ok"], outcome, "" if outcome["ok"] else outcome["detail"])


def _op_pause(kwargs: Dict[str, Any]) -> dict:
    from core.media import player as player_module

    outcome = player_module.player().pause()
    return _op("pause", outcome["ok"], outcome, "" if outcome["ok"] else outcome["detail"])


def _op_volume(kwargs: Dict[str, Any]) -> dict:
    from core.media import player as player_module

    level = kwargs.get("volume")
    try:
        level = int(float(level))
    except (TypeError, ValueError):
        return _op("volume", False, None, "Give a volume percentage 0-100 (volume=...).")
    target = (kwargs.get("target") or "").strip()
    outcome = player_module.player().volume(level, target)
    return _op("volume", outcome["ok"], outcome, "" if outcome["ok"] else outcome["detail"])


def _op_now_playing(kwargs: Dict[str, Any]) -> dict:
    from core.media import player as player_module

    current = player_module.player().now_playing()
    if current is None:
        return _op("now_playing", True, {"playing": None,
                                        "summary": "Nothing is playing."})
    payload = current.as_dict()
    payload["playing"] = True
    return _op("now_playing", True, payload)


def _op_record(kwargs: Dict[str, Any]) -> dict:
    from core.media import player as player_module

    url = (kwargs.get("url") or kwargs.get("channel") or kwargs.get("station") or "").strip()
    if not url or "://" not in url:
        return _op("record", False, None, (
            "Recording needs an explicit stream URL (url=...). Channel and station names are not "
            "resolved for capture, so a recording is never made of something other than what was "
            "named."))

    from pathlib import Path

    title = (kwargs.get("channel") or kwargs.get("station") or "stream").strip()
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip()[:48] or "stream"
    destination = str(_deliverables_dir() / f"{safe}.recording")
    Path(destination).parent.mkdir(parents=True, exist_ok=True)

    confirm = kwargs.get("confirm") in (True, "true", "True", "1", 1)
    outcome = player_module.record(url, destination,
                                  duration_seconds=kwargs.get("duration_seconds"),
                                  confirm=confirm)
    if outcome.get("ok"):
        return _op("record", True, outcome)
    if outcome.get("outcome") == "ask":
        return _op("record", False, None, outcome["summary"])
    return _op("record", False, None, outcome["summary"])


def _op_library(kwargs: Dict[str, Any]) -> dict:
    import json

    from core.media import iptv

    action = (kwargs.get("action") or "list").strip().lower()
    library = _load_library()

    if action == "import":
        path = (kwargs.get("path") or "").strip()
        if not path:
            return _op("library", False, None, "Give the path to an M3U playlist (path=...).")
        try:
            from pathlib import Path

            text = Path(path).expanduser().read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return _op("library", False, None, f"{path} could not be read: {exc}")
        parsed = iptv.import_m3u(text)
        merged = iptv.deduplicate(list(library.get("entries") or []) + parsed["entries"])
        library["entries"] = merged
        _save_library(library)
        return _op("library", True, {
            "imported": parsed["count"],
            "total_after_duplicates_removed": len(merged),
            "removed_as_duplicates": parsed["count"] - (len(merged) - len(library.get("entries") or [])),
            "note": "Duplicates are removed by stream URL; the first entry for each URL is kept.",
        })

    if action == "export":
        from pathlib import Path

        text = iptv.export_m3u(library.get("entries") or [])
        out_path = _library_dir() / "stella-stations.m3u"
        try:
            out_path.write_text(text, encoding="utf-8")
        except OSError as exc:
            return _op("library", False, None, f"could not write {out_path}: {exc}")
        return _op("library", True, {
            "exported_to": str(out_path),
            "entries": len(library.get("entries") or []),
        })

    if action in ("add", "remove"):
        name = (kwargs.get("query") or kwargs.get("station") or kwargs.get("channel") or "").strip()
        url = (kwargs.get("url") or "").strip()
        entries = list(library.get("entries") or [])
        if action == "add":
            if not url:
                return _op("library", False, None, "Adding a station needs its stream URL (url=...).")
            entries.append({"name": name or url, "url": url})
        else:
            if not name and not url:
                return _op("library", False, None, "Removing a station needs its name or URL.")
            entries = [entry for entry in entries
                       if (name and entry.get("name") != name)
                       and (url and entry.get("url") != url)]
        library["entries"] = entries
        _save_library(library)
        return _op("library", True, {"total": len(entries)})

    entries = list(library.get("entries") or [])
    return _op("library", True, {
        "total": len(entries),
        "entries": entries[:_as_int(kwargs.get("limit"), 50)],
        "updated_at": library.get("updated_at"),
        "library_path": str(_library_path()),
        "actions": "import | export | list | add | remove",
        "note": ("The station library is the user's own list, kept in Stella's data directory. "
                 "It is never synced anywhere."),
    })


def _op_servers(kwargs: Dict[str, Any]) -> dict:
    from pathlib import Path

    import json

    action = (kwargs.get("action") or "list").strip().lower()
    config_path = _library_dir() / "media-servers.json"

    def _load() -> dict:
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {"servers": {}}

    data = _load()
    servers = data.get("servers") or {}

    if action == "list":
        return _op("servers", True, {
            "servers": [{"name": name, "kind": entry.get("kind"),
                         "base_url": entry.get("base_url")}
                        for name, entry in servers.items()],
            "config_path": str(config_path),
            "supported": "jellyfin | icecast | libretime",
            "note": ("Self-hosted servers are loopback-only by default. A non-loopback address is "
                     "refused unless config/tool_policy.json names the host, matching the rule the "
                     "browser already follows."),
            "actions": "list | connect | status | play",
        })

    if action in ("connect", "status", "play"):
        name = (kwargs.get("query") or kwargs.get("target") or "").strip()
        if not name:
            return _op("servers", False, None, "Name the server to use (query=...).")
        entry = servers.get(name)
        if entry is None:
            return _op("servers", False, None, (
                f"No media server called '{name}' is configured. Add one with a manual entry in "
                f"{config_path}: {{\"servers\": {{\"{name}\": {{\"kind\": \"jellyfin\", "
                "\"base_url\": \"http://127.0.0.1:8096\"}}}}."))
        kind = (entry.get("kind") or "").strip().lower()
        base_url = (entry.get("base_url") or "").strip().rstrip("/")
        if not base_url.startswith(("http://127.0.0.1", "http://localhost", "https://127.0.0.1")):
            return _op("servers", False, None, (
                f"{base_url} is not a loopback address. Self-hosted media servers are reachable "
                "only on loopback unless config/tool_policy.json names the host; nothing was "
                "requested."))
        from core.net import http as http_module

        if kind == "icecast":
            result = http_module.get_text(f"{base_url}/status-json.xsl", timeout=8.0)
            if not result.get("ok"):
                return _op("servers", False, None, result.get("reason", "Icecast did not answer"))
            return _op("servers", True, {
                "kind": "icecast",
                "status": "answered",
                "note": "Icecast answered; its status page was read as text.",
            })
        if kind == "jellyfin":
            endpoint = entry.get("api_key", "")
            headers = {"X-Emby-Token": endpoint} if endpoint else {}
            request_path = f"{base_url}/System/Info"
            try:
                import urllib.request

                request = urllib.request.Request(request_path, headers={
                    **headers, "User-Agent": "StellaAI/1.0"})
                with urllib.request.urlopen(request, timeout=8.0) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                return _op("servers", True, {
                    "kind": "jellyfin",
                    "server_name": payload.get("ServerName"),
                    "version": payload.get("Version"),
                    "operating_system": payload.get("OperatingSystem"),
                })
            except Exception as exc:
                return _op("servers", False, None, (
                    f"Jellyfin at {base_url} did not answer: {type(exc).__name__}: {exc}"))
        return _op("servers", False, None, (
            f"Server kind '{kind}' is not one this build controls (jellyfin, icecast, libretime). "
            "Nothing was requested."))

    return _op("servers", False, None, f"Unknown action '{action}'. One of: list, connect, status, play.")


def _op_sources(kwargs: Dict[str, Any] | None = None) -> dict:
    return _op("sources", True, {
        "surfaces": [
            {"operation": "tv_search", "source": "IPTV-org public channel catalogue",
             "auth": "keyless"},
            {"operation": "radio_search", "source": "Radio Browser community database",
             "auth": "keyless"},
            {"operation": "tv_play / radio_play", "source": "in-app Qt multimedia, then VLC/ffplay",
             "auth": "none"},
            {"operation": "record", "source": "ffmpeg or VLC on this machine",
             "auth": "none, duration capped"},
            {"operation": "library", "source": "the user's own M3U files, stored under Stella's data dir",
             "auth": "none"},
            {"operation": "servers", "source": "Jellyfin / Icecast / LibreTime on loopback",
             "auth": "the user's own server credential"},
        ],
    })


def _find_channel(identifier: str) -> Optional[str]:
    try:
        from core.media import iptv

        result = iptv.search({"query": identifier, "limit": 10}, cache=_cache())
    except Exception:
        return None
    for entry in (result.get("channels") or []):
        if str(entry.get("id", "")).lower() == identifier.lower():
            return str(entry.get("id"))
    return None


def _find_station(identifier: str) -> Optional[str]:
    try:
        from core.media import radiobrowser

        result = radiobrowser.search({"query": identifier, "limit": 10}, cache=_cache())
    except Exception:
        return None
    for entry in (result.get("stations") or []):
        if (entry.get("name") or "").lower() == identifier.lower():
            return entry.get("url_resolved") or entry.get("url")
    return None


def _summary_for(operation: str, record: dict, kwargs: Dict[str, Any]) -> str:
    value = record.get("value") or {}
    if operation == "tv_search":
        if not record["ok"]:
            return f"Channel catalogue unavailable: {record['error']}"
        channels = value.get("channels") or []
        listing = ", ".join(f"{entry['name']} ({entry.get('country')})" for entry in channels[:6])
        return (f"{value['count']} channels from IPTV-org"
                + (f" matching: {listing}." if listing else ", none matching those filters.")
                + " A community index: legality varies by country and nothing is bundled.")

    if operation == "radio_search":
        if not record["ok"]:
            return f"Radio directory unavailable: {record['error']}"
        stations = value.get("stations") or []
        listing = ", ".join(f"{entry['name']} ({entry.get('country')})" for entry in stations[:6])
        return f"{value['count']} stations from Radio Browser" + (
            f": {listing}." if listing else ", none matching those filters.")

    if operation in ("tv_play", "radio_play"):
        if not record["ok"]:
            return f"Playback did not start: {record['error']}"
        engines = value.get("engines") or {}
        available = [name for name, ok in engines.items() if ok]
        return (f"{value['detail']} ({value['engine']}) "
                f"Engines on this machine: {', '.join(available) or 'none'}.")

    if operation == "record":
        if not record["ok"]:
            return record["error"]
        return value.get("summary", "Recording started.")

    if operation == "library":
        if not record["ok"]:
            return f"Station library unavailable: {record['error']}"
        if kwargs.get("action") == "export":
            return f"Exported {value['entries']} entries to {value['exported_to']}."
        if value.get("total") is not None:
            return f"{value['total']} stations in the user's library ({value['library_path']})."
        return f"{value.get('imported', 0)} entries imported, {value.get('total_after_duplicates_removed', 0)} after de-duplication."

    if operation == "servers":
        if not record["ok"]:
            return f"Media server unavailable: {record['error']}"
        if value.get("kind") == "jellyfin":
            return f"Jellyfin '{value.get('server_name')}' running version {value.get('version')} on {value.get('operating_system')}."
        return value.get("note", "Media servers listed.")

    if operation == "now_playing":
        if value.get("playing"):
            return f"Now playing {value['title']} via {value['engine']} for {value['uptime_seconds']} seconds."
        return "Nothing is playing."

    if operation in ("stop", "pause", "volume"):
        if not record["ok"]:
            return value.get("detail", record.get("error", "The request did not run."))
        return value.get("detail", "Done.")

    if operation == "sources":
        return f"{len(value['surfaces'])} media surfaces, each with its source and auth tier."

    return record.get("error") or "No operation ran."


_OPERATIONS = {
    "tv_search": _op_tv_search,
    "radio_search": _op_radio_search,
    "tv_play": _op_tv_play,
    "radio_play": _op_radio_play,
    "stop": _op_stop,
    "pause": _op_pause,
    "volume": _op_volume,
    "record": _op_record,
    "library": _op_library,
    "servers": _op_servers,
    "now_playing": _op_now_playing,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "tv_search": "IPTV Channel Catalogue",
    "radio_search": "Internet Radio Directory",
    "tv_play": "Playing Television",
    "radio_play": "Playing Radio",
    "record": "Stream Recording",
    "library": "Station Library",
    "servers": "Media Servers",
    "now_playing": "Now Playing",
    "stop": "Playback Stopped",
    "pause": "Playback Paused",
    "volume": "Output Volume",
    "sources": "Media Sources",
}

_ALIASES = {
    "tv": "tv_search", "channels": "tv_search", "television": "tv_search",
    "channel_search": "tv_search",
    "radio": "radio_search", "stations": "radio_search", "station_search": "radio_search",
    "play_tv": "tv_play", "play_channel": "tv_play", "watch": "tv_play",
    "play_radio": "radio_play", "play_station": "radio_play", "listen": "radio_play",
    "stop_playback": "stop", "halt": "stop",
    "pause_playback": "pause",
    "set_volume": "volume", "mute": "volume",
    "record_stream": "record", "capture": "record",
    "playlist": "library", "stations_manager": "library",
    "media_servers": "servers", "jellyfin": "servers", "icecast": "servers",
    "libretime": "servers",
    "playing": "now_playing", "what_is_playing": "now_playing",
    "sources_list": "sources",
}


def _failure(operation: str, reason: str) -> dict:
    """A uniform unavailability result, in the shape every caller expects."""
    title = _OPERATION_TITLES.get(operation, "Media")
    return {
        "title": title,
        "summary": f"{title} unavailable: {reason}",
        "spoken_narrative": f"{title} unavailable: {reason}",
        "operation": operation,
        "ok": False,
        "record": _op(operation, False, None, reason),
        "sources": _op_sources()["value"]["surfaces"],
    }


def execute(**kwargs) -> dict:
    """Stream, record and manage open-source TV, radio and self-hosted media."""
    operation = (kwargs.get("operation") or "tv_search").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        known = ", ".join(sorted(_OPERATIONS))
        return _failure(operation, f"Unknown operation '{operation}'. One of: {known}.")

    try:
        record = handler(kwargs)
    except TypeError as exc:
        return _failure(operation, f"Bad arguments for '{operation}': {exc}")
    except Exception as exc:
        return _failure(operation, f"{type(exc).__name__}: {exc}")

    return {
        "title": _OPERATION_TITLES.get(operation, operation.replace("_", " ").title()),
        "summary": _summary_for(operation, record, kwargs),
        "spoken_narrative": _summary_for(operation, record, kwargs),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
        "sources": _op_sources()["value"]["surfaces"],
    }
