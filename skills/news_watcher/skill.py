"""
news_watcher — Fetch latest crypto/forex news headlines.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_headlines(kwargs: dict) -> dict:
    category = (kwargs.get("category") or "crypto").strip().lower()
    limit = max(1, min(int(kwargs.get("limit", 10)), 50))
    api_key = os.getenv("NEWS_API_KEY")
    try:
        if api_key:
            url = "https://newsapi.org/v2/top-headlines"
            params_q = {
                "category": "technology" if category == "crypto" else category,
                "pageSize": limit,
                "apiKey": api_key,
            }
        else:
            url = "https://cryptopanic.com/api/v1/posts/"
            params_q = {"public": "true", "filter": "hot", "limit": limit}
        r = requests.get(url, params=params_q, timeout=15)
        r.raise_for_status()
        data = r.json()
        articles = data.get("articles") or data.get("results") or []
        headlines = []
        for a in articles[:limit]:
            headlines.append({
                "title": a.get("title"),
                "url": a.get("url") or a.get("link"),
                "source": (
                    (a.get("source") or {}).get("name")
                    if isinstance(a.get("source"), dict)
                    else a.get("domain")
                ),
                "published_at": a.get("publishedAt") or a.get("published_at"),
            })
        return _op("headlines", True, {
            "category": category,
            "headlines": headlines,
            "total": len(headlines),
        })
    except Exception as exc:
        return _op("headlines", False, None, f"News watcher failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["newsapi.org", "cryptopanic.com"],
        "content": "News headlines from NewsAPI (key optional) or CryptoPanic public feed.",
    })


_OPERATIONS = {
    "headlines": _op_headlines,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "headlines": "News Watcher",
    "sources": "News Sources",
}

_ALIASES = {
    "news": "headlines",
    "top_news": "headlines",
    "crypto_news": "headlines",
    "forex_news": "headlines",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "headlines":
        heads = value.get("headlines") or []
        titles = "; ".join(h.get("title", "") for h in heads[:3])
        return f"{value.get('total')} {value.get('category')} headline(s): {titles}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Fetch latest crypto/forex news headlines."""
    operation = (kwargs.get("operation") or "headlines").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "News Watcher",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "News Watcher",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "News Watcher",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"News error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "News Watcher"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="headlines", category="crypto", limit=5))