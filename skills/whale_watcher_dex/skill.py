from __future__ import annotations
from typing import Any, Dict
import requests, os

FEATURE_METADATA = {
    "name": "whale_watcher_dex",
    "description": "Watch large DEX swaps via DexScreener API.",
    "triggers": ["dex whale"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "chain": {"type": "STRING", "description": "Chain id, e.g., ethereum, bsc", "default": "ethereum"},
            "min_usd": {"type": "NUMBER", "description": "Minimum USD volume", "default": 100000}
        },
        "required": []
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    chain = params.get("chain", "ethereum")
    min_usd = float(params.get("min_usd", 100000))
    url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs", [])
        whales = []
        for p in pairs:
            volume_usd = float(p.get("volume", {}).get("h24", 0))
            if volume_usd >= min_usd:
                whales.append({
                    "pair": p.get("pairAddress"),
                    "baseToken": p.get("baseToken", {}).get("symbol"),
                    "quoteToken": p.get("quoteToken", {}).get("symbol"),
                    "volume_usd": volume_usd,
                    "priceUsd": p.get("priceUsd")
                })
        return {"ok": True, "chain": chain, "whales": whales}
    except Exception as e:
        return {"ok": False, "error": str(e)}