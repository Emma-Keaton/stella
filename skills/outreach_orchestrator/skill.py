"""
outreach_orchestrator — Orchestrate full outreach workflow: find leads, enrich emails, store in CRM, send mail.
"""

from __future__ import annotations

from typing import Any, Dict


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_plan(kwargs: dict) -> dict:
    query = (kwargs.get("query") or "").strip()
    if not query:
        return _op("plan", False, None, "Missing query.")
    max_results = max(1, min(int(kwargs.get("max_results", 10)), 50))
    return _op("plan", True, {
        "query": query,
        "max_results": max_results,
        "plan": [
            {"skill": "lead_finder", "params": {"query": query, "max_results": max_results}},
            {"skill": "email_enricher", "params": {"name": "<lead.name>", "company": "<lead.company>", "domain": "<lead.domain>"}},
            {"skill": "crm_tracker", "params": {"action": "create", "lead": "<enriched_lead>"}},
            {"skill": "mail_sender", "params": {"to": "<lead.email>", "template": "intro"}},
        ],
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["lead_finder", "email_enricher", "crm_tracker"],
        "content": "Orchestration plan using lead_finder, email_enricher, crm_tracker skills.",
    })


_OPERATIONS = {
    "plan": _op_plan,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "plan": "Outreach Plan",
    "sources": "Outreach Sources",
}

_ALIASES = {
    "outreach": "plan",
    "orchestrate": "plan",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "plan":
        plan = value.get("plan") or []
        return f"Outreach plan for '{value.get('query')}' — {len(plan)} step(s)."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Orchestrate full outreach workflow: find leads, enrich emails, store in CRM, send mail."""
    operation = (kwargs.get("operation") or "plan").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Outreach Orchestrator",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Outreach Orchestrator",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Outreach Orchestrator",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Outreach error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Outreach Orchestrator"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="plan", query="SaaS founders"))