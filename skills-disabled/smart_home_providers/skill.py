"""
smart_home_providers — Smart home device providers for integrating with various smart home platforms.
"""

from __future__ import annotations

from typing import Any, Dict


class ProviderField:
    def __init__(self, key: str, label: str, secret: bool = False):
        self.key = key
        self.label = label
        self.secret = secret

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "secret": self.secret}


class SmartHomeProvider:
    key = "base"
    name = "Base Provider"

    def auth_fields(self) -> list[dict]:
        return []

    def authenticate(self, credentials: dict) -> dict:
        return {"credentials": credentials, "account_label": "default"}

    def discover_devices(self, credentials: dict) -> list[dict]:
        return []

    def execute(self, device: str, action: str, payload: dict) -> dict:
        return {"ok": False, "error": "execute not implemented"}

    def get_status(self, device: str) -> dict:
        return {"ok": False, "error": "get_status not implemented"}


def built_in_provider_classes() -> list[type]:
    return [SmartHomeProvider]


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_list(kwargs: dict) -> dict:
    return _op("list", True, {
        "providers": [p.key for p in built_in_provider_classes()],
        "total": len(built_in_provider_classes()),
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["local"],
        "content": "Smart home provider classes defined locally.",
    })


_OPERATIONS = {
    "list": _op_list,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "list": "List Providers",
    "sources": "Provider Sources",
}

_ALIASES = {
    "list_providers": "list",
    "providers": "list",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "list":
        return f"{value.get('total')} provider(s): {', '.join(value.get('providers') or [])}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Smart home device providers for integrating with various smart home platforms."""
    operation = (kwargs.get("operation") or "list").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Smart Home Providers",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Smart Home Providers",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Smart Home Providers",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Provider error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Smart Home Providers"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="list"))