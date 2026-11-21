"""core/gui_control.py — Cross-OS GUI automation: see and operate any app.

Screenshot, click, type and key injection across Windows, macOS and Linux.
Uses pyautogui when installed (best fidelity); otherwise falls back to
platform-native tools (osascript / xdotool / PowerShell SendKeys).
Every function returns an honest outcome dict — never a fabricated success.
"""
from __future__ import annotations

import base64
import io
import platform
import subprocess
from typing import Optional

SYSTEM = platform.system().lower()

_pyautogui = None
try:
    import pyautogui as _pyautogui  # type: ignore
    _pyautogui.FAILSAFE = False
except Exception:
    _pyautogui = None


def available() -> bool:
    return _pyautogui is not None or SYSTEM in ("darwin", "linux", "windows")


def _run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10, **kw)
    except Exception:
        return None


def _png_b64(path: str) -> dict:
    with open(path, "rb") as f:
        return {"outcome": "done", "image_b64": base64.b64encode(f.read()).decode()}


def screenshot() -> dict:
    """Capture the screen. Returns {"outcome", "image_b64", ...}."""
    if _pyautogui is not None:
        try:
            img = _pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return {"outcome": "done", "image_b64": base64.b64encode(buf.getvalue()).decode(),
                    "width": img.width, "height": img.height}
        except Exception as e:
            return {"outcome": "failed", "error": str(e)}
    path = "/tmp/stella_shot.png"
    if SYSTEM == "darwin":
        r = _run(["screencapture", "-x", path])
    elif SYSTEM == "linux":
        r = None
        for tool, args in (("gnome-screenshot", ["-f", path]), ("scrot", [path]), ("import", ["-window", "root", path])):
            r = _run([tool, *args])
            if r is not None and r.returncode == 0:
                break
    elif SYSTEM == "windows":
        ps = ("Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
              "$b=[System.Windows.Forms.SystemInformation]::VirtualScreen;"
              "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
              "$g=$bmp.Graphics; $g.CopyFromScreen($b.Left,$b.Top,0,0,$bmp.Size);"
              f"$bmp.Save('{path}',[System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()")
        r = _run(["powershell", "-NoProfile", "-Command", ps])
    else:
        return {"outcome": "failed", "error": f"unsupported platform {SYSTEM}"}
    if r is not None and r.returncode == 0:
        try:
            return _png_b64(path)
        except Exception:
            pass
    return {"outcome": "failed", "error": "screenshot capture failed"}


def click(x: int, y: int, button: str = "left") -> dict:
    if _pyautogui is not None:
        try:
            _pyautogui.click(int(x), int(y), button=button)
            return {"outcome": "done", "x": x, "y": y, "button": button}
        except Exception as e:
            return {"outcome": "failed", "error": str(e)}
    if SYSTEM == "darwin":
        r = _run(["osascript", "-e", f'tell application "System Events" to click {{{int(x)}, {int(y)}}}'])
    elif SYSTEM == "linux":
        n = "1" if button == "left" else ("3" if button == "right" else "2")
        r = _run(["xdotool", "mousemove", str(int(x)), str(int(y)), "click", n])
    else:
        return {"outcome": "failed", "error": "click requires pyautogui on this platform"}
    return {"outcome": "done" if r is not None and r.returncode == 0 else "failed"}


def type_text(text: str, interval: float = 0.01) -> dict:
    if _pyautogui is not None:
        try:
            _pyautogui.typewrite(text, interval=interval)
            return {"outcome": "done", "chars": len(text)}
        except Exception as e:
            return {"outcome": "failed", "error": str(e)}
    if SYSTEM == "darwin":
        escaped = text.replace('"', '\\"')
        r = _run(["osascript", "-e", f'tell application "System Events" to keystroke "{escaped}"'])
    elif SYSTEM == "linux":
        r = _run(["xdotool", "type", "--delay", "12", text])
    elif SYSTEM == "windows":
        escaped = text.replace("'", "''")
        ps = ("Add-Type -AssemblyName System.Windows.Forms;"
              f"[System.Windows.Forms.SendKeys]::SendWait('{escaped}')")
        r = _run(["powershell", "-NoProfile", "-Command", ps])
    else:
        return {"outcome": "failed", "error": "unsupported platform"}
    return {"outcome": "done", "chars": len(text)} if r is not None and r.returncode == 0 else {"outcome": "failed"}


def key(keys) -> dict:
    """Press a key or chord, e.g. 'enter', 'ctrl+c', 'win'."""
    if isinstance(keys, str):
        keys = [k.strip() for k in keys.split("+") if k.strip()]
    if _pyautogui is not None:
        try:
            if len(keys) == 1:
                _pyautogui.press(keys[0])
            else:
                _pyautogui.hotkey(*keys)
            return {"outcome": "done", "keys": keys}
        except Exception as e:
            return {"outcome": "failed", "error": str(e)}
    if SYSTEM == "linux":
        r = _run(["xdotool", "key", "+".join(keys)])
        return {"outcome": "done" if r is not None and r.returncode == 0 else "failed", "keys": keys}
    return {"outcome": "failed", "error": "key requires pyautogui on this platform"}


def gui_command(command: str, payload: Optional[dict] = None) -> dict:
    """Dispatch a GUI command: screenshot | click | type | key."""
    payload = payload or {}
    if command == "screenshot":
        return screenshot()
    if command == "click":
        return click(payload.get("x", 0), payload.get("y", 0), payload.get("button", "left"))
    if command == "type":
        return type_text(str(payload.get("text", "")))
    if command == "key":
        return key(payload.get("keys", "enter"))
    return {"outcome": "failed", "error": f"unknown gui command {command}"}

    with open(path, "rb") as f:
        return {"outcome": "done", "image_b64": base64.b64encode(f.read()).decode()}
