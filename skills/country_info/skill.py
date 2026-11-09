from __future__ import annotations
from typing import Any, Dict
import requests

FEATURE_METADATA = {"name":"country_info","description":"Country info.","triggers":["country"],"parameters":{"type":"OBJECT","properties":{"name":{"type":"STRING"}},"required":["name"]}}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("name")
    r = requests.get(f"https://restcountries.com/v3.1/name/{name}", timeout=15)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list) and data:
        c = data[0]
        return {"ok":True,"name":c.get("name",{}).get("common"),"capital":c.get("capital"),"population":c.get("population")}
    return {"ok":False,"error":"not found"}