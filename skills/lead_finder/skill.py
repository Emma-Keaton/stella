from __future__ import annotations
from typing import Any, Dict
import os, requests, urllib.parse

FEATURE_METADATA = {
    "name": "lead_finder",
    "description": "Find leads via public profiles using browser automation.",
    "triggers": ["find leads"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Search query for leads"},
            "max_results": {"type": "INTEGER", "description": "Maximum number of leads", "default": 10}
        },
        "required": ["query"]
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get("query")
    max_results = int(params.get("max_results", 10))
    if not query:
        return {"ok": False, "error": "Missing query parameter"}
    browser_endpoint = os.getenv("STELLA_BROWSER_ENDPOINT", "http://localhost:8001/browser")
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    payload = {
        "url": search_url,
        "action": "extract",
        "selector": "div.g a"
    }
    try:
        r = requests.post(browser_endpoint, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        links = data.get("links", [])
        leads = []
        for link in links[:max_results]:
            leads.append({
                "title": link.get("text"),
                "url": link.get("href")
            })
        return {"ok": True, "leads": leads}
    except Exception as e:
        return {"ok": False, "error": str(e)}