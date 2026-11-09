"""agent/continual_learning.py - Phase 6: continual learning.

Stella gets better at *your* tasks over time, without sending your data
anywhere. Three mechanisms:

* **Preference signals** — the user accepts, rejects, or corrects an agent
  response. Each signal is recorded (append-only JSONL) and attached to the
  goal + tool trace so the agent can learn what good looks like for *you*.
* **Fine-tune export** — successful, confirmed traces are exported to JSONL in
  a format ready for fine-tuning a local model. Nothing leaves the machine
  unless you explicitly export.
* **Per-user adapters** — each user gets their own adapter directory with
  preference + trace history, so a shared install personalizes per user.

Honesty: preference signals are observations ("the user rejected this"), not
judgments ("this answer was bad"). A rejected trace is kept for contrastive
learning, never deleted — but never used as a positive example.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from agent import procedural as proc

#: Where continual-learning state lives (per user, per install).
_USER_DIR = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~"))) / "StellaAI"
CL_DIR = _USER_DIR / "continual_learning"
PREFERENCES_DIR = CL_DIR / "preferences"
EXPORTS_DIR = CL_DIR / "exports"
ADAPTERS_DIR = CL_DIR / "adapters"

#: Signals the user can send about an agent response.
SIGNALS: tuple[str, ...] = ("accept", "reject", "correct")


def _cl_dir() -> Path:
    for d in (CL_DIR, PREFERENCES_DIR, EXPORTS_DIR, ADAPTERS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    return CL_DIR


def _append(path: Path, entry: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return rows
    return rows


# ---------------------------------------------------------------------------
# 1. Preference signals — accept / reject / correct
# ---------------------------------------------------------------------------

def record_signal(goal: str, signal: str, tool_trace: list[dict] | None = None,
                  answer: str = "", context: str = "") -> dict[str, Any]:
    """Record one user preference signal.

    `signal` is one of accept / reject / correct. The signal is stored with
    the goal, the tool trace that produced the answer, the answer text, and
    any free-form context. Never deleted — kept as contrastive evidence.
    """
    if signal not in SIGNALS:
        return {"ok": False, "error": f"signal must be one of {list(SIGNALS)}"}

    entry = {
        "ts": time.time(),
        "goal": (goal or "")[:400],
        "signal": signal,
        "tool_trace": tool_trace or [],
        "answer": (answer or "")[:1000],
        "context": (context or "")[:500],
    }
    _append(PREFERENCES_DIR / "signals.jsonl", entry)

    # If the signal is a correction, also record the corrected answer as a
    # positive trace so the agent can learn what "right" looks like for you.
    if signal == "correct" and answer:
        proc.record(
            goal=goal,
            tool_sequence=[t.get("name", "") for t in (tool_trace or [])
                         if isinstance(t, dict)],
            success=True,
            elapsed=0.0,
            notes=f"corrected answer (user signal=correct): {context[:120]}",
        )

    return {"ok": True, "signal": signal, "goal": goal}


def list_signals(limit: int = 50) -> list[dict]:
    """Return the most recent preference signals, newest first."""
    rows = _load_jsonl(PREFERENCES_DIR / "signals.jsonl")
    rows.sort(key=lambda r: float(r.get("ts", 0)), reverse=True)
    return rows[:limit]


def signal_counts() -> dict[str, int]:
    """Count of each signal type, across all time."""
    rows = _load_jsonl(PREFERENCES_DIR / "signals.jsonl")
    counts = {s: 0 for s in SIGNALS}
    for r in rows:
        s = r.get("signal")
        if s in counts:
            counts[s] += 1
    return counts


# ---------------------------------------------------------------------------
# 2. Fine-tuning pipeline — export successful traces to JSONL
# ---------------------------------------------------------------------------

def export_finetune_jsonl(min_uses: int = 1) -> dict[str, Any]:
    """Export confirmed-successful procedures to a JSONL fine-tune file.

    Each line is one training example with `goal` (prompt) and `completion`
    (the tool sequence + answer the agent should have produced). Only
    procedures marked `success=True` and with `uses >= min_uses` are exported,
    so only proven-good behavior becomes training data.

    Returns the path to the exported file and the number of examples.
    """
    rows = proc._load()  # noqa: SLF001
    examples = []
    for row in rows:
        if not row.get("success"):
            continue
        if int(row.get("uses", 0)) < min_uses:
            continue
        goal = row.get("goal", "")
        tools = row.get("tools", []) or []
        completion = " -> ".join(tools) if tools else "(no tools)"
        if row.get("notes"):
            completion += " | " + row["notes"]
        examples.append({
            "goal": goal,
            "completion": completion,
            "uses": int(row.get("uses", 0)),
            "ts": float(row.get("ts", 0)),
        })

    examples.sort(key=lambda e: e["ts"])
    path = EXPORTS_DIR / f"finetune_{int(time.time())}.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for ex in examples:
                fh.write(json.dumps(ex, ensure_ascii=False) + "\n")
    except OSError as exc:
        return {"ok": False, "error": f"export failed: {exc}"}

    return {
        "ok": True,
        "path": str(path),
        "examples": len(examples),
        "min_uses": min_uses,
        "note": "Exported successful traces for fine-tuning. Nothing leaves this machine unless you copy the file.",
    }


# ---------------------------------------------------------------------------
# 3. Per-user adapters
# ---------------------------------------------------------------------------

def _adapter_dir(user_id: str) -> Path:
    d = ADAPTERS_DIR / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def adapter_state(user_id: str) -> dict[str, Any]:
    """Return the per-user adapter state (preferences + signal counts)."""
    d = _adapter_dir(user_id)
    state_path = d / "state.json"
    state: dict[str, Any] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state = {}
    state.setdefault("user_id", user_id)
    state.setdefault("signals", signal_counts())
    state.setdefault("created_at", state.get("created_at", time.time()))
    state.setdefault("last_updated", time.time())
    return state


def record_user_signal(user_id: str, goal: str, signal: str,
                       tool_trace: list[dict] | None = None,
                       answer: str = "") -> dict[str, Any]:
    """Record a preference signal for a specific user, then update adapter state."""
    result = record_signal(goal, signal, tool_trace=tool_trace, answer=answer)
    if not result.get("ok"):
        return result

    # Update per-user adapter state.
    d = _adapter_dir(user_id)
    state_path = d / "state.json"
    state = adapter_state(user_id)
    sigs = dict(state.get("signals", {}))
    sigs[signal] = sigs.get(signal, 0) + 1
    state["signals"] = sigs
    state["last_updated"] = time.time()
    state["last_signal"] = signal
    state["last_goal"] = (goal or "")[:200]
    try:
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": f"adapter state write failed: {exc}"}

    result["adapter_state"] = state
    return result


def adapter_preferences(user_id: str) -> dict[str, Any]:
    """Return the per-user adapter's preference profile."""
    return adapter_state(user_id)


__all__ = [
    "record_signal",
    "list_signals",
    "signal_counts",
    "export_finetune_jsonl",
    "adapter_state",
    "record_user_signal",
    "adapter_preferences",
    "CL_DIR",
    "SIGNALS",
]
