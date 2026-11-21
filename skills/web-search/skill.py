"""Feature: web_search — Web search and research using DuckDuckGo HTML.
No API key required. Searches the web and returns structured results.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import re
import urllib.parse
import urllib.request

FEATURE_METADATA = {
    "name": "web_search",
    "aliases": ["web_search", "web_search_skill", "web_search_tool", "websearch", "search_web", "google_search", "duckduckgo", "search", "look_up", "find_online"],
    "description": "Search the web using DuckDuckGo HTML scraping. No API key required. Returns structured search results with titles, URLs, and snippets.",
    "triggers": ["search", "search web", "web search", "google", "duckduckgo", "look up", "find online", "search for", "search the web"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "enum": ["search", "sources"],
                "description": "One of: search | sources. Defaults to search.",
                "default": "search",
            },
            "query": {
                "type": "STRING",
                "description": "Search query string.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Number of results to return (default 10, max 50).",
                "default": 10,
            },
        },
        "required": ["query"],
    },
    "version": "1.0.0",
    "category": "research",
    "source": "stella",
    "active": True,
    "author": "Stella",
    "surface": "mobile",
    "notes": "Uses DuckDuckGo HTML scraping. No API key required. Respectful scraping.",
}

DDG_URL = "https://html.duckduckgo.com/html/"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def _op_result(title: str, summary: str, ok: bool, operation: str, data: Dict = None) -> Dict:
    return {
        "ok": ok,
        "summary": summary,
        "spoken_narrative": summary,
        "operation": operation,
        "record": data or {},
    }

def _fetch_ddg(query: str, max_results: int = 10) -> List[Dict]:
    params = {"q": query, "kl": "us-en"}
    url = DDG_URL + "?" + urllib.parse.urlencode(params)
    headers = _HEADERS
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        return [{"error": f"Fetch failed: {e}"}]

    results = []
    snippet_pattern = r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    snippet_text_pattern = r'<a class="result__snippet"[^>]*>([^<]*(?:<[^>]*>[^<]*)*)</a>'

    urls = re.findall(snippet_pattern, html)
    snippets = re.findall(snippet_text_pattern, html)

    for i, (url, title_snippet) in enumerate(zip(urls, snippets)):
        if i >= max_results:
            break
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        title = re.sub(r'<[^>]+>', '', title_snippet).strip()
        if url.startswith("//duckduckgo.com/l/?"):
            uddg_match = re.search(r'uddg=([^&]+)', url)
            if uddg_match:
                url = urllib.parse.unquote(uddg_match.group(1))
        results.append({
            "title": title or url,
            "url": url,
            "snippet": snippet,
        })

    return results

def _op_search(kwargs: dict) -> dict:
    query = kwargs.get("query", "")
    max_results = kwargs.get("limit", 10)
    if not query:
        return _op_result("Web Search", "Query is required", False, "search")
    results = _fetch_ddg(query, max_results)
    return _op_result(
        "Web Search",
        f"Found {len(results)} result(s) for '{query}'",
        True,
        "search",
        {"query": query, "results": results},
    )

def _op_sources(kwargs: dict) -> dict:
    return _op_result(
        "Web Search",
        "Web search via DuckDuckGo HTML scraping (keyless, no API key required).",
        True,
        "sources",
        {"sources": ["DuckDuckGo HTML"], "auth_tier": "keyless", "rate_limit": "Respectful scraping"},
    )

_OPERATIONS = {
    "search": _op_search,
    "sources": _op_sources,
}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "search").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Web Search",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown web search operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Web Search",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Web Search",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Web search error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Web Search"),
        "summary": record.get("summary", "Operation completed"),
        "spoken_narrative": record.get("summary", "Operation completed"),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record.get("record", {}),
    }

if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="search", query="Stella AI assistant", limit=3))