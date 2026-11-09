"""Lightweight theme-token reader for Stella skills.

Reads the single source of truth (themes.json) so skills never ship
hardcoded colours.  Skills run standalone (no Qt), so this module has no
Qt dependency and degrades gracefully when themes.json is unavailable.

Usage::

    from theme_tokens import token, active_theme_id, theme_colour

    bg = token("bg")                 # active theme
    mint = token("primary", "void")  # specific theme
    bg_hex = theme_colour("bg")      # same as token, returns str or None
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_THEMES_FILE = Path(__file__).resolve().parent.parent / "themes.json"

# Cache so we don't re-read themes.json on every call.
_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    """Load and cache the themes.json document."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        _cache = json.loads(_THEMES_FILE.read_text(encoding="utf-8"))
    except Exception:
        _cache = {"version": 1, "themes": []}
    return _cache


def list_themes() -> list[str]:
    """Return every theme id defined in themes.json."""
    return [t.get("id", "") for t in _load().get("themes", [])]


def active_theme_id() -> str:
    """Return the active theme id.  Skills have no persistence layer, so we
    default to ``void`` unless a consumer overrides it."""
    data = _load()
    themes = data.get("themes", [])
    return themes[0].get("id", "void") if themes else "void"


def token(key: str, theme_id: str | None = None) -> Any:
    """Return the value of a single token key for a theme.

    Returns ``None`` when the theme or token is missing — callers should
    treat absence as "no theme colour available" rather than guessing a
    hardcoded fallback.
    """
    tid = theme_id or active_theme_id()
    for t in _load().get("themes", []):
        if t.get("id") == tid:
            return t.get("tokens", {}).get(key)
    return None


def theme_colour(key: str, theme_id: str | None = None) -> str | None:
    """Alias of :func:`token` that explicitly returns a colour string or None."""
    value = token(key, theme_id)
    return value if isinstance(value, str) else None


def all_tokens(theme_id: str | None = None) -> dict[str, Any]:
    """Return every token for a theme, or an empty dict when missing."""
    tid = theme_id or active_theme_id()
    for t in _load().get("themes", []):
        if t.get("id") == tid:
            return dict(t.get("tokens", {}))
    return {}
