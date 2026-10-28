"""core/device_command_handler.py

Cross-OS actuator dispatch + Android node bridge.
"""
from __future__ import annotations
import os, platform, subprocess
from typing import Any, Dict, Optional

SYSTEM = platform.system().lower()


def _run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw)
    except FileNotFoundError:
        return None


def _android_bridge(command, payload):
    try:
        from stella_connect import android_bridge
    except Exception:
        try:
            import stella_connect.android_bridge as android_bridge
        except Exception:
            android_bridge = None
    if android_bridge is None:
        return None
    fn = getattr(android_bridge, "send_command", None)
    if not callable(fn):
        return None
    try:
        return fn(command, payload)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_volume(level):
    level = max(0, min(100, int(level)))
    if SYSTEM == "windows":
        _run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"])
        return {"ok": True, "level": level, "os": SYSTEM}
    if SYSTEM == "darwin":
        _run(["osascript", "-e", f"set volume output volume {level}"])
        return {"ok": True, "level": level, "os": SYSTEM}
    if SYSTEM == "linux":
        _run(["amixer", "set", "Master", f"{level}%"])
        return {"ok": True, "level": level, "os": SYSTEM}
    res = _android_bridge("volume", {"level": level})
    if res is not None:
        return res
    return {"ok": False, "error": f"unsupported os: {SYSTEM}"}


def handle_brightness(level):
    level = max(0, min(100, int(level)))
    if SYSTEM == "windows":
        _run(["powershell", "-Command", f"(Get-WmiObject -Ns root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"])
        return {"ok": True, "level": level, "os": SYSTEM}
    if SYSTEM == "darwin":
        _run(["brightness", str(level / 100.0)])
        return {"ok": True, "level": level, "os": SYSTEM}
    if SYSTEM == "linux":
        _run(["brightnessctl", "set", f"{level}%"])
        return {"ok": True, "level": level, "os": SYSTEM}
    res = _android_bridge("brightness", {"level": level})
    if res is not None:
        return res
    return {"ok": False, "error": f"unsupported os: {SYSTEM}"}


def handle_notify(title, message):
    if SYSTEM == "windows":
        return {"ok": True, "os": SYSTEM}
    if SYSTEM == "darwin":
        _run(["osascript", "-e", f'display notification "{message}" with title "{title}"'])
        return {"ok": True, "os": SYSTEM}
    if SYSTEM == "linux":
        _run(["notify-send", title, message])
        return {"ok": True, "os": SYSTEM}
    res = _android_bridge("notify", {"title": title, "message": message})
    if res is not None:
        return res
    return {"ok": False, "error": f"unsupported os: {SYSTEM}"}


def handle_launch(target):
    if SYSTEM == "windows":
        if hasattr(os, "startfile"):
            os.startfile(target)
        else:
            subprocess.Popen(["start", target], shell=True)
        return {"ok": True, "target": target, "os": SYSTEM}
    if SYSTEM == "darwin":
        _run(["open", target])
        return {"ok": True, "target": target, "os": SYSTEM}
    if SYSTEM == "linux":
        _run(["xdg-open", target])
        return {"ok": True, "target": target, "os": SYSTEM}
    res = _android_bridge("launch", {"target": target})
    if res is not None:
        return res
    return {"ok": False, "error": f"unsupported os: {SYSTEM}"}


def handle_device_command(command, payload=None):
    payload = payload or {}
    cmd = (command or "").lower().strip()
    if cmd == "volume":
        return handle_volume(payload.get("level", 50))
    if cmd == "brightness":
        return handle_brightness(payload.get("level", 50))
    if cmd == "notify":
        return handle_notify(payload.get("title", "Stella"), payload.get("message", ""))
    if cmd == "launch":
        return handle_launch(payload.get("target", ""))
    res = _android_bridge(cmd, payload)
    if res is not None:
        return res
    return {"ok": False, "error": f"unknown command: {command}"}


__all__ = ["handle_device_command", "handle_volume", "handle_brightness", "handle_notify", "handle_launch"]