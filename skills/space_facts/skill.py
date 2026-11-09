"""
space_facts — Fetch NASA Astronomy Picture of the Day (APOD).
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_apod(kwargs: dict) -> dict:
    apod_date = (kwargs.get("date") or "").strip()
    try:
        params = {"api_key": "DEMO_KEY"}
        if apod_date:
            params["date"] = apod_date
        r = requests.get("https://api.nasa.gov/planetary/apod", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        return _op("apod", True, {
            "title": data.get("title"),
            "url": data.get("url"),
            "explanation": data.get("explanation"),
            "date": data.get("date"),
        })
    except Exception as exc:
        return _op("apod", False, None, f"APOD fetch failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["api.nasa.gov"],
        "content": "Astronomy Picture of the Day from NASA API (api.nasa.gov). DEMO_KEY used; no registration required.",
    })


_OPERATIONS = {
    "apod": _op_apod,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "apod": "NASA APOD",
    "sources": "Space Sources",
}

_ALIASES = {
    "apod": "apod",
    "space": "apod",
    "astronomy": "apod",
    "nasa": "apod",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "apod":
        return f"{value.get('title')} ({value.get('date')}) — {value.get('explanation') or ''}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Fetch NASA Astronomy Picture of the Day (APOD)."""
    operation = (kwargs.get("operation") or "apod").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Space Facts",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Space Facts",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Space Facts",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Space error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Space Facts"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="apod"))