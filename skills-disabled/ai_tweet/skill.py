"""
ai_tweet — Generate a tweet using Stella's internal model router.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_generate(kwargs: dict) -> dict:
    prompt = (kwargs.get("prompt") or "").strip()
    if not prompt:
        return _op("generate", False, None, "Missing prompt.")
    endpoint = os.getenv("STELLA_MODEL_ENDPOINT", "http://localhost:8000/model/chat")
    try:
        r = requests.post(
            endpoint,
            json={"prompt": f"Write a concise tweet (<=280 chars) about: {prompt}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        tweet = data.get("response") or data.get("text") or str(data)
        tweet = tweet[:280]
        return _op("generate", True, {
            "prompt": prompt,
            "tweet": tweet,
            "chars": len(tweet),
        })
    except Exception as exc:
        return _op("generate", False, None, f"Failed to generate tweet: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["stella_model_endpoint"],
        "content": "Tweet generation via Stella internal model endpoint (STELLA_MODEL_ENDPOINT).",
    })


_OPERATIONS = {
    "generate": _op_generate,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "generate": "Generate Tweet",
    "sources": "Tweet Sources",
}

_ALIASES = {
    "tweet": "generate",
    "write_tweet": "generate",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "generate":
        return f"Tweet ({value.get('chars')} chars): {value.get('tweet')}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Generate a tweet using Stella's internal model router."""
    operation = (kwargs.get("operation") or "generate").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "AI Tweet",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "AI Tweet",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "AI Tweet",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Tweet error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "AI Tweet"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="generate", prompt="Stella AI assistant launch"))