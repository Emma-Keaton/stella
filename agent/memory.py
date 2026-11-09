"""agent/memory.py - durable, searchable notes the agent keeps between runs.

A plain newline-delimited JSON file, deliberately. It has to survive crashes,
be readable with a text editor, and be trivially deletable by the user. A
vector database would be the wrong trade at this scale.

Two tiers:
  * `remember` writes an entry with tags.
  * `recall` scores entries by term overlap (and a light recency boost), which
    is enough for the kind of lookups an assistant actually does - "what did I
    tell it about my wifi" - without pulling in an embedding model.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

_STOP = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or",
    "in", "on", "for", "with", "about", "my", "i", "it", "that", "this",
}

_STOP = {s.lower() for s in _STOP}


def _store() -> Path:
    base = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
    d = Path(base) / "StellaAI" / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d / "memories.jsonl"


def _terms(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if t not in _STOP}


def remember(fact: str, tags: list[str] | None = None) -> "ToolResult":  # type: ignore[name-defined]
    """Append one durable fact. Deduplicates against near-identical entries."""
    from agent.tools import ToolResult

    fact = (fact or "").strip()
    if not fact:
        return ToolResult(ok=False, error="nothing to remember")

    path = _store()
    existing = _load()
    key = _terms(fact)
    for row in existing:
        if _terms(row.get("fact", "")) == key:
            return ToolResult(ok=True, output="already remembered; no duplicate added")

    row = {
        "fact": fact,
        "tags": tags or [],
        "ts": time.time(),
    }
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        return ToolResult(ok=False, error=f"cannot write memory: {exc}")
    return ToolResult(ok=True, output=f"remembered: {fact[:120]}")


def recall(query: str, limit: int = 8) -> "ToolResult":  # type: ignore[name-defined]
    """Return the best-matching stored facts, newest first on ties."""
    from agent.tools import ToolResult

    rows = _load()
    if not rows:
        return ToolResult(ok=True, output="(no memories stored yet)")
    q = _terms(query)
    if not q:
        return ToolResult(ok=True, output="(empty query)")

    scored: list[tuple[float, str]] = []
    now = time.time()
    for row in rows:
        fact_terms = _terms(row.get("fact", ""))
        tag_terms = _terms(" ".join(row.get("tags", [])))
        if not fact_terms:
            continue
        overlap = len(q & fact_terms) / len(q)
        tagged = 1.0 if q & tag_terms else 0.0
        age_days = max(0.0, (now - float(row.get("ts", now))) / 86400.0)
        recency = 0.15 / (1.0 + age_days)  # newer wins small ties
        score = overlap + tagged + recency
        if score > 0.05:
            scored.append((score, row.get("fact", "")))

    if not scored:
        return ToolResult(ok=True, output="(no matching memories)")
    scored.sort(reverse=True)
    out = "\n".join(f"- {fact}" for _, fact in scored[:max(1, limit)])
    return ToolResult(ok=True, output=out, data={"matched": len(scored)})


def all_memories(limit: int = 500) -> list[dict]:
    rows = _load()
    return rows[-limit:]


def clear() -> int:
    """Delete every stored memory. Returns the count removed."""
    path = _store()
    n = len(_load())
    try:
        path.unlink()
    except OSError:
        return 0
    return n


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
                continue  # skip a torn line rather than losing the whole file
            if isinstance(obj, dict) and obj.get("fact"):
                rows.append(obj)
    except OSError:
        return []
    return rows