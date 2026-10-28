"""
src/backend/agent/reflection.py - the reflection job (Phase 3, self-improvement loop).

A scheduled, off-hot-path job that looks back at procedural memory
(src/backend/agent/procedural.py), clusters failed executions by pattern,
extracts recurring failure modes, and writes a human-readable reflection report.

Design (from AGI_ROADMAP.md Phase 3):

* **Scheduled, not hot-path.** The reflection job never runs inside a user turn.
* **Cluster failures.** Groups failed procedures by their tool sequence
  signature so repeated failure modes stand out.
* **Extract patterns.** For each cluster, names the tools involved, the
  failure count, and a short pattern description.
* **Append-only report.** Writes one JSONL row per reflection cycle to
  `evals/reflections/`. Never overwrites history.
* **Guardrail.** Reflection only reads and reports - it never edits safety
  rules or core agent code.

Honesty: the reflection reports what the data shows — failure patterns the
agent has actually exhibited — never promising a fix it hasn't verified.
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .procedural import _load as _procedural_rows

REFLECTIONS_DIR = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~"))) / "StellaAI" / "memory" / "reflections"
MIN_FAILURES = 2  # a cluster needs at least two failures to be worth naming


def _failed_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not r.get("success")]


def _cluster_key(row: dict) -> tuple[str, ...]:
    """Group by tool sequence shape: (category, first_tool, last_tool, len)."""
    tools = row.get("tools", []) or []
    return (
        row.get("shape", "other"),
        tools[0] if tools else "",
        tools[-1] if tools else "",
        len(tools),
    )


def _cluster_failures(rows: list[dict]) -> list[dict[str, Any]]:
    """Cluster failed rows by tool-sequence pattern."""
    clusters: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in _failed_rows(rows):
        clusters[_cluster_key(row)].append(row)

    out: list[dict[str, Any]] = []
    for key, members in clusters.items():
        if len(members) < MIN_FAILURES:
            continue
        tool_counts: Counter[str] = Counter()
        for m in members:
            for t in m.get("tools", []) or []:
                tool_counts[t] += 1
        top_tools = [t for t, _ in tool_counts.most_common(5)]
        out.append({
            "cluster_key": list(key),
            "failure_count": len(members),
            "top_tools": top_tools,
            "sample_goals": [m.get("goal", "")[:80] for m in members[:3]],
            "shape": key[0],
            "pattern": (
                f"{key[0]} tasks: {len(members)} failed runs, "
                f"most used tools: {', '.join(top_tools)}"
            ),
        })
    out.sort(key=lambda c: -c["failure_count"])
    return out


def _reflection_dir() -> Path:
    REFLECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    return REFLECTIONS_DIR


def _append(path: Path, entry: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _load_reflections() -> list[dict]:
    path = _reflection_dir() / "reflections.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
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
        return []
    return rows


def reflect() -> dict[str, Any]:
    """Run one reflection cycle.

    Reads procedural memory, clusters failures, writes a reflection row.
    Returns the cluster report. Safe to call repeatedly — each cycle appends
    one row; nothing is ever overwritten.
    """
    rows = _procedural_rows()
    clusters = _cluster_failures(rows)

    entry = {
        "ts": time.time(),
        "total_procedures": len(rows),
        "failed_procedures": len(_failed_rows(rows)),
        "clusters": clusters,
        "note": "Reflection clusters failed execution patterns from procedural memory.",
    }
    _append(_reflection_dir() / "reflections.jsonl", entry)
    return entry


def reflect_summary(limit: int = 10) -> dict[str, Any]:
    """Return a human-readable summary of all reflection cycles."""
    rows = _load_reflections()
    if not rows:
        return {
            "cycles": 0,
            "clusters": [],
            "note": "No reflection cycles recorded yet.",
        }
    latest = rows[-1]
    clusters = latest.get("clusters", [])[:limit]
    return {
        "cycles": len(rows),
        "latest_ts": latest.get("ts"),
        "total_procedures": latest.get("total_procedures", 0),
        "failed_procedures": latest.get("failed_procedures", 0),
        "clusters": clusters,
        "note": "Read-only reflection summary; nothing is modified.",
    }


__all__ = [
    "reflect",
    "reflect_summary",
    "REFLECTIONS_DIR",
]
