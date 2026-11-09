"""skills/stella_trading_orderflow/skill.py - Order Flow Integration"""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "stella_trading_orderflow"
FEATURE_METADATA = {"name": "stella_trading_orderflow", "description": "Order flow analysis", "version": "1.0.0", "active": True, "source": "orderflow-integrated", "tags": ["trading", "orderflow"]}

def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _op_sources():
    return {"ok": True, "source": "orderflow-integrated", "skill": "stella_trading_orderflow", "operations": ["orderflow_heatmap", "sources"]}

_OPERATIONS = {"sources": _op_sources}

def execute(**kwargs):
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "Stella Trading Order Flow", "ok": False}
    try:
        record = handler()
    except Exception as exc:
        return {"title": "Stella Trading Order Flow", "ok": False, "error": str(exc)}
    return {"title": "Stella Trading Order Flow", "ok": True, "operation": operation, "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))