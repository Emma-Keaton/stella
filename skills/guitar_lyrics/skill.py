from __future__ import annotations
from typing import Any, Dict
import requests

FEATURE_METADATA = {"name":"guitar_lyrics","description":"Lyrics search.","triggers":["lyrics"],"parameters":{"type":"OBJECT","properties":{"artist":{"type":"STRING"},"title":{"type":"STRING"}},"required":["artist","title"]}}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    # Genius search is keyed; use public lyrics API as fallback
    artist = params.get("artist")
    title = params.get("title")
    url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
    r = requests.get(url, timeout=15)
    if r.status_code==200:
        return {"ok":True,"lyrics":r.json().get("lyrics")}
    return {"ok":False,"error":"not found"}