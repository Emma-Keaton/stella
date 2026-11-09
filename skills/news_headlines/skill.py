from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional, List

FEATURE_METADATA = {
    "name": "news_headlines",
    "aliases": [
        "news_headlines", "news", "headlines", "top news",
        "breaking news", "latest news", "news summary",
        "world news", "technology news", "business news",
    ],
    "description": (
        "Live news headlines from multiple sources using free RSS feeds "
        "(no API key required). Aggregates top stories from major news "
        "outlets with categorization by topic and source attribution."
    ),
    "triggers": [
        "news", "headlines", "top news", "breaking news", "latest news",
        "news summary", "world news", "technology news", "business news",
        "what's happening", "current events",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: top | category | sources. Defaults to top.",
            },
            "category": {
                "type": "STRING",
                "description": "News category: world, technology, business, science, health, sports, entertainment.",
            },
            "source": {
                "type": "STRING",
                "description": "Specific news source name.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum number of headlines to return (default 10, max 30).",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": [],
}

API_SOURCES = {
    "rss_feeds": {
        "name": "RSS Feeds (Various)",
        "description": "Free RSS news feeds from major outlets",
        "url": "various",
        "docs": "https://en.wikipedia.org/wiki/RSS",
        "auth_tier": "keyless",
        "rate_limit": "Varies by source",
        "uses": ["top", "category", "sources"],
    },
}

_RATE_LIMIT = 1.0
_last_call = 0.0

NEWS_FEEDS = {
    "top": [
        ("BBC News", "http://feeds.bbci.co.uk/news/rss.xml"),
        ("Reuters", "http://feeds.reuters.com/reuters/topNews"),
        ("AP News", "https://feeds.apnews.com/rss/ap/topnews"),
    ],
    "technology": [
        ("TechCrunch", "http://feeds.feedburner.com/TechCrunch/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Wired", "https://www.wired.com/feed/rss"),
    ],
    "business": [
        ("Reuters Business", "http://feeds.reuters.com/reuters/businessNews"),
        ("Bloomberg", "https://feeds.bloomberg.com/markets/news"),
        ("Financial Times", "https://www.ft.com/rss/home"),
    ],
    "science": [
        ("Reuters Science", "http://feeds.reuters.com/reuters/scienceNews"),
        ("BBC Science", "http://feeds.bbci.co.uk/news/science/rss.xml"),
        ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ],
    "health": [
        ("Reuters Health", "http://feeds.reuters.com/reuters/healthNews"),
        ("BBC Health", "http://feeds.bbci.co.uk/news/health/rss.xml"),
    ],
    "sports": [
        ("BBC Sport", "http://feeds.bbci.co.uk/sport/rss.xml"),
        ("Reuters Sports", "http://feeds.reuters.com/reuters/sportsNews"),
    ],
}
_RATE_LIMIT = 1.0
_last_call = 0.0


def _throttle() -> None:
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < _RATE_LIMIT:
        time.sleep(_RATE_LIMIT - elapsed)
    _last_call = time.time()


def _http_get_xml(url: str, timeout: int = 15) -> Optional[ET.Element]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Stella-AI/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return ET.parse(resp).getroot()
    except Exception:
        return None


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _parse_rss_feed(root: ET.Element, source_name: str) -> List[Dict[str, str]]:
    items = []
    channel = root.find("channel")
    if channel is None:
        return items
    for item in channel.findall("item")[:10]:
        title = item.find("title")
        link = item.find("link")
        desc = item.find("description")
        pub_date = item.find("pubDate")
        items.append({
            "title": title.text.strip() if title is not None and title.text else "",
            "link": link.text.strip() if link is not None and link.text else "",
            "description": desc.text.strip()[:200] if desc is not None and desc.text else "",
            "pub_date": pub_date.text.strip() if pub_date is not None and pub_date.text else "",
            "source": source_name,
        })
    return items


def _op_top(kwargs: dict) -> dict:
    limit = int(kwargs.get("limit") or 10)
    limit = max(1, min(limit, 30))
    all_items = []
    for source_name, feed_url in NEWS_FEEDS["top"]:
        root = _http_get_xml(feed_url)
        if root is None:
            continue
        items = _parse_rss_feed(root, source_name)
        all_items.extend(items)
    all_items = all_items[:limit]
    content_lines = [f"Top News Headlines ({len(all_items)} stories):"]
    for i, item in enumerate(all_items, 1):
        content_lines.append(f"  {i}. {item['title']} [{item['source']}]")
    content = "\n".join(content_lines)
    return _op("top", True, {
        "headlines": all_items,
        "count": len(all_items),
        "content": content,
    })


def _op_category(kwargs: dict) -> dict:
    category = (kwargs.get("category") or "top").lower()
    limit = int(kwargs.get("limit") or 10)
    limit = max(1, min(limit, 30))
    if category not in NEWS_FEEDS:
        return _op("category", False, None, f"Unknown category '{category}'. Available: {', '.join(NEWS_FEEDS.keys())}")
    all_items = []
    for source_name, feed_url in NEWS_FEEDS[category]:
        root = _http_get_xml(feed_url)
        if root is None:
            continue
        items = _parse_rss_feed(root, source_name)
        all_items.extend(items)
    all_items = all_items[:limit]
    content_lines = [f"{category.title()} News ({len(all_items)} stories):"]
    for i, item in enumerate(all_items, 1):
        content_lines.append(f"  {i}. {item['title']} [{item['source']}]")
    content = "\n".join(content_lines)
    return _op("category", True, {
        "category": category,
        "headlines": all_items,
        "count": len(all_items),
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "news_headlines (Stella news headlines skill)",
        "dependencies": [],
        "operations": ["top", "category", "sources"],
        "apis": API_SOURCES,
        "note": "News headlines via free RSS feeds (keyless, no API key required).",
        "categories": list(NEWS_FEEDS.keys()),
    })


_OPERATIONS = {
    "sources": _op_sources,
    "top": _op_top,
    "category": _op_category,
}

_OPERATION_TITLES = {
    "sources": "News Sources",
    "top": "Top News Headlines",
    "category": "Category News",
}


def execute(**kwargs) -> dict:
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "News Headlines",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "News Headlines",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"News error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "News Headlines"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
