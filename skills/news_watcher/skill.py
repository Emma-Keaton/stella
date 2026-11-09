from __future__ import annotations
from typing import Any, Dict
import os, requests

FEATURE_METADATA = {
    "name": "news_watcher",
    "description": "Fetch latest crypto/forex news headlines.",
    "triggers": ["news"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "category": {"type": "STRING", "description": "News category: crypto, forex, general", "default": "crypto"},
            "limit": {"type": "INTEGER", "default": 10}
        },
        "required": []
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    category = params.get("category", "crypto")
    limit = int(params.get("limit", 10))
    api_key = os.getenv("NEWS_API_KEY")
    try:
        if api_key:
            url = "https://newsapi.org/v2/top-headlines"
            params_q = {"category": "technology" if category=="crypto" else category, "pageSize": limit, "apiKey": api_key}
        else:
            # fallback CryptoPanic public
            url = "https://cryptopanic.com/api/v1/posts/"
            params_q = {"public": "true", "filter": "hot", "limit": limit}
        r = requests.get(url, params=params_q, timeout=15)
        r.raise_for_status()
        data = r.json()
        articles = data.get("articles") or data.get("results") or []
        headlines = []
        for a in articles[:limit]:
            headlines.append({
                "title": a.get("title") or a.get("title"),
                "url": a.get("url") or a.get("link"),
                "source": a.get("source", {}).get("name") if isinstance(a.get("source"), dict) else a.get("domain"),
                "published_at": a.get("publishedAt") or a.get("published_at")
            })
        return {"ok": True, "category": category, "headlines": headlines}
    except Exception as e:
        return {"ok": False, "error": str(e)}