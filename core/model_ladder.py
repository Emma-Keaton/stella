"""core/model_ladder.py - model ladder with cooldowns.

A model ladder is an ordered list of backends the agent tries in sequence:
the cheapest capable model first, falling back to larger/slower models only
when the current one is unavailable, rate-limited, or cooldown-locked.

Each model entry carries:
- name: backend identifier (matches agent.llm.Backend name)
- tier: 1 = cheap/fast/local, 2 = moderate, 3 = large/expensive
- cooldown_seconds: how long to wait after a failure before retrying
- last_failure_ts: timestamp of the last failure (0 if never failed)
- available: whether the backend reports itself as usable right now

A model in cooldown is skipped. A model that fails gets its cooldown started.
Honesty: the ladder reports which model it tried and why it fell back, never
pretending a smaller model answered when it did not.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

DEFAULT_LADDER: list[dict[str, Any]] = [
    {"name": "local", "tier": 1, "cooldown_seconds": 30},
    {"name": "ollama", "tier": 1, "cooldown_seconds": 30},
    {"name": "lmstudio", "tier": 2, "cooldown_seconds": 60},
    {"name": "groq", "tier": 2, "cooldown_seconds": 60},
    {"name": "gemini", "tier": 3, "cooldown_seconds": 120},
    {"name": "openai", "tier": 3, "cooldown_seconds": 120},
]


@dataclass
class ModelEntry:
    """One rung on the ladder."""
    name: str
    tier: int
    cooldown_seconds: float
    last_failure_ts: float = 0.0
    available: bool = True
    failures: int = 0
    successes: int = 0

    def in_cooldown(self, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        if self.last_failure_ts <= 0:
            return False
        return (now - self.last_failure_ts) < self.cooldown_seconds

    def remaining_cooldown(self, now: float | None = None) -> float:
        now = now if now is not None else time.time()
        if self.last_failure_ts <= 0:
            return 0.0
        return max(0.0, self.cooldown_seconds - (now - self.last_failure_ts))

    def mark_failure(self, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        self.last_failure_ts = now
        self.available = False
        self.failures += 1

    def mark_success(self) -> None:
        self.available = True
        self.last_failure_ts = 0.0
        self.successes += 1


class ModelLadder:
    """Ordered model rungs with per-rung cooldowns. Picks the highest-tier
    available model, falling down the ladder on failure."""

    def __init__(self, entries: list[ModelEntry] | None = None):
        self._entries: list[ModelEntry] = list(entries or [])
        self._index = 0  # last attempted rung index

    @classmethod
    def from_config(cls, config: list[dict[str, Any]] | None = None) -> "ModelLadder":
        raw = config if config is not None else list(DEFAULT_LADDER)
        entries = [
            ModelEntry(
                name=str(e["name"]),
                tier=int(e.get("tier", 2)),
                cooldown_seconds=float(e.get("cooldown_seconds", 60)),
            )
            for e in raw
        ]
        # Stable sort by tier ascending (cheapest first).
        entries.sort(key=lambda e: e.tier)
        return cls(entries)

    def names(self) -> list[str]:
        return [e.name for e in self._entries]

    def tiers(self) -> dict[str, int]:
        return {e.name: e.tier for e in self._entries}

    def available_models(self, now: float | None = None) -> list[ModelEntry]:
        """All models not in cooldown and marked available, tier order."""
        now = now if now is not None else time.time()
        return [e for e in self._entries if e.available and not e.in_cooldown(now)]

    def pick(self, now: float | None = None) -> ModelEntry | None:
        """Pick the best available model (lowest tier first), advancing the
        index so repeated picks walk the ladder on cooldown lock."""
        now = now if now is not None else time.time()
        avail = self.available_models(now)
        if not avail:
            return None
        # Prefer the lowest tier; within a tier, round-robin from last index.
        best = min(avail, key=lambda e: e.tier)
        self._index = self._entries.index(best) if best in self._entries else 0
        return best

    def report_failure(self, name: str, now: float | None = None) -> None:
        """Mark one model as failed: starts its cooldown."""
        now = now if now is not None else time.time()
        for e in self._entries:
            if e.name == name:
                e.mark_failure(now)
                return

    def report_success(self, name: str) -> None:
        for e in self._entries:
            if e.name == name:
                e.mark_success()
                return

    def set_available(self, name: str, available: bool) -> None:
        for e in self._entries:
            if e.name == name:
                e.available = available
                if not available:
                    e.last_failure_ts = time.time()
                return

    def status(self, now: float | None = None) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        return [
            {
                "name": e.name,
                "tier": e.tier,
                "available": e.available,
                "in_cooldown": e.in_cooldown(now),
                "cooldown_remaining": round(e.remaining_cooldown(now), 1),
                "failures": e.failures,
                "successes": e.successes,
            }
            for e in self._entries
        ]

    def summary(self) -> str:
        now = time.time()
        rows = []
        for e in self.status(now):
            tag = "OK" if e["available"] and not e["in_cooldown"] else (
                f"cooldown {e['cooldown_remaining']}s" if e["in_cooldown"] else "unavailable")
            rows.append(f"{e['name']}(t{e['tier']}): {tag}")
        return " | ".join(rows)


__all__ = [
    "ModelEntry", "ModelLadder", "DEFAULT_LADDER",
]
