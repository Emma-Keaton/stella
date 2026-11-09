from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "currency_exchange",
    "aliases": [
        "currency_exchange", "currency converter", "currency exchange",
        "exchange rate", "forex", "fx rate", "convert currency",
        "currency rate", "money converter",
    ],
    "description": (
        "Currency exchange rates and conversion using the exchangerate.host "
        "public API (no API key required). Supports live rates, historical "
        "rates, and currency conversion for over 170 currencies."
    ),
    "triggers": [
        "currency", "exchange rate", "convert", "forex", "fx",
        "currency converter", "money convert", "USD to", "EUR to",
        "GBP to", "JPY to", "CAD to", "AUD to",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: latest | convert | historical | sources. Defaults to latest.",
            },
            "base": {
                "type": "STRING",
                "description": "Base currency code (e.g., 'USD', 'EUR', 'GBP'). Defaults to 'USD'.",
            },
            "target": {
                "type": "STRING",
                "description": "Target currency code (e.g., 'EUR', 'GBP', 'JPY').",
            },
            "amount": {
                "type": "NUMBER",
                "description": "Amount to convert (for convert operation).",
            },
            "date": {
                "type": "STRING",
                "description": "Date for historical rates (YYYY-MM-DD format).",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": [],
}
API_SOURCES = {
    "exchangerate_host": {
        "name": "exchangerate.host",
        "description": "Free foreign exchange rates and currency conversion API",
        "url": "https://exchangerate.host/",
        "docs": "https://exchangerate.host/#/docs",
        "auth_tier": "keyless",
        "rate_limit": "Unlimited for personal use",
        "uses": ["latest", "convert", "historical"],
    },
}

_RATE_LIMIT = 1.0
_last_call = 0.0


def _throttle() -> None:
    global _last_call
    import time
    elapsed = time.time() - _last_call
    if elapsed < _RATE_LIMIT:
        time.sleep(_RATE_LIMIT - elapsed)
    _last_call = time.time()


def _http_get_json(url: str, timeout: int = 15) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Stella-AI/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_latest(kwargs: dict) -> dict:
    base = (kwargs.get("base") or "USD").upper()
    data = _http_get_json(f"https://api.exchangerate.host/latest?base={base}")
    if not data or not data.get("success"):
        return _op("latest", False, None, "Failed to fetch exchange rates.")
    rates = data.get("rates", {})
    content_lines = [f"Exchange rates (base: {base}):"]
    for cur, rate in sorted(rates.items())[:15]:
        content_lines.append(f"  1 {base} = {rate:.4f} {cur}")
    content = "\n".join(content_lines)
    return _op("latest", True, {
        "base": base,
        "rates": rates,
        "date": data.get("date"),
        "content": content,
    })


def _op_convert(kwargs: dict) -> dict:
    base = (kwargs.get("base") or "USD").upper()
    target = (kwargs.get("target") or "EUR").upper()
    amount = float(kwargs.get("amount") or 1)
    data = _http_get_json(
        f"https://api.exchangerate.host/convert?from={base}&to={target}&amount={amount}"
    )
    if not data or not data.get("success"):
        return _op("convert", False, None, "Failed to convert currency.")
    result = data.get("result", 0)
    rate = data.get("info", {}).get("rate", 0)
    content = (
        f"{amount} {base} = {result:.2f} {target} "
        f"(rate: 1 {base} = {rate:.4f} {target})"
    )
    return _op("convert", True, {
        "base": base,
        "target": target,
        "amount": amount,
        "result": result,
        "rate": rate,
        "content": content,
    })


def _op_historical(kwargs: dict) -> dict:
    base = (kwargs.get("base") or "USD").upper()
    date = kwargs.get("date") or ""
    if not date:
        return _op("historical", False, None, "Date required (YYYY-MM-DD).")
    data = _http_get_json(f"https://api.exchangerate.host/{date}?base={base}")
    if not data or not data.get("success"):
        return _op("historical", False, None, "Failed to fetch historical rates.")
    rates = data.get("rates", {})
    content_lines = [f"Historical rates for {date} (base: {base}):"]
    for cur, rate in sorted(rates.items())[:15]:
        content_lines.append(f"  1 {base} = {rate:.4f} {cur}")
    content = "\n".join(content_lines)
    return _op("historical", True, {
        "base": base,
        "date": date,
        "rates": rates,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    """Return list of available currency data sources."""
    sources = []
    for key, info in API_SOURCES.items():
        sources.append(
            f"{key}: {info['name']} ({info['auth_tier']}) - {info['url']}"
        )
    content = "Available currency sources:\n" + "\n".join(f"  - {s}" for s in sources)
    return _op("sources", True, {"sources": sources, "content": content})
_OPERATIONS = {
    "sources": _op_sources,
    "latest": _op_latest,
    "convert": _op_convert,
    "historical": _op_historical,
}

_OPERATION_TITLES = {
    "sources": "Currency Sources",
    "latest": "Latest Exchange Rates",
    "convert": "Currency Conversion",
    "historical": "Historical Rates",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "latest").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Currency Exchange",
            "summary": f"Unknown operation '{operation}'. One of: "
                       f"{', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown currency operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Currency Exchange",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Currency Exchange",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Currency error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Currency Exchange"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))


