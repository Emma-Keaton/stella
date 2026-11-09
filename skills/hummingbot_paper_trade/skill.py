from __future__ import annotations
from typing import Any, Dict
import subprocess, tempfile, json, os, pathlib, importlib.util

FEATURE_METADATA = {
    "name": "hummingbot_paper_trade",
    "description": "Run Hummingbot in paper‑trading mode for a given strategy.",
    "triggers": ["paper trade"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "strategy": {"type": "STRING", "description": "Strategy name"},
            "symbol": {"type": "STRING", "description": "Trading pair"},
            "exchange": {"type": "STRING", "description": "Connector name", "default": "binance"},
            "config_overrides": {"type": "OBJECT", "default": {}}
        },
        "required": ["strategy", "symbol"]
    }
}

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
    return CONNECTOR_ALIASES.get(user_input.strip().lower(), user_input.strip().lower())

def _make_paper_config(params: Dict[str, Any]) -> Dict[str, Any]:
    connector = _resolve_connector(params.get("exchange", "binance"))
    cfg = {
        "strategy": params["strategy"],
        "market": connector,
        "symbol": params["symbol"],
        "paper_trade": True
    }
    cfg.update(params.get("config_overrides", {}))
    return cfg

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    for req in ("strategy", "symbol"):
        if not params.get(req):
            return {"ok": False, "error": f"Missing required parameter: {req}"}

    # Ensure hummingbot installed
    installer_path = pathlib.Path(r"E:\Projects\stella\skills\hummingbot_installer\skill.py")
    spec = importlib.util.spec_from_file_location("installer", installer_path)
    installer_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer_mod)
    install_res = installer_mod.run({"force_reinstall": False})
    if not install_res.get("ok"):
        return {"ok": False, "error": f"Hummingbot install failed: {install_res.get('error')}"}
    hummingbot_bin = install_res["hummingbot_bin"]

    cfg = _make_paper_config(params)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        json.dump(cfg, tf, indent=2)
        config_path = tf.name

    try:
        # Assuming hummingbot supports --paper flag or reads paper_trade from config
        cmd = [hummingbot_bin, "start", "--config", config_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "config": cfg
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Paper trade startup timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            os.unlink(config_path)
        except Exception:
            pass