"""
lead_finder — Find leads via public profiles using browser automation.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests
import urllib.parse


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_find(kwargs: dict) -> dict:
    query = (kwargs.get("query") or "").strip()
    if not query:
        return _op("find", False, None, "Missing query parameter.")
    max_results = max(1, min(int(kwargs.get("max_results", 10)), 50))
    browser_endpoint = os.getenv("STELLA_BROWSER_ENDPOINT", "http://localhost:8001/browser")
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    payload = {
        "url": search_url,
        "action": "extract",
        "selector": "div.g a",
    }
    try:
        r = requests.post(browser_endpoint, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        links = data.get("links", [])
        leads = []
        for link in links[:max_results]:
            leads.append({
                "title": link.get("text"),
                "url": link.get("href"),
            })
        return _op("find", True, {
            "query": query,
            "leads": leads,
            "total": len(leads),
        })
    except Exception as exc:
        return _op("find", False, None, f"Lead finder failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["stella_browser_endpoint", "google.com"],
        "content": "Lead finding via Stella browser endpoint (STELLA_BROWSER_ENDPOINT) and public search results.",
    })


_OPERATIONS = {
    "find": _op_find,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "find": "Find Leads",
    "sources": "Lead Sources",
}

_ALIASES = {
    "find_leads": "find",
    "find_lead": "find",
    "search_leads": "find",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "find":
        return f"{value.get('total')} lead(s) for '{value.get('query')}'"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Find leads via public profiles using browser automation."""
    operation = (kwargs.get("operation") or "find").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Lead Finder",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Lead Finder",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Lead Finder",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Lead error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Lead Finder"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="find", query="software engineers hiring"))