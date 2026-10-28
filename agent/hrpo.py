"""agent/hrpo.py - Hop-grouped Relative Policy Optimization (from Phase K / drzero).

HRPO reduces evaluation cost by grouping structurally similar questions into
groups and computing group-level baselines, rather than evaluating every
question individually. It also implements cooldown-based failure tracking for
the model ladder, so failed models are not retried immediately.

Design (from drzero):
- Group questions by their structural pattern (tool sequence, activity class,
  target pattern).
- Compute group-level baselines (average score, success rate).
- Skip re-evaluation of questions within the same group if the group already
  has a confident baseline.
- Track per-model cooldowns: failed models are locked for cooldown_seconds,
  preventing immediate retries.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from core.model_ladder import ModelLadder, ModelEntry


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


@dataclass
class HopGroup:
    """One group of structurally similar questions."""
    group_id: str
    pattern: str  # e.g. "dns|active|example.com" or "file|passive|/tmp/*"
    questions: list[dict[str, Any]] = field(default_factory=list)
    baseline_score: float = 0.0
    baseline_confidence: float = 0.0
    runs: int = 0
    successes: int = 0
    failures: int = 0
    last_updated: float = 0.0

    def add(self, question: dict[str, Any], score: float, success: bool) -> None:
        self.questions.append(question)
        self.runs += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        # Running average
        self.baseline_score = (
            (self.baseline_score * (self.runs - 1) + score) / self.runs
        )
        self.last_updated = time.time()

    def summary(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "pattern": self.pattern,
            "questions": len(self.questions),
            "runs": self.runs,
            "successes": self.successes,
            "failures": self.failures,
            "baseline_score": round(self.baseline_score, 3),
            "baseline_confidence": round(self.baseline_confidence, 3),
        }


class HRPO:
    """Hop-grouped Relative Policy Optimization.

    Groups questions by structural pattern and computes group-level baselines.
    Skips re-evaluation of questions within a group that already has a
    confident baseline. Tracks per-model cooldowns so failed models are not
    retried immediately.
    """

    def __init__(self, ladder: ModelLadder | None = None,
                 cooldown_threshold: float = 0.5):
        self.ladder = ladder or ModelLadder.from_config()
        self.cooldown_threshold = cooldown_threshold
        self._groups: dict[str, HopGroup] = {}
        self._global_stats: dict[str, Any] = {
            "total_questions": 0,
            "total_groups": 0,
            "skipped_duplicates": 0,
            "total_failures": 0,
            "total_successes": 0,
        }

    def _group_key(self, question: dict[str, Any]) -> str:
        """Compute a group key from question attributes."""
        activity = str(question.get("activity", "passive"))
        target = str(question.get("target", ""))
        tool = str(question.get("tool", "none"))
        # Hash the structural pattern
        raw = f"{activity}|{target}|{tool}"
        return hashlib.md5(raw.encode()).hexdigest()[:8]

    def _group_name(self, key: str) -> str:
        return f"grp-{key}"

    def evaluate(self, question: dict[str, Any],
                 score_fn) -> dict[str, Any]:
        """Evaluate one question through HRPO.

        Returns a dict with:
          - group_id, group_name
          - skipped: whether this question was skipped (baseline already exists)
          - score: the score (from cache or fresh evaluation)
          - success: whether the question succeeded
          - reason: why this decision was made
        """
        key = self._group_key(question)
        group = self._groups.get(key)

        if group is None:
            group = HopGroup(group_id=key, pattern=key)
            self._groups[key] = group
            self._global_stats["total_groups"] += 1

        # Check if we have a confident baseline for this group
        if group.runs >= 3 and group.baseline_score >= self.cooldown_threshold:
            # Skip re-evaluation: use the baseline
            self._global_stats["skipped_duplicates"] += 1
            return {
                "group_id": key,
                "group_name": self._group_name(key),
                "skipped": True,
                "score": group.baseline_score,
                "success": group.baseline_score >= self.cooldown_threshold,
                "reason": "baseline_cached",
            }

        # Run the actual evaluation
        score = score_fn(question)
        success = score >= self.cooldown_threshold

        group.add(question, score, success)
        self._global_stats["total_questions"] += 1
        if success:
            self._global_stats["successes"] += 1
        else:
            self._global_stats["total_failures"] += 1

        return {
            "group_id": key,
            "group_name": self._group_name(key),
            "skipped": False,
            "score": score,
            "success": success,
            "reason": "fresh_evaluation",
        }

    def report_failure(self, model_name: str) -> None:
        """Report a model failure to start its cooldown."""
        self.ladder.report_failure(model_name)

    def report_success(self, model_name: str) -> None:
        """Report a model success to end its cooldown."""
        self.ladder.report_success(model_name)

    def summary(self) -> dict[str, Any]:
        return {
            "total_questions": self._global_stats["total_questions"],
            "total_groups": self._global_stats["total_groups"],
            "skipped_duplicates": self._global_stats["skipped_duplicates"],
            "total_failures": self._global_stats["total_failures"],
            "total_successes": self._global_stats["total_successes"],
            "groups": {k: v.summary() for k, v in self._groups.items()},
        }


__all__ = [
    "HopGroup",
    "HRPO",
    "_op",
]
