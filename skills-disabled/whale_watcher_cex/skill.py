"""
whale_watcher_cex — Watch large CEX trades via Binance public trade endpoint.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_watch(kwargs: dict) -> dict:
    symbol = (kwargs.get("symbol") or "BTCUSDT").strip().upper()
    min_usd = float(kwargs.get("min_usd", 50000))
    url = f"https://api.binance.com/api/v3/trades?symbol={symbol}&limit=100"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        trades = r.json()
        whales = []
        for t in trades:
            qty = float(t.get("qty", 0))
            price = float(t.get("price", 0))
            usd_val = qty * price
            if usd_val >= min_usd:
                whales.append({
                    "trade_id": t.get("id"),
                    "symbol": symbol,
                    "qty": qty,
                    "price": price,
                    "usd_value": usd_val,
                    "time": t.get("time"),
                })
        return _op("watch", True, {
            "symbol": symbol,
            "min_usd": min_usd,
            "whales": whales,
            "total": len(whales),
        })
    except Exception as exc:
        return _op("watch", False, None, f"CEX whale watch failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["api.binance.com"],
        "content": "CEX whale trades from Binance public API (api.binance.com). No API key required.",
    })


_OPERATIONS = {
    "watch": _op_watch,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "watch": "CEX Whale Watch",
    "sources": "Whale Sources",
}

_ALIASES = {
    "cex_whale": "watch",
    "watch_whales": "watch",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "watch":
        return f"{value.get('total')} whale trade(s) for {value.get('symbol')} (min ${value.get('min_usd')})."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Watch large CEX trades via Binance public trade endpoint."""
    operation = (kwargs.get("operation") or "watch").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "CEX Whale Watcher",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "CEX Whale Watcher",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "CEX Whale Watcher",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Whale error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "CEX Whale Watcher"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="watch", symbol="BTCUSDT", min_usd=50000))