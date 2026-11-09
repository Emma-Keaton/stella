"""
skills/market_prediction/skill.py - Stella Market Prediction Engine.

Combines market intelligence agent outputs with:
  - Correlation analysis across assets
  - Arbitrage detection (DEX, forex, cross-exchange)
  - Whale movement tracking and wallet analysis
  - Cross-asset influence modeling (what moves what)
  - Market psychology and sentiment analysis
  - Polymarket prediction market odds correlation

Operations:
  correlate        - Find correlations between assets
  arbitrage        - Detect arbitrage opportunities
  whale_tracking   - Track large wallet movements
  influence_map    - Map what influences what in markets
  sentiment        - Aggregate market sentiment across platforms
  predict          - Generate price prediction with confidence
  sources          - Return skill metadata
"""

from __future__ import annotations

import json
import math
import os
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "market_prediction"
CORRELATIONS_FILE = DATA_DIR / "correlations.json"
ARBITRAGE_FILE = DATA_DIR / "arbitrage.json"
WHALE_FILE = DATA_DIR / "whales.json"
INFLUENCE_FILE = DATA_DIR / "influence.json"
SENTIMENT_FILE = DATA_DIR / "sentiment.json"
PREDICTIONS_FILE = DATA_DIR / "predictions.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path, default: Any) -> Any:
    _ensure_data_dir()
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save(path: Path, data: Any) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _now() -> str:
    return datetime.now().isoformat()


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _wrap(text: str, width: int = 80) -> str:
    words = text.split()
    lines = []
    current = []
    current_len = 0
    for w in words:
        if current_len + len(w) + len(current) > width:
            lines.append(" ".join(current))
            current = [w]
            current_len = len(w)
        else:
            current.append(w)
            current_len += len(w)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def _op_correlate(kwargs: dict) -> dict:
    asset_a = (kwargs.get("asset_a") or "").strip().upper()
    asset_b = (kwargs.get("asset_b") or "").strip().upper()
    timeframe = (kwargs.get("timeframe") or "24h").strip()

    if not asset_a or not asset_b:
        return _op("correlate", False, None, "Provide asset_a and asset_b.")

    mi_dir = Path(__file__).resolve().parent.parent.parent / "memory" / "market_intelligence"
    reports_file = mi_dir / "reports.json"
    reports = _load(reports_file, [])

    correlations = []
    for r in reports:
        content = r.get("content", "") or ""
        signals = r.get("signals", [])
        if asset_a in content and asset_b in content:
            correlations.append({
                "report_id": r.get("id", ""),
                "timestamp": r.get("timestamp", ""),
                "signals": signals,
            })

    if not correlations:
        return _op("correlate", False, None, "No co-occurrence data for " + asset_a + " and " + asset_b + ". Run market intelligence agents first.")

    same_direction = sum(1 for c in correlations if c.get("signals") and all(s.get("direction") == c["signals"][0].get("direction") for s in c["signals"]))
    total = len(correlations)
    correlation_score = round(same_direction / total * 100, 1) if total else 0

    relationship = "strongly correlated" if correlation_score > 70 else "moderately correlated" if correlation_score > 40 else "weakly correlated"

    lines = []
    lines.append("Correlation: " + asset_a + " <-> " + asset_b + " (" + timeframe + ")")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Relationship: " + relationship.upper())
    lines.append("Correlation Score: " + str(correlation_score) + "%")
    lines.append("Co-occurring Reports: " + str(total))
    lines.append("Same Direction: " + str(same_direction))
    lines.append("")
    lines.append("Interpretation: " + asset_a + " and " + asset_b + " " + relationship + ".")
    lines.append("")

    content = "\n".join(lines)
    return _op("correlate", True, {
        "asset_a": asset_a,
        "asset_b": asset_b,
        "timeframe": timeframe,
        "correlation_score": correlation_score,
        "relationship": relationship,
        "co_occurring_reports": total,
        "content": content,
    })


def _op_arbitrage(kwargs: dict) -> dict:
    asset = (kwargs.get("asset") or "").strip().upper()
    platforms = (kwargs.get("platforms") or "dex,cex").strip()

    mi_dir = Path(__file__).resolve().parent.parent.parent / "memory" / "market_intelligence"
    reports_file = mi_dir / "reports.json"
    reports = _load(reports_file, [])

    opportunities = []
    for r in reports:
        content = r.get("content", "") or ""
        signals = r.get("signals", [])
        if asset in content or any(asset in str(s) for s in signals):
            for s in signals:
                if s.get("type") == "arbitrage" or "arbitrage" in str(s).lower():
                    opportunities.append({
                        "timestamp": r.get("timestamp", ""),
                        "asset": asset,
                        "buy_platform": s.get("buy_platform", "unknown"),
                        "sell_platform": s.get("sell_platform", "unknown"),
                        "price_diff_pct": s.get("price_diff_pct", 0),
                        "profit_potential": s.get("profit_potential", 0),
                    })

    if not opportunities:
        return _op("arbitrage", False, None, "No arbitrage opportunities detected for " + asset + ". Deploy market intelligence agents first.")

    opportunities.sort(key=lambda x: -x.get("profit_potential", 0))

    lines = []
    lines.append("Arbitrage Opportunities: " + asset)
    lines.append("=" * 60)
    lines.append("")
    lines.append("Opportunities Found: " + str(len(opportunities)))
    lines.append("")
    for opp in opportunities[:10]:
        lines.append("  " + opp["timestamp"][:16] + " | " + opp["buy_platform"] + " -> " + opp["sell_platform"])
        lines.append("    Price Diff: " + str(opp["price_diff_pct"]) + "% | Profit: " + str(opp["profit_potential"]) + "%")
        lines.append("")

    content = "\n".join(lines)
    return _op("arbitrage", True, {
        "asset": asset,
        "opportunities": opportunities[:10],
        "count": len(opportunities),
        "content": content,
    })


def _op_whale_tracking(kwargs: dict) -> dict:
    asset = (kwargs.get("asset") or "").strip().upper()
    min_usd = float(kwargs.get("min_usd") or 100000)

    mi_dir = Path(__file__).resolve().parent.parent.parent / "memory" / "market_intelligence"
    reports_file = mi_dir / "reports.json"
    reports = _load(reports_file, [])

    whale_movements = []
    for r in reports:
        signals = r.get("signals", [])
        for s in signals:
            if s.get("type") == "whale" and asset.lower() in str(s).lower():
                whale_movements.append({
                    "timestamp": r.get("timestamp", ""),
                    "asset": asset,
                    "wallet": s.get("wallet", "unknown"),
                    "action": s.get("action", "unknown"),
                    "amount_usd": s.get("amount_usd", 0),
                    "direction": s.get("direction", "unknown"),
                })

    if not whale_movements:
        return _op("whale_tracking", False, None, "No whale movements tracked for " + asset + ".")

    whale_movements.sort(key=lambda x: -x.get("amount_usd", 0))

    lines = []
    lines.append("Whale Movements: " + asset + " (min $" + str(min_usd) + ")")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Movements Tracked: " + str(len(whale_movements)))
    lines.append("")
    for w in whale_movements[:10]:
        lines.append("  " + w["timestamp"][:16] + " | " + w["wallet"][:20] + "...")
        lines.append("    " + w["action"] + " " + w["direction"] + " | $" + str(round(w["amount_usd"])) )
        lines.append("")

    content = "\n".join(lines)
    return _op("whale_tracking", True, {
        "asset": asset,
        "movements": whale_movements[:10],
        "count": len(whale_movements),
        "content": content,
    })


def _op_influence_map(kwargs: dict) -> dict:
    asset = (kwargs.get("asset") or "").strip().upper()

    mi_dir = Path(__file__).resolve().parent.parent.parent / "memory" / "market_intelligence"
    reports_file = mi_dir / "reports.json"
    reports = _load(reports_file, [])

    influencers = {}
    for r in reports:
        signals = r.get("signals", [])
        for s in signals:
            influencer = s.get("influencer", "")
            influenced = s.get("influenced", asset)
            if influencer and (not asset or influenced == asset):
                key = influencer
                if key not in influencers:
                    influencers[key] = {"count": 0, "impacts": []}
                influencers[key]["count"] += 1
                influencers[key]["impacts"].append(s.get("impact", "unknown"))

    if not influencers:
        return _op("influence_map", False, None, "No influence data for " + asset + ".")

    sorted_influencers = sorted(influencers.items(), key=lambda x: -x[1]["count"])

    lines = []
    lines.append("Influence Map: " + asset)
    lines.append("=" * 60)
    lines.append("")
    lines.append("Influencers Found: " + str(len(influencers)))
    lines.append("")
    for inf, data in sorted_influencers[:15]:
        impacts = data["impacts"]
        most_common = max(set(impacts), key=impacts.count) if impacts else "unknown"
        lines.append("  " + inf + ": " + str(data["count"]) + " mentions | Most common impact: " + most_common)
    lines.append("")

    content = "\n".join(lines)
    return _op("influence_map", True, {
        "asset": asset,
        "influencers": sorted_influencers[:15],
        "count": len(influencers),
        "content": content,
    })


def _op_sentiment(kwargs: dict) -> dict:
    asset = (kwargs.get("asset") or "").strip().upper()
    platforms = (kwargs.get("platforms") or "x,telegram,polymarket").strip()

    mi_dir = Path(__file__).resolve().parent.parent.parent / "memory" / "market_intelligence"
    reports_file = mi_dir / "reports.json"
    reports = _load(reports_file, [])

    platform_sentiment = {}
    for r in reports:
        signals = r.get("signals", [])
        for s in signals:
            platform = s.get("platform", "unknown")
            if platforms and platform not in platforms.split(","):
                continue
            if asset in str(s).lower() or not asset:
                sentiment = s.get("sentiment", "neutral")
                if platform not in platform_sentiment:
                    platform_sentiment[platform] = {"bullish": 0, "bearish": 0, "neutral": 0, "total": 0}
                platform_sentiment[platform][sentiment] = platform_sentiment[platform].get(sentiment, 0) + 1
                platform_sentiment[platform]["total"] += 1

    if not platform_sentiment:
        return _op("sentiment", False, None, "No sentiment data for " + asset + ".")

    lines = []
    lines.append("Market Sentiment: " + asset)
    lines.append("=" * 60)
    lines.append("")
    for platform, data in platform_sentiment.items():
        total = data["total"]
        bullish_pct = round(data["bullish"] / total * 100, 1) if total else 0
        bearish_pct = round(data["bearish"] / total * 100, 1) if total else 0
        lines.append("  " + platform + ": " + str(total) + " signals | Bullish: " + str(bullish_pct) + "% | Bearish: " + str(bearish_pct) + "%")
    lines.append("")

    total_bullish = sum(d["bullish"] for d in platform_sentiment.values())
    total_bearish = sum(d["bearish"] for d in platform_sentiment.values())
    total_all = sum(d["total"] for d in platform_sentiment.values())
    overall_bullish = round(total_bullish / total_all * 100, 1) if total_all else 0
    overall_bearish = round(total_bearish / total_all * 100, 1) if total_all else 0

    overall = "bullish" if overall_bullish > overall_bearish + 10 else "bearish" if overall_bearish > overall_bullish + 10 else "neutral"

    lines.append("Overall Sentiment: " + overall.upper())
    lines.append("Bullish: " + str(overall_bullish) + "% | Bearish: " + str(overall_bearish) + "%")

    content = "\n".join(lines)
    return _op("sentiment", True, {
        "asset": asset,
        "platform_sentiment": platform_sentiment,
        "overall": overall,
        "overall_bullish_pct": overall_bullish,
        "overall_bearish_pct": overall_bearish,
        "content": content,
    })


def _op_predict(kwargs: dict) -> dict:
    asset = (kwargs.get("asset") or "").strip().upper()
    timeframe = (kwargs.get("timeframe") or "24h").strip()

    if not asset:
        return _op("predict", False, None, "Provide an asset to predict (asset=...).")

    mi_dir = Path(__file__).resolve().parent.parent.parent / "memory" / "market_intelligence"
    reports_file = mi_dir / "reports.json"
    reports = _load(reports_file, [])

    asset_reports = [r for r in reports if asset in (r.get("content", "") or "").upper()]

    if not asset_reports:
        return _op("predict", False, None, "No data for " + asset + ". Run market intelligence agents first.")

    all_signals = []
    for r in asset_reports:
        all_signals.extend(r.get("signals", []))

    up = sum(1 for s in all_signals if s.get("direction") == "up")
    down = sum(1 for s in all_signals if s.get("direction") == "down")
    flat = sum(1 for s in all_signals if s.get("direction") == "flat")
    total = len(all_signals)

    weighted_up = sum(s.get("confidence", 50) for s in all_signals if s.get("direction") == "up")
    weighted_down = sum(s.get("confidence", 50) for s in all_signals if s.get("direction") == "down")
    weighted_flat = sum(s.get("confidence", 50) for s in all_signals if s.get("direction") == "flat")
    total_weight = weighted_up + weighted_down + weighted_flat

    if weighted_up > weighted_down:
        direction = "up"
        confidence = round(weighted_up / total_weight * 100, 1) if total_weight else 50
    elif weighted_down > weighted_up:
        direction = "down"
        confidence = round(weighted_down / total_weight * 100, 1) if total_weight else 50
    else:
        direction = "flat"
        confidence = 50

    targets = []
    for r in asset_reports:
        if r.get("predicted_price"):
            targets.append(r["predicted_price"])
    avg_target = round(statistics.mean(targets), 4) if targets else None

    drivers = []
    for s in all_signals:
        if s.get("driver"):
            drivers.append(s["driver"])
    top_drivers = list(set(drivers))[:5]

    risks = []
    for s in all_signals:
        if s.get("risk"):
            risks.append(s["risk"])
    top_risks = list(set(risks))[:5]

    lines = []
    lines.append("Market Prediction: " + asset + " (" + timeframe + ")")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Predicted Direction: " + direction.upper())
    lines.append("Confidence: " + str(confidence) + "%")
    lines.append("Weighted Votes: Up " + str(round(weighted_up/total_weight*100,1)) + "% | Down " + str(round(weighted_down/total_weight*100,1)) + "% | Flat " + str(round(weighted_flat/total_weight*100,1)) + "%")
    if avg_target:
        lines.append("Predicted Price: " + str(avg_target))
    lines.append("")
    if top_drivers:
        lines.append("Key Drivers:")
        for d in top_drivers:
            lines.append("  - " + d)
    lines.append("")
    if top_risks:
        lines.append("Risk Factors:")
        for r in top_risks:
            lines.append("  - " + r)
        lines.append("")
    lines.append("Based on " + str(total) + " signals from " + str(len(asset_reports)) + " reports")
    lines.append("")
    lines.append("Disclaimer: This is AI-generated market analysis, not financial advice.")

    content = "\n".join(lines)
    predictions_store = _load(PREDICTIONS_FILE, [])
    prediction_record = {
        "asset": asset,
        "timeframe": timeframe,
        "direction": direction,
        "confidence": confidence,
        "predicted_price": avg_target,
        "drivers": top_drivers,
        "risks": top_risks,
        "timestamp": _now(),
        "signal_count": total,
        "weighted_up": weighted_up,
        "weighted_down": weighted_down,
    }
    predictions_store.append(prediction_record)
    _save(PREDICTIONS_FILE, predictions_store)

    return _op("predict", True, {
        "asset": asset,
        "timeframe": timeframe,
        "direction": direction,
        "confidence": confidence,
        "predicted_price": avg_target,
        "drivers": top_drivers,
        "risks": top_risks,
        "weighted_votes": {
            "up": round(weighted_up/total_weight*100,1) if total_weight else 0,
            "down": round(weighted_down/total_weight*100,1) if total_weight else 0,
            "flat": round(weighted_flat/total_weight*100,1) if total_weight else 0,
        },
        "signal_count": total,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "market_prediction (Stella Market Prediction Engine)",
        "dependencies": [],
        "operations": ["correlate", "arbitrage", "whale_tracking",
                       "influence_map", "sentiment", "predict", "sources"],
        "asset_categories": ["crypto", "forex", "polymarket", "dex", "stocks"],
        "timeframes": ["1h", "24h", "7d", "30d"],
        "note": "Advanced market prediction using correlation analysis, arbitrage "
                "detection, whale tracking, influence mapping, and sentiment "
                "aggregation across all market intelligence data.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "correlate": _op_correlate,
    "arbitrage": _op_arbitrage,
    "whale_tracking": _op_whale_tracking,
    "influence_map": _op_influence_map,
    "sentiment": _op_sentiment,
    "predict": _op_predict,
}

_OPERATION_TITLES = {
    "sources": "Market Prediction Sources",
    "correlate": "Asset Correlation",
    "arbitrage": "Arbitrage Detection",
    "whale_tracking": "Whale Tracking",
    "influence_map": "Influence Map",
    "sentiment": "Market Sentiment",
    "predict": "Price Prediction",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Market Prediction",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown market prediction operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Market Prediction",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Market Prediction",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Market prediction error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Market Prediction"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
