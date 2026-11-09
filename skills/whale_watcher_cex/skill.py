from __future__ import annotations
from typing import Any, Dict
import requests, os

FEATURE_METADATA = {
    "name": "whale_watcher_cex",
    "description": "Watch large CEX trades via Binance public trade endpoint.",
    "triggers": ["cex whale"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "symbol": {"type": "STRING", "description": "Binance symbol, e.g., BTCUSDT", "default": "BTCUSDT"},
            "min_usd": {"type": "NUMBER", "description": "Minimum USD value per trade", "default": 50000}
        },
        "required": []
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    symbol = params.get("symbol", "BTCUSDT")
    min_usd = float(params.get("min_usd", 50000))
    url = f"https://api.binance.com/api/v3/trades?symbol={symbol}&limit=100"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        trades = r.json()
        whales = []
        for t in trades:
            qty = float(t.get("qty", 0))
            price = float(t.get("price", 0))
            usd_val = qty * price
            if usd_val >= min_usd:
                whales.append({
                    "trade_id": t.get("id"),
                    "symbol": symbol,
                    "qty": qty,
                    "price": price,
                    "usd_value": usd_val,
                    "time": t.get("time")
                })
        return {"ok": True, "symbol": symbol, "whales": whales}
    except Exception as e:
        return {"ok": False, "error": str(e)}