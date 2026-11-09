from __future__ import annotations
from typing import Any, Dict
import os, requests

FEATURE_METADATA = {"name":"news_summarizer","aliases":["news"],"description":"Fetch top headlines.","triggers":["news"],"parameters":{"type":"OBJECT","properties":{"country":{"type":"STRING","default":"us"},"limit":{"type":"INTEGER","default":5}},"required":[]}}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        # fallback to keyless public feed
        r = requests.get("https://api.currentsapi.services/v1/latest-news", params={"language":"en"}, timeout=20)
    else:
        country = params.get("country","us")
        limit = int(params.get("limit",5))
        r = requests.get("https://newsapi.org/v2/top-headlines", params={"country":country,"pageSize":limit,"apiKey":api_key}, timeout=20)
    try:
        r.raise_for_status()
        data = r.json()
        articles = data.get("articles") or data.get("news") or []
        return {"ok":True,"articles":[{"title":a.get("title"),"url":a.get("url")} for a in articles[:5]]}
    except Exception as e:
        return {"ok":False,"error":str(e)}