from __future__ import annotations
from typing import Any, Dict
import os, json, pathlib, getpass

FEATURE_METADATA = {
    "name": "wallet_connector",
    "description": "Securely store exchange API keys and mark wallet as connected.",
    "triggers": ["connect wallet"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "exchange": {"type": "STRING"},
            "api_key": {"type": "STRING"},
            "api_secret": {"type": "STRING"},
            "passphrase": {"type": "STRING", "description": "Optional passphrase for some exchanges"}
        },
        "required": ["exchange", "api_key", "api_secret"]
    }
}

VAULT_PATH = pathlib.Path(r"E:\Projects\stella\data\wallets.json")
VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)

def _load_vault() -> Dict[str, Any]:
    if VAULT_PATH.exists():
        return json.loads(VAULT_PATH.read_text())
    return {}

def _save_vault(data: Dict[str, Any]) -> None:
    VAULT_PATH.write_text(json.dumps(data, indent=2))

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    exchange = params.get("exchange")
    api_key = params.get("api_key")
    api_secret = params.get("api_secret")
    passphrase = params.get("passphrase")
    if not exchange or not api_key or not api_secret:
        return {"ok": False, "error": "Missing exchange, api_key or api_secret"}
    vault = _load_vault()
    vault[exchange.lower()] = {
        "api_key": api_key,
        "api_secret": api_secret,
        "passphrase": passphrase
    }
    _save_vault(vault)
    # Mark wallet as connected for this process
    os.environ["WALLET_CONNECTED"] = "1"
    return {"ok": True, "exchange": exchange, "connected": True}