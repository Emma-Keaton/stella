"""core/reflex.py — Tier-1 Instant Action Reflexes (<15ms).

High-frequency device commands bypass the LLM loop entirely: a regex
fast-path maps common phrasings straight onto core.device_command_handler,
which works on Windows, macOS, Linux and (via the Android bridge) mobile.
Anything not recognised returns None and falls through to the agent loop.
"""
from __future__ import annotations

import re
import time
import urllib.parse
from typing import Optional, Tuple

from core.device_command_handler import handle_device_command

_RULES = [
    (re.compile(r"^\s*(?:volume|set volume)\s*(?:to\s*)?(\d{1,3})\s*%?\s*$", re.I), "volume", lambda m: {"level": int(m.group(1))}),
    (re.compile(r"^\s*(?:volume up|turn (?:the )?volume up|increase volume)\s*$", re.I), "volume_up", None),
    (re.compile(r"^\s*(?:volume down|turn (?:the )?volume down|decrease volume)\s*$", re.I), "volume_down", None),
    (re.compile(r"^\s*(?:mute|unmute|toggle mute)\s*$", re.I), "mute", None),
    (re.compile(r"^\s*(?:get|what(?:'s| is) the) volume\s*$", re.I), "get_volume", None),
    (re.compile(r"^\s*(?:brightness|set brightness)\s*(?:to\s*)?(\d{1,3})\s*%?\s*$", re.I), "brightness", lambda m: {"level": int(m.group(1))}),
    (re.compile(r"^\s*(?:brightness up|increase brightness)\s*$", re.I), "brightness_up", None),
    (re.compile(r"^\s*(?:brightness down|decrease brightness)\s*$", re.I), "brightness_down", None),
    (re.compile(r"^\s*(?:get|what(?:'s| is) the) brightness\s*$", re.I), "get_brightness", None),
    (re.compile(r"^\s*(?:open|launch|start)\s+(.+?)\s*$", re.I), "launch", lambda m: {"target": m.group(1).strip()}),
    (re.compile(r"^\s*play\s+(.+?)\s*(?:on youtube)?\s*$", re.I), "play_youtube", lambda m: {"query": m.group(1).strip()}),
    (re.compile(r"^\s*(?:calculator|open calculator)\s*$", re.I), "launch", lambda m: {"target": "calculator"}),
    (re.compile(r"^\s*(?:scan wifi|scan wi-?fi|list wifi networks)\s*$", re.I), "network_scan", None),
    (re.compile(r"^\s*(?:list apps|installed apps|what apps)\s*$", re.I), "app_list", None),
    (re.compile(r"^\s*(?:running processes|list processes|task list)\s*$", re.I), "process_list", None),
    (re.compile(r"^\s*(?:kill|close|stop)\s+(?:process\s+)?(.+?)\s*$", re.I), "process_kill", lambda m: {"target": m.group(1).strip()}),
    (re.compile(r"^\s*(?:device status|battery|system status)\s*$", re.I), "device_status", None),
    (re.compile(r"^\s*notify\s+(.+?)\s*[:\-]\s*(.+)$", re.I), "notify", lambda m: {"title": m.group(1).strip(), "message": m.group(2).strip()}),
]

_VOLUME_STEP = 10
_BRIGHTNESS_STEP = 10


def _level_of(result, *keys):
    if isinstance(result, dict):
        for k in keys:
            v = result.get(k)
            if isinstance(v, (int, float)):
                return int(v)
    return None


def _delta(getter, setter, delta, label):
    current = _level_of(getter(), "level", "volume", "brightness")
    new_level = max(0, min(100, (current if current is not None else 50) + delta))
    result = setter(new_level)
    return f"{label} set to {new_level}%", result


def try_reflex(text: str) -> Optional[Tuple[str, object, float]]:
    """Attempt a Tier-1 reflex.

    Returns (spoken_reply, raw_result, elapsed_ms) when handled, else None.
    """
    t0 = time.perf_counter()
    text = (text or "").strip()
    for pattern, command, builder in _RULES:
        m = pattern.match(text)
        if not m:
            continue
        payload = builder(m) if builder else {}

        if command == "volume_up":
            reply, result = _delta(lambda: handle_device_command("get_volume"),
                                   lambda l: handle_device_command("volume", {"level": l}),
                                   _VOLUME_STEP, "Volume")
        elif command == "volume_down":
            reply, result = _delta(lambda: handle_device_command("get_volume"),
                                   lambda l: handle_device_command("volume", {"level": l}),
                                   -_VOLUME_STEP, "Volume")
        elif command == "mute":
            current = handle_device_command("get_volume") or {}
            if isinstance(current, dict) and current.get("muted"):
                result = handle_device_command("volume", {"level": current.get("level") or 50})
                reply = "Unmuted"
            else:
                result = handle_device_command("volume", {"level": 0})
                reply = "Muted"
        elif command == "brightness_up":
            reply, result = _delta(lambda: handle_device_command("get_brightness"),
                                   lambda l: handle_device_command("brightness", {"level": l}),
                                   _BRIGHTNESS_STEP, "Brightness")
        elif command == "brightness_down":
            reply, result = _delta(lambda: handle_device_command("get_brightness"),
                                   lambda l: handle_device_command("brightness", {"level": l}),
                                   -_BRIGHTNESS_STEP, "Brightness")
        elif command == "play_youtube":
            query = payload.get("query", "")
            url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
            result = handle_device_command("launch", {"target": url})
            reply = f"Playing {query} on YouTube"
        else:
            result = handle_device_command(command, payload)
            reply = {
                "volume": f"Volume set to {payload.get('level')}%",
                "brightness": f"Brightness set to {payload.get('level')}%",
                "launch": f"Opening {payload.get('target')}",
                "get_volume": "Here's the current volume",
                "get_brightness": "Here's the current brightness",
                "network_scan": "Scanning Wi-Fi networks",
                "app_list": "Listing installed apps",
                "process_list": "Listing running processes",
                "process_kill": f"Killing {payload.get('target')}",
                "device_status": "Here's the device status",
                "notify": f"Notification sent: {payload.get('title')}",
            }.get(command, f"Done: {command}")

        elapsed = (time.perf_counter() - t0) * 1000.0
        return reply, result, elapsed
    return None


def available() -> bool:
    """Reflexes are always available — they only use device_command_handler."""
    return True
