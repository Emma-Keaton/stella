from __future__ import annotations
from typing import Any, Dict
import requests, pathlib, json

FEATURE_METADATA = {"name":"public_api_browser","aliases":["apis"],"description":"Browse public APIs catalogue.","triggers":["public apis"],"parameters":{"type":"OBJECT","properties":{"category":{"type":"STRING"},"q":{"type":"STRING"}},"required":[]}}

CACHE = pathlib.Path("E:\\Projects\\stella\\data\\public_apis.json")

def _fetch():
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    r = requests.get("https://api.publicapis.org/entries", timeout=20)
    data = r.json()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(data))
    return data

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    data = _fetch()
    entries = data.get("entries", [])
    cat = params.get("category")
    q = str(params.get("q","")).lower()
    filtered = [e for e in entries if (not cat or e.get("Category")==cat) and (not q or q in e.get("API","").lower() or q in e.get("Description","").lower())]
    return {"ok":True,"count":len(filtered),"results":filtered[:50]}