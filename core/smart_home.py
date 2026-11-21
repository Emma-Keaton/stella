"""core/smart_home.py — Smart home / IoT control facade.

Thin service layer over the packaged smart-home skills (smart_home_service,
smart_home_providers, smart_home_storage, smart_device_manager) plus
python-kasa for direct TP-Link Kasa devices. Gives the agent one call surface:

    smart_home("turn on bedroom light")   -> natural language control
    smart_home_command("list_devices")    -> structured operations
    smart_home_command("control", {"device": ..., "state": ...})

Works fully offline for LAN protocols (kasa, Home Assistant local API);
cloud platforms are only contacted when the user configured them.
"""
from __future__ import annotations

import json
from typing import Any, Optional


def _skill_execute(skill: str, **kwargs) -> dict:
    try:
        import importlib
        mod = importlib.import_module(f"skills.{skill}.skill")
        return mod.execute(**kwargs)
    except Exception as e:
        return {"ok": False, "error": f"{skill}: {e}"}


def smart_home_command(operation: str, **params) -> dict:
    """Structured smart-home operations via the packaged skills."""
    params["operation"] = operation
    return _skill_execute("smart_home_service", **params)


def smart_home(nl: str) -> dict:
    """Natural-language smart home command, routed by the local LLM."""
    try:
        from core.local_brain import LocalBrain
        brain = LocalBrain()
        prompt = (
            "Convert this smart home command into a JSON action. "
            'Return only JSON like {"operation":"control","device":"bedroom light","state":"on"} '
            'or {"operation":"list_devices"}.\nCommand: ' + nl
        )
        raw = brain.generate(prompt) if hasattr(brain, "generate") else ""
        start = raw.find("{")
        end = raw.rfind("}")
        action = json.loads(raw[start:end + 1]) if start != -1 and end > start else {"operation": "unknown"}
        return smart_home_command(action.get("operation", "unknown"), **{k: v for k, v in action.items() if k != "operation"})
    except Exception as e:
        return {"ok": False, "error": str(e)}


def kasa_control(host: str, on: bool) -> dict:
    """Direct TP-Link Kasa plug control (offline LAN protocol)."""
    try:
        from kasa import SmartPlug
        plug = SmartPlug(host)
        import asyncio
        asyncio.run(plug.update())
        asyncio.run(plug.set_on(on) if hasattr(plug, "set_on") else (plug.turn_on() if on else plug.turn_off()))
        return {"ok": True, "host": host, "on": on}
    except Exception as e:
        return {"ok": False, "error": f"kasa: {e}"}


def list_platforms() -> dict:
    return _skill_execute("smart_home_service", operation="list_platforms")
