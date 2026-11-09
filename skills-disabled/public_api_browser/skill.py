"""
public_api_browser — Browse the public APIs catalogue from public-apis.org.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import requests

_CACHE_PATH = Path(os.getenv("STELLA_DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data")) / "public_apis.json"


def _fetch() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        r = requests.get("https://api.publicapis.org/entries", timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {"entries": [], "count": 0}
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass
    return data


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_browse(kwargs: dict) -> dict:
    data = _fetch()
    entries = data.get("entries", [])
    cat = (kwargs.get("category") or "").strip()
    q = str(kwargs.get("q") or "").lower()
    filtered = [
        e for e in entries
        if (not cat or e.get("Category", "").lower() == cat.lower())
        and (not q or q in e.get("API", "").lower() or q in e.get("Description", "").lower())
    ]
    return _op("browse", True, {
        "count": len(filtered),
        "results": filtered[:50],
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["api.publicapis.org"],
        "content": "Public APIs catalogue from public-apis.org.",
    })


_OPERATIONS = {
    "browse": _op_browse,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "browse": "Public APIs",
    "sources": "API Sources",
}

_ALIASES = {
    "apis": "browse",
    "browse_apis": "browse",
    "list_apis": "browse",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "browse":
        return f"{value.get('count')} public API(s) found."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Browse the public APIs catalogue from public-apis.org."""
    operation = (kwargs.get("operation") or "browse").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Public API Browser",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Public API Browser",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Public API Browser",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"API error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Public API Browser"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="browse"))