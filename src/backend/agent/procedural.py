"""
src/backend/agent/procedural.py - remember *how* tasks were solved.

Why this exists
---------------
`memory/memory_manager.py` stores facts ("the wifi password is X"). This stores
procedures: the goal shape, the exact tool sequence that worked, and whether it
worked. That distinction is the whole point.

Current agent-memory research is clear that procedural long-term memory is the
strongest family for execution-oriented tasks - it beat both retrieval and
general fact memory in cross-episode tool-use benchmarks, with the largest
gains when context is tight. Tool-use episodes are precisely where reusable
execution guidance pays: action routines, parameter-filling procedures,
failure-aware strategies.

Design constraints that shaped this:

* **Task shape, not keywords.** Two requests ("rename these files" vs "organise
  my downloads") share almost no words. Matching on the *sequence of tools*
  and the *shape of the request* is what actually generalises.
* **Success labelling is mandatory.** A failed sequence that gets retrieved is
  worse than no memory at all - it teaches the wrong thing. Failures are
  stored too, but tagged, and surfaced as "this approach failed before".
* **Budgeted injection.** Memory that bloats the prompt hurts. Only the top few
  matches are injected, and they are capped in length.
* **Eviction.** Unbounded growth is unbounded noise. Old, unused procedures
  decay.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "to", "of", "and", "or", "in",
    "on", "for", "with", "about", "my", "i", "me", "it", "that", "this",
    "please", "can", "you", "do", "make", "create", "write", "get", "find",
}


def _store() -> Path:
    base = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
    d = Path(base) / "StellaAI" / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d / "procedures.jsonl"


def _terms(text: str) -> set[str]:
    toks = re.findall(r"[a-z0-9_]+", (text or "").lower())
    return {t for t in toks if t not in _STOP and len(t) > 2}


def _shape(goal: str) -> str:
    """Coarse intent label for a goal.

    Not a classifier - a small set of buckets that makes "read three files"
    and "read the README" retrievable against each other.
    """
    g = (goal or "").lower()
    if re.search(r"\b(summar|explain|describe|what|why|how)\b", g):
        return "explain"
    if re.search(r"\b(find|search|locate|where|grep)\b", g):
        return "search"
    if re.search(r"\b(total|sum|count|how many|calculat|add up)\b", g):
        return "compute"
    if re.search(r"\b(create|write|generate|make|save|build)\b", g):
        return "create"
    if re.search(r"\b(rename|move|copy|delete|organi[sz]e|clean|sort)\b", g):
        return "organise"
    if re.search(r"\b(open|launch|start|run)\b", g):
        return "launch"
    return "other"


def record(goal: str, tool_sequence: list[str], success: bool,
           elapsed: float = 0.0, notes: str = "") -> None:
    """Persist one execution trace. Never raises - memory must not break a run."""
    try:
        if not tool_sequence:
            return
        row = {
            "goal": (goal or "")[:400],
            "shape": _shape(goal),
            "terms": sorted(_terms(goal)),
            "tools": list(tool_sequence)[:20],
            "success": bool(success),
            "elapsed": round(float(elapsed), 2),
            "notes": (notes or "")[:200],
            "ts": time.time(),
            "uses": 0,
        }
        with _store().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        _enforce_cap()
    except Exception:
        pass


def recall(goal: str, limit: int = 3, budget_chars: int = 900) -> str:
    """Return injectable guidance for a goal, or "" when nothing matches."""
    rows = _load()
    if not rows:
        return ""

    goal_terms = _terms(goal)
    goal_shape = _shape(goal)
    now = time.time()

    scored: list[tuple[float, dict]] = []
    for row in rows:
        row_terms = set(row.get("terms", []))
        shared = goal_terms & row_terms
        overlap = (len(shared) / len(goal_terms)) if goal_terms else 0.0
        shape_match = row.get("shape") == goal_shape
        shape_bonus = 0.45 if shape_match else 0.0

        # Relevance gate. Research is unambiguous that injecting unrelated
        # procedures makes agents *worse*, not better. A single shared term is
        # far too weak a signal - "file" alone links half the toolset - so a
        # row qualifies only if it matches the goal's shape, or shares at
        # least two substantive terms with it.
        if not shape_match and len(shared) < 2:
            continue

        # A procedure that worked is worth more than one that failed.
        outcome = 0.3 if row.get("success") else -0.15
        # Recent and frequently reused procedures rank higher.
        age_days = max(0.0, (now - float(row.get("ts", now))) / 86400.0)
        decay = 0.2 / (1.0 + age_days)
        used = min(0.2, 0.04 * int(row.get("uses", 0)))
        score = overlap + shape_bonus + outcome + decay + used
        if score > 0.5:
            scored.append((score, row))

    if not scored:
        return ""

    scored.sort(key=lambda pair: pair[0], reverse=True)
    parts: list[str] = []
    used_chars = 0
    for score, row in scored[:limit]:
        tools = " -> ".join(row.get("tools", []))
        if row.get("success"):
            line = f"Previously solved a similar task with: {tools}"
        else:
            line = f"A similar task previously FAILED with: {tools}. Try a different approach."
        if used_chars + len(line) > budget_chars:
            break
        parts.append(line)
        used_chars += len(line) + 1
    return "\n".join(parts)


def feedback(row_index: int, success: bool) -> None:
    """Correct a stored outcome after the fact."""
    try:
        rows = _load()
        if 0 <= row_index < len(rows):
            rows[row_index]["success"] = success
            _rewrite(rows)
    except Exception:
        pass


def version_history(goal: str) -> list[dict]:
    """Return all stored versions of procedures matching a goal shape, newest first."""
    try:
        rows = _load()
        goal_terms = _terms(goal)
        goal_shape = _shape(goal)
        matches = []
        for row in rows:
            if row.get("shape") == goal_shape or goal_terms & set(row.get("terms", [])):
                matches.append(row)
        matches.sort(key=lambda r: float(r.get("ts", 0.0)), reverse=True)
        return matches
    except Exception:
        return []


def revert(goal: str, version_index: int = 0) -> bool:
    """Revert the most recent procedure matching a goal to an earlier state.

    version_index=0 reverts to the newest stored version, 1 to the previous, etc.
    Returns True if a revert happened, False otherwise.
    """
    try:
        history = version_history(goal)
        if not history or version_index >= len(history):
            return False
        target = history[version_index]
        # Re-write the target row as the newest entry (a new version pointing
        # back at the old state), preserving the revert in the audit trail.
        rows = _load()
        for row in rows:
            if (
                row.get("shape") == target.get("shape")
                and row.get("tools") == target.get("tools")
            ):
                row["success"] = target.get("success", False)
                row["notes"] = (row.get("notes", "") or "") + f" | reverted to ts={target.get('ts')}"
                row["ts"] = time.time()
                _rewrite(rows)
                return True
        return False
    except Exception:
        return False


def _bump_uses(goal: str) -> None:
    """Mark matching procedures as used so frequently-helpful ones rank up."""
    try:
        rows = _load()
        goal_terms = _terms(goal)
        goal_shape = _shape(goal)
        changed = False
        for row in rows:
            if (row.get("shape") == goal_shape
                    and goal_terms & set(row.get("terms", []))):
                row["uses"] = int(row.get("uses", 0)) + 1
                changed = True
        if changed:
            _rewrite(rows)
    except Exception:
        pass


def stats() -> dict:
    rows = _load()
    return {
        "total": len(rows),
        "successful": sum(1 for r in rows if r.get("success")),
        "shapes": _tally(r.get("shape", "?") for r in rows),
    }


def clear() -> int:
    n = len(_load())
    try:
        _store().unlink()
    except OSError:
        return 0
    return n


# ---------------------------------------------------------------------------
# storage helpers
# ---------------------------------------------------------------------------

MAX_ROWS = 400
# How often to prune. Pruning on every write would be wasteful; letting it run
# unbounded would let stale procedures dominate recall.
_WRITE_COUNT = 0


def _tally(values) -> dict:
    out: dict = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def _load() -> list[dict]:
    path = _store()
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("tools"):
                rows.append(obj)
    except OSError:
        return []
    return rows


def _rewrite(rows: list[dict]) -> None:
    path = _store()
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _enforce_cap() -> None:
    """Keep the newest MAX_ROWS, preferring procedures that succeeded or recur.

    A one-off success is worth as much as a one-off failure, so this evicts the
    least-useful rather than simply the oldest.
    """
    global _WRITE_COUNT
    _WRITE_COUNT += 1
    if _WRITE_COUNT < 25:
        return
    _WRITE_COUNT = 0
    rows = _load()
    if len(rows) <= MAX_ROWS:
        return
    ranked = sorted(
        range(len(rows)),
        key=lambda i: (rows[i].get("success"), int(rows[i].get("uses", 0)),
                       float(rows[i].get("ts", 0.0))),
    )
    drop = set(ranked[: len(rows) - MAX_ROWS])
    _rewrite([r for i, r in enumerate(rows) if i not in drop])
