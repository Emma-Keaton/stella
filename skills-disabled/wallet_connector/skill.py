"""
wallet_connector — Securely store exchange API keys and mark wallet as connected.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

_VAULT_PATH = Path(os.getenv("STELLA_DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data")) / "wallets.json"


def _load_vault() -> Dict[str, Any]:
    if not _VAULT_PATH.exists():
        return {}
    try:
        return json.loads(_VAULT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_vault(data: Dict[str, Any]) -> None:
    _VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _VAULT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_connect(kwargs: dict) -> dict:
    exchange = (kwargs.get("exchange") or "").strip()
    api_key = (kwargs.get("api_key") or "").strip()
    api_secret = (kwargs.get("api_secret") or "").strip()
    passphrase = (kwargs.get("passphrase") or "").strip()
    if not exchange or not api_key or not api_secret:
        return _op("connect", False, None, "Missing exchange, api_key or api_secret.")
    vault = _load_vault()
    vault[exchange.lower()] = {
        "api_key": api_key,
        "api_secret": api_secret,
        "passphrase": passphrase,
    }
    _save_vault(vault)
    os.environ["WALLET_CONNECTED"] = "1"
    return _op("connect", True, {
        "exchange": exchange,
        "connected": True,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["local_json"],
        "content": "Wallet keys stored locally in wallets.json.",
    })


_OPERATIONS = {
    "connect": _op_connect,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "connect": "Connect Wallet",
    "sources": "Wallet Sources",
}

_ALIASES = {
    "connect_wallet": "connect",
    "add_wallet": "connect",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "connect":
        return f"Wallet connected for exchange '{value.get('exchange')}'."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Securely store exchange API keys and mark wallet as connected."""
    operation = (kwargs.get("operation") or "connect").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Wallet Connector",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Wallet Connector",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Wallet Connector",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Wallet error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Wallet Connector"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))