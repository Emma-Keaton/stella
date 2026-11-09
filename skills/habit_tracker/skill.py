"""
habit_tracker — Create, log and query habits stored locally.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict

_DATA_PATH = Path(os.getenv("STELLA_DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data")) / "habits.json"


def _load() -> dict:
    if not _DATA_PATH.exists():
        return {}
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DATA_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_create(kwargs: dict) -> dict:
    name = (kwargs.get("name") or "").strip()
    if not name:
        return _op("create", False, None, "Habit name required.")
    data = _load()
    if name in data:
        return _op("create", False, None, f"Habit '{name}' already exists.")
    data[name] = {"created": date.today().isoformat(), "logs": []}
    _save(data)
    return _op("create", True, {"habit": name, "total": len(data)})


def _op_log(kwargs: dict) -> dict:
    name = (kwargs.get("name") or "").strip()
    if not name:
        return _op("log", False, None, "Habit name required.")
    data = _load()
    if name not in data:
        return _op("log", False, None, f"Habit '{name}' not found.")
    today = date.today().isoformat()
    if today not in data[name]["logs"]:
        data[name]["logs"].append(today)
    _save(data)
    return _op("log", True, {"habit": name, "logs": data[name]["logs"]})


def _op_list(kwargs: dict) -> dict:
    data = _load()
    return _op("list", True, {"habits": list(data.keys()), "total": len(data)})


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["local_json"],
        "content": "Habits stored locally in habits.json.",
    })


_OPERATIONS = {
    "create": _op_create,
    "log": _op_log,
    "list": _op_list,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "create": "Create Habit",
    "log": "Log Habit",
    "list": "List Habits",
    "sources": "Habit Sources",
}

_ALIASES = {
    "add_habit": "create",
    "new_habit": "create",
    "track_habit": "log",
    "log_habit": "log",
    "list_habits": "list",
    "get_habits": "list",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "create":
        return f"Created habit '{value.get('habit')}' — total: {value.get('total')}"
    if operation == "log":
        return f"Logged '{value.get('habit')}' — {len(value.get('logs') or [])} entry(ies)"
    if operation == "list":
        return f"{value.get('total')} habit(s): {', '.join(value.get('habits') or [])}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Create, log and query habits stored locally."""
    operation = (kwargs.get("operation") or "list").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Habit Tracker",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Habit Tracker",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Habit Tracker",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Habit error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Habit Tracker"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="list"))