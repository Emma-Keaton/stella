"""
smart_home_service - Smart home service layer for managing providers, accounts, and devices.
"""

from __future__ import annotations

from typing import Any, Dict


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_list_platforms(kwargs: dict) -> dict:
    return _op("list_platforms", True, {
        "platforms": [],
        "total": 0,
        "note": "Smart home providers available via smart_home_providers skill.",
    })


def _op_count_devices(kwargs: dict) -> dict:
    return _op("count_devices", True, {
        "count": 0,
        "note": "Device storage available via smart_home_storage skill.",
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["smart_home_providers", "smart_home_storage", "smart_device_manager"],
        "content": "Smart home service layer. Use smart_home_providers, smart_home_storage, and smart_device_manager skills for full functionality.",
    })


_OPERATIONS = {
    "list_platforms": _op_list_platforms,
    "count_devices": _op_count_devices,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "list_platforms": "List Platforms",
    "count_devices": "Count Devices",
    "sources": "Smart Home Sources",
}

_ALIASES = {
    "platforms": "list_platforms",
    "list_platforms": "list_platforms",
    "count": "count_devices",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "list_platforms":
        return f"{value.get('total')} platform(s) available."
    if operation == "count_devices":
        return f"{value.get('count')} device(s) in storage."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Smart home service layer for managing providers, accounts, and devices."""
    operation = (kwargs.get("operation") or "list_platforms").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Smart Home Service",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Smart Home Service",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Smart Home Service",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Service error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Smart Home Service"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))