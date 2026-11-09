"""
Feature: api_anything
Description: Wrap any website/app into an API using goodnight000/api-anything and Stella's browser.
"""

from __future__ import annotations
from typing import Any, Dict
import os, requests, json

FEATURE_METADATA = {
    "name": "api_anything",
    "aliases": ["api anything", "web api"],
    "description": "Turn any website/app into an API, poll/watch sites, social media, crypto platforms and marketplaces using browser automation.",
    "triggers": ["api anything", "watch website"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "Target URL to watch/interact"},
            "action": {"type": "STRING", "description": "fetch|poll|click|type|extract", "default": "fetch"},
            "selector": {"type": "STRING", "description": "CSS selector for extraction"},
            "poll_interval": {"type": "INTEGER", "description": "Seconds between polls", "default": 60}
        },
        "required": ["url"]
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    url = params.get("url")
    if not url:
        return {"ok": False, "error": "Missing url"}
    action = str(params.get("action","fetch"))
    # 1. Use Stella's browser service if available
    browser_endpoint = os.getenv("STELLA_BROWSER_ENDPOINT", "http://localhost:8001/browser")
    # 2. Fallback to api-anything local service
    api_any_endpoint = os.getenv("API_ANYTHING_ENDPOINT", "http://localhost:8002/api-anything")
    payload = {"url": url, "action": action, "selector": params.get("selector")}
    try:
        # Prefer browser automation
        r = requests.post(browser_endpoint, json=payload, timeout=60)
        if r.status_code == 200:
            return {"ok": True, "source": "stella_browser", "data": r.json()}
        # Fallback to api-anything
        r2 = requests.post(api_any_endpoint, json=payload, timeout=60)
        r2.raise_for_status()
        return {"ok": True, "source": "api_anything", "data": r2.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_fetch(kwargs: dict) -> dict:
    return run(kwargs)


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["stella_browser", "api_anything"],
        "content": "API anything via Stella browser endpoint or api-anything service.",
    })


_OPERATIONS = {
    "fetch": _op_fetch,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "fetch": "API Anything Fetch",
    "sources": "API Anything Sources",
}

_ALIASES = {
    "fetch": "fetch",
    "watch": "fetch",
    "poll": "fetch",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    if operation == "sources":
        return f"{len(record.get('value', {}).get('sources') or [])} source(s)"
    return record.get("error") or "Operation complete."


def execute(**kwargs) -> dict:
    """Turn any website/app into an API using browser automation."""
    operation = (kwargs.get("operation") or "fetch").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "API Anything",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "API Anything",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "API Anything",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"API error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "API Anything"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))