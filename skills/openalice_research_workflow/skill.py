"""skills/openalice_research_workflow/skill.py - OpenAlice research workflows."""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "openalice_research_workflow"
TASKS_FILE = DATA_DIR / "tasks.json"

FEATURE_METADATA = {
    "name": "openalice_research_workflow",
    "description": "OpenAlice-inspired research workflows: morning_scan, weekly_macro, thesis_check.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "morning_scan, weekly_macro, thesis_check, list_tasks, sources.", "default": "sources"},
            "symbols": {"type": "STRING", "description": "Comma-separated symbols for morning scan."},
            "thesis_id": {"type": "STRING", "description": "Thesis ID for thesis_check."},
            "thesis_name": {"type": "STRING", "description": "Thesis name."},
            "thesis_notes": {"type": "STRING", "description": "Notes for thesis."},
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "source": "openalice",
    "optional_dependencies": [],
    "tags": ["trading", "research", "openalice"],
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

def _op_morning_scan(symbols: str) -> dict:
    import urllib.request, urllib.parse
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else ["SPY", "QQQ", "DIA", "IWM"]
    results = []
    for sym in symbol_list:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + "?range=1d&interval=1d"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            price = meta.get("regularMarketPrice")
            prev_close = meta.get("previousClose")
            change = None; change_pct = None
            if price is not None and prev_close:
                change = price - prev_close; change_pct = (change / prev_close) * 100
            results.append({"symbol": sym, "price": price, "change": round(change, 2) if change is not None else None, "change_pct": round(change_pct, 2) if change_pct is not None else None, "market_state": meta.get("marketState", "")})
        except Exception:
            results.append({"symbol": sym, "price": None, "error": "Data unavailable"})
    return {"ok": True, "scan_type": "morning", "symbols": results, "count": len(results), "timestamp": time.time()}


def _op_weekly_macro() -> dict:
    return {"ok": True, "review_type": "weekly_macro", "summary": "Weekly macro review: Monitor key macro indicators (interest rates, inflation, employment, GDP) and their impact on asset classes. Review open positions for macro risk exposure.", "checklist": ["Review Fed policy stance and interest rate outlook", "Check CPI/PCE inflation data trends", "Review employment reports", "Check GDP growth", "Assess currency impacts", "Check commodity prices", "Scan open positions for macro risk exposure"], "timestamp": time.time()}


def _op_thesis_check(thesis_id: str, thesis_name: str, thesis_notes: str) -> dict:
    tasks = _load(TASKS_FILE, [])
    if thesis_id:
        for task in tasks:
            if task.get("thesis_id") == thesis_id:
                if thesis_notes:
                    task["notes"] = thesis_notes; task["updated_at"] = time.time(); _save(TASKS_FILE, tasks)
                return {"ok": True, "thesis": task}
        return {"ok": False, "error": "Thesis '" + thesis_id + "' not found."}
    for task in tasks:
        if task.get("thesis_name") == thesis_name:
            if thesis_notes:
                task["notes"] = thesis_notes; task["updated_at"] = time.time(); _save(TASKS_FILE, tasks)
            return {"ok": True, "thesis": task, "updated": bool(thesis_notes)}
    new_id = str(uuid.uuid4())
    task = {"thesis_id": new_id, "thesis_name": thesis_name, "notes": thesis_notes or "", "status": "active", "created_at": time.time(), "updated_at": time.time()}
    tasks.append(task); _save(TASKS_FILE, tasks)
    return {"ok": True, "thesis": task, "created": True}


def _op_list_tasks() -> dict:
    tasks = _load(TASKS_FILE, [])
    tasks.sort(key=lambda t: t.get("updated_at", 0), reverse=True)
    return {"ok": True, "tasks": tasks, "count": len(tasks)}


def _op_sources() -> dict:
    return {"ok": True, "source": "openalice", "skill": "openalice_research_workflow", "description": "OpenAlice research workflows: morning_scan, weekly_macro, thesis_check.", "operations": ["morning_scan", "weekly_macro", "thesis_check", "list_tasks", "sources"], "api_key_required": False}

_OPERATIONS = {"morning_scan": _op_morning_scan, "weekly_macro": _op_weekly_macro, "thesis_check": _op_thesis_check, "list_tasks": _op_list_tasks, "sources": _op_sources}
_OPERATION_TITLES = {"morning_scan": "Morning Scan", "weekly_macro": "Weekly Macro", "thesis_check": "Thesis Check", "list_tasks": "Tasks", "sources": "Sources"}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "OpenAlice Research Workflow", "summary": "Unknown operation '" + operation + "'.", "ok": False, "operation": operation}
    try:
        if operation == "morning_scan":
            record = handler(kwargs.get("symbols", ""))
        elif operation == "weekly_macro":
            record = handler()
        elif operation == "thesis_check":
            record = handler(kwargs.get("thesis_id", ""), kwargs.get("thesis_name", ""), kwargs.get("thesis_notes", ""))
        elif operation == "list_tasks":
            record = handler()
        else:
            record = handler()
    except TypeError as exc:
        return {"title": "OpenAlice Research Workflow", "summary": "Bad arguments for '" + operation + "': " + str(exc), "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "OpenAlice Research Workflow", "summary": str(type(exc).__name__) + ": " + str(exc), "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "OpenAlice Research Workflow"), "summary": str(record.get("error", record))[:200] if not record.get("ok") else str(record)[:200], "ok": bool(record.get("ok")), "operation": operation, "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))
