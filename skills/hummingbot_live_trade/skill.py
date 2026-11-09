"""
hummingbot_live_trade - Run Hummingbot in live-trading mode (requires wallet connection).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict

CONNECTOR_ALIASES: dict[str, str] = {
    "binance": "binance",
    "binance_us": "binance_us",
    "coinbase_pro": "coinbase_pro",
    "kraken": "kraken",
    "kucoin": "kucoin",
    "bybit": "bybit",
    "okx": "okx",
    "uniswap_v2": "uniswap_v2",
    "uniswap_v3": "uniswap_v3",
    "sushiswap": "sushiswap",
    "pancakeswap": "pancakeswap",
    "polymarket": "polymarket",
    "fxcm": "fxcm",
    "oanda": "oanda",
}


def _resolve_connector(user_input: str) -> str:
    return CONNECTOR_ALIASES.get((user_input or "binance").strip().lower(), (user_input or "binance").strip().lower())


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_live_trade(kwargs: dict) -> dict:
    if not os.getenv("WALLET_CONNECTED"):
        return _op("live_trade", False, None, "Wallet not connected. Set WALLET_CONNECTED=1 after linking wallet.")
    strategy = (kwargs.get("strategy") or "").strip()
    symbol = (kwargs.get("symbol") or "").strip()
    if not strategy or not symbol:
        return _op("live_trade", False, None, "Missing required parameters: strategy, symbol.")

    exchange = _resolve_connector(kwargs.get("exchange", "binance"))
    config_overrides = kwargs.get("config_overrides") or {}

    cfg: Dict[str, Any] = {
        "strategy": strategy,
        "market": exchange,
        "symbol": symbol,
        "paper_trade": False,
    }
    cfg.update(config_overrides)

    hummingbot_bin = shutil.which("hummingbot") or os.getenv("HUMMINGBOT_BIN")
    if not hummingbot_bin:
        return _op("live_trade", False, None, {
            "config": cfg,
            "message": "Hummingbot binary not found. Install Hummingbot first.",
        })

    config_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
            json.dump(cfg, tf, indent=2)
            config_path = tf.name
        cmd = [hummingbot_bin, "start", "--config", config_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return _op("live_trade", result.returncode == 0, {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "config": cfg,
        })
    except subprocess.TimeoutExpired:
        return _op("live_trade", False, None, "Live trade startup timed out.", {"config": cfg})
    except Exception as exc:
        return _op("live_trade", False, None, f"Live trade failed: {exc}", {"config": cfg})
    finally:
        if config_path:
            try:
                os.unlink(config_path)
            except Exception:
                pass


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["hummingbot"],
        "content": "Live trading via Hummingbot. WALLET_CONNECTED must be set and Hummingbot binary installed.",
        "connectors": list(CONNECTOR_ALIASES.keys()),
    })


_OPERATIONS = {
    "live_trade": _op_live_trade,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "live_trade": "Hummingbot Live Trade",
    "sources": "Hummingbot Sources",
}

_ALIASES = {
    "live": "live_trade",
    "trade_live": "live_trade",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "live_trade":
        cfg = value.get("config") or {}
        msg = value.get("message", "")
        if not record.get("ok"):
            return f"Live trade '{cfg.get('strategy')}' on {cfg.get('symbol')} - {msg or 'failed'}"
        return f"Live trade '{cfg.get('strategy')}' on {cfg.get('symbol')} started (rc={value.get('returncode')})."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run Hummingbot in live‑trading mode."""
    operation = (kwargs.get("operation") or "live_trade").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Hummingbot Live Trade",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Hummingbot Live Trade",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Hummingbot Live Trade",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Live trade error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Hummingbot Live Trade"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))