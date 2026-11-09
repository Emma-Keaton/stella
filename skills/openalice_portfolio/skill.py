"""skills/openalice_portfolio/skill.py - OpenAlice-inspired portfolio."""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "openalice_portfolio"
POSITIONS_FILE = DATA_DIR / "positions.json"
TRADES_FILE = DATA_DIR / "trades.json"

FEATURE_METADATA = {
    "name": "openalice_portfolio",
    "description": "OpenAlice-inspired portfolio: positions, P&L, holdings, account state.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "positions, pnl, holdings, account, add_position, remove_position, sources.", "default": "account"},
            "symbol": {"type": "STRING", "description": "Ticker symbol."},
            "quantity": {"type": "NUMBER", "description": "Number of shares/units."},
            "avg_cost": {"type": "NUMBER", "description": "Average cost per share/unit."},
            "asset_class": {"type": "STRING", "description": "stocks, crypto, forex, options, futures.", "default": "stocks"},
            "position_id": {"type": "STRING", "description": "Position ID for remove_position."},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "source": "openalice",
    "optional_dependencies": [],
    "tags": ["trading", "portfolio", "openalice", "positions", "pnl"],
}

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

def _op_positions() -> dict:
    positions = _load(POSITIONS_FILE, [])
    return {"ok": True, "positions": positions, "count": len(positions)}


def _op_pnl() -> dict:
    positions = _load(POSITIONS_FILE, [])
    trades = _load(TRADES_FILE, [])
    total_cost = 0.0; total_value = 0.0; realized_pnl = 0.0
    for pos in positions:
        qty = pos.get("quantity", 0); avg_cost = pos.get("avg_cost", 0)
        current_price = pos.get("current_price", avg_cost)
        total_cost += qty * avg_cost; total_value += qty * current_price
    for trade in trades:
        if trade.get("type") == "sell":
            realized_pnl += trade.get("quantity", 0) * (trade.get("price", 0) - trade.get("avg_cost", 0))
    unrealized_pnl = total_value - total_cost
    return {"ok": True, "total_cost": round(total_cost, 2), "total_value": round(total_value, 2), "unrealized_pnl": round(unrealized_pnl, 2), "realized_pnl": round(realized_pnl, 2), "total_pnl": round(unrealized_pnl + realized_pnl, 2), "positions_count": len(positions)}


def _op_holdings() -> dict:
    positions = _load(POSITIONS_FILE, [])
    holdings = {}
    for pos in positions:
        symbol = pos.get("symbol", "UNKNOWN")
        if symbol not in holdings:
            holdings[symbol] = {"symbol": symbol, "asset_class": pos.get("asset_class", "stocks"), "total_quantity": 0, "total_cost": 0.0}
        holdings[symbol]["total_quantity"] += pos.get("quantity", 0)
        holdings[symbol]["total_cost"] += pos.get("quantity", 0) * pos.get("avg_cost", 0)
    return {"ok": True, "holdings": list(holdings.values()), "count": len(holdings)}


def _op_account() -> dict:
    positions = _load(POSITIONS_FILE, [])
    pnl = _op_pnl()
    holdings = _op_holdings()
    return {"ok": True, "account_id": "stella-openalice-uta", "positions_count": len(positions), "holdings_count": holdings["count"], "total_value": pnl["total_value"], "total_cost": pnl["total_cost"], "unrealized_pnl": pnl["unrealized_pnl"], "realized_pnl": pnl["realized_pnl"], "total_pnl": pnl["total_pnl"]}


def _op_add_position(symbol: str, quantity: float, avg_cost: float, asset_class: str) -> dict:
    if not symbol:
        return {"ok": False, "error": "Symbol required."}
    positions = _load(POSITIONS_FILE, [])
    position = {"position_id": str(uuid.uuid4()), "symbol": symbol.upper(), "quantity": quantity, "avg_cost": avg_cost, "current_price": avg_cost, "asset_class": asset_class, "created_at": time.time(), "updated_at": time.time()}
    positions.append(position)
    _save(POSITIONS_FILE, positions)
    return {"ok": True, "position_id": position["position_id"], "position": position}


def _op_remove_position(position_id: str) -> dict:
    positions = _load(POSITIONS_FILE, [])
    for i, pos in enumerate(positions):
        if pos.get("position_id") == position_id:
            removed = positions.pop(i); _save(POSITIONS_FILE, positions)
            return {"ok": True, "removed": removed}
    return {"ok": False, "error": "Position '" + position_id + "' not found."}


def _op_sources() -> dict:
    return {"ok": True, "source": "openalice", "skill": "openalice_portfolio", "description": "OpenAlice-inspired portfolio management.", "operations": ["positions", "pnl", "holdings", "account", "add_position", "remove_position", "sources"], "asset_classes": ["stocks", "crypto", "forex", "options", "futures"], "api_key_required": False}

_OPERATIONS = {"positions": _op_positions, "pnl": _op_pnl, "holdings": _op_holdings, "account": _op_account, "add_position": _op_add_position, "remove_position": _op_remove_position, "sources": _op_sources}
_OPERATION_TITLES = {"positions": "Positions", "pnl": "P&L", "holdings": "Holdings", "account": "Account", "add_position": "Add Position", "remove_position": "Remove Position", "sources": "Sources"}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "account").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "OpenAlice Portfolio", "summary": "Unknown operation '" + operation + "'.", "ok": False, "operation": operation}
    try:
        if operation == "add_position":
            record = handler(kwargs.get("symbol", ""), kwargs.get("quantity", 0), kwargs.get("avg_cost", 0), kwargs.get("asset_class", "stocks"))
        elif operation == "remove_position":
            record = handler(kwargs.get("position_id", ""))
        else:
            record = handler()
    except TypeError as exc:
        return {"title": "OpenAlice Portfolio", "summary": "Bad arguments for '" + operation + "': " + str(exc), "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "OpenAlice Portfolio", "summary": str(type(exc).__name__) + ": " + str(exc), "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "OpenAlice Portfolio"), "summary": str(record.get("error", record))[:200] if not record.get("ok") else str(record)[:200], "ok": bool(record.get("ok")), "operation": operation, "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))
