"""
theme_tokens — Lightweight theme-token reader for Stella skills.

Reads the single source of truth (themes.json) so skills never ship
hardcoded colours.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

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
    """Return the active theme id."""
    data = _load()
    themes = data.get("themes", [])
    return themes[0].get("id", "void") if themes else "void"


def token(key: str, theme_id: str | None = None) -> Any:
    """Return the value of a single token key for a theme."""
    tid = theme_id or active_theme_id()
    for t in _load().get("themes", []):
        if t.get("id") == tid:
            return t.get("tokens", {}).get(key)
    return None


def theme_colour(key: str, theme_id: str | None = None) -> str | None:
    """Alias of token that explicitly returns a colour string or None."""
    value = token(key, theme_id)
    return value if isinstance(value, str) else None


def all_tokens(theme_id: str | None = None) -> dict[str, Any]:
    """Return every token for a theme, or an empty dict when missing."""
    tid = theme_id or active_theme_id()
    for t in _load().get("themes", []):
        if t.get("id") == tid:
            return dict(t.get("tokens", {}))
    return {}


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_list(kwargs: dict) -> dict:
    return _op("list", True, {"themes": list_themes(), "total": len(list_themes())})


def _op_token(kwargs: dict) -> dict:
    key = (kwargs.get("key") or "").strip()
    theme_id = kwargs.get("theme_id")
    if not key:
        return _op("token", False, None, "Missing token key.")
    return _op("token", True, {"key": key, "value": token(key, theme_id), "theme_id": theme_id or active_theme_id()})


def _op_all(kwargs: dict) -> dict:
    theme_id = kwargs.get("theme_id")
    return _op("all", True, {"tokens": all_tokens(theme_id), "theme_id": theme_id or active_theme_id()})


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["themes.json"],
        "content": "Theme tokens read from themes.json at repo root.",
    })


_OPERATIONS = {
    "list": _op_list,
    "token": _op_token,
    "all": _op_all,
    "sources": _op_sources,
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "list":
        return f"{value.get('total')} theme(s): {', '.join(value.get('themes') or [])}"
    if operation == "token":
        return f"Token '{value.get('key')}' for theme '{value.get('theme_id')}': {value.get('value')}"
    if operation == "all":
        tokens = value.get("tokens") or {}
        return f"{len(tokens)} token(s) for theme '{value.get('theme_id')}'"
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Lightweight theme-token reader for Stella skills."""
    operation = (kwargs.get("operation") or "list").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Theme Tokens",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Theme Tokens",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Theme Tokens",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Theme error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Theme Tokens"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="list"))
