"""
top_performer_tracker — Track top gainers and losers across crypto markets via CoinGecko.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_track(kwargs: dict) -> dict:
    vs = kwargs.get("vs_currency", "usd")
    n = max(1, min(int(kwargs.get("top_n", 10)), 50))
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params_q = {
        "vs_currency": vs,
        "order": "price_change_percentage_24h_desc",
        "per_page": 250,
        "page": 1,
        "price_change_percentage": "24h",
    }
    try:
        r = requests.get(url, params=params_q, timeout=15)
        r.raise_for_status()
        data = r.json()
        filtered = [c for c in data if c.get("price_change_percentage_24h") is not None]
        gainers = sorted(filtered, key=lambda x: x.get("price_change_percentage_24h", -1e9), reverse=True)[:n]
        losers = sorted(filtered, key=lambda x: x.get("price_change_percentage_24h", 1e9))[:n]
        fmt = lambda c: {
            "id": c.get("id"),
            "symbol": c.get("symbol"),
            "name": c.get("name"),
            "price": c.get("current_price"),
            "change_24h": c.get("price_change_percentage_24h"),
        }
        return _op("track", True, {
            "vs_currency": vs,
            "gainers": [fmt(c) for c in gainers],
            "losers": [fmt(c) for c in losers],
        })
    except Exception as exc:
        return _op("track", False, None, f"Top performer tracking failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["api.coingecko.com"],
        "content": "Crypto market data from CoinGecko (api.coingecko.com). No API key required.",
    })


_OPERATIONS = {
    "track": _op_track,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "track": "Top Performers",
    "sources": "Performer Sources",
}

_ALIASES = {
    "top_performers": "track",
    "top_gainers": "track",
    "top_losers": "track",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "track":
        gainers = value.get("gainers") or []
        losers = value.get("losers") or []
        return f"Top gainer: {gainers[0].get('symbol')} ({gainers[0].get('change_24h')}%) — Top loser: {losers[0].get('symbol')} ({losers[0].get('change_24h')}%)"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Track top gainers and losers across crypto markets via CoinGecko."""
    operation = (kwargs.get("operation") or "track").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Top Performer Tracker",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Top Performer Tracker",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Top Performer Tracker",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Market error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Top Performer Tracker"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="track", top_n=5))