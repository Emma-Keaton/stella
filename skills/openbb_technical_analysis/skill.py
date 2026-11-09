from __future__ import annotations
import math
import urllib.request
import urllib.parse
import json
from datetime import datetime
from typing import Any

FEATURE_METADATA = {
    "name": "openbb_technical_analysis",
    "description": "OpenBB-inspired technical analysis: SMA, EMA, RSI, MACD, Bollinger Bands, support/resistance.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "indicators, signals, support_res, sources.", "default": "indicators"},
            "symbol": {"type": "STRING", "description": "Ticker symbol (e.g., 'AAPL', 'BTC-USD')."},
            "period": {"type": "STRING", "description": "Period: 1mo, 3mo, 6mo, 1y.", "default": "3mo"},
            "interval": {"type": "STRING", "description": "Interval: 1d, 1wk, 1mo.", "default": "1d"},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "source": "openbb",
    "optional_dependencies": [],
    "tags": ["trading", "technical-analysis", "openbb", "indicators", "signals"],
}


def _fetch_json(url: str, timeout: int = 10) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _sma(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i < window - 1:
            out.append(None)
        else:
            out.append(sum(values[i - window + 1 : i + 1]) / window)
    return out


def _ema(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    k = 2 / (window + 1)
    ema = None
    for v in values:
        if v is None:
            out.append(None)
            continue
        if ema is None:
            ema = v
        else:
            ema = v * k + ema * (1 - k)
        out.append(ema)
    return out


def _rsi(values: list[float], window: int = 14) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i < window:
            out.append(None)
            continue
        gains = 0.0
        losses = 0.0
        for j in range(i - window + 1, i + 1):
            change = values[j] - values[j - 1]
            if change > 0:
                gains += change
            else:
                losses -= change
        avg_gain = gains / window
        avg_loss = losses / window
        if avg_loss == 0:
            out.append(100.0)
        else:
            rs = avg_gain / avg_loss
            out.append(100 - (100 / (1 + rs)))
    return out


def _macd(values: list[float]) -> dict:
    ema12 = _ema(values, 12)
    ema26 = _ema(values, 26)
    macd_line: list[float | None] = []
    for a, b in zip(ema12, ema26):
        macd_line.append((a - b) if (a is not None and b is not None) else None)
    non_none = [x for x in macd_line if x is not None]
    signal_line = _ema(non_none, 9) if non_none else [None] * len(values)
    signal_aligned: list[float | None] = []
    idx = 0
    for v in macd_line:
        if v is None:
            signal_aligned.append(None)
        else:
            signal_aligned.append(signal_line[idx] if idx < len(signal_line) else None)
            idx += 1
    histogram: list[float | None] = []
    for m, s in zip(macd_line, signal_aligned):
        histogram.append((m - s) if (m is not None and s is not None) else None)
    return {"macd": macd_line, "signal": signal_aligned, "histogram": histogram}


def _bollinger(values: list[float], window: int = 20, num_std: float = 2.0) -> dict:
    sma_vals = _sma(values, window)
    upper: list[float | None] = []
    lower: list[float | None] = []
    for i in range(len(values)):
        if sma_vals[i] is None:
            upper.append(None)
            lower.append(None)
            continue
        window_vals = values[i - window + 1 : i + 1]
        mean = sum(window_vals) / len(window_vals)
        variance = sum((x - mean) ** 2 for x in window_vals) / len(window_vals)
        std = math.sqrt(variance)
        upper.append(mean + num_std * std)
        lower.append(mean - num_std * std)
    return {"upper": upper, "middle": sma_vals, "lower": lower}


def _op_indicators(symbol: str, period: str, interval: str) -> dict:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol) + "?range=" + period + "&interval=" + interval
    data = _fetch_json(url)
    if not data or "chart" not in data or not data["chart"].get("result"):
        return {"ok": False, "error": "Could not retrieve price data for '" + symbol + "'."}
    result = data["chart"]["result"][0]
    indicators = result.get("indicators", {}).get("quote", [{}])[0]
    closes = indicators.get("close", [])
    valid_closes = [c for c in closes if c is not None]
    if len(valid_closes) < 20:
        return {"ok": False, "error": "Insufficient price data for '" + symbol + "'."}
    sma_20 = _sma(valid_closes, 20)
    sma_50 = _sma(valid_closes, 50)
    ema_12 = _ema(valid_closes, 12)
    ema_26 = _ema(valid_closes, 26)
    rsi_vals = _rsi(valid_closes)
    macd_data = _macd(valid_closes)
    bb_data = _bollinger(valid_closes)
    last_close = valid_closes[-1]
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "period": period,
        "interval": interval,
        "data_points": len(valid_closes),
        "last_close": last_close,
        "sma_20": sma_20[-1],
        "sma_50": sma_50[-1],
        "ema_12": ema_12[-1],
        "ema_26": ema_26[-1],
        "rsi_14": rsi_vals[-1],
        "macd": macd_data["macd"][-1],
        "macd_signal": macd_data["signal"][-1],
        "macd_histogram": macd_data["histogram"][-1],
        "bollinger_upper": bb_data["upper"][-1],
        "bollinger_middle": bb_data["middle"][-1],
        "bollinger_lower": bb_data["lower"][-1],
    }


def _op_signals(symbol: str, period: str, interval: str) -> dict:
    ind = _op_indicators(symbol, period, interval)
    if not ind.get("ok"):
        return ind
    signals = []
    score = 0
    price = ind["last_close"]
    sma_20 = ind["sma_20"]
    sma_50 = ind["sma_50"]
    rsi = ind["rsi_14"]
    macd = ind["macd"]
    macd_signal = ind["macd_signal"]
    bb_upper = ind["bollinger_upper"]
    bb_lower = ind["bollinger_lower"]
    if sma_20 is not None and sma_50 is not None:
        if price > sma_20 > sma_50:
            signals.append("Bullish: price above SMA20 above SMA50")
            score += 1
        elif price < sma_20 < sma_50:
            signals.append("Bearish: price below SMA20 below SMA50")
            score -= 1
    if rsi is not None:
        if rsi < 30:
            signals.append("Oversold: RSI below 30")
            score += 1
        elif rsi > 70:
            signals.append("Overbought: RSI above 70")
            score -= 1
    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            signals.append("MACD bullish: MACD above signal")
            score += 1
        else:
            signals.append("MACD bearish: MACD below signal")
            score -= 1
    if bb_upper is not None and bb_lower is not None:
        if price <= bb_lower:
            signals.append("At support: price at or below Bollinger lower band")
            score += 1
        elif price >= bb_upper:
            signals.append("At resistance: price at or above Bollinger upper band")
            score -= 1
    verdict = "BUY" if score >= 2 else ("SELL" if score <= -2 else "HOLD")
    return {"ok": True, "symbol": symbol.upper(), "verdict": verdict, "score": score, "signals": signals, "price": price, "rsi": rsi}


def _op_support_res(symbol: str, period: str, interval: str) -> dict:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol) + "?range=" + period + "&interval=" + interval
    data = _fetch_json(url)
    if not data or "chart" not in data or not data["chart"].get("result"):
        return {"ok": False, "error": "Could not retrieve price data for '" + symbol + "'."}
    result = data["chart"]["result"][0]
    indicators = result.get("indicators", {}).get("quote", [{}])[0]
    highs = indicators.get("high", [])
    lows = indicators.get("low", [])
    closes = indicators.get("close", [])
    valid_highs = [h for h in highs if h is not None]
    valid_lows = [l for l in lows if l is not None]
    valid_closes = [c for c in closes if c is not None]
    if len(valid_closes) < 10:
        return {"ok": False, "error": "Insufficient data for '" + symbol + "'."}
    last_close = valid_closes[-1]
    window = min(10, len(valid_lows) // 2)
    recent_lows = valid_lows[-window:]
    recent_highs = valid_highs[-window:]
    support = min(recent_lows) if recent_lows else None
    resistance = max(recent_highs) if recent_highs else None
    nearby_support = [s for s in sorted(set(recent_lows), reverse=True) if s <= last_close * 1.05][:3]
    nearby_resistance = [r for r in sorted(set(recent_highs)) if r >= last_close * 0.95][:3]
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "last_close": last_close,
        "support": support,
        "resistance": resistance,
        "nearby_support": nearby_support,
        "nearby_resistance": nearby_resistance,
    }


def _op_sources() -> dict:
    return {"ok": True, "source": "openbb", "skill": "openbb_technical_analysis", "description": "OpenBB-inspired technical analysis: SMA, EMA, RSI, MACD, Bollinger Bands, support/resistance.", "operations": ["indicators", "signals", "support_res", "sources"], "indicators": ["sma_20", "sma_50", "ema_12", "ema_26", "rsi_14", "macd", "bollinger_bands"], "api_key_required": False}

_OPERATIONS = {"indicators": _op_indicators, "signals": _op_signals, "support_res": _op_support_res, "sources": _op_sources}
_OPERATION_TITLES = {"indicators": "Technical Indicators", "signals": "Trading Signals", "support_res": "Support & Resistance", "sources": "Technical Analysis Sources"}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "indicators").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "OpenBB Technical Analysis", "summary": "Unknown operation '" + operation + "'.", "ok": False, "operation": operation}
    try:
        if operation in ("indicators", "signals", "support_res"):
            record = handler(kwargs.get("symbol", ""), kwargs.get("period", "3mo"), kwargs.get("interval", "1d"))
        else:
            record = handler()
    except TypeError as exc:
        return {"title": "OpenBB Technical Analysis", "summary": "Bad arguments for '" + operation + "': " + str(exc), "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "OpenBB Technical Analysis", "summary": str(type(exc).__name__) + ": " + str(exc), "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "OpenBB Technical Analysis"), "summary": str(record.get("error", record))[:200] if not record.get("ok") else str(record)[:200], "ok": bool(record.get("ok")), "operation": operation, "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))


def _op_support_res(symbol: str, period: str, interval: str) -> dict:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol) + "?range=" + period + "&interval=" + interval
    data = _fetch_json(url)
    if not data or "chart" not in data or not data["chart"].get("result"):
        return {"ok": False, "error": "Could not retrieve price data for '" + symbol + "'."}
    result = data["chart"]["result"][0]
    indicators = result.get("indicators", {}).get("quote", [{}])[0]
    highs = indicators.get("high", [])
    lows = indicators.get("low", [])
    closes = indicators.get("close", [])
    valid_highs = [h for h in highs if h is not None]
    valid_lows = [l for l in lows if l is not None]
    valid_closes = [c for c in closes if c is not None]
    if len(valid_closes) < 10:
        return {"ok": False, "error": "Insufficient data for '" + symbol + "'."}
    last_close = valid_closes[-1]
    window = min(10, len(valid_lows) // 2)
    recent_lows = valid_lows[-window:]
    recent_highs = valid_highs[-window:]
    support = min(recent_lows) if recent_lows else None
    resistance = max(recent_highs) if recent_highs else None
    nearby_support = [s for s in sorted(set(recent_lows), reverse=True) if s <= last_close * 1.05][:3]
    nearby_resistance = [r for r in sorted(set(recent_highs)) if r >= last_close * 0.95][:3]
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "last_close": last_close,
        "support": support,
        "resistance": resistance,
        "nearby_support": nearby_support,
        "nearby_resistance": nearby_resistance,
    }


def _op_sources() -> dict:
    return {"ok": True, "source": "openbb", "skill": "openbb_technical_analysis", "description": "OpenBB-inspired technical analysis: SMA, EMA, RSI, MACD, Bollinger Bands, support/resistance.", "operations": ["indicators", "signals", "support_res", "sources"], "indicators": ["sma_20", "sma_50", "ema_12", "ema_26", "rsi_14", "macd", "bollinger_bands"], "api_key_required": False}

_OPERATIONS = {"indicators": _op_indicators, "signals": _op_signals, "support_res": _op_support_res, "sources": _op_sources}
_OPERATION_TITLES = {"indicators": "Technical Indicators", "signals": "Trading Signals", "support_res": "Support & Resistance", "sources": "Technical Analysis Sources"}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "indicators").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "OpenBB Technical Analysis", "summary": "Unknown operation '" + operation + "'.", "ok": False, "operation": operation}
    try:
        if operation in ("indicators", "signals", "support_res"):
            record = handler(kwargs.get("symbol", ""), kwargs.get("period", "3mo"), kwargs.get("interval", "1d"))
        else:
            record = handler()
    except TypeError as exc:
        return {"title": "OpenBB Technical Analysis", "summary": "Bad arguments for '" + operation + "': " + str(exc), "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "OpenBB Technical Analysis", "summary": str(type(exc).__name__) + ": " + str(exc), "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "OpenBB Technical Analysis"), "summary": str(record.get("error", record))[:200] if not record.get("ok") else str(record)[:200], "ok": bool(record.get("ok")), "operation": operation, "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))
