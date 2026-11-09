"""skills/openbb_options_data/skill.py - OpenBB-inspired options data."""
from __future__ import annotations
import json, urllib.request, urllib.parse
from typing import Any

FEATURE_METADATA = {
    "name": "openbb_options_data",
    "description": "OpenBB-inspired options data: options chains, option quotes.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "options_chain, option_quote, sources.", "default": "sources"},
            "symbol": {"type": "STRING", "description": "Underlying ticker (e.g., 'AAPL', 'SPY')."},
            "expiration": {"type": "STRING", "description": "Expiration date YYYY-MM-DD."},
            "option_symbol": {"type": "STRING", "description": "Option contract symbol (e.g., 'AAPL240119C00150000')."},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "source": "openbb",
    "optional_dependencies": [],
    "tags": ["trading", "options", "derivatives", "openbb"],
}

def _fetch_json(url: str, timeout: int = 10) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def _op_options_chain(symbol: str, expiration: str) -> dict:
    url = "https://query2.finance.yahoo.com/v7/finance/options/" + urllib.parse.quote(symbol) + "?date=" + urllib.parse.quote(expiration)
    data = _fetch_json(url)
    if not data or "optionChain" not in data or not data["optionChain"].get("result"):
        return {"ok": False, "error": "Could not retrieve options chain for '" + symbol + "'."}
    result = data["optionChain"]["result"][0]
    options = result.get("options", [])
    if not options:
        return {"ok": False, "error": "No options data for '" + symbol + "'."}
    opt = options[0]
    calls = opt.get("calls", [])
    puts = opt.get("puts", [])
    return {"ok": True, "symbol": symbol.upper(), "underlying_price": result.get("underlyingPrice", 0), "expiration": expiration, "calls": [{"contract_symbol": c.get("contractSymbol", ""), "strike": c.get("strike"), "last_price": c.get("lastPrice"), "bid": c.get("bid"), "ask": c.get("ask"), "volume": c.get("volume"), "open_interest": c.get("openInterest"), "implied_volatility": c.get("impliedVolatility")} for c in calls[:20]], "puts": [{"contract_symbol": p.get("contractSymbol", ""), "strike": p.get("strike"), "last_price": p.get("lastPrice"), "bid": p.get("bid"), "ask": p.get("ask"), "volume": p.get("volume"), "open_interest": p.get("openInterest"), "implied_volatility": p.get("impliedVolatility")} for p in puts[:20]]}

def _op_option_quote(option_symbol: str) -> dict:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(option_symbol) + "?range=1d&interval=1d"
    data = _fetch_json(url)
    if not data or "chart" not in data or not data["chart"].get("result"):
        return {"ok": False, "error": "Could not retrieve quote for '" + option_symbol + "'."}
    result = data["chart"]["result"][0]
    meta = result.get("meta", {})
    indicators = result.get("indicators", {}).get("quote", [{}])[0]
    closes = indicators.get("close", [])
    last_close = closes[-1] if closes else None
    return {"ok": True, "contract_symbol": option_symbol, "price": meta.get("regularMarketPrice") or last_close, "currency": meta.get("currency", "USD"), "exchange": meta.get("exchangeName", ""), "previous_close": meta.get("previousClose"), "volume": meta.get("regularMarketVolume")}

def _op_sources() -> dict:
    return {"ok": True, "source": "openbb", "skill": "openbb_options_data", "description": "OpenBB-inspired options data: options chains, option quotes.", "operations": ["options_chain", "option_quote", "sources"], "asset_classes": ["stocks", "etf", "indices"], "api_key_required": False}

_OPERATIONS = {"options_chain": _op_options_chain, "option_quote": _op_option_quote, "sources": _op_sources}
_OPERATION_TITLES = {"options_chain": "Options Chain", "option_quote": "Option Quote", "sources": "Options Data Sources"}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "OpenBB Options Data", "summary": "Unknown operation '" + operation + "'.", "ok": False, "operation": operation}
    try:
        if operation == "options_chain":
            record = handler(kwargs.get("symbol", ""), kwargs.get("expiration", ""))
        elif operation == "option_quote":
            record = handler(kwargs.get("option_symbol", ""))
        else:
            record = handler()
    except TypeError as exc:
        return {"title": "OpenBB Options Data", "summary": "Bad arguments for '" + operation + "': " + str(exc), "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "OpenBB Options Data", "summary": str(type(exc).__name__) + ": " + str(exc), "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "OpenBB Options Data"), "summary": str(record.get("error", record))[:200] if not record.get("ok") else str(record)[:200], "ok": bool(record.get("ok")), "operation": operation, "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))