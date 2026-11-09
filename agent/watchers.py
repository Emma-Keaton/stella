"""agent/watchers.py - watchers on the scheduler.

A watcher observes a recurring condition (a tool result, a budget line, a
model in cooldown, a file appearing, a port opening) and fires an action when
the condition becomes true. Watchers are the scheduler's eyes: they run on a
tick, never block the agent loop, and report honestly when a condition has
not yet been met.

Design:
* `Watcher` holds a condition callable, an action callable, a tick interval,
  and a fire-once flag. `tick(now)` evaluates the condition; when true it runs
  the action and returns the result.
* `WatcherRegistry` holds all watchers for a session and ticks them on each
  scheduler pass.
* Watchers never widen permissions: they run within the agent's existing
  tool registry and policy gate.

Honesty: a watcher that fires reports what it observed and what it did; a
watcher that has not fired yet reports "pending" with its condition.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from agent.tools import ToolResult, Honesty

Condition = Callable[[], tuple[bool, str]]
Action = Callable[[], ToolResult]


@dataclass
class Watcher:
    """One scheduled observation + action."""
    name: str
    condition: Condition
    action: Action
    interval_s: float = 30.0
    fire_once: bool = True
    last_tick: float = 0.0
    fired: bool = False
    fires: int = 0
    last_result: str | None = None
    last_error: str | None = None

    def due(self, now: float) -> bool:
        return (now - self.last_tick) >= self.interval_s

    def tick(self, now: float | None = None) -> dict[str, Any] | None:
        """Evaluate once if due. Returns a tick record or None if not due."""
        now = now if now is not None else time.time()
        if not self.due(now):
            return None
        self.last_tick = now

        try:
            met, reason = self.condition()
        except Exception as exc:  # pragma: no cover - condition failure is logged
            self.last_error = f"{type(exc).__name__}: {exc}"
            return {"watcher": self.name, "fired": False, "error": self.last_error,
                    "condition_met": False, "at": now}

        if not met:
            self.last_result = f"pending: {reason}"
            return {"watcher": self.name, "fired": False,
                    "condition_met": False, "reason": reason, "at": now}

        if self.fire_once and self.fired:
            self.last_result = "already fired"
            return {"watcher": self.name, "fired": False,
                    "condition_met": True, "reason": "already fired (fire_once)", "at": now}

        try:
            outcome = self.action()
            self.fired = True
            self.fires += 1
            self.last_result = outcome.as_message()
            return {
                "watcher": self.name, "fired": True,
                "condition_met": True, "ok": outcome.ok,
                "output": outcome.output, "error": outcome.error,
                "honesty": str(outcome.honesty), "at": now,
            }
        except Exception as exc:  # pragma: no cover - action failure is logged
            self.last_error = f"{type(exc).__name__}: {exc}"
            return {"watcher": self.name, "fired": False, "error": self.last_error,
                    "condition_met": True, "at": now}

    def status(self, now: float | None = None) -> dict[str, Any]:
        now = now if now is not None else time.time()
        return {
            "name": self.name,
            "fired": self.fired,
            "fires": self.fires,
            "interval_s": self.interval_s,
            "fire_once": self.fire_once,
            "last_tick": self.last_tick,
            "next_tick_in": round(max(0.0, self.interval_s - (now - self.last_tick)), 1),
            "last_result": self.last_result,
            "last_error": self.last_error,
        }


class WatcherRegistry:
    """Holds all watchers for a session and ticks them on each scheduler pass."""

    def __init__(self):
        self._watchers: dict[str, Watcher] = {}

    def add(self, watcher: Watcher) -> None:
        self._watchers[watcher.name] = watcher

    def remove(self, name: str) -> bool:
        return self._watchers.pop(name, None) is not None

    def get(self, name: str) -> Watcher | None:
        return self._watchers.get(name)

    def tick_all(self, now: float | None = None) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        records = []
        for watcher in self._watchers.values():
            record = watcher.tick(now)
            if record is not None:
                records.append(record)
        return records

    def status_all(self, now: float | None = None) -> list[dict[str, Any]]:
        now = now if now is not None else time.time()
        return [w.status(now) for w in self._watchers.values()]

    def names(self) -> list[str]:
        return sorted(self._watchers)

    def __len__(self) -> int:
        return len(self._watchers)


def make_watcher(
    name: str,
    condition: Condition,
    action: Action,
    interval_s: float = 30.0,
    fire_once: bool = True,
) -> Watcher:
    """Convenience constructor."""
    return Watcher(
        name=name, condition=condition, action=action,
        interval_s=interval_s, fire_once=fire_once,
    )


__all__ = [
    "Watcher", "WatcherRegistry", "make_watcher",
    "Condition", "Action",
]
