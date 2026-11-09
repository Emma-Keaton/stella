"""
activity_suggester — Suggest a random activity from Bored API.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_suggest(kwargs: dict) -> dict:
    activity_type = (kwargs.get("type") or "").strip()
    url = "https://www.boredapi.com/api/activity"
    if activity_type:
        url += f"?type={activity_type}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        return _op("suggest", True, {
            "activity": data.get("activity"),
            "type": data.get("type"),
            "participants": data.get("participants"),
            "price": data.get("price"),
            "accessibility": data.get("accessibility"),
            "key": data.get("key"),
        })
    except Exception as exc:
        return _op("suggest", False, None, f"Failed to fetch activity: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["boredapi.com"],
        "content": "Activity suggestions powered by the Bored API (boredapi.com). No API key required.",
    })


_OPERATIONS = {
    "suggest": _op_suggest,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "suggest": "Activity Suggestion",
    "sources": "Activity Sources",
}

_ALIASES = {
    "get_activity": "suggest",
    "random_activity": "suggest",
    "activity": "suggest",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "suggest":
        return f"Activity: {value.get('activity')} ({value.get('type')}) — {value.get('participants')} participant(s)"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Suggest a random activity from the Bored API."""
    operation = (kwargs.get("operation") or "suggest").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Activity Suggester",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Activity Suggester",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Activity Suggester",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Activity error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Activity Suggester"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="suggest"))