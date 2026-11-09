"""
polymarket_watcher — Watch Polymarket prediction markets for significant price moves.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_watch(kwargs: dict) -> dict:
    keyword = (kwargs.get("keyword") or "").strip().lower()
    min_volume = float(kwargs.get("min_volume", 10000))
    url = "https://gamma-api.polymarket.com/markets"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        markets = r.json()
        alerts = []
        for m in markets:
            vol = float(m.get("volume24h", 0) or 0)
            if vol >= min_volume and (keyword in (m.get("question") or "").lower()):
                alerts.append({
                    "id": m.get("id"),
                    "question": m.get("question"),
                    "volume24h": vol,
                    "yes_price": m.get("yesPrice"),
                    "no_price": m.get("noPrice"),
                })
        return _op("watch", True, {
            "keyword": keyword,
            "min_volume": min_volume,
            "alerts": alerts,
            "total": len(alerts),
        })
    except Exception as exc:
        return _op("watch", False, None, f"Polymarket watch failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["gamma-api.polymarket.com"],
        "content": "Prediction markets from Polymarket (gamma-api.polymarket.com).",
    })


_OPERATIONS = {
    "watch": _op_watch,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "watch": "Polymarket Watch",
    "sources": "Polymarket Sources",
}

_ALIASES = {
    "polymarket": "watch",
    "watch_markets": "watch",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "watch":
        return f"{value.get('total')} Polymarket market(s) match (min_volume={value.get('min_volume')})."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Watch Polymarket prediction markets for significant price moves."""
    operation = (kwargs.get("operation") or "watch").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Polymarket Watcher",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Polymarket Watcher",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Polymarket Watcher",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Polymarket error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Polymarket Watcher"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="watch", min_volume=10000))