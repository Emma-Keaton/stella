"""
crm_tracker — Local CRM for outreach leads.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

_DB_PATH = Path(os.getenv("STELLA_DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data")) / "crm_leads.json"


def _load_leads() -> Dict[str, dict]:
    if not _DB_PATH.exists():
        return {}
    try:
        return json.loads(_DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_leads(data: Dict[str, dict]) -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DB_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_create(kwargs: dict) -> dict:
    data = _load_leads()
    lead = kwargs.get("lead") or {}
    lead_id = (lead.get("email") or lead.get("name") or "").strip()
    if not lead_id:
        return _op("create", False, None, "Lead needs a name or email.")
    data[lead_id] = {
        "created": __import__("datetime").date.today().isoformat(),
        **lead,
    }
    _save_leads(data)
    return _op("create", True, {"id": lead_id, "lead": data[lead_id], "total": len(data)})


def _op_list(kwargs: dict) -> dict:
    data = _load_leads()
    status = (kwargs.get("status") or "").strip()
    leads = list(data.values())
    if status:
        leads = [l for l in leads if l.get("status", "").lower() == status.lower()]
    return _op("list", True, {"leads": leads, "total": len(leads)})


def _op_update(kwargs: dict) -> dict:
    lead_id = (kwargs.get("id") or "").strip()
    data = _load_leads()
    if lead_id not in data:
        return _op("update", False, None, f"Lead '{lead_id}' not found.")
    lead = kwargs.get("lead") or {}
    data[lead_id].update(lead)
    _save_leads(data)
    return _op("update", True, {"id": lead_id, "lead": data[lead_id], "total": len(data)})


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["local_json"],
        "content": "Local CRM stored in crm_leads.json.",
    })


_OPERATIONS = {
    "create": _op_create,
    "list": _op_list,
    "update": _op_update,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "create": "Create Lead",
    "list": "List Leads",
    "update": "Update Lead",
    "sources": "CRM Sources",
}

_ALIASES = {
    "add": "create",
    "add_lead": "create",
    "get_leads": "list",
    "list_leads": "list",
    "edit_lead": "update",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "create":
        return f"Created lead '{value.get('id')}' — total: {value.get('total')}"
    if operation == "list":
        return f"{value.get('total')} lead(s)."
    if operation == "update":
        return f"Updated lead '{value.get('id')}' — total: {value.get('total')}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Local CRM for outreach leads."""
    operation = (kwargs.get("operation") or "list").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "CRM Tracker",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "CRM Tracker",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "CRM Tracker",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"CRM error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "CRM Tracker"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="list"))