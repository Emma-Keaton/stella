"""
email_enricher — Enrich leads with email addresses using Hunter.io or fallback pattern.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_enrich(kwargs: dict) -> dict:
    name = (kwargs.get("name") or "").strip()
    company = (kwargs.get("company") or "").strip()
    domain = (kwargs.get("domain") or "").strip()
    if not name or not company:
        return _op("enrich", False, None, "Missing name or company.")
    hunter_key = os.getenv("HUNTER_API_KEY")
    if hunter_key and domain:
        try:
            parts = name.split()
            first = parts[0]
            last = " ".join(parts[1:]) if len(parts) > 1 else ""
            url = "https://api.hunter.io/v2/email-finder"
            r = requests.get(
                url,
                params={
                    "domain": domain,
                    "first_name": first,
                    "last_name": last,
                    "api_key": hunter_key,
                },
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            email = data.get("data", {}).get("email")
            if email:
                return _op("enrich", True, {
                    "name": name,
                    "company": company,
                    "email": email,
                    "source": "hunter",
                })
        except Exception:
            pass
    email = f"{name.lower().replace(' ', '.')}@{company.lower().replace(' ', '')}.com"
    return _op("enrich", True, {
        "name": name,
        "company": company,
        "email": email,
        "source": "pattern",
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["hunter.io", "pattern"],
        "content": "Email enrichment via Hunter.io API (key optional) or local pattern fallback.",
    })


_OPERATIONS = {
    "enrich": _op_enrich,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "enrich": "Email Enrichment",
    "sources": "Email Sources",
}

_ALIASES = {
    "enrich_email": "enrich",
    "enrich_lead": "enrich",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "enrich":
        return f"{value.get('name')} <{value.get('email')}> at {value.get('company')} (source: {value.get('source')})"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Enrich leads with email addresses using Hunter.io or fallback pattern."""
    operation = (kwargs.get("operation") or "enrich").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Email Enricher",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Email Enricher",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Email Enricher",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Email error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Email Enricher"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="enrich", name="Jane Doe", company="Acme", domain="acme.com"))