"""
whale_watcher_dex — Watch large DEX swaps via DexScreener API.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_watch(kwargs: dict) -> dict:
    chain = (kwargs.get("chain") or "ethereum").strip().lower()
    min_usd = float(kwargs.get("min_usd", 100000))
    url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs", [])
        whales = []
        for p in pairs:
            volume_usd = float((p.get("volume") or {}).get("h24", 0))
            if volume_usd >= min_usd:
                whales.append({
                    "pair": p.get("pairAddress"),
                    "baseToken": (p.get("baseToken") or {}).get("symbol"),
                    "quoteToken": (p.get("quoteToken") or {}).get("symbol"),
                    "volume_usd": volume_usd,
                    "priceUsd": p.get("priceUsd"),
                })
        return _op("watch", True, {
            "chain": chain,
            "min_usd": min_usd,
            "whales": whales,
            "total": len(whales),
        })
    except Exception as exc:
        return _op("watch", False, None, f"DEX whale watch failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["api.dexscreener.com"],
        "content": "DEX whale swaps from DexScreener (api.dexscreener.com). No API key required.",
    })


_OPERATIONS = {
    "watch": _op_watch,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "watch": "DEX Whale Watch",
    "sources": "Whale Sources",
}

_ALIASES = {
    "dex_whale": "watch",
    "watch_whales": "watch",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "watch":
        return f"{value.get('total')} whale swap(s) on {value.get('chain')} (min ${value.get('min_usd')})."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Watch large DEX swaps via DexScreener API."""
    operation = (kwargs.get("operation") or "watch").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "DEX Whale Watcher",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "DEX Whale Watcher",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "DEX Whale Watcher",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Whale error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "DEX Whale Watcher"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="watch", chain="ethereum", min_usd=100000))