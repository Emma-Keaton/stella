from __future__ import annotations
from typing import Any, Dict
import os, requests

FEATURE_METADATA = {"name":"gif_search","description":"GIF search.","triggers":["gif"],"parameters":{"type":"OBJECT","properties":{"q":{"type":"STRING"}},"required":["q"]}}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    q = params.get("q")
    api_key = os.getenv("TENOR_API_KEY","")
    url = f"https://tenor.googleapis.com/v2/search?q={q}&key={api_key}&limit=5"
    r = requests.get(url, timeout=15)
    if r.status_code!=200:
        return {"ok":False,"error":"tenor api key missing"}
    return {"ok":True,"results":r.json().get("results",[])}