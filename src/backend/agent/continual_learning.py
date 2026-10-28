"""
src/backend/agent/continual_learning.py - Phase 6: Continual learning pipeline.

Implements the feedback loop that lets Stella specialise to one person over time,
using only her own successful traces and the user's accept/reject/correct signals.

Design (from AGI_ROADMAP.md Phase 6):

* **Preference signals** - user accept/reject/correct on any agent action,
  stored as JSONL signals. These are the ground truth for what "good" means
  to this person.
- **Fine-tuning pipeline** - export Stella's own successful execution traces
  (from procedural memory) as a fine-tune dataset for the local model.
* **Held-out eval** - a held-out slice of traces is reserved to prove a
  fine-tune actually helped before it is adopted.
* **Per-user adapters** - each user gets their own adapter directory under
  the user data dir; the model specialises to that one person.

Honesty: nothing is auto-applied. A fine-tune only becomes active after the
held-out eval shows a measurable improvement over the baseline.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

from .procedural import _load as _procedural_rows

# ── Preference signals ──────────────────────────────────────────────────

SIGNALS_DIR = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~"))) / "StellaAI" / "continual_learning"
SIGNALS_FILE = SIGNALS_DIR / "signals.jsonl"
FINE_TUNE_DIR = SIGNALS_DIR / "finetune"
ADAPTERS_DIR = SIGNALS_DIR / "adapters"


def _ensure_dirs() -> None:
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    FINE_TUNE_DIR.mkdir(parents=True, exist_ok=True)
    ADAPTERS_DIR.mkdir(parents=True, exist_ok=True)


def record_signal(
    goal: str,
    action: str,
    result: str,
    signal: str,  # "accept" | "reject" | "correct"
    corrected_result: Optional[str] = None,
) -> None:
    """Record a user preference signal on an agent action.

    signal values:
      - "accept"   - the user liked the result as-is
      - "reject"   - the user disliked the result
      - "correct"  - the user provided a corrected result (corrected_result)
    """
    _ensure_dirs()
    row = {
        "ts": time.time(),
        "goal": (goal or "")[:400],
        "action": action,
        "result": (result or "")[:2000],
        "signal": signal,
        "corrected_result": (corrected_result or "")[:2000] if corrected_result else None,
    }
    try:
        with SIGNALS_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def load_signals(limit: int | None = None) -> list[dict]:
    """Load all recorded preference signals, newest first."""
    if not SIGNALS_FILE.exists():
        return []
    rows: list[dict] = []
    try:
        with SIGNALS_FILE.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    rows.sort(key=lambda r: float(r.get("ts", 0)), reverse=True)
    if limit is not None:
        rows = rows[:limit]
    return rows


def signal_stats() -> dict[str, Any]:
    """Summary counts of preference signals."""
    rows = load_signals()
    accept = sum(1 for r in rows if r.get("signal") == "accept")
    reject = sum(1 for r in rows if r.get("signal") == "reject")
    correct = sum(1 for r in rows if r.get("signal") == "correct")
    return {
        "total": len(rows),
        "accept": accept,
        "reject": reject,
        "correct": correct,
        "accept_rate": round(accept / len(rows), 3) if rows else 0.0,
    }


# ── Fine-tune dataset export ────────────────────────────────────────────


def export_finetune_dataset(
    min_successes: int = 10,
    held_out_frac: float = 0.2,
) -> dict[str, Any]:
    """Export successful procedural traces as a fine-tune dataset.

    Splits into train / held-out. The held-out slice is reserved to prove the
    fine-tune actually helped before adoption.

    Returns paths to train.jsonl and held_out.jsonl, plus counts.
    """
    _ensure_dirs()
    rows = _procedural_rows()
    successes = [r for r in rows if r.get("success")]
    if len(successes) < min_successes:
        return {
            "ok": False,
            "error": f"only {len(successes)} successful traces, need {min_successes}",
            "train_path": None,
            "held_out_path": None,
            "train_count": 0,
            "held_out_count": 0,
        }

    # Deterministic split by timestamp (oldest = train, newest = held_out)
    successes.sort(key=lambda r: float(r.get("ts", 0)))
    split = int(len(successes) * (1.0 - held_out_frac))
    train_rows = successes[:split]
    held_out_rows = successes[split:]

    def to_chatml(row: dict) -> dict:
        goal = row.get("goal", "")
        tools = " -> ".join(row.get("tools", []) or [])
        return {
            "messages": [
                {"role": "system", "content": "You are Stella, a helpful local assistant."},
                {"role": "user", "content": goal},
                {"role": "assistant", "content": f"I used: {tools}"},
            ],
        }

    train_path = FINE_TUNE_DIR / "train.jsonl"
    held_out_path = FINE_TUNE_DIR / "held_out.jsonl"

    try:
        with train_path.open("w", encoding="utf-8") as fh:
            for r in train_rows:
                fh.write(json.dumps(to_chatml(r), ensure_ascii=False) + "\n")
        with held_out_path.open("w", encoding="utf-8") as fh:
            for r in held_out_rows:
                fh.write(json.dumps(to_chatml(r), ensure_ascii=False) + "\n")
    except OSError as exc:
        return {
            "ok": False,
            "error": f"write failed: {exc}",
            "train_path": None,
            "held_out_path": None,
            "train_count": 0,
            "held_out_count": 0,
        }

    return {
        "ok": True,
        "train_path": str(train_path),
        "held_out_path": str(held_out_path),
        "train_count": len(train_rows),
        "held_out_count": len(held_out_rows),
        "total_successes": len(successes),
    }


# ── Held-out eval ───────────────────────────────────────────────────────


def run_held_out_eval(
    held_out_path: str | Path,
    adapter_path: str | Path | None = None,
    baseline_path: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate a fine-tune adapter against baseline on held-out traces.

    This is a placeholder scaffold - the actual model forward pass is
    provider-specific (local llama.cpp server, etc.). It reports whether the
    held-out set is usable and how many examples it contains.

    Returns an eval report dict.
    """
    held_out = Path(held_out_path)
    if not held_out.exists():
        return {"ok": False, "error": f"held-out file not found: {held_out_path}"}

    rows: list[dict] = []
    try:
        with held_out.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        return {"ok": False, "error": f"read failed: {exc}"}

    if not rows:
        return {"ok": False, "error": "held-out set is empty"}

    # Placeholder: report usability. A real eval runs each example through the
    # model (baseline + adapter) and scores exact-match / LLM-as-judge.
    return {
        "ok": True,
        "held_out_examples": len(rows),
        "adapter": str(adapter_path) if adapter_path else None,
        "baseline": str(baseline_path) if baseline_path else None,
        "note": "held-out set is usable; run model forward passes to score",
    }


# ── Per-user adapters ───────────────────────────────────────────────────


def list_adapters() -> list[dict[str, Any]]:
    """List per-user adapter directories."""
    if not ADAPTERS_DIR.exists():
        return []
    adapters: list[dict[str, Any]] = []
    try:
        for entry in sorted(ADAPTERS_DIR.iterdir()):
            if entry.is_dir():
                adapters.append({
                    "name": entry.name,
                    "path": str(entry),
                    "created": entry.stat().st_ctime,
                })
    except OSError:
        pass
    return adapters


def adapter_dir(user_id: str) -> Path:
    """Return (and create) the adapter directory for a user id."""
    d = ADAPTERS_DIR / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def continual_learning_status() -> dict[str, Any]:
    """One-line status of the continual learning pipeline."""
    sig_stats = signal_stats()
    return {
        "signals": sig_stats,
        "adapters": len(list_adapters()),
        "finetune_dir": str(FINE_TUNE_DIR),
        "adapters_dir": str(ADAPTERS_DIR),
        "note": "Phase 6 continual learning pipeline initialised",
    }


__all__ = [
    "record_signal",
    "load_signals",
    "signal_stats",
    "export_finetune_dataset",
    "run_held_out_eval",
    "list_adapters",
    "adapter_dir",
    "continual_learning_status",
    "SIGNALS_DIR",
    "FINE_TUNE_DIR",
    "ADAPTERS_DIR",
]
