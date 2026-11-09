"""
hummingbot_strategy_learn — Analyse backtest results and suggest strategy improvements.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_learn(kwargs: dict) -> dict:
    backtest = kwargs.get("backtest_result")
    strategy = (kwargs.get("strategy") or "").strip()
    if backtest is None or not strategy:
        return _op("learn", False, None, "Missing backtest_result or strategy.")
    prompt = (
        f"Given the following Hummingbot backtest output for strategy '{strategy}':\n"
        f"{json.dumps(backtest, indent=2)}\n"
        "Provide concrete suggestions to improve profitability, reduce drawdown, and adjust parameters."
    )
    model_endpoint = os.getenv("STELLA_MODEL_ENDPOINT", "http://localhost:8000/model/chat")
    try:
        r = requests.post(model_endpoint, json={"prompt": prompt}, timeout=60)
        r.raise_for_status()
        data = r.json()
        suggestion = data.get("response") or data.get("text") or str(data)
        return _op("learn", True, {
            "strategy": strategy,
            "suggestion": suggestion,
        })
    except Exception as exc:
        return _op("learn", False, None, f"Strategy learn failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["stella_model_endpoint"],
        "content": "Strategy improvement suggestions via Stella internal model endpoint (STELLA_MODEL_ENDPOINT).",
    })


_OPERATIONS = {
    "learn": _op_learn,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "learn": "Strategy Learn",
    "sources": "Strategy Sources",
}

_ALIASES = {
    "learn_strategy": "learn",
    "improve_strategy": "learn",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "learn":
        return f"Strategy '{value.get('strategy)}' — {value.get('suggestion') or ''}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Analyse backtest results and suggest strategy improvements."""
    operation = (kwargs.get("operation") or "learn").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Hummingbot Strategy Learn",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Hummingbot Strategy Learn",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Hummingbot Strategy Learn",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Strategy error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Hummingbot Strategy Learn"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))