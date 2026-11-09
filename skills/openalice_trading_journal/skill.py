"""skills/openalice_trading_journal/skill.py - OpenAlice-inspired trading journal."""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "openalice_trading_journal"
ENTRIES_FILE = DATA_DIR / "entries.json"

FEATURE_METADATA = {
    "name": "openalice_trading_journal",
    "description": "OpenAlice-inspired trading journal: add entries, list, review, summary.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "add_entry, list_entries, review_entry, summary, sources.", "default": "summary"},
            "symbol": {"type": "STRING", "description": "Ticker symbol."},
            "side": {"type": "STRING", "description": "buy or sell."},
            "quantity": {"type": "NUMBER", "description": "Number of shares/units."},
            "price": {"type": "NUMBER", "description": "Entry price per share/unit."},
            "rationale": {"type": "STRING", "description": "Reasoning behind the trade."},
            "entry_id": {"type": "STRING", "description": "Entry ID for review_entry."},
            "outcome": {"type": "STRING", "description": "Outcome notes for review_entry."},
            "status": {"type": "STRING", "description": "Filter: open, closed, all.", "default": "all"},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "source": "openalice",
    "optional_dependencies": [],
    "tags": ["trading", "journal", "openalice"],
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

def _op_add_entry(symbol: str, side: str, quantity: float, price: float, rationale: str) -> dict:
    if not symbol:
        return {"ok": False, "error": "Symbol required."}
    entries = _load(ENTRIES_FILE, [])
    entry = {"entry_id": str(uuid.uuid4()), "symbol": symbol.upper(), "side": side.lower(), "quantity": quantity, "price": price, "rationale": rationale, "status": "open", "created_at": time.time(), "updated_at": time.time(), "outcome": None, "exit_price": None, "pnl": None}
    entries.append(entry)
    _save(ENTRIES_FILE, entries)
    return {"ok": True, "entry_id": entry["entry_id"], "entry": entry}


def _op_list_entries(status: str) -> dict:
    entries = _load(ENTRIES_FILE, [])
    if status and status != "all":
        entries = [e for e in entries if e.get("status") == status]
    entries.sort(key=lambda e: e.get("created_at", 0), reverse=True)
    return {"ok": True, "entries": entries, "count": len(entries)}


def _op_review_entry(entry_id: str, outcome: str) -> dict:
    entries = _load(ENTRIES_FILE, [])
    for i, entry in enumerate(entries):
        if entry.get("entry_id") == entry_id:
            entries[i]["status"] = "closed"
            entries[i]["outcome"] = outcome
            entries[i]["updated_at"] = time.time()
            _save(ENTRIES_FILE, entries)
            return {"ok": True, "entry": entries[i]}
    return {"ok": False, "error": "Entry '" + entry_id + "' not found."}


def _op_summary() -> dict:
    entries = _load(ENTRIES_FILE, [])
    open_count = sum(1 for e in entries if e.get("status") == "open")
    closed_count = sum(1 for e in entries if e.get("status") == "closed")
    total_pnl = sum(e.get("pnl") or 0 for e in entries if e.get("pnl") is not None)
    winning = sum(1 for e in entries if e.get("pnl", 0) > 0)
    losing = sum(1 for e in entries if e.get("pnl", 0) < 0)
    win_rate = (winning / closed_count * 100) if closed_count > 0 else 0
    return {"ok": True, "total_entries": len(entries), "open_count": open_count, "closed_count": closed_count, "total_pnl": round(total_pnl, 2), "winning_trades": winning, "losing_trades": losing, "win_rate": round(win_rate, 1)}


def _op_sources() -> dict:
    return {"ok": True, "source": "openalice", "skill": "openalice_trading_journal", "description": "OpenAlice-inspired trading journal: add entries, list, review, summary.", "operations": ["add_entry", "list_entries", "review_entry", "summary", "sources"], "sides": ["buy", "sell"], "statuses": ["open", "closed", "all"], "api_key_required": False}

_OPERATIONS = {"add_entry": _op_add_entry, "list_entries": _op_list_entries, "review_entry": _op_review_entry, "summary": _op_summary, "sources": _op_sources}
_OPERATION_TITLES = {"add_entry": "Add Entry", "list_entries": "List Entries", "review_entry": "Review Entry", "summary": "Summary", "sources": "Sources"}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "summary").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "OpenAlice Trading Journal", "summary": "Unknown operation '" + operation + "'.", "ok": False, "operation": operation}
    try:
        if operation == "add_entry":
            record = handler(kwargs.get("symbol", ""), kwargs.get("side", ""), kwargs.get("quantity", 0), kwargs.get("price", 0), kwargs.get("rationale", ""))
        elif operation == "list_entries":
            record = handler(kwargs.get("status", "all"))
        elif operation == "review_entry":
            record = handler(kwargs.get("entry_id", ""), kwargs.get("outcome", ""))
        else:
            record = handler()
    except TypeError as exc:
        return {"title": "OpenAlice Trading Journal", "summary": "Bad arguments for '" + operation + "': " + str(exc), "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "OpenAlice Trading Journal", "summary": str(type(exc).__name__) + ": " + str(exc), "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "OpenAlice Trading Journal"), "summary": str(record.get("error", record))[:200] if not record.get("ok") else str(record)[:200], "ok": bool(record.get("ok")), "operation": operation, "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))
