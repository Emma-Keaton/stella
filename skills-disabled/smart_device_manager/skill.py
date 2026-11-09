"""
smart_device_manager — Singleton device manager for tracking active device context and routing commands.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


class SmartDeviceManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._active_device_id: Optional[str] = None
            self._active_device_name: Optional[str] = None
            self._initialized = True

    def set_active_device(self, device_id: Optional[str], device_name: Optional[str] = None):
        self._active_device_id = device_id
        self._active_device_name = device_name

    def get_active_device_id(self) -> Optional[str]:
        return self._active_device_id

    def get_active_device_name(self) -> Optional[str]:
        return self._active_device_name

    def route_command(self, text: str, devices: list[dict[str, Any]]) -> str:
        if not self._active_device_name:
            return text
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        any_name_mentioned = False
        for d in devices:
            d_name = d.get("name", "").lower()
            if d_name and d_name in normalized:
                any_name_mentioned = True
                break
        if any_name_mentioned:
            return text
        generic_patterns = [
            r"^(turn\s+)?(on|off)$",
            r"^switch\s+(on|off)$",
            r"^power\s+(on|off)$",
            r"^toggle$",
            r"^(increase|decrease|speed\s+up|slow\s+down|set\s+speed\s+to\s+\d+|speed\s+\d+)$",
            r"^(increase\s+brightness|decrease\s+brightness|brighten|dim|set\s+brightness\s+to\s+\d+|brightness\s+\d+%?)$",
            r"^(set\s+temperature\s+to\s+\d+|warm|neutral|cool)$",
        ]
        is_generic = False
        for pattern in generic_patterns:
            if re.search(pattern, normalized):
                is_generic = True
                break
        action_verbs = (
            "turn on", "turn off", "switch on", "switch off", "power on",
            "power off", "increase speed", "decrease speed", "set speed to",
            "set brightness to", "toggle",
        )
        if not is_generic:
            is_generic = normalized in action_verbs or any(
                normalized.startswith(verb + " ") for verb in action_verbs
            )
        if is_generic:
            device_name = self._active_device_name
            if "of" in normalized or "for" in normalized or "to" in normalized:
                return f"{text} {device_name}"
            else:
                return f"{text} of {device_name}"
        return text


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_set_device(kwargs: dict) -> dict:
    device_id = kwargs.get("device_id")
    device_name = kwargs.get("device_name")
    manager = SmartDeviceManager()
    manager.set_active_device(device_id, device_name)
    return _op("set_device", True, {
        "device_id": device_id,
        "device_name": device_name,
    })


def _op_get_device(kwargs: dict) -> dict:
    manager = SmartDeviceManager()
    return _op("get_device", True, {
        "device_id": manager.get_active_device_id(),
        "device_name": manager.get_active_device_name(),
    })


def _op_route(kwargs: dict) -> dict:
    text = kwargs.get("text", "")
    devices = kwargs.get("devices") or []
    manager = SmartDeviceManager()
    return _op("route", True, {"routed_command": manager.route_command(text, devices)})


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["local"],
        "content": "Local smart device manager for command routing.",
    })


_OPERATIONS = {
    "set_device": _op_set_device,
    "get_device": _op_get_device,
    "route": _op_route,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "set_device": "Set Active Device",
    "get_device": "Get Active Device",
    "route": "Route Command",
    "sources": "Device Sources",
}

_ALIASES = {
    "set_active_device": "set_device",
    "get_active_device": "get_device",
    "route_command": "route",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "set_device":
        return f"Active device set: {value.get('device_name')} ({value.get('device_id')})"
    if operation == "get_device":
        return f"Active device: {value.get('device_name')} ({value.get('device_id')})"
    if operation == "route":
        return f"Routed command: {value.get('routed_command')}"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Singleton device manager for tracking active device context and routing commands."""
    operation = (kwargs.get("operation") or "get_device").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Smart Device Manager",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Smart Device Manager",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Smart Device Manager",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Device error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Smart Device Manager"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="get_device"))
