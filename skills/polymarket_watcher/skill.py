from __future__ import annotations
from typing import Any, Dict
import requests

FEATURE_METADATA = {
    "name": "polymarket_watcher",
    "description": "Watch Polymarket prediction markets for significant price moves.",
    "triggers": ["polymarket"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "keyword": {"type": "STRING", "description": "Filter markets by keyword", "default": ""},
            "min_volume": {"type": "NUMBER", "description": "Minimum 24h volume USD", "default": 10000}
        },
        "required": []
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    keyword = params.get("keyword", "").lower()
    min_volume = float(params.get("min_volume", 10000))
    url = "https://gamma-api.polymarket.com/markets"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        markets = r.json()
        alerts = []
        for m in markets:
            vol = float(m.get("volume24h", 0) or 0)
            if vol >= min_volume and (keyword in m.get("question", "").lower()):
                alerts.append({
                    "id": m.get("id"),
                    "question": m.get("question"),
                    "volume24h": vol,
                    "yes_price": m.get("yesPrice"),
                    "no_price": m.get("noPrice")
                })
        return {"ok": True, "alerts": alerts}
    except Exception as e:
        return {"ok": False, "error": str(e)}