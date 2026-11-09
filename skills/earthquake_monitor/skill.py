"""
earthquake_monitor — Fetch recent earthquake data from USGS.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_recent(kwargs: dict) -> dict:
    limit = max(1, min(int(kwargs.get("limit", 10)), 50))
    try:
        r = requests.get(
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            params={"format": "geojson", "limit": limit, "orderby": "time"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        events = []
        for f in data.get("features", []):
            p = f.get("properties", {})
            events.append({
                "id": f.get("id"),
                "place": p.get("place"),
                "magnitude": p.get("mag"),
                "time": p.get("time"),
                "url": p.get("url"),
            })
        return _op("recent", True, {
            "events": events,
            "total": len(events),
        })
    except Exception as exc:
        return _op("recent", False, None, f"Earthquake fetch failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["earthquake.usgs.gov"],
        "content": "Earthquake data from USGS (earthquake.usgs.gov). No API key required.",
    })


_OPERATIONS = {
    "recent": _op_recent,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "recent": "Recent Earthquakes",
    "sources": "Earthquake Sources",
}

_ALIASES = {
    "earthquake": "recent",
    "recent_earthquakes": "recent",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "recent":
        return f"{value.get('total')} recent earthquake(s)."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Fetch recent earthquake data from USGS."""
    operation = (kwargs.get("operation") or "recent").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Earthquake Monitor",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Earthquake Monitor",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Earthquake Monitor",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Earthquake error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Earthquake Monitor"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="recent", limit=5))