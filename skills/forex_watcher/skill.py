from __future__ import annotations
from typing import Any, Dict
import requests

FEATURE_METADATA = {
    "name": "forex_watcher",
    "description": "Watch forex rate movements via exchangerate.host.",
    "triggers": ["forex"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "base": {"type": "STRING", "description": "Base currency, e.g., USD", "default": "USD"},
            "symbols": {"type": "STRING", "description": "Comma-separated target currencies, e.g., EUR,GBP,JPY", "default": "EUR,GBP,JPY"}
        },
        "required": []
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    base = params.get("base", "USD")
    symbols = params.get("symbols", "EUR,GBP,JPY")
    url = f"https://api.exchangerate.host/latest?base={base}&symbols={symbols}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        rates = data.get("rates", {})
        return {"ok": True, "base": base, "rates": rates, "date": data.get("date")}
    except Exception as e:
        return {"ok": False, "error": str(e)}