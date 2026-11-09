"""
skills/market_intelligence/skill.py - Stella Market Intelligence Agent System.

Spawns and manages child agents that monitor:
  - X (Twitter) for polymarket, crypto, forex accounts and sentiment
  - Telegram channels/groups for crypto/forex/polymarket alpha
  - DEX markets and screeners for token movements
  - Top performer tokens and whale wallet activity
  - Forex markets across multiple pairs (arbitrage detection)
  - Polymarket + biggest players/investors

Aggregates all agent returns into unified market predictions and auto-discovers
new sources to watch, spawning additional agents as needed.

Operations:
  spawn_agent      - Create a new monitoring agent for a specific asset/source
  list_agents      - List all active monitoring agents
  agent_report     - Get the latest report from a specific agent
  aggregate        - Combine all agent data into a market prediction
  predict          - Predict next price move for an asset
  discover_sources - Auto-discover new sources from agent findings
  spawn_from_source- Spawn a new agent from a discovered source
  stop_agent       - Stop a monitoring agent
  sources          - Return skill metadata
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "market_intelligence"
AGENTS_FILE = DATA_DIR / "agents.json"
REPORTS_FILE = DATA_DIR / "reports.json"
PREDICTIONS_FILE = DATA_DIR / "predictions.json"
SOURCES_FILE = DATA_DIR / "sources.json"


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


ASSET_CATEGORIES = {
    "crypto": {
        "description": "Cryptocurrency markets (BTC, ETH, altcoins, memecoins)",
        "sources": ["x", "telegram", "dex", "coingecko", "coinmarketcap"],
        "whale_tracking": True,
    },
    "forex": {
        "description": "Foreign exchange markets (EUR/USD, GBP/USD, USD/JPY, etc.)",
        "sources": ["x", "telegram", "forex_factory", "investing"],
        "arbitrage": True,
    },
    "polymarket": {
        "description": "Polymarket prediction market odds and events",
        "sources": ["x", "telegram", "polymarket", "dune"],
        "whale_tracking": True,
    },
    "dex": {
        "description": "Decentralized exchange markets and screeners",
        "sources": ["dexscreener", "dextool", "uniswap", "pancakeswap"],
        "arbitrage": True,
    },
}


def _op_spawn_agent(kwargs: dict) -> dict:
    asset = (kwargs.get("asset") or "").strip()
    category = (kwargs.get("category") or "crypto").strip()
    platform = (kwargs.get("platform") or "x").strip()
    source = (kwargs.get("source") or "").strip()
    monitor_whales = bool(kwargs.get("monitor_whales", False))
    monitor_arbitrage = bool(kwargs.get("monitor_arbitrage", False))
    check_interval = int(kwargs.get("check_interval") or 300)

    if not asset:
        return _op("spawn_agent", False, None, "Provide an asset to monitor (asset=...).")

    agent_id = str(uuid.uuid4())[:8]
    agent = {
        "id": agent_id,
        "asset": asset,
        "category": category,
        "platform": platform,
        "source": source,
        "monitor_whales": monitor_whales,
        "monitor_arbitrage": monitor_arbitrage,
        "check_interval": check_interval,
        "status": "active",
        "created_at": _now(),
        "last_report": None,
        "findings": [],
        "signals": [],
    }

    agents = _load(AGENTS_FILE, [])
    agents.append(agent)
    _save(AGENTS_FILE, agents)

    return _op("spawn_agent", True, {
        "agent_id": agent_id,
        "asset": asset,
        "category": category,
        "platform": platform,
        "source": source,
        "status": "active",
        "message": "Agent " + agent_id + " spawned to monitor " + asset + " on " + platform,
    })


def _op_list_agents(kwargs: dict) -> dict:
    status_filter = (kwargs.get("status") or "active").strip()
    agents = _load(AGENTS_FILE, [])

    if status_filter != "all":
        agents = [a for a in agents if a.get("status") == status_filter]

    lines = []
    lines.append("Market Intelligence Agents (" + str(len(agents)) + " active)")
    lines.append("=" * 60)
    lines.append("")
    for a in agents:
        lines.append("[" + a["id"] + "] " + a["asset"] + " (" + a["category"] + ")")
        lines.append("    Platform: " + a["platform"] + " | Source: " + a["source"])
        lines.append("    Status: " + a["status"] + " | Whales: " + str(a.get("monitor_whales", False)) + " | Arb: " + str(a.get("monitor_arbitrage", False)))
        lines.append("    Created: " + a.get("created_at", "")[:16] + " | Last report: " + (a.get("last_report") or "none"))
        if a.get("signals"):
            lines.append("    Signals: " + str(len(a["signals"])) + " recent")
        lines.append("")

    content = "\n".join(lines)
    return _op("list_agents", True, {
        "agents": agents,
        "count": len(agents),
        "content": content,
    })


def _op_agent_report(kwargs: dict) -> dict:
    agent_id = (kwargs.get("id") or "").strip()
    if not agent_id:
        return _op("agent_report", False, None, "Provide an agent id (id=...).")

    agents = _load(AGENTS_FILE, [])
    agent = None
    for a in agents:
        if a["id"] == agent_id:
            agent = a
            break

    if not agent:
        return _op("agent_report", False, None, "Agent " + agent_id + " not found.")

    reports = _load(REPORTS_FILE, [])
    agent_reports = [r for r in reports if r.get("agent_id") == agent_id]
    agent_reports.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

    lines = []
    lines.append("Agent Report: " + agent_id)
    lines.append("=" * 60)
    lines.append("")
    lines.append("Asset: " + agent["asset"] + " (" + agent["category"] + ")")
    lines.append("Platform: " + agent["platform"] + " | Source: " + agent["source"])
    lines.append("Status: " + agent["status"])
    lines.append("Created: " + agent.get("created_at", ""))
    lines.append("")
    if agent_reports:
        latest = agent_reports[0]
        lines.append("Latest Report (" + latest.get("timestamp", "") + "):")
        lines.append("-" * 40)
        lines.append(latest.get("content", "No content"))
        lines.append("")
        if latest.get("signals"):
            lines.append("Signals:")
            for s in latest["signals"]:
                lines.append("  - " + s)
        lines.append("")
    else:
        lines.append("No reports yet. Agent is still gathering data.")
        lines.append("")

    if agent.get("findings"):
        lines.append("Recent Findings:")
        for f in agent["findings"][-5:]:
            lines.append("  - " + f)
        lines.append("")

    content = "\n".join(lines)
    return _op("agent_report", True, {
        "agent_id": agent_id,
        "agent": agent,
        "reports": agent_reports,
        "content": content,
    })


def _op_aggregate(kwargs: dict) -> dict:
    category = (kwargs.get("category") or "all").strip()
    asset = (kwargs.get("asset") or "").strip()

    agents = _load(AGENTS_FILE, [])
    if category != "all":
        agents = [a for a in agents if a.get("category") == category]
    if asset:
        agents = [a for a in agents if a.get("asset") == asset]

    reports = _load(REPORTS_FILE, [])
    agent_reports = []
    for a in agents:
        agent_reports.extend([r for r in reports if r.get("agent_id") == a["id"]])

    all_signals = []
    for r in agent_reports:
        all_signals.extend(r.get("signals", []))

    bullish = sum(1 for s in all_signals if s.get("type") == "bullish")
    bearish = sum(1 for s in all_signals if s.get("type") == "bearish")
    neutral = sum(1 for s in all_signals if s.get("type") == "neutral")

    total = bullish + bearish + neutral
    bullish_pct = round(bullish / total * 100, 1) if total else 0
    bearish_pct = round(bearish / total * 100, 1) if total else 0

    if bullish_pct > bearish_pct + 10:
        direction = "bullish"
        confidence = min(90, bullish_pct)
    elif bearish_pct > bullish_pct + 10:
        direction = "bearish"
        confidence = min(90, bearish_pct)
    else:
        direction = "neutral"
        confidence = 50

    themes = {}
    for s in all_signals:
        t = s.get("theme", "general")
        themes[t] = themes.get(t, 0) + 1
    top_themes = sorted(themes.items(), key=lambda x: -x[1])[:5]

    lines = []
    lines.append("Market Intelligence Aggregate")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Asset: " + (asset or "all") + " | Category: " + category)
    lines.append("Active Agents: " + str(len(agents)) + " | Reports: " + str(len(agent_reports)))
    lines.append("")
    lines.append("Overall Direction: " + direction.upper())
    lines.append("Confidence: " + str(confidence) + "%")
    lines.append("Signals: " + str(bullish) + " bullish, " + str(bearish) + " bearish, " + str(neutral) + " neutral")
    lines.append("")
    if top_themes:
        lines.append("Key Themes:")
        for theme, count in top_themes:
            lines.append("  - " + theme + ": " + str(count) + " mentions")
        lines.append("")

    content = "\n".join(lines)
    return _op("aggregate", True, {
        "asset": asset or "all",
        "category": category,
        "direction": direction,
        "confidence": confidence,
        "bullish_pct": bullish_pct,
        "bearish_pct": bearish_pct,
        "neutral_pct": round(neutral / total * 100, 1) if total else 0,
        "total_signals": total,
        "top_themes": top_themes,
        "agents": len(agents),
        "content": content,
    })


def _op_predict(kwargs: dict) -> dict:
    asset = (kwargs.get("asset") or "").strip()
    timeframe = (kwargs.get("timeframe") or "24h").strip()

    if not asset:
        return _op("predict", False, None, "Provide an asset to predict (asset=...).")

    agents = _load(AGENTS_FILE, [])
    asset_agents = [a for a in agents if a.get("asset", "").lower() == asset.lower()]

    reports = _load(REPORTS_FILE, [])
    asset_reports = []
    for a in asset_agents:
        asset_reports.extend([r for r in reports if r.get("agent_id") == a["id"]])

    if not asset_reports:
        return _op("predict", False, None, "No data for " + asset + ". Spawn agents first with spawn_agent.")

    predictions = []
    for r in asset_reports:
        if r.get("prediction"):
            predictions.append(r["prediction"])

    if not predictions:
        return _op("predict", False, None, "No predictions available for " + asset + " yet. Agents need more data.")

    up = sum(1 for p in predictions if p.get("direction") == "up")
    down = sum(1 for p in predictions if p.get("direction") == "down")
    flat = sum(1 for p in predictions if p.get("direction") == "flat")
    total = len(predictions)

    if up > down:
        predicted_direction = "up"
        confidence = round(up / total * 100, 1)
    elif down > up:
        predicted_direction = "down"
        confidence = round(down / total * 100, 1)
    else:
        predicted_direction = "flat"
        confidence = 50

    targets = [p.get("target_price", 0) for p in predictions if p.get("target_price")]
    avg_target = round(sum(targets) / len(targets), 4) if targets else None

    factors = []
    for r in asset_reports:
        if r.get("key_factors"):
            factors.extend(r["key_factors"])
    top_factors = list(set(factors))[:5]

    lines = []
    lines.append("Market Prediction: " + asset + " (" + timeframe + ")")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Predicted Direction: " + predicted_direction.upper())
    lines.append("Confidence: " + str(confidence) + "%")
    lines.append("Votes: " + str(up) + " up, " + str(down) + " down, " + str(flat) + " flat (from " + str(total) + " predictions)")
    if avg_target:
        lines.append("Average Price Target: " + str(avg_target))
    lines.append("")
    if top_factors:
        lines.append("Key Factors:")
        for f in top_factors:
            lines.append("  - " + f)
        lines.append("")
    lines.append("Data from " + str(len(asset_agents)) + " agents, " + str(len(asset_reports)) + " reports")
    lines.append("")
    lines.append("Disclaimer: This is aggregated agent data, not financial advice.")

    content = "\n".join(lines)
    predictions_store = _load(PREDICTIONS_FILE, [])
    prediction_record = {
        "asset": asset,
        "timeframe": timeframe,
        "direction": predicted_direction,
        "confidence": confidence,
        "target_price": avg_target,
        "factors": top_factors,
        "timestamp": _now(),
        "sources": [a["id"] for a in asset_agents],
    }
    predictions_store.append(prediction_record)
    _save(PREDICTIONS_FILE, predictions_store)

    return _op("predict", True, {
        "asset": asset,
        "timeframe": timeframe,
        "direction": predicted_direction,
        "confidence": confidence,
        "target_price": avg_target,
        "factors": top_factors,
        "votes": {"up": up, "down": down, "flat": flat},
        "content": content,
    })


def _op_discover_sources(kwargs: dict) -> dict:
    category = (kwargs.get("category") or "all").strip()
    agents = _load(AGENTS_FILE, [])
    if category != "all":
        agents = [a for a in agents if a.get("category") == category]

    reports = _load(REPORTS_FILE, [])
    all_findings = []
    for a in agents:
        agent_reports = [r for r in reports if r.get("agent_id") == a["id"]]
        for r in agent_reports:
            all_findings.extend(r.get("findings", []))

    discovered = []
    for f in all_findings:
        if isinstance(f, dict):
            source = f.get("source") or f.get("url") or f.get("account") or f.get("channel")
            if source and source not in discovered:
                discovered.append(source)
        elif isinstance(f, str):
            import re
            handles = re.findall(r"@(\w+)", f)
            urls = re.findall(r"https?://[\w./-]+", f)
            for h in handles:
                if h not in discovered:
                    discovered.append("x:" + h)
            for u in urls:
                if u not in discovered:
                    discovered.append("web:" + u)

    existing_sources = _load(SOURCES_FILE, [])
    existing_ids = {s.get("id") for s in existing_sources}
    new_sources = []
    for d in discovered:
        if d not in existing_ids:
            source_id = str(uuid.uuid4())[:8]
            new_sources.append({
                "id": source_id,
                "source": d,
                "category": category if category != "all" else "discovered",
                "discovered_at": _now(),
                "status": "pending",
            })
            existing_sources.append(new_sources[-1])

    _save(SOURCES_FILE, existing_sources)

    lines = []
    lines.append("Source Discovery Results")
    lines.append("=" * 60)
    lines.append("")
    lines.append("New sources discovered: " + str(len(new_sources)))
    lines.append("")
    for s in new_sources:
        lines.append("  [" + s["id"] + "] " + s["source"] + " (" + s["category"] + ")")
    lines.append("")
    lines.append("Use spawn_from_source to create monitoring agents for these sources.")

    content = "\n".join(lines)
    return _op("discover_sources", True, {
        "new_sources": new_sources,
        "count": len(new_sources),
        "content": content,
    })


def _op_spawn_from_source(kwargs: dict) -> dict:
    source_id = (kwargs.get("source_id") or "").strip()
    asset = (kwargs.get("asset") or "").strip()
    category = (kwargs.get("category") or "discovered").strip()
    if not source_id:
        return _op("spawn_from_source", False, None, "Provide a source_id.")

    sources = _load(SOURCES_FILE, [])
    source = None
    for s in sources:
        if s["id"] == source_id:
            source = s
            break

    if not source:
        return _op("spawn_from_source", False, None, "Source " + source_id + " not found.")

    source_str = source["source"]
    if source_str.startswith("x:"):
        platform = "x"
        source_val = source_str[2:]
    elif source_str.startswith("web:"):
        platform = "web"
        source_val = source_str[4:]
    elif source_str.startswith("tg:"):
        platform = "telegram"
        source_val = source_str[3:]
    else:
        platform = "web"
        source_val = source_str

    source["status"] = "active"
    source["used_at"] = _now()
    _save(SOURCES_FILE, sources)

    agent_id = str(uuid.uuid4())[:8]
    agent = {
        "id": agent_id,
        "asset": asset or source_str,
        "category": category,
        "platform": platform,
        "source": source_val,
        "monitor_whales": False,
        "monitor_arbitrage": False,
        "check_interval": 300,
        "status": "active",
        "created_at": _now(),
        "last_report": None,
        "findings": [],
        "signals": [],
        "spawned_from_source": source_id,
    }

    agents = _load(AGENTS_FILE, [])
    agents.append(agent)
    _save(AGENTS_FILE, agents)

    return _op("spawn_from_source", True, {
        "agent_id": agent_id,
        "asset": agent["asset"],
        "platform": platform,
        "source": source_val,
        "source_id": source_id,
        "message": "Agent " + agent_id + " spawned from discovered source " + source_str,
    })


def _op_stop_agent(kwargs: dict) -> dict:
    agent_id = (kwargs.get("id") or "").strip()
    if not agent_id:
        return _op("stop_agent", False, None, "Provide an agent id (id=...).")

    agents = _load(AGENTS_FILE, [])
    for a in agents:
        if a["id"] == agent_id:
            a["status"] = "stopped"
            a["stopped_at"] = _now()
            _save(AGENTS_FILE, agents)
            return _op("stop_agent", True, {
                "agent_id": agent_id,
                "message": "Agent " + agent_id + " stopped.",
            })

    return _op("stop_agent", False, None, "Agent " + agent_id + " not found.")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "market_intelligence (Stella Market Intelligence Agent System)",
        "dependencies": [],
        "operations": ["spawn_agent", "list_agents", "agent_report",
                       "aggregate", "predict", "discover_sources",
                       "spawn_from_source", "stop_agent", "sources"],
        "asset_categories": list(ASSET_CATEGORIES.keys()),
        "platforms": ["x", "telegram", "dex", "polymarket", "forex", "web"],
        "note": "Multi-agent market intelligence. Spawns child agents to monitor "
                "crypto, forex, polymarket, DEX, Telegram, and X. Aggregates findings "
                "into market predictions and auto-discovers new sources.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "spawn_agent": _op_spawn_agent,
    "list_agents": _op_list_agents,
    "agent_report": _op_agent_report,
    "aggregate": _op_aggregate,
    "predict": _op_predict,
    "discover_sources": _op_discover_sources,
    "spawn_from_source": _op_spawn_from_source,
    "stop_agent": _op_stop_agent,
}

_OPERATION_TITLES = {
    "sources": "Market Intelligence Sources",
    "spawn_agent": "Spawn Agent",
    "list_agents": "List Agents",
    "agent_report": "Agent Report",
    "aggregate": "Aggregate Market Data",
    "predict": "Predict Price Move",
    "discover_sources": "Discover Sources",
    "spawn_from_source": "Spawn from Source",
    "stop_agent": "Stop Agent",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Market Intelligence",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown market intelligence operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Market Intelligence",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Market Intelligence",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Market intelligence error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Market Intelligence"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
