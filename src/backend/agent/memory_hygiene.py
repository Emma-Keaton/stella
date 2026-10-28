"""
src/backend/agent/memory_hygiene.py - Phase 4 memory hygiene policies.

Implements the guardrails around what gets stored, what gets evicted, how
contradictions are resolved, how duplicates are consolidated, and how much
is injected back into the agent's prompt.

Design (from AGI_ROADMAP.md Phase 4):

* **Write policy** - not everything is worth keeping. A procedure is only
  stored if it has at least two tool steps, a non-empty goal, and a definite
  outcome (success or failure). Empty, single-step, or ambiguous records are
  dropped at write time.
* **Eviction and decay** - old, unused procedures decay.
  _enforce_cap() in src/backend/agent/procedural.py keeps the newest MAX_ROWS,
  preferring procedures that succeeded or recur. This module exposes a
  decay_score() helper.
* **Contradiction resolution** - when two procedures share the same shape
  but disagree on success, the newer one wins and the older is marked
  superseded (never deleted - the audit trail is append-only).
* **Consolidation** - when two procedures have identical tool sequences and
  identical outcomes, they are merged into one, with uses summed.
* **Injection budget** - recall() already caps injected guidance at
  budget_chars; this module exposes injection_budget() to compute how much
  room is left before a turn.

All functions are read-only or append-only on src/backend/agent/procedural.py's
store. Nothing is ever deleted in place - superseded rows are marked, not
erased.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .procedural import _load as _store_rows, _rewrite as _save_rows

MAX_PROCEDURE_AGE_DAYS = 90  # procedures older than this are candidates for decay
MIN_TOOL_STEPS = 2  # a procedure needs at least two tool steps to be worth storing


# ---------------------------------------------------------------------------
# 1. Write policy - not everything is worth keeping
# ---------------------------------------------------------------------------

def should_store(goal: str, tool_sequence: list[str], success: bool,
                 elapsed: float = 0.0, notes: str = "") -> tuple[bool, str]:
    """Decide whether a procedure is worth storing.

    Returns (store, reason). A procedure is stored only if:
      * it has a non-empty goal
      * it has at least MIN_TOOL_STEPS tool steps (single-step procedures
        are usually trivial and not worth generalising)
      * it has a definite outcome (success is True or False, not None)
    """
    if not goal or not goal.strip():
        return False, "empty goal"
    if not tool_sequence or len(tool_sequence) < MIN_TOOL_STEPS:
        return False, f"fewer than {MIN_TOOL_STEPS} tool steps"
    if success is None:
        return False, "no definite outcome"
    return True, "worth storing"


def record_with_policy(goal: str, tool_sequence: list[str], success: bool,
                       elapsed: float = 0.0, notes: str = "") -> tuple[bool, str]:
    """Record a procedure only if should_store() says so.

    Returns (stored, reason). If not stored, nothing is written.
    """
    store, reason = should_store(goal, tool_sequence, success, elapsed, notes)
    if not store:
        return False, reason
    try:
        from .procedural import record as proc_record
        proc_record(goal, tool_sequence, success, elapsed=elapsed, notes=notes)
        return True, "stored"
    except Exception as exc:  # noqa: BLE001
        return False, f"write failed: {exc}"


# ---------------------------------------------------------------------------
# 2. Eviction and decay
# ---------------------------------------------------------------------------

def decay_score(row: dict, now: float | None = None) -> float:
    """Return a decay score for a procedure row (higher = more decayed).

    Factors: age (procedures older than MAX_PROCEDURE_AGE_DAYS decay),
    lack of reuse (uses == 0), and failure (failed procedures decay faster).
    """
    now = now or time.time()
    age_days = max(0.0, (now - float(row.get("ts", now))) / 86400.0)
    uses = int(row.get("uses", 0))
    success = bool(row.get("success", False))

    age_factor = min(1.0, age_days / MAX_PROCEDURE_AGE_DAYS)
    use_factor = 1.0 / (1.0 + uses)
    failure_factor = 0.0 if success else 0.3
    return age_factor + use_factor + failure_factor


def decay_candidates(rows: list[dict] | None = None,
                     now: float | None = None) -> list[dict]:
    """Return rows sorted by decay score (highest = most decayed first)."""
    now = now or time.time()
    rows = rows or _store_rows()
    scored = [(decay_score(r, now), r) for r in rows]
    scored.sort(key=lambda pair: -pair[0])
    return [r for _, r in scored]


# ---------------------------------------------------------------------------
# 3. Contradiction resolution - newer wins, record supersession
# ---------------------------------------------------------------------------

def _same_shape(a: dict, b: dict) -> bool:
    return (a.get("shape") == b.get("shape")
            and a.get("tools") == b.get("tools"))


def resolve_contradictions(rows: list[dict] | None = None) -> list[dict]:
    """Resolve contradictions: when two procedures share shape+tools but
    disagree on success, the newer one wins. The older is marked superseded.

    Returns the (possibly modified) rows list. Call _save_rows() to persist.
    """
    rows = rows or _store_rows()
    changed = False
    for i, row_a in enumerate(rows):
        for row_b in rows[i + 1:]:
            if not _same_shape(row_a, row_b):
                continue
            a_success = bool(row_a.get("success", False))
            b_success = bool(row_b.get("success", False))
            if a_success == b_success:
                continue
            # They disagree. Newer wins.
            a_ts = float(row_a.get("ts", 0))
            b_ts = float(row_b.get("ts", 0))
            if a_ts >= b_ts:
                winner, loser = row_a, row_b
            else:
                winner, loser = row_b, row_a
            loser["superseded"] = True
            loser["superseded_by_ts"] = winner.get("ts")
            loser["superseded_reason"] = (
                f"contradiction: newer run ({winner.get('ts')}) "
                f"reports success={winner.get('success')}, "
                f"older reported success={loser.get('success')}"
            )
            changed = True
    if changed:
        _save_rows(rows)
    return rows


# ---------------------------------------------------------------------------
# 4. Consolidation - merge duplicates
# ---------------------------------------------------------------------------

def consolidate_duplicates(rows: list[dict] | None = None) -> list[dict]:
    """Merge procedures with identical tool sequences and identical outcomes.

    Uses are summed; the earliest timestamp is kept; notes are concatenated.
    Returns the (possibly modified) rows list. Call _save_rows() to persist.
    """
    rows = rows or _store_rows()
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (row.get("shape", ""), tuple(row.get("tools", []) or []),
               bool(row.get("success", False)))
        groups.setdefault(key, []).append(row)

    changed = False
    merged: list[dict] = []
    for key, group in groups.items():
        if len(group) <= 1:
            merged.extend(group)
            continue
        changed = True
        # Keep the earliest, merge uses and notes.
        base = dict(group[0])
        base["uses"] = sum(int(r.get("uses", 0)) for r in group)
        base["ts"] = min(float(r.get("ts", 0)) for r in group)
        notes = [r.get("notes", "") for r in group if r.get("notes")]
        base["notes"] = " | ".join(n for n in notes if n)
        base["consolidated_from"] = len(group)
        merged.append(base)

    if changed:
        _save_rows(merged)
    return merged


# ---------------------------------------------------------------------------
# 5. Injection budget
# ---------------------------------------------------------------------------

def injection_budget(total_chars: int = 4000,
                     used_chars: int = 0) -> dict[str, Any]:
    """Return how much injection budget remains for a turn.

    The agent should not inject more than total_chars of procedural guidance
    into a single turn's prompt. This reports how much is left.
    """
    remaining = max(0, total_chars - used_chars)
    return {
        "total_chars": total_chars,
        "used_chars": used_chars,
        "remaining_chars": remaining,
        "pct_used": round(used_chars / total_chars * 100, 1) if total_chars else 0.0,
        "note": "Recall budget in src/backend/agent/procedural.py recall() uses budget_chars.",
    }


def hygiene_report() -> dict[str, Any]:
    """Run all hygiene checks and return a summary report."""
    rows = _store_rows()
    total = len(rows)
    successful = sum(1 for r in rows if r.get("success"))
    failed = total - successful
    superseded = sum(1 for r in rows if r.get("superseded"))
    decayed = [r for r in decay_candidates(rows) if decay_score(r) > 1.0]

    return {
        "total_procedures": total,
        "successful": successful,
        "failed": failed,
        "superseded": superseded,
        "decay_candidates": len(decay_candidates(rows)),
        "highly_decayed": len(decayed),
        "injection_budget": injection_budget(),
        "note": "Memory hygiene report; nothing is modified by this call.",
    }


__all__ = [
    "should_store",
    "record_with_policy",
    "decay_score",
    "decay_candidates",
    "resolve_contradictions",
    "consolidate_duplicates",
    "injection_budget",
    "hygiene_report",
]
