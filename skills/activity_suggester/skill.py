from __future__ import annotations
from typing import Any, Dict
import requests

FEATURE_METADATA = {"name":"activity_suggester","description":"Bored API activity.","triggers":["activity"],"parameters":{"type":"OBJECT","properties":{"type":{"type":"STRING"}},"required":[]}}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    t = params.get("type")
    url = "https://www.boredapi.com/api/activity"
    if t: url += f"?type={t}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return {"ok":True,"activity":r.json()}