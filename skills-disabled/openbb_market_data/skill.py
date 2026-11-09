"""
openbb_market_data — OpenBB-inspired market data: quotes, historical prices,
symbol search, instrument overviews. Uses free public APIs only.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
from typing import Any, Dict


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _fetch_json(url: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Stella/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _op_quote(kwargs: dict) -> dict:
    symbol = (kwargs.get("symbol") or "AAPL").strip().upper()
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        data = _fetch_json(url)
        result = data.get("quoteResponse", {}).get("result", [])
        if not result:
            return _op("quote", False, None, f"No quote for {symbol}.")
        q = result[0]
        return _op("quote", True, {
            "symbol": q.get("symbol"),
            "price": q.get("regularMarketPrice"),
            "currency": q.get("currency"),
            "change": q.get("regularMarketChange"),
            "change_percent": q.get("regularMarketChangePercent"),
        })
    except Exception as exc:
        return _op("quote", False, None, f"Quote fetch failed: {exc}")


def _op_historical(kwargs: dict) -> dict:
    symbol = (kwargs.get("symbol") or "AAPL").strip().upper()
    period = kwargs.get("period", "1mo")
    interval = kwargs.get("interval", "1d")
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={period}&interval={interval}"
        data = _fetch_json(url)
        result = data.get("chart", {}).get("result", [])
        if not result:
            return _op("historical", False, None, f"No historical data for {symbol}.")
        r = result[0]
        ts = r.get("timestamp", [])
        indicators = r.get("indicators", {}).get("quote", [{}])[0]
        prices = indicators.get("close", [])
        points = []
        for i, t in enumerate(ts):
            if i < len(prices) and prices[i] is not None:
                points.append({"t": t, "c": prices[i]})
        return _op("historical", True, {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "points": points,
            "total": len(points),
        })
    except Exception as exc:
        return _op("historical", False, None, f"Historical fetch failed: {exc}")


def _op_search(kwargs: dict) -> dict:
    query = (kwargs.get("query") or "Microsoft").strip()
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}"
        data = _fetch_json(url)
        quotes = data.get("quotes", [])
        results = []
        for q in quotes[:20]:
            results.append({
                "symbol": q.get("symbol"),
                "name": q.get("shortname") or q.get("longname"),
                "type": q.get("quoteType"),
                "exchange": q.get("exchange"),
            })
        return _op("search", True, {
            "query": query,
            "results": results,
            "total": len(results),
        })
    except Exception as exc:
        return _op("search", False, None, f"Symbol search failed: {exc}")


def _op_overview(kwargs: dict) -> dict:
    symbol = (kwargs.get("symbol") or "AAPL").strip().upper()
    try:
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=summaryProfile,summaryDetail"
        data = _fetch_json(url)
        result = data.get("quoteSummary", {}).get("result", [])
        if not result:
            return _op("overview", False, None, f"No overview for {symbol}.")
        profile = result[0].get("summaryProfile", {})
        detail = result[0].get("summaryDetail", {})
        return _op("overview", True, {
            "symbol": symbol,
            "name": profile.get("longName"),
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "description": profile.get("longBusinessSummary"),
            "market_cap": detail.get("marketCap"),
        })
    except Exception as exc:
        return _op("overview", False, None, f"Overview fetch failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["query1.finance.yahoo.com"],
        "content": "Market data from Yahoo Finance (query1.finance.yahoo.com). No API key required.",
    })


_OPERATIONS = {
    "quote": _op_quote,
    "historical": _op_historical,
    "search": _op_search,
    "overview": _op_overview,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "quote": "Market Quote",
    "historical": "Historical Prices",
    "search": "Symbol Search",
    "overview": "Instrument Overview",
    "sources": "Market Data Sources",
}

_ALIASES = {
    "quote": "quote",
    "price": "quote",
    "historical": "historical",
    "history": "historical",
    "search": "search",
    "symbol_search": "search",
    "overview": "overview",
    "company": "overview",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "quote":
        return f"{value.get('symbol')} — {value.get('price')} {value.get('currency') or ''} (change: {value.get('change_percent')}%)"
    if operation == "historical":
        return f"{value.get('total')} point(s) for {value.get('symbol')} ({value.get('period')} @ {value.get('interval')})"
    if operation == "search":
        return f"{value.get('total')} result(s) for '{value.get('query')}'"
    if operation == "overview":
        return f"{value.get('name')} — {value.get('sector')} / {value.get('industry')}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """OpenBB-inspired market data: quotes, historical prices, symbol search, instrument overviews."""
    operation = (kwargs.get("operation") or "quote").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "OpenBB Market Data",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "OpenBB Market Data",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "OpenBB Market Data",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Market data error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "OpenBB Market Data"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="quote", symbol="AAPL"))