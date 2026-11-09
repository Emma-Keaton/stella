from __future__ import annotations
from typing import Any, Dict
import requests

FEATURE_METADATA = {"name":"space_facts","description":"NASA APOD.","triggers":["space","apod"],"parameters":{"type":"OBJECT","properties":{"date":{"type":"STRING"}},"required":[]}}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    date = params.get("date")
    url = f"https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY"
    if date: url += f"&date={date}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    return {"ok":True,"title":data.get("title"),"url":data.get("url"),"explanation":data.get("explanation")}