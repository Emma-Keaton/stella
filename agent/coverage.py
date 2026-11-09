"""agent/coverage.py - the shared coverage ledger (Strix pattern).

A scan that never reconciles what it looked at cannot say what it *did not* look
at. This module is that ledger: agents record a surface, the risk area they
considered, the outcome, and the evidence - and a report can list the surfaces
that were never touched.

State is per-run and lives under the user's data dir, so a later operation can
read it back and the audit trail has something to reconcile against.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

#: Outcome vocabulary for a coverage entry.
CONFIRMED = "confirmed"
RULED_OUT = "ruled_out"
OPEN_PROOF_GAP = "open_proof_gap"
NEEDS_FOLLOW_UP = "needs_follow_up"
OUTCOMES = (CONFIRMED, RULED_OUT, OPEN_PROOF_GAP, NEEDS_FOLLOW_UP)


def _path() -> Path:
    try:
        from core.user_paths import get_user_data_dir

        path = Path(get_user_data_dir()) / "pentest" / "coverage.json"
    except Exception:
        path = Path("coverage.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"entries": []}
    except Exception:
        return {"entries": []}


def save(state: dict) -> None:
    try:
        _path().write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass


def reset() -> dict:
    state = {"entries": [], "started_at": round(time.time(), 3), "run_id": _run_id()}
    save(state)
    return state


def _run_id() -> str:
    return f"run-{int(time.time())}"


def record(target: str, surface: str, risk_area: str, outcome: str,
           evidence: str = "", agent: str = "stella") -> dict:
    """Record one coverage entry, replacing an earlier entry for the same surface."""
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, not {outcome!r}")
    state = load()
    entry = {
        "target": target,
        "surface": surface,
        "risk_area": risk_area,
        "outcome": outcome,
        "evidence": evidence,
        "agent": agent,
        "recorded_at": round(time.time(), 3),
    }
    state["entries"] = [item for item in state.get("entries", [])
                        if not (item.get("target") == target and item.get("surface") == surface)]
    state["entries"].append(entry)
    save(state)
    return entry


def update(target: str, surface: str, **changes) -> bool:
    """Change one entry in place, keeping its identity."""
    state = load()
    for entry in state.get("entries", []):
        if entry.get("target") == target and entry.get("surface") == surface:
            entry.update(changes)
            save(state)
            return True
    return False


def list_entries(target: Optional[str] = None) -> list:
    entries = load().get("entries", [])
    if target:
        return [entry for entry in entries if entry.get("target") == target]
    return entries


def untouched(target: str, surfaces: list) -> list:
    """The surfaces from a list that no entry has covered."""
    covered = {entry.get("surface") for entry in list_entries(target)}
    return sorted({surface for surface in surfaces} - covered)


def summarise(target: Optional[str] = None) -> dict:
    entries = list_entries(target)
    counts: dict = {}
    for entry in entries:
        counts[entry.get("outcome", "unknown")] = counts.get(entry.get("outcome", "unknown"), 0) + 1
    return {
        "target": target,
        "total": len(entries),
        "by_outcome": counts,
        "surfaces": sorted({entry.get("surface", "?") for entry in entries}),
    }
