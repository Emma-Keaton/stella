"""skills/stella_watch/skill.py - Stella Watch (Sonarr + IPTV + App Routing)"""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "stella_watch"
FEATURE_METADATA = {"name": "stella_watch", "description": "Smart PVR with app routing for TV/radio/IPTV streaming", "version": "1.2.0", "active": True, "source": "sonarr,iptv", "tags": ["media", "tv", "iptv", "m3u", "playback", "apps"]}

def _op_sources():
    return {"ok": True, "source": "sonarr,iptv", "skill": "stella_watch", "operations": ["monitor_shows", "manage_channels", "load_m3u", "record_program", "route_playback", "suggest_player", "sources"]}

_OPERATIONS = {"sources": _op_sources}

def execute(**kwargs):
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "Stella Watch", "ok": False}
    try:
        record = handler()
    except Exception as exc:
        return {"title": "Stella Watch", "ok": False, "error": str(exc)}
    return {"title": "Stella Watch", "ok": True, "operation": operation, "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))