from __future__ import annotations
from typing import Any, Dict
import subprocess, tempfile, json, os, pathlib, importlib.util

FEATURE_METADATA = {
    "name": "hummingbot_backtest",
    "description": "Run a Hummingbot backtest for any supported market (CEX, DEX, Polymarket, Forex, ...).",
    "triggers": ["backtest"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "strategy": {"type": "STRING", "description": "Hummingbot strategy name (e.g. pure_market_making)"},
            "symbol": {"type": "STRING", "description": "Trading pair, e.g. ETH-USDT, BTC/USD, POLY/USDC"},
            "exchange": {"type": "STRING", "description": "Hummingbot connector name – see list below", "default": "binance"},
            "start_date": {"type": "STRING", "description": "YYYY-MM-DD (optional)"},
            "end_date": {"type": "STRING", "description": "YYYY-MM-DD (optional)"},
            "config_overrides": {"type": "OBJECT", "description": "Any extra Hummingbot config keys/values", "default": {}}
        },
        "required": ["strategy", "symbol"]
    }
}

# Mapping of user‑friendly market names → Hummingbot connector IDs
CONNECTOR_ALIASES = {
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
    key = user_input.strip().lower()
    return CONNECTOR_ALIASES.get(key, key)

def _make_backtest_config(params: Dict[str, Any]) -> Dict[str, Any]:
    connector = _resolve_connector(params.get("exchange", "binance"))
    cfg = {
        "strategy": params["strategy"],
        "market": connector,
        "symbol": params["symbol"],
        "start_date": params.get("start_date"),
        "end_date": params.get("end_date"),
    }
    cfg.update(params.get("config_overrides", {}))
    return cfg

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    # ---- 1️⃣ Validate required args -------------------------------------------------
    for req in ("strategy", "symbol"):
        if not params.get(req):
            return {"ok": False, "error": f"Missing required parameter: {req}"}

    # ---- 2️⃣ Ensure Hummingbot is installed -----------------------------------------
    installer_path = pathlib.Path(r"E:\Projects\stella\skills\hummingbot_installer\skill.py")
    spec = importlib.util.spec_from_file_location("installer", installer_path)
    installer_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer_mod)
    install_res = installer_mod.run({"force_reinstall": False})
    if not install_res.get("ok"):
        return {"ok": False, "error": f"Hummingbot install failed: {install_res.get('error')}"}
    hummingbot_bin = install_res["hummingbot_bin"]

    # ---- 3️⃣ Build config file -------------------------------------------------------
    cfg = _make_backtest_config(params)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        json.dump(cfg, tf, indent=2)
        config_path = tf.name

    # ---- 4️⃣ Execute backtest --------------------------------------------------------
    try:
        cmd = [hummingbot_bin, "backtest", "--config", config_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "config": cfg
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Backtest timed out after 10 minutes"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            os.unlink(config_path)
        except Exception:
            pass