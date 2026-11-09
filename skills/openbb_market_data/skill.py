"""skills/openbb_market_data/skill.py - OpenBB-inspired market data for Stella."""
from __future__ import annotations
import json, urllib.request, urllib.parse
from datetime import datetime
from typing import Any

FEATURE_METADATA = {
    "name": "openbb_market_data",
    "description": "OpenBB-inspired market data: quotes, historical prices, symbol search, instrument overviews.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "quote, historical, search, overview, sources.", "default": "quote"},
            "symbol": {"type": "STRING", "description": "Ticker symbol (e.g., 'AAPL', 'BTC-USD')."},
            "period": {"type": "STRING", "description": "Period: 1d, 5d, 1mo, 3mo, 6mo, 1y, max.", "default": "1mo"},
            "interval": {"type": "STRING", "description": "Interval: 1m, 1h, 1d, 1wk, 1mo.", "default": "1d"},
            "query": {"type": "STRING", "description": "Search keyword for symbol lookup."},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "source": "openbb",
    "optional_dependencies": [],
    "tags": ["trading", "market-data", "openbb", "stocks", "crypto", "forex", "etf"],
}