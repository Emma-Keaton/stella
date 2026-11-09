"""
news_summarizer — Fetch top headlines and produce a short summary.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_headlines(kwargs: dict) -> dict:
    country = (kwargs.get("country") or "us").strip().lower()
    limit = max(1, min(int(kwargs.get("limit", 5)), 20))
    api_key = __import__("os").getenv("NEWS_API_KEY")
    try:
        if api_key:
            r = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={"country": country, "pageSize": limit, "apiKey": api_key},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            articles = data.get("articles", [])
        else:
            r = requests.get(
                "https://api.currentsapi.services/v1/latest-news",
                params={"language": "en", "country": country, "limit": limit},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
            articles = data.get("news", [])
        items = [
            {
                "title": a.get("title"),
                "source": (a.get("source") or {}).get("name") if isinstance(a.get("source"), dict) else a.get("source"),
                "url": a.get("url"),
            }
            for a in articles[:limit]
        ]
        return _op("headlines", True, {
            "country": country,
            "articles": items,
            "total": len(items),
        })
    except Exception as exc:
        return _op("headlines", False, None, f"Failed to fetch headlines: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["newsapi.org", "currentsapi.services"],
        "content": "Headlines from NewsAPI or Currents API. NewsAPI key optional.",
    })


_OPERATIONS = {
    "headlines": _op_headlines,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "headlines": "Top Headlines",
    "sources": "News Sources",
}

_ALIASES = {
    "news": "headlines",
    "top_news": "headlines",
    "headlines": "headlines",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "headlines":
        arts = value.get("articles") or []
        titles = "; ".join(a.get("title", "") for a in arts[:3])
        return f"{value.get('total')} headline(s): {titles}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Fetch top headlines and produce a short summary."""
    operation = (kwargs.get("operation") or "headlines").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "News Summarizer",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "News Summarizer",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "News Summarizer",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"News error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "News Summarizer"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="headlines"))