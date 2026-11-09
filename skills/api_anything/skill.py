"""
Feature: api_anything
Description: Wrap any website/app into an API using goodnight000/api-anything and Stella's browser.
"""

from __future__ import annotations
from typing import Any, Dict
import os, requests, json

FEATURE_METADATA = {
    "name": "api_anything",
    "aliases": ["api anything", "web api"],
    "description": "Turn any website/app into an API, poll/watch sites, social media, crypto platforms and marketplaces using browser automation.",
    "triggers": ["api anything", "watch website"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {"type": "STRING", "description": "Target URL to watch/interact"},
            "action": {"type": "STRING", "description": "fetch|poll|click|type|extract", "default": "fetch"},
            "selector": {"type": "STRING", "description": "CSS selector for extraction"},
            "poll_interval": {"type": "INTEGER", "description": "Seconds between polls", "default": 60}
        },
        "required": ["url"]
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    url = params.get("url")
    if not url:
        return {"ok": False, "error": "Missing url"}
    action = str(params.get("action","fetch"))
    # 1. Use Stella's browser service if available
    browser_endpoint = os.getenv("STELLA_BROWSER_ENDPOINT", "http://localhost:8001/browser")
    # 2. Fallback to api-anything local service
    api_any_endpoint = os.getenv("API_ANYTHING_ENDPOINT", "http://localhost:8002/api-anything")
    payload = {"url": url, "action": action, "selector": params.get("selector")}
    try:
        # Prefer browser automation
        r = requests.post(browser_endpoint, json=payload, timeout=60)
        if r.status_code == 200:
            return {"ok": True, "source": "stella_browser", "data": r.json()}
        # Fallback to api-anything
        r2 = requests.post(api_any_endpoint, json=payload, timeout=60)
        r2.raise_for_status()
        return {"ok": True, "source": "api_anything", "data": r2.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}