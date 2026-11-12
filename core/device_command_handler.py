"""core/device_command_handler.py

Cross-OS actuator dispatch + Android node bridge.

Stella uses this module to take direct control of the host device:
volume, brightness, launching any app, sending keystrokes/types/clicks so the
agent can operate any software, listing running tasks/processes, scanning
wireless networks, and showing notifications. Every command works on Windows,
macOS and Linux using only the standard library (plus psutil, already a
Stella dependency). On Android the call is forwarded to the Termux
`stella_connect.android_bridge` node so Stella has the same control surface
on mobile regardless of OS.
"""
from __future__ import annotations

import os
import platform
import shlex
import subprocess
from typing import Any, Dict, List, Optional

try:  # psutil is a declared Stella dependency
    import psutil
except Exception:  # pragma: no cover - fallback when psutil missing
    psutil = None

SYSTEM = platform.system().lower()


def _run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw)
    except FileNotFoundError:
        return None
    except Exception:  # pragma: no cover
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


# ── Volume (verified via core.media.volume with read-back, fallback to shell) ──


def _volume_backend_available() -> bool:
    try:
        from core.media.volume import backend as _volume_backend  # type: ignore

        return _volume_backend() != "none"
    except Exception:
        return False


def handle_volume(level, _verify: bool = True):
    """Set system output volume and (when possible) read it back."""
    level = max(0, min(100, int(level)))
    if _verify:
        try:
            from core.media.volume import set_volume as _set_volume  # type: ignore

            result = _set_volume(level, "")
            if isinstance(result, dict) and result.get("outcome") in ("done", "unverified"):
                actual = None
                try:
                    from core.media.volume import get_volume as _get_volume  # type: ignore

                    actual = _get_volume("")
                except Exception:
                    actual = None
                return {
                    "ok": True,
                    "level": level,
                    "actual": actual,
                    "os": SYSTEM,
                    "detail": result.get("detail", ""),
                    "outcome": result.get("outcome"),
                }
        except Exception:
            pass  # fall through to shell fallback

    if SYSTEM == "windows":
        _run(
            [
                "powershell",
                "-Command",
                "(New-Object -ComObject WScript.Shell).SendKeys([char]174)",
            ]
        )
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


def handle_get_volume():
    """Read the current output volume (verified when possible)."""
    try:
        from core.media.volume import get_volume as _get_volume  # type: ignore

        actual = _get_volume("")
        if actual is not None:
            return {"ok": True, "level": actual, "os": SYSTEM, "source": "verified"}
    except Exception:
        pass
    if SYSTEM == "darwin":
        r = _run(["osascript", "-e", "output volume of (get volume settings)"])
        if r and r.returncode == 0:
            try:
                return {"ok": True, "level": int(r.stdout.strip()), "os": SYSTEM}
            except Exception:
                pass
    if SYSTEM == "linux":
        r = _run(["amixer", "get", "Master"])
        if r and r.returncode == 0:
            for token in r.stdout.replace("[", " ").split():
                if token.endswith("%"):
                    try:
                        return {"ok": True, "level": int(token.rstrip("%")), "os": SYSTEM}
                    except Exception:
                        pass
    res = _android_bridge("volume.get", {})
    if res is not None:
        return res
    return {"ok": False, "error": "could not read volume", "os": SYSTEM}


def handle_brightness(level):
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
        _run(
            [
                "powershell",
                "-Command",
                f"(Get-WmiObject -Ns root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})",
            ]
        )
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


def handle_get_brightness():
    if SYSTEM == "windows":
        r = _run(
            [
                "powershell",
                "-Command",
                "(Get-WmiObject -Ns root/WMI -Class WmiMonitorBrightness).CurrentBrightness",
            ]
        )
        if r and r.returncode == 0:
            try:
                return {"ok": True, "level": int(r.stdout.strip().splitlines()[-1]), "os": SYSTEM}
            except Exception:
                pass
    if SYSTEM == "linux":
        r = _run(["brightnessctl", "get", "-m"])
        if r and r.returncode == 0:
            try:
                last = r.stdout.strip().splitlines()[-1]
                return {"ok": True, "level": int(last.split(",")[-1].rstrip("%")), "os": SYSTEM}
            except Exception:
                pass
    res = _android_bridge("brightness.get", {})
    if res is not None:
        return res
    return {"ok": False, "error": "could not read brightness", "os": SYSTEM}


def handle_notify(title, message):
    if SYSTEM == "windows":
        # Toast via PowerShell (best-effort; no-op is still "ok" so UI stays responsive)
        _run(
            [
                "powershell",
                "-Command",
                f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('{message}','{title}')",
            ]
        )
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


def handle_app_list():
    """List currently visible application windows (best effort)."""
    if SYSTEM == "windows":
        r = _run(
            [
                "powershell",
                "-Command",
                "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -First 30 ProcessName, MainWindowTitle | ConvertTo-Csv -NoTypeInformation",
            ]
        )
        if r and r.returncode == 0:
            return {"ok": True, "apps": r.stdout.strip(), "os": SYSTEM}
    if SYSTEM == "darwin":
        r = _run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to name of every process whose background only is false',
            ]
        )
        if r and r.returncode == 0:
            apps = [a.strip() for a in r.stdout.split(",") if a.strip()]
            return {"ok": True, "apps": apps, "os": SYSTEM}
    if SYSTEM == "linux":
        r = _run(["ps", "-e", "-o", "comm="])
        if r and r.returncode == 0:
            apps = [a for a in r.stdout.splitlines() if a][:50]
            return {"ok": True, "apps": apps, "os": SYSTEM}
    res = _android_bridge("apps.list", {})
    if res is not None:
        return res
    return {"ok": False, "error": "could not list apps", "os": SYSTEM}


# ── Running tasks / processes (Stella sees all running tasks) ──


def handle_process_list():
    if psutil is not None:
        procs: List[Dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_info"]):
            try:
                info = p.info
                procs.append(
                    {
                        "pid": info.get("pid"),
                        "name": info.get("name"),
                        "user": info.get("username"),
                        "cpu": info.get("cpu_percent"),
                        "mem_mb": round((info.get("memory_info") or {}).get("rss", 0) / 1024 / 1024, 1)
                        if info.get("memory_info")
                        else 0,
                    }
                )
            except Exception:
                continue
        procs.sort(key=lambda x: (x.get("mem_mb") or 0), reverse=True)
        return {"ok": True, "processes": procs[:60], "count": len(procs), "os": SYSTEM}
    if SYSTEM == "windows":
        r = _run(["tasklist", "/FO", "CSV", "/NH"])
        if r and r.returncode == 0:
            return {"ok": True, "processes": r.stdout.strip(), "os": SYSTEM}
    if SYSTEM in ("darwin", "linux"):
        r = _run(["ps", "-e", "-o", "pid,comm,%cpu,%mem"])
        if r and r.returncode == 0:
            return {"ok": True, "processes": r.stdout.strip(), "os": SYSTEM}
    res = _android_bridge("process.list", {})
    if res is not None:
        return res
    return {"ok": False, "error": "could not list processes", "os": SYSTEM}


def handle_process_kill(target):
    killed = []
    if psutil is not None:
        for p in psutil.process_iter(["pid", "name"]):
            try:
                name = (p.info.get("name") or "").lower()
                pid = p.info.get("pid")
                if str(target).lower() in (name, str(pid)) or name == str(target).lower() + ".exe":
                    p.kill()
                    killed.append({"pid": pid, "name": p.info.get("name")})
            except Exception:
                continue
        if killed:
            return {"ok": True, "killed": killed, "os": SYSTEM}
        return {"ok": False, "error": f"process not found: {target}", "os": SYSTEM}
    if SYSTEM == "windows":
        r = _run(["taskkill", "/F", "/IM", str(target)])
        if r and r.returncode == 0:
            return {"ok": True, "killed": [target], "os": SYSTEM}
    else:
        r = _run(["pkill", "-f", str(target)])
        if r and r.returncode == 0:
            return {"ok": True, "killed": [target], "os": SYSTEM}
    res = _android_bridge("process.kill", {"target": target})
    if res is not None:
        return res
    return {"ok": False, "error": f"could not kill process: {target}", "os": SYSTEM}


# ── Wireless networks (Stella sees Wi-Fi) ──


def handle_network_scan():
    if SYSTEM == "windows":
        r = _run(["netsh", "wlan", "show", "networks", "mode=ssid"])
        if r and r.returncode == 0:
            networks = []
            for block in r.stdout.split("SSID "):
                if ":" not in block:
                    continue
                lines = block.splitlines()
                ssid = lines[0].split(":", 1)[-1].strip() if lines else ""
                auth = ""
                enc = ""
                for line in lines:
                    if "Authentication" in line:
                        auth = line.split(":", 1)[-1].strip()
                    if "Encryption" in line:
                        enc = line.split(":", 1)[-1].strip()
                if ssid:
                    networks.append({"ssid": ssid, "auth": auth, "encryption": enc})
            return {"ok": True, "networks": networks, "os": SYSTEM}
    if SYSTEM == "linux":
        for cmd in (["nmcli", "-t", "-f", "ssid,signal,security", "device", "wifi", "list"], ["iwlist", "scan"]):
            r = _run(cmd)
            if r and r.returncode == 0:
                networks = []
                if cmd[0] == "nmcli":
                    for line in r.stdout.splitlines():
                        parts = line.split(":")
                        if len(parts) >= 1 and parts[0]:
                            networks.append(
                                {"ssid": parts[0], "signal": parts[1] if len(parts) > 1 else "",
                                 "security": parts[2] if len(parts) > 2 else ""}
                            )
                else:
                    ssid = ""
                    for line in r.stdout.splitlines():
                        if "ESSID" in line:
                            ssid = line.split("ESSID:")[1].strip('"').strip()
                        if "Quality" in line and ssid:
                            networks.append({"ssid": ssid, "signal": line.split("Quality=")[-1].split()[0] if "Quality=" in line else "", "security": ""})
                            ssid = ""
                return {"ok": True, "networks": networks, "os": SYSTEM}
    if SYSTEM == "darwin":
        r = _run(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"])
        if r and r.returncode == 0:
            networks = []
            for line in r.stdout.splitlines()[1:]:
                parts = line.split()
                if parts:
                    networks.append({"ssid": parts[0], "signal": parts[1] if len(parts) > 1 else "", "security": parts[-1] if len(parts) > 1 else ""})
            return {"ok": True, "networks": networks, "os": SYSTEM}
    res = _android_bridge("wifi.scan", {})
    if res is not None:
        return res
    return {"ok": False, "error": "could not scan wireless networks", "os": SYSTEM}


# ── Keyboard/mouse control (operate any app/software) ──


def handle_keystroke(keys):
    """Press a key or key combination, e.g. keys='ctrl+c' or 'volumeup'."""
    if SYSTEM == "windows":
        vk_map = {
            "volumeup": "174", "volumedown": "175", "volumemute": "173",
            "playpause": "179", "nexttrack": "176", "prevtrack": "177",
        }
        key = vk_map.get(keys.lower(), keys)
        script = f'(New-Object -ComObject WScript.Shell).SendKeys([char]{key})' if key.isdigit() else f'(New-Object -ComObject WScript.Shell).SendKeys("{keys}")'
        r = _run(["powershell", "-Command", script])
        return {"ok": bool(r and r.returncode == 0), "key": keys, "os": SYSTEM}
    if SYSTEM == "darwin":
        r = _run(["osascript", "-e", f'tell application "System Events" to keystroke "{keys}"'])
        return {"ok": bool(r and r.returncode == 0), "key": keys, "os": SYSTEM}
    if SYSTEM == "linux":
        r = _run(["xdotool", "key", "--clearmodifiers", str(keys)])
        return {"ok": bool(r and r.returncode == 0), "key": keys, "os": SYSTEM}
    res = _android_bridge("keystroke", {"keys": keys})
    if res is not None:
        return res
    return {"ok": False, "error": f"unsupported os: {SYSTEM}"}


def handle_type_text(text):
    """Type a string into the focused field (operate any app)."""
    if SYSTEM == "windows":
        escaped = str(text).replace('"', '`"')
        r = _run(["powershell", "-Command", f'(New-Object -ComObject WScript.Shell).SendKeys("{escaped}")'])
        return {"ok": bool(r and r.returncode == 0), "os": SYSTEM}
    if SYSTEM == "darwin":
        r = _run(["osascript", "-e", f'tell application "System Events" to keystroke "{str(text)}"'])
        return {"ok": bool(r and r.returncode == 0), "os": SYSTEM}
    if SYSTEM == "linux":
        r = _run(["xdotool", "type", "--clearmodifiers", shlex.quote(str(text))])
        return {"ok": bool(r and r.returncode == 0), "os": SYSTEM}
    res = _android_bridge("type_text", {"text": text})
    if res is not None:
        return res
    return {"ok": False, "error": f"unsupported os: {SYSTEM}"}


def handle_click(x=0, y=0, button="left"):
    x = int(x)
    y = int(y)
    if SYSTEM == "windows":
        script = f'Add-Type -TypeDefinition \"using System;using System.Runtime.InteropServices;public class C{{[DllImport(\\\"user32.dll\\\")]public static extern void SetCursorPos(int x,int y);[DllImport(\\\"user32.dll\\\")]public static extern void mouse_event(int dwFlags,int dx,int dy,int dwData,int dwExtraInfo);}}\";$c=New-Object C;$c.SetCursorPos({x},{y});$c.mouse_event(0x0002,0,0,0,0);$c.mouse_event(0x0004,0,0,0,0)'
        r = _run(["powershell", "-Command", script])
        return {"ok": bool(r and r.returncode == 0), "x": x, "y": y, "os": SYSTEM}
    if SYSTEM == "darwin":
        r = _run(["osascript", "-e", f'tell application "System Events" to click at {{{x},{y}}}'])
        return {"ok": bool(r and r.returncode == 0), "x": x, "y": y, "os": SYSTEM}
    if SYSTEM == "linux":
        r = _run(["xdotool", "mousemove", str(x), str(y), "&&", "xdotool", "click", "1"])
        return {"ok": bool(r and r.returncode == 0), "x": x, "y": y, "os": SYSTEM}
    res = _android_bridge("click", {"x": x, "y": y, "button": button})
    if res is not None:
        return res
    return {"ok": False, "error": f"unsupported os: {SYSTEM}"}


# ── Device status snapshot ──


def handle_device_status():
    status: Dict[str, Any] = {"os": SYSTEM, "platform": platform.platform()}
    try:
        vol = handle_get_volume()
        status["volume"] = vol.get("level") if vol.get("ok") else None
        status["isMuted"] = vol.get("level") == 0
    except Exception:
        status["volume"] = None
    try:
        br = handle_get_brightness()
        status["brightness"] = br.get("level") if br.get("ok") else None
    except Exception:
        status["brightness"] = None
    if psutil is not None:
        try:
            batt = psutil.sensors_battery()
            if batt:
                status["batteryLevel"] = int(round(batt.percent))
                status["isCharging"] = bool(batt.power_plugged)
        except Exception:
            pass
        try:
            status["cpuPercent"] = psutil.cpu_percent(interval=0.1)
            status["memoryPercent"] = psutil.virtual_memory().percent
        except Exception:
            pass
    status["networks"] = handle_network_scan() if handle_network_scan().get("ok") else {"networks": []}
    return {"ok": True, "status": status, "os": SYSTEM}


# ── Central dispatch ──


def handle_device_command(command, payload=None):
    payload = payload or {}
    cmd = (command or "").lower().strip()
    if cmd in ("volume", "set_volume"):
        return handle_volume(payload.get("level", 50))
    if cmd == "get_volume":
        return handle_get_volume()
    if cmd in ("brightness", "set_brightness"):
        return handle_brightness(payload.get("level", 50))
    if cmd == "get_brightness":
        return handle_get_brightness()
    if cmd == "notify":
        return handle_notify(payload.get("title", "Stella"), payload.get("message", ""))
    if cmd in ("launch", "app.launch", "open"):
        return handle_launch(payload.get("target", ""))
    if cmd == "apps.list":
        return handle_app_list()
    if cmd == "process.list":
        return handle_process_list()
    if cmd == "process.kill":
        return handle_process_kill(payload.get("target", "") or payload.get("pid", ""))
    if cmd in ("network.scan", "wifi.scan", "networks"):
        return handle_network_scan()
    if cmd == "keystroke":
        return handle_keystroke(payload.get("keys", "") or payload.get("key", ""))
    if cmd == "type":
        return handle_type_text(payload.get("text", "") or payload.get("message", ""))
    if cmd == "click":
        return handle_click(payload.get("x", 0), payload.get("y", 0), payload.get("button", "left"))
    if cmd == "device.status":
        return handle_device_status()
    # Fall back to Android bridge for any mobile-only command
    res = _android_bridge(cmd, payload)
    if res is not None:
        return res
    return {"ok": False, "error": f"unknown command: {command}"}


__all__ = [
    "handle_device_command",
    "handle_volume",
    "handle_brightness",
    "handle_notify",
    "handle_launch",
    "handle_get_volume",
    "handle_get_brightness",
    "handle_process_list",
    "handle_process_kill",
    "handle_network_scan",
    "handle_keystroke",
    "handle_type_text",
    "handle_click",
    "handle_device_status",
    "handle_app_list",
]