"""
feature/system_time - System time and timezone skills for Stella.

Provides timezone-aware time reporting, timezone conversion, and system
time inspection. Skills are self-describing and follow Stella's skill
contract (FEATURE_METADATA + execute(**kwargs)).

Design principles (from skills best practices):
- Keys never echoed back after saving (for any credential-related tools)
- Degrades gracefully when dependencies are missing
- Reports what can and cannot work so users can plan workarounds
"""

from __future__ import annotations

import datetime
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from zoneinfo import available_timezones, ZoneInfo
    _HAS_ZONEINFO = True
except Exception:  # pragma: no cover - Python < 3.9
    _HAS_ZONEINFO = False

FEATURE_METADATA = {
    "name": "system_time",
    "aliases": ["system_time", "time", "world_clock", "timezone", "current_time", "world_time"],
    "description": (
        "Get the current system time, convert between timezones, list "
        "available timezones, and perform timezone-aware time calculations. "
        "All operations are local and do not require network access."
    ),
    "triggers": [
        "time", "timezone", "current time", "world clock", "what time is it",
        "what time is it in", "convert time", "timezone conversion",
        "list timezones", "current datetime", "utc time", "local time",
    ],
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "One of: current_time, convert_timezone, list_timezones, system_info. Defaults to current_time.",
                "default": "current_time",
            },
            "timezone": {
                "type": "string",
                "description": "IANA timezone name (e.g. 'America/New_York', 'Europe/London', 'Asia/Tokyo', 'UTC'). Defaults to local timezone.",
            },
            "target_timezone": {
                "type": "string",
                "description": "Target IANA timezone for conversion (e.g. 'Asia/Tokyo'). Required for convert_timezone.",
            },
            "source_timezone": {
                "type": "string",
                "description": "Source IANA timezone (defaults to local timezone).",
            },
            "source_time": {
                "type": "string",
                "description": "Source time in ISO 8601 format (e.g. '2024-01-15T14:30:00'). Defaults to current time.",
            },
            "format": {
                "type": "string",
                "description": "Output format: 'iso', 'readable', 'rfc2822', 'timestamp'. Defaults to 'readable'.",
                "default": "readable",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "category": "system",
    "optional_dependencies": [],
}


def _format_time(dt: datetime.datetime, fmt: str) -> str:
    """Format a datetime according to the requested format style."""
    if fmt == "iso":
        return dt.isoformat()
    if fmt == "rfc2822":
        return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
    if fmt == "timestamp":
        return str(int(dt.timestamp()))
    # readable (default)
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def _resolve_tz(name: Optional[str]) -> Optional[object]:
    """Resolve a timezone name to a tzinfo object. Returns None on failure."""
    if not _HAS_ZONEINFO:
        return None
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        return None


def _resolve_source_tz(name: Optional[str]) -> Optional[object]:
    """Resolve source timezone, defaulting to local."""
    tz = _resolve_tz(name)
    if tz is not None:
        return tz
    return None  # caller will use local time


def execute(**kwargs: Any) -> Dict[str, Any]:
    """Execute a system_time operation.

    Supported operations:
      - current_time: Get current time in a timezone (default: local)
      - convert_timezone: Convert a time from source to target timezone
      - list_timezones: List available IANA timezone names
      - system_info: Get system time info (local, UTC, timezone, etc.)
    """
    operation = kwargs.get("operation", "current_time") or "current_time"

    if operation == "backends":
        return _op_backends()

    if operation == "current_time":
        return _op_current_time(kwargs)

    if operation == "convert_timezone":
        return _op_convert_timezone(kwargs)

    if operation == "list_timezones":
        return _op_list_timezones(kwargs)

    if operation == "system_info":
        return _op_system_info(kwargs)

    return _op_result("system_time", False, error=f"Unknown operation: {operation}")


def _op_result(operation: str, ok: bool, value: Any = None, error: Optional[str] = None) -> Dict[str, Any]:
    result = {"operation": operation, "ok": ok}
    if value is not None:
        result["value"] = value
    if error is not None:
        result["error"] = error
    return result


def _op_backends() -> Dict[str, Any]:
    """Report backend availability."""
    backends = {
        "zoneinfo": {
            "available": _HAS_ZONEINFO,
            "description": "IANA timezone database support",
        },
    }
    all_ok = all(b["available"] for b in backends.values())
    return {
        "operation": "backends",
        "ok": all_ok,
        "value": backends,
        "spoken_narrative": "Timezone support is available." if all_ok else "Timezone support is limited.",
    }


def _op_current_time(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    tz_name = kwargs.get("timezone") or "local"
    fmt = kwargs.get("format", "readable") or "readable"

    tz = _resolve_tz(tz_name) if tz_name != "local" else None
    if tz_name == "local":
        now = datetime.datetime.now()
    elif tz is not None:
        now = datetime.datetime.now(tz)
    else:
        # Fallback: try local, then UTC
        now = datetime.datetime.now()

    formatted = _format_time(now, fmt)
    return _op_result("current_time", True, value={
        "time": formatted,
        "timezone": str(now.tzinfo) if now.tzinfo else "local",
        "iso": now.isoformat(),
        "timestamp": int(now.timestamp()),
        "operation": "current_time",
    })


def _op_convert_timezone(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    source_tz_name = kwargs.get("source_timezone") or "local"
    target_tz_name = kwargs.get("target_timezone")
    if not target_tz_name:
        return _op_result("convert_timezone", False, error="target_timezone is required for convert_timezone")

    source_tz = None if source_tz_name == "local" else _resolve_tz(source_tz_name)
    target_tz = _resolve_tz(target_tz_name)
    if target_tz is None:
        return _op_result("convert_timezone", False, error=f"Unknown target timezone: {target_tz_name}")

    fmt = kwargs.get("format", "readable") or "readable"
    source_time_str = kwargs.get("source_time")

    if source_time_str:
        try:
            source_dt = datetime.datetime.fromisoformat(source_time_str)
        except ValueError:
            return _op_result("convert_timezone", False, error=f"Invalid source_time format: {source_time_str}. Use ISO 8601 (e.g. '2024-01-15T14:30:00').")
        if source_dt.tzinfo is None:
            if source_tz is not None:
                source_dt = source_dt.replace(tzinfo=source_tz)
            else:
                source_dt = source_dt.replace(tzinfo=datetime.timezone.utc)
    else:
        source_dt = datetime.datetime.now(source_tz if source_tz else datetime.timezone.utc)

    target_dt = source_dt.astimezone(target_tz)
    formatted = _format_time(target_dt, fmt)

    return _op_result("convert_timezone", True, value={
        "source_time": _format_time(source_dt, fmt),
        "source_timezone": str(source_dt.tzinfo) if source_dt.tzinfo else "local",
        "target_time": formatted,
        "target_timezone": str(target_dt.tzinfo),
        "iso": target_dt.isoformat(),
        "timestamp": int(target_dt.timestamp()),
        "operation": "convert_timezone",
    })


def _op_list_timezones(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    if not _HAS_ZONEINFO:
        return _op_result("list_timezones", False, error="ZoneInfo not available on this Python version")

    filter_str = kwargs.get("filter", "") or ""
    all_zones = sorted(available_timezones())
    if filter_str:
        f = filter_str.lower()
        all_zones = [z for z in all_zones if f in z.lower()]

    return _op_result("list_timezones", True, value={
        "timezones": all_zones,
        "count": len(all_zones),
        "filter": filter_str or None,
        "operation": "list_timezones",
    })


def _op_system_info(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.datetime.now()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    local_tz = None
    try:
        from zoneinfo import ZoneInfo
        local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    except Exception:
        pass

    return _op_result("system_info", True, value={
        "local_time": now.isoformat(),
        "utc_time": now_utc.isoformat(),
        "local_timezone": str(local_tz) if local_tz else "unknown",
        "utc_offset_seconds": int(now_utc.utcoffset().total_seconds()) if now_utc.utcoffset() else 0,
        "timezone_available": _HAS_ZONEINFO,
        "operation": "system_info",
    })
