"""
writing_skills — Writing assistance: draft emails, messages, summaries, and creative content.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_draft(kwargs: dict) -> dict:
    prompt = (kwargs.get("prompt") or "").strip()
    if not prompt:
        return _op("draft", False, None, "Missing prompt.")
    format_type = (kwargs.get("format") or "text").strip().lower()
    model_endpoint = os.getenv("STELLA_MODEL_ENDPOINT", "http://localhost:8000/model/chat")
    try:
        r = requests.post(
            model_endpoint,
            json={"prompt": f"Write a {format_type} about: {prompt}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        content = data.get("response") or data.get("text") or str(data)
        return _op("draft", True, {
            "prompt": prompt,
            "format": format_type,
            "content": content,
        })
    except Exception as exc:
        return _op("draft", False, None, f"Drafting failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["stella_model_endpoint"],
        "content": "Writing assistance via Stella internal model endpoint (STELLA_MODEL_ENDPOINT).",
    })


_OPERATIONS = {
    "draft": _op_draft,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "draft": "Draft Content",
    "sources": "Writing Sources",
}

_ALIASES = {
    "write": "draft",
    "draft_content": "draft",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "draft":
        return f"Drafted {value.get('format')} content ({len(value.get('content') or '')} chars)."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Writing assistance: draft emails, messages, summaries, and creative content."""
    operation = (kwargs.get("operation") or "draft").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Writing Skills",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Writing Skills",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Writing Skills",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Writing error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Writing Skills"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="draft", prompt="Welcome email for new users", format="email"))