"""
guitar_lyrics — Fetch song lyrics via public lyrics.ovh API.
"""

from __future__ import annotations

from typing import Any, Dict

import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_lookup(kwargs: dict) -> dict:
    artist = (kwargs.get("artist") or "").strip()
    title = (kwargs.get("title") or "").strip()
    if not artist or not title:
        return _op("lookup", False, None, "Missing artist or title.")
    try:
        r = requests.get(f"https://api.lyrics.ovh/v1/{artist}/{title}", timeout=15)
        if r.status_code == 404:
            return _op("lookup", False, None, f"Lyrics not found for '{artist} - {title}'.")
        r.raise_for_status()
        data = r.json()
        return _op("lookup", True, {
            "artist": artist,
            "title": title,
            "lyrics": data.get("lyrics", ""),
        })
    except Exception as exc:
        return _op("lookup", False, None, f"Lyrics lookup failed: {exc}")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["api.lyrics.ovh"],
        "content": "Lyrics via lyrics.ovh API. No API key required.",
    })


_OPERATIONS = {
    "lookup": _op_lookup,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "lookup": "Lyrics Lookup",
    "sources": "Lyrics Sources",
}

_ALIASES = {
    "lyrics": "lookup",
    "get_lyrics": "lookup",
    "song_lyrics": "lookup",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "lookup":
        lyrics = value.get("lyrics") or ""
        return f"Lyrics for '{value.get('artist')} - {value.get('title')}' ({len(lyrics)} chars): {lyrics[:200]}..."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Fetch song lyrics via public lyrics.ovh API."""
    operation = (kwargs.get("operation") or "lookup").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Guitar Lyrics",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Guitar Lyrics",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Guitar Lyrics",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Lyrics error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Guitar Lyrics"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="lookup", artist="The Beatles", title="Yesterday"))