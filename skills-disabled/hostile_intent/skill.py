"""
hostile_intent — Analyse text for hostile intent using Anthropic Claude.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_analyse(kwargs: dict) -> dict:
    text = (kwargs.get("text") or "").strip()
    if not text:
        return _op("analyse", False, None, "Missing text.")
    model = kwargs.get("model", "claude-3-5-sonnet-20241022")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _op("analyse", False, None, "ANTHROPIC_API_KEY not set.")
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Analyse the following text for hostile intent and return JSON "
                            "with risk_level (low/medium/high), indicators[], summary. "
                            f"Text: {text}"
                        ),
                    }
                ],
                "max_tokens": 500,
            },
            timeout=30,
        )
        r.raise_for_status()
        content = r.json()
        return _op("analyse", True, {
            "result": content,
            "source": "Anthropic",
            "text_length": len(text),
        })
    except Exception as exc:
        return _op("analyse", False, None, f"Hostile intent analysis failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["api.anthropic.com"],
        "content": "Hostile intent analysis via Anthropic Claude (ANTHROPIC_API_KEY required).",
    })


_OPERATIONS = {
    "analyse": _op_analyse,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "analyse": "Hostile Intent Analysis",
    "sources": "Threat Analysis Sources",
}

_ALIASES = {
    "hostile_intent": "analyse",
    "threat_analysis": "analyse",
    "analyse_text": "analyse",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "analyse":
        result = value.get("result") or {}
        return f"Hostile intent analysed ({value.get('text_length')} chars) — source: {value.get('source')}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Analyse text for hostile intent using Anthropic Claude."""
    operation = (kwargs.get("operation") or "analyse").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Hostile Intent",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Hostile Intent",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Hostile Intent",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Security error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Hostile Intent"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="analyse", text="This is a friendly message."))