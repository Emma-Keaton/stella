"""
country_info — Get basic info about a country from REST Countries.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_lookup(kwargs: dict) -> dict:
    name = (kwargs.get("name") or "").strip()
    if not name:
        return _op("lookup", False, None, "Country name is required.")
    try:
        r = requests.get(f"https://restcountries.com/v3.1/name/{name}", timeout=15)
        if r.status_code == 404:
            return _op("lookup", False, None, f"Country '{name}' not found.")
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            c = data[0]
            name_obj = c.get("name", {}) or {}
            return _op("lookup", True, {
                "name": name_obj.get("common"),
                "official": name_obj.get("official"),
                "capital": (c.get("capital") or [""])[0] if c.get("capital") else "",
                "region": c.get("region"),
                "subregion": c.get("subregion"),
                "population": c.get("population"),
                "area": c.get("area"),
                "currencies": list((c.get("currencies") or {}).keys()),
                "languages": list((c.get("languages") or {}).values()),
                "flag": c.get("flag"),
            })
        return _op("lookup", False, None, "No data returned.")
    except Exception as exc:
        return _op("lookup", False, None, f"Failed to fetch country info: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["restcountries.com"],
        "content": "Country information powered by REST Countries (restcountries.com). No API key required.",
    })


_OPERATIONS = {
    "lookup": _op_lookup,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "lookup": "Country Info",
    "sources": "Country Sources",
}

_ALIASES = {
    "country": "lookup",
    "get_country": "lookup",
    "lookup_country": "lookup",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "lookup":
        return f"{value.get('name')} — Capital: {value.get('capital') or 'N/A'}, Region: {value.get('region') or 'N/A'}, Population: {value.get('population') or 'N/A'}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Get basic info about a country from REST Countries."""
    operation = (kwargs.get("operation") or "lookup").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Country Info",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Country Info",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Country Info",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Country error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Country Info"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="lookup", name="Canada"))