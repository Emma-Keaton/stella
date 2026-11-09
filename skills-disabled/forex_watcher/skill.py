"""
forex_watcher — Watch forex rate movements via exchangerate.host.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_rate(kwargs: dict) -> dict:
    base = (kwargs.get("base") or "USD").strip().upper()
    symbols = (kwargs.get("symbols") or "EUR,GBP,JPY").strip().upper()
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    try:
        r = requests.get(
            "https://api.exchangerate.host/latest",
            params={"base": base, "symbols": ",".join(symbol_list)},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        rates = data.get("rates", {})
        return _op("rate", True, {
            "base": base,
            "symbols": symbol_list,
            "rates": rates,
            "date": data.get("date"),
            "content": f"Forex rates for {base}: " + ", ".join(f"{s}={rates.get(s)}" for s in symbol_list),
        })
    except Exception as exc:
        return _op("rate", False, None, f"Failed to fetch forex rates: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["exchangerate.host"],
        "content": "Forex rates powered by exchangerate.host. No API key required.",
    })


_OPERATIONS = {
    "rate": _op_rate,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "rate": "Forex Rates",
    "sources": "Forex Sources",
}

_ALIASES = {
    "quote": "rate",
    "rates": "rate",
    "currency": "rate",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "rate":
        rates = value.get("rates") or {}
        return f"{value.get('base')} rates: " + ", ".join(f"{k}={v}" for k, v in list(rates.items())[:5])
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Watch forex rate movements."""
    operation = (kwargs.get("operation") or "rate").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Forex Watcher",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Forex Watcher",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Forex Watcher",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Forex error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Forex Watcher"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="rate"))