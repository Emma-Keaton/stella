"""Stella theme token system — single source of truth driven by themes.json.

Loads the theme contract, exposes token lookup, and provides a ThemeManager
that notifies listeners on theme change. All UI color values should come from here.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
THEMES_FILE = ROOT / "themes.json"

# All 32 token keys from themes.json (validated by theme_contrast_test.py)
TOKEN_KEYS = [
    "bg", "surface", "surface-raised", "glass", "glass-border",
    "text-primary", "text-secondary", "text-muted",
    "border", "border-strong",
    "primary", "on-primary", "secondary", "on-secondary", "tertiary", "on-tertiary",
    "success", "on-success", "warning", "on-warning", "error", "on-error",
    "focus-ring",
    "bubble-user", "bubble-stella", "bubble-user-text", "bubble-stella-text",
    "button-content", "button-content-disabled",
    "scrim", "glow", "elevation-shadow",
]


class ThemeManager:
    """Loads themes.json, tracks active theme, notifies listeners."""

    _instance: "ThemeManager | None" = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._themes: dict[str, dict[str, Any]] = {}
        self._theme_ids: list[str] = []
        self._active_id = "void"
        self._listeners: list[Callable[[str], None]] = []
        self._load()
        self._initialized = True

    def _load(self):
        data = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
        self._themes = {t["id"]: t["tokens"] for t in data["themes"]}
        self._theme_ids = [t["id"] for t in data["themes"]]
        # Validate all themes have all tokens
        for tid, toks in self._themes.items():
            missing = [k for k in TOKEN_KEYS if k not in toks]
            if missing:
                raise ValueError(f"Theme '{tid}' missing tokens: {missing}")

    def list_themes(self) -> list[str]:
        return list(self._theme_ids)

    def get_theme(self, theme_id: str | None = None) -> dict[str, Any]:
        tid = theme_id or self._active_id
        if tid not in self._themes:
            tid = "void"
        return self._themes[tid]

    def get_token(self, key: str, theme_id: str | None = None) -> Any:
        return self.get_theme(theme_id).get(key)

    def get_preview(self, theme_id: str) -> list[str]:
        """Return the 4-color preview array for a theme."""
        data = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
        for t in data["themes"]:
            if t["id"] == theme_id:
                return t.get("preview", [])
        return []

    def get_name(self, theme_id: str) -> str:
        data = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
        for t in data["themes"]:
            if t["id"] == theme_id:
                return t.get("name", theme_id)
        return theme_id

    def get_description(self, theme_id: str) -> str:
        data = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
        for t in data["themes"]:
            if t["id"] == theme_id:
                return t.get("description", "")
        return ""

    def get_mode(self, theme_id: str) -> str:
        """Return 'light' or 'dark'."""
        data = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
        for t in data["themes"]:
            if t["id"] == theme_id:
                return t.get("mode", "dark")
        return "dark"

    @property
    def active_theme(self) -> str:
        return self._active_id

    @active_theme.setter
    def active_theme(self, theme_id: str):
        if theme_id not in self._themes:
            return
        if theme_id == self._active_id:
            return
        self._active_id = theme_id
        for cb in list(self._listeners):
            try:
                cb(theme_id)
            except Exception:
                pass

    def register(self, callback: Callable[[str], None]):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unregister(self, callback: Callable[[str], None]):
        if callback in self._listeners:
            self._listeners.remove(callback)


# Singleton instance
theme_manager = ThemeManager()


# Convenience functions
def get_theme(theme_id: str | None = None) -> dict[str, Any]:
    return theme_manager.get_theme(theme_id)


def get_token(key: str, theme_id: str | None = None) -> Any:
    return theme_manager.get_token(key, theme_id)


def active_theme_id() -> str:
    return theme_manager.active_theme


def set_active_theme(theme_id: str):
    theme_manager.active_theme = theme_id


def list_themes() -> list[str]:
    return theme_manager.list_themes()


def register_theme_listener(callback: Callable[[str], None]):
    theme_manager.register(callback)


def unregister_theme_listener(callback: Callable[[str], None]):
    theme_manager.unregister(callback)