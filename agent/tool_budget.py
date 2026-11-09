"""agent/tool_budget.py - tool budget by count AND size.

A tool call has two costs: how many tools the model calls (turn pressure) and
how large the tool's payload is (context pressure). Both are tracked here so
the agent can stay inside a local model's small context window without lying
about what it did.

Design (from the Phase K A1-A5 spec):

* `Budget` holds a per-session allowance: max calls, max total payload bytes,
  max per-call payload bytes, and a per-turn call cap.
* `spent()` reports what has been consumed so far.
* `room_left()` says whether another call of a given estimated size fits.
* `charge(call_name, payload_bytes)` records one call and returns whether it
  was within budget - an over-budget call is refused with `Honesty.ASK` and a
  reason naming the budget line that broke.
* Budgets are declared in config/tool_policy.json-adjacent shape (JSON) and
  can be tuned per agent without touching code.

Honesty: budget refusals say exactly which limit was hit, so the model can
pick a smaller tool or finish with what it has - never round up to "done".
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.tools import ToolResult, Honesty

logger = logging.getLogger("tool_budget")


DEFAULT_LIMITS: dict[str, Any] = {
    "max_calls": 40,            # total tool calls in a session
    "max_total_bytes": 64 * 1024,  # 64 KiB of tool payload text in a session
    "max_per_call_bytes": 8 * 1024,  # 8 KiB per single call
    "max_calls_per_turn": 4,  # how many calls one turn may issue
}


@dataclass
class CallRecord:
    """One recorded tool call, enough to audit budget spending."""
    name: str
    turn: int
    payload_bytes: int
    ok: bool
    within_budget: bool
    reason: str = ""


@dataclass
class Budget:
    """A per-session tool budget: count + size, both enforced."""

    max_calls: int = DEFAULT_LIMITS["max_calls"]
    max_total_bytes: int = DEFAULT_LIMITS["max_total_bytes"]
    max_per_call_bytes: int = DEFAULT_LIMITS["max_per_call_bytes"]
    max_calls_per_turn: int = DEFAULT_LIMITS["max_calls_per_turn"]

    # Runtime state
    calls: list[CallRecord] = field(default_factory=list)
    total_bytes: int = 0
    calls_this_turn: int = 0
    current_turn: int = 0

    # ---------------------------------------------------------------- query

    def spent_calls(self) -> int:
        return len(self.calls)

    def spent_bytes(self) -> int:
        return self.total_bytes

    def calls_remaining(self) -> int:
        return max(0, self.max_calls - len(self.calls))

    def bytes_remaining(self) -> int:
        return max(0, self.max_total_bytes - self.total_bytes)

    def room_for(self, estimated_bytes: int) -> tuple[bool, str]:
        """True if a call of `estimated_bytes` fits, with the reason if not."""
        if estimated_bytes > self.max_per_call_bytes:
            return False, (
                f"single-call budget {self.max_per_call_bytes} bytes "
                f"would be exceeded by {estimated_bytes} bytes"
            )
        if len(self.calls) >= self.max_calls:
            return False, f"call budget {self.max_calls} exhausted"
        if self.total_bytes + estimated_bytes > self.max_total_bytes:
            return False, (
                f"total byte budget {self.max_total_bytes} would be exceeded "
                f"({self.total_bytes} + {estimated_bytes})"
            )
        if self.calls_this_turn >= self.max_calls_per_turn:
            return False, f"per-turn call cap {self.max_calls_per_turn} reached"
        return True, "within budget"

    def summary(self) -> dict[str, Any]:
        return {
            "calls": len(self.calls),
            "max_calls": self.max_calls,
            "calls_remaining": self.calls_remaining(),
            "total_bytes": self.total_bytes,
            "max_total_bytes": self.max_total_bytes,
            "bytes_remaining": self.bytes_remaining(),
            "per_call_bytes_limit": self.max_per_call_bytes,
            "calls_this_turn": self.calls_this_turn,
            "max_calls_per_turn": self.max_calls_per_turn,
        }

    # ---------------------------------------------------------------- charge

    def begin_turn(self, turn: int) -> None:
        self.current_turn = turn
        self.calls_this_turn = 0

    def charge(self, name: str, payload_bytes: int) -> tuple[bool, str]:
        """Record one call; returns (within_budget, reason). A refusal carries
        the exact budget line that broke so the model can adapt."""
        within, reason = self.room_for(payload_bytes)
        record = CallRecord(
            name=name,
            turn=self.current_turn,
            payload_bytes=payload_bytes,
            ok=within,
            within_budget=within,
            reason=reason,
        )
        self.calls.append(record)
        self.calls_this_turn += 1
        if within:
            self.total_bytes += payload_bytes
        return within, reason


def _budget_path() -> Path:
    try:
        from core.user_paths import get_user_data_dir
        return Path(get_user_data_dir()) / "config" / "tool_budget.json"
    except Exception:
        return Path("config") / "tool_budget.json"


def load_limits() -> dict[str, Any]:
    """Load budget limits from the user-data config, falling back to defaults."""
    path = _budget_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = dict(DEFAULT_LIMITS)
                merged.update(data)
                return merged
    except Exception as exc:  # pragma: no cover - never block the agent
        logger.warning("Could not read tool budget %s: %s", path, exc)
    return dict(DEFAULT_LIMITS)


def ensure_default_budget_file() -> Path:
    """Write the shipped default budget file if it is missing."""
    path = _budget_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"version": 1, "limits": DEFAULT_LIMITS}, indent=2),
            encoding="utf-8",
        )
    return path


def budget_refusal(name: str, reason: str) -> ToolResult:
    """Build a ToolResult for a budget-refused call: honesty ASK, reason names
    the budget line."""
    return ToolResult(
        ok=False,
        error=(
            f"Tool budget refused '{name}': {reason}. "
            "Pick a smaller tool, batch fewer calls, or finish with what you "
            "have - do not round a budget refusal up to done."
        ),
        honesty=Honesty.ASK,
    )


__all__ = [
    "Budget", "CallRecord", "DEFAULT_LIMITS",
    "load_limits", "ensure_default_budget_file",
    "budget_refusal",
]
