from __future__ import annotations
from typing import Any, Dict
import requests

FEATURE_METADATA = {
    "name": "top_performer_tracker",
    "description": "Track top gainers and losers across crypto markets via CoinGecko.",
    "triggers": ["top performers"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "vs_currency": {"type": "STRING", "default": "usd"},
            "top_n": {"type": "INTEGER", "default": 10}
        },
        "required": []
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    vs = params.get("vs_currency", "usd")
    n = int(params.get("top_n", 10))
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params_q = {"vs_currency": vs, "order": "price_change_percentage_24h_desc", "per_page": 250, "page": 1, "price_change_percentage": "24h"}
    try:
        r = requests.get(url, params=params_q, timeout=15)
        r.raise_for_status()
        data = r.json()
        # filter out entries without change
        filtered = [c for c in data if c.get("price_change_percentage_24h") is not None]
        gainers = sorted(filtered, key=lambda x: x.get("price_change_percentage_24h", -1e9), reverse=True)[:n]
        losers = sorted(filtered, key=lambda x: x.get("price_change_percentage_24h", 1e9))[:n]
        fmt = lambda c: {
            "id": c.get("id"),
            "symbol": c.get("symbol"),
            "name": c.get("name"),
            "price": c.get("current_price"),
            "change_24h": c.get("price_change_percentage_24h")
        }
        return {"ok": True, "gainers": [fmt(c) for c in gainers], "losers": [fmt(c) for c in losers]}
    except Exception as e:
        return {"ok": False, "error": str(e)}