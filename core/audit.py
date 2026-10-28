"""core/audit.py - append-only JSONL audit log.

Every tool invocation appends one row. A row carries what ran, against what,
what the outcome was, and - for anything gated - the activity class and the
policy rule that decided it (openbot pattern: a refusal carries the rule that
caused it, so a user can read exactly why Stella declined).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

AUDIT_PATH = os.path.join("logs", "audit.jsonl")


def _ensure_dir():
    os.makedirs(os.path.dirname(AUDIT_PATH) or ".", exist_ok=True)


def record(actor, tool, target, result, activity: str = "", rule: str = "", extra: dict | None = None):
    """Append one audit row and return it.

    Kept positional-compatible with the original four-argument call.
    """
    _ensure_dir()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "tool": tool,
        "target": target,
        "result": result,
    }
    if activity:
        entry["activity"] = activity
    if rule:
        entry["rule"] = rule
    if extra:
        entry["extra"] = extra
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def tail(limit: int = 50) -> list[dict]:
    """The most recent rows, oldest first - used by the Settings audit view."""
    if not os.path.exists(AUDIT_PATH):
        return []
    rows: list[dict] = []
    try:
        with open(AUDIT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows[-max(1, int(limit)):]
