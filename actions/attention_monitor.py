from __future__ import annotations

import hashlib
import os
import platform
import re
import sqlite3
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import xml.etree.ElementTree as ET
import subprocess


try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


_APP_ALIASES: dict[str, tuple[str, ...]] = {
    "discord": ("discord",),
    "whatsapp": ("whatsapp",),
    "telegram": ("telegram",),
    "signal": ("signal",),
    "skype": ("skype",),
    "zoom": ("zoom",),
    "teams": ("teams", "microsoft teams"),
    "phone link": ("phone link", "your phone"),
    "messenger": ("messenger", "facebook messenger"),
    "instagram": ("instagram",),
    "facebook": ("facebook",),
    "slack": ("slack",),
    "gmail": ("gmail", "google mail"),
    "mail": ("mail", "outlook"),
}

_MESSAGE_HINTS = (
    "new message",
    "message",
    "chat",
    "dm",
    "direct message",
    "unread",
    "notification",
    "mention",
    "reply",
    "preview",
    "received",
)

_CALL_HINTS = (
    "incoming call",
    "call from",
    "voice call",
    "video call",
    "ringing",
    "incoming video",
    "incoming voice",
    "accept",
    "answer",
    "decline",
    "reject",
    "hang up",
    "end call",
)

_ACCEPT_HINTS = ("accept", "answer", "pick up", "join", "allow")
_DECLINE_HINTS = ("decline", "reject", "ignore", "hang up", "end", "cut", "dismiss")
_WINDOW_CALL_HINTS = (
    "call",
    "incoming",
    "ringing",
    "voice",
    "video",
    "answer",
    "accept",
    "decline",
    "reject",
    "hang up",
    "end call",
    "meeting",
    "joined",
    "conference",
)


def _db_path() -> Path:
    local = os.environ.get("LOCALAPPDATA", "")
    return Path(local) / "Microsoft" / "Windows" / "Notifications" / "wpndatabase.db"


def _normalize_app_from_primary(primary: str | None, fallback: str = "") -> str | None:
    hay = f"{primary or ''} {fallback or ''}".lower()
    mapping = [
        ("whatsapp", "WhatsApp"),
        ("discord", "Discord"),
        ("telegram", "Telegram"),
        ("signal", "Signal"),
        ("skype", "Skype"),
        ("zoom", "Zoom"),
        ("teams", "Teams"),
        ("phone link", "Phone Link"),
        ("yourphone", "Phone Link"),
        ("phonelink", "Phone Link"),
        ("messenger", "Messenger"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("slack", "Slack"),
        ("outlook", "Mail"),
        ("mail", "Mail"),
        ("gmail", "Gmail"),
        ("sms", "Messages"),
        ("messages", "Messages"),
    ]
    for token, name in mapping:
        if token in hay:
            return name
    return None


def _parse_toast_payload(payload: bytes | str | None) -> tuple[str, list[str], list[str], str]:
    if payload is None:
        return "", [], [], ""
    if isinstance(payload, (bytes, bytearray)):
        raw = payload.decode("utf-8", "ignore")
    else:
        raw = str(payload)

    texts: list[str] = []
    actions: list[str] = []
    try:
        root = ET.fromstring(raw)
        for node in root.findall(".//text"):
            txt = (node.text or "").strip()
            if txt:
                texts.append(txt)
        for node in root.findall(".//action"):
            for attr in ("content", "arguments", "hint-inputId"):
                val = (node.get(attr) or "").strip()
                if val:
                    actions.append(val)
    except Exception:
        pass

    flat = " ".join(texts + actions + [raw]).lower()
    kind = "call" if any(k in flat for k in _CALL_HINTS) else "message"
    if "call" in flat and not any(m in flat for m in _MESSAGE_HINTS):
        kind = "call"
    return raw, texts, actions, kind


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _proc_name(pid: int | None) -> str:
    if not pid or psutil is None:
        return ""
    try:
        return psutil.Process(pid).name().lower()
    except Exception:
        return ""


def _match_app(text: str, proc_name: str) -> str | None:
    hay = f"{text or ''} {proc_name or ''}".lower()
    for app, aliases in _APP_ALIASES.items():
        for alias in aliases:
            if alias in hay:
                return app.title()
    return None


def _contains_any(hay: str, hints: tuple[str, ...]) -> bool:
    return any(h in hay for h in hints)


# ── Lazy-imported heavy deps (Mark-LVI pattern) ──


def _ctypes_windll():
    import ctypes
    return ctypes.windll


def _ctypes_create_unicode_buffer(size: int):
    import ctypes
    return ctypes.create_unicode_buffer(size)


def _ctypes_wintypes():
    import ctypes
    from ctypes import wintypes
    return wintypes


def _pyautogui():
    import pyautogui
    return pyautogui


def _desktop():
    from pywinauto import Desktop
    return Desktop


# ── Window enumeration (ctypes, lazy) ──


def _enum_visible_windows() -> list[dict]:
    """Enumerate visible windows using ctypes (lazy import)."""
    user32 = _ctypes_windll().user32
    wintypes = _ctypes_wintypes()

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    windows: list[dict] = []

    @enum_proc
    def callback(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            buf = _ctypes_create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, len(buf))
            title = buf.value

            class_buf = _ctypes_create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_buf, len(class_buf))
            cls = class_buf.value

            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            windows.append({
                "hwnd": hwnd,
                "title": title,
                "class": cls,
                "pid": pid.value,
            })
        return True

    user32.EnumWindows(callback, 0)
    return windows


def _get_foreground_window_info() -> dict | None:
    """Get the foreground window info using ctypes (lazy import)."""
    user32 = _ctypes_windll().user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    buf = _ctypes_create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    title = buf.value

    class_buf = _ctypes_create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_buf, len(class_buf))
    cls = class_buf.value

    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    return {
        "hwnd": hwnd,
        "title": title,
        "class": cls,
        "pid": pid.value,
    }


# ── Media control (ctypes winmm, lazy) ──


_CURRENT_PLAYER_ALIAS = "stella_media"


def _media_stop() -> None:
    import ctypes
    ctypes.windll.winmm.mciSendStringW(f"stop {_CURRENT_PLAYER_ALIAS}", None, 0, None)


def _media_close() -> None:
    import ctypes
    ctypes.windll.winmm.mciSendStringW(f"close {_CURRENT_PLAYER_ALIAS}", None, 0, None)


# ── Desktop automation (pywinauto, lazy) ──


def _enum_desktop_windows() -> list:
    """Enumerate desktop windows using pywinauto (lazy import)."""
    Desktop = _desktop()
    if Desktop is None:
        return []
    desktop = Desktop(backend="uia")
    results = []
    for win in desktop.windows():
        try:
            results.append({
                "title": win.window_text(),
                "class": win.class_name(),
            })
        except Exception:
            pass
    return results


# ── Key presses (pyautogui, lazy) ──


def _press_key(key: str) -> None:
    pyautogui = _pyautogui()
    pyautogui.press(key)


# ── Action registry (TOOL dict) ──

TOOL = {
    "name": "attention_monitor",
    "description": "Monitor Windows notifications and active windows for messages and calls. Reads the Windows notification database and enumerates visible windows to detect incoming messages, calls, and app focus changes.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: check_notifications, check_windows, check_foreground, media_stop, media_close, press_key, enum_desktop. Defaults to check_notifications.",
                "default": "check_notifications",
            },
            "key": {
                "type": "STRING",
                "description": "Key to press (for press_key operation). e.g. 'enter', 'esc', 'space'.",
            },
        },
        "required": [],
    },
    "handler": None,  # set below after handler functions are defined
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
    "tier": "extra",
    "brief": "Monitor notifications and windows for messages/calls",
}


class AttentionMonitor:
    """Monitors Windows notifications and windows for attention-worthy events."""

    def __init__(self) -> None:
        self._seen_keys: set[str] = set()
        self._on_event: Callable[[dict], None] | None = None
        self._db_conn: sqlite3.Connection | None = None

    def set_on_event(self, cb: Callable[[dict], None]) -> None:
        self._on_event = cb

    def _remember_seen(self, dedupe: str) -> None:
        self._seen_keys.add(dedupe)
        if len(self._seen_keys) > 5000:
            self._seen_keys = set(list(self._seen_keys)[-2500:])

    def _open_db(self) -> sqlite3.Connection | None:
        if self._db_conn is not None:
            return self._db_conn
        try:
            db = _db_path()
            if not db.exists():
                return None
            conn = sqlite3.connect(str(db))
            self._db_conn = conn
            return conn
        except Exception:
            return None

    def check_notifications(self, limit: int = 20) -> list[dict]:
        """Read recent notifications from the Windows notification database."""
        conn = self._open_db()
        if conn is None:
            return []

        events: list[dict] = []
        try:
            cur = conn.execute(
                "SELECT ItemID, AppID, Title, Payload, ArrivalTime FROM Notification WHERE ArrivalTime IS NOT NULL ORDER BY ArrivalTime DESC LIMIT ?",
                (limit,),
            )
            columns = [d[0] for d in cur.description]
            for row in cur.fetchall():
                row_dict = dict(zip(columns, row))
                raw = row_dict.get("Payload")
                primary = row_dict.get("AppID")
                texts = []
                actions = []
                raw_text, texts, actions, kind = _parse_toast_payload(raw)
                app = _normalize_app_from_primary(primary, "")
                if not app:
                    app = _match_app(row_dict.get("Title") or "", "")

                flat = " ".join(texts + actions + [raw_text or ""]).lower()
                if kind == "call":
                    if not any(k in flat for k in _CALL_HINTS):
                        if not any(x in flat for x in ("incoming", "ringing", "accept", "decline", "answer", "reject")):
                            continue
                elif not any(k in flat for k in _MESSAGE_HINTS) and not texts:
                    continue

                preview = ""
                if texts:
                    if len(texts) >= 2:
                        preview = " ".join(texts[1:3]).strip()
                    else:
                        preview = texts[0].strip()
                if not preview and actions:
                    preview = " ".join(actions[:2]).strip()

                dedupe = hashlib.sha1(
                    f"{app}|{kind}|{preview}|{raw_text[:240]}".encode("utf-8", "ignore")
                ).hexdigest()
                if dedupe in self._seen_keys:
                    continue
                self._remember_seen(dedupe)

                event = {
                    "kind": kind,
                    "app": app,
                    "title": texts[0] if texts else app,
                    "preview": preview,
                    "source": "wpndb",
                    "notification_id": row_dict.get("ItemID"),
                    "arrival_time": row_dict.get("ArrivalTime"),
                    "timestamp": time.time(),
                    "raw": raw_text,
                    "primary_id": primary,
                    "actions": actions,
                }
                events.append(event)

                if self._on_event:
                    self._on_event(event)
        except Exception:
            pass
        return events

    def check_windows(self) -> list[dict]:
        """Enumerate visible windows and detect call/message-related ones."""
        events: list[dict] = []
        now = time.time()
        for win in _enum_visible_windows():
            title = win.get("title") or ""
            pid = int(win.get("pid") or 0)
            proc_name = _proc_name(pid)
            app = _match_app(title, proc_name)
            if not app:
                continue

            hay = f"{title} {win.get('class') or ''} {proc_name}".lower()
            if "stella" in hay:
                continue

            if app in {"Zoom", "Teams", "WhatsApp"} and _contains_any(hay, ("meeting", "call", "incoming", "ringing", "conference", "joined")):
                pass
            elif not _contains_any(hay, _WINDOW_CALL_HINTS):
                continue

            dedupe = hashlib.sha1(
                f"window|{app}|{title}|{pid}".encode("utf-8", "ignore")
            ).hexdigest()
            if dedupe in self._seen_keys:
                continue
            self._remember_seen(dedupe)

            event = {
                "kind": "call",
                "app": app,
                "title": title,
                "preview": title,
                "source": "window",
                "notification_id": None,
                "arrival_time": None,
                "timestamp": now,
                "raw": title,
                "primary_id": proc_name,
                "actions": [],
            }
            events.append(event)

            if self._on_event:
                self._on_event(event)
        return events

    def check_foreground(self) -> dict | None:
        """Get the currently active foreground window."""
        return _get_foreground_window_info()

    def media_stop(self) -> None:
        _media_stop()

    def media_close(self) -> None:
        _media_close()

    def press_key(self, key: str) -> None:
        _press_key(key)

    def enum_desktop(self) -> list:
        return _enum_desktop_windows()


_monitor = AttentionMonitor()


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def execute(**kwargs) -> dict:
    """Run one attention monitor operation."""
    operation = (kwargs.get("operation") or "check_notifications").strip().lower()

    if operation == "check_notifications":
        limit = int(kwargs.get("limit") or 20)
        events = _monitor.check_notifications(limit=limit)
        return _op(operation, True, {
            "events": events,
            "count": len(events),
        })

    if operation == "check_windows":
        events = _monitor.check_windows()
        return _op(operation, True, {
            "events": events,
            "count": len(events),
        })

    if operation == "check_foreground":
        info = _monitor.check_foreground()
        return _op(operation, True, {"foreground": info})

    if operation == "media_stop":
        _monitor.media_stop()
        return _op(operation, True, {"message": "Media stopped"})

    if operation == "media_close":
        _monitor.media_close()
        return _op(operation, True, {"message": "Media closed"})

    if operation == "press_key":
        key = kwargs.get("key") or ""
        if not key:
            return _op(operation, False, None, "Provide a key to press (key=...).")
        _monitor.press_key(key)
        return _op(operation, True, {"key": key, "message": f"Pressed {key}"})

    if operation == "enum_desktop":
        wins = _monitor.enum_desktop()
        return _op(operation, True, {
            "windows": wins,
            "count": len(wins),
        })

    return _op(operation, False, None, f"Unknown operation '{operation}'. One of: check_notifications, check_windows, check_foreground, media_stop, media_close, press_key, enum_desktop.")


TOOL["handler"] = execute
