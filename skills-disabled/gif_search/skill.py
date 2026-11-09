"""
gif_search — Search Tenor for GIFs.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_search(kwargs: dict) -> dict:
    q = (kwargs.get("q") or "").strip()
    if not q:
        return _op("search", False, None, "Missing search query 'q'.")
    api_key = os.getenv("TENOR_API_KEY", "")
    try:
        r = requests.get(
            "https://tenor.googleapis.com/v2/search",
            params={"q": q, "key": api_key, "limit": 5},
            timeout=15,
        )
        if r.status_code != 200:
            return _op("search", False, None, f"Tenor API returned {r.status_code} (API key may be missing).")
        data = r.json()
        results = data.get("results", [])
        items = []
        for item in results:
            media = item.get("media", [])
            gif_url = ""
            if media and isinstance(media, list) and len(media) > 0:
                gif_url = media[0].get("gif", {}).get("url", "")
            items.append({
                "title": item.get("content_description", ""),
                "url": item.get("url", ""),
                "gif_url": gif_url,
            })
        return _op("search", True, {
            "query": q,
            "results": items,
            "total": len(items),
        })
    except Exception as exc:
        return _op("search", False, None, f"GIF search failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["tenor.googleapis.com"],
        "content": "GIF search via Tenor API. TENOR_API_KEY required.",
    })


_OPERATIONS = {
    "search": _op_search,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "search": "GIF Search",
    "sources": "GIF Sources",
}

_ALIASES = {
    "gif": "search",
    "search_gif": "search",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "search":
        return f"{value.get('total')} GIF(s) for '{value.get('query')}'"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Search Tenor for GIFs."""
    operation = (kwargs.get("operation") or "search").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "GIF Search",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "GIF Search",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "GIF Search",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"GIF error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "GIF Search"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="search", q="hello"))