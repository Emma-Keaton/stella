"""
Feature: memory_inspector
Description: Inspects Stella's durable memory store - lists every remembered fact with tags and timestamps, searches by keyword, reports counts, and (with confirm=true) clears the store. Never invents memories; reports exactly what is on disk.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

FEATURE_METADATA = {
    "name": "memory_inspector",
    "aliases": ["memory_inspector", "inspect memory", "what stella remembers",
                "memory inspector", "show memories", "stored facts",
                "recall all", "memory audit"],
    "description": (
        "Inspects Stella's durable memory store: lists every remembered fact "
        "with its tags and timestamp, searches by keyword, reports the count, "
        "and - with confirm=true - clears the store. Never invents memories; "
        "reports exactly what is on disk, or that nothing is stored."
    ),
    "triggers": [
        "inspect memory", "what stella remembers", "memory inspector",
        "show memories", "stored facts", "recall all", "memory audit",
        "what do I remember", "list memories",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: list | search | count | clear. Defaults to list.",
            },
            "query": {
                "type": "STRING",
                "description": "Keyword to search memories by (search operation).",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum facts to return. Defaults to 100.",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to actually clear the store. Defaults to false.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "memory",
    "surface": "both",
    "requires": [],
    "optional_dependencies": [],
    "notes": "Reads agent/memory.py's memories.jsonl under the user data dir. Clearing is destructive: confirm=true required.",
}


def _store() -> Path:
    base = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
    d = Path(base) / "StellaAI" / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d / "memories.jsonl"


def _load() -> list[dict]:
    path = _store()
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("fact"):
                rows.append(obj)
    except OSError:
        return []
    return rows


def _terms(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower())}


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_list(kwargs: dict) -> dict:
    limit = _as_int(kwargs.get("limit"), 100)
    rows = _load()[-limit:]
    return _op("list", True, {
        "facts": rows,
        "count": len(rows),
        "total_on_disk": len(_load()),
    })


def _op_search(kwargs: dict) -> dict:
    query = (kwargs.get("query") or "").strip()
    limit = _as_int(kwargs.get("limit"), 100)
    if not query:
        return _op("search", False, None, "query is required for search")
    q = _terms(query)
    if not q:
        return _op("search", True, {"facts": [], "count": 0, "query": query})
    scored = []
    for row in _load():
        fact = row.get("fact", "")
        f_terms = _terms(fact)
        if not f_terms:
            continue
        overlap = len(q & f_terms) / len(q)
        if overlap > 0:
            scored.append((overlap, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    facts = [row for _, row in scored[:limit]]
    return _op("search", True, {
        "facts": facts,
        "count": len(facts),
        "query": query,
    })


def _op_count(kwargs: dict) -> dict:
    rows = _load()
    return _op("count", True, {
        "count": len(rows),
    })


def _op_clear(kwargs: dict) -> dict:
    confirm = kwargs.get("confirm") in (True, "true", "True", 1, "1")
    if not confirm:
        return _op("clear", False, None, (
            "Clearing memory was not started because confirm was not set. "
            "Set confirm=true to delete every stored memory."))
    path = _store()
    n = len(_load())
    try:
        path.unlink()
    except OSError:
        return _op("clear", False, None, "could not remove memory file")
    return _op("clear", True, {"removed": n})


def _as_int(value, default: int = 100, ceiling: int = 1000) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


_OPERATIONS = {
    "list": _op_list,
    "search": _op_search,
    "count": _op_count,
    "clear": _op_clear,
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "list":
        return f"{value.get('count')} fact(s) in memory ({value.get('total_on_disk')} total on disk)."
    if operation == "search":
        return f"{value.get('count')} fact(s) matched '{value.get('query')}'."
    if operation == "count":
        return f"{value.get('count')} fact(s) stored."
    if operation == "clear":
        if not record.get("ok"):
            return f"Not cleared: {record.get('error')}"
        return f"Cleared {value.get('removed')} fact(s)."
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Inspect Stella's memory store."""
    operation = (kwargs.get("operation") or "list").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Memory Inspector",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }

    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Memory Inspector",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Memory Inspector",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Memory inspector error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }

    return {
        "title": "Memory Inspector",
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="count"))
