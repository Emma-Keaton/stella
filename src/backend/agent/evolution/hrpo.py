"""
src/backend/agent/evolution/hrpo.py — Hop-Grouped Relative Policy Optimization.

Clusters structurally similar questions to construct group-level baselines,
effectively minimizing the sampling overhead in evaluating each query's
individual difficulty and solvability. Reduces compute requirements for
evaluating solver performance without compromising stability.

From Dr. Zero paper: HRPO groups questions by "hop" (number of reasoning steps
or tool calls needed) and compares solver performance within each group rather
than absolutely.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from .solver import SolverResult

logger = logging.getLogger("stella.evolution.hrpo")


def group_by_hop(results: List[SolverResult]) -> Dict[int, List[SolverResult]]:
    """
    Group solver results by estimated hop count.

    Hop count is estimated from the tools_used list length or the question's
    expected_tools count. Questions in the same hop group have similar
    structural complexity.
    """
    groups: Dict[int, List[SolverResult]] = defaultdict(list)
    for r in results:
        # Estimate hops from tools used
        hop = len(r.tools_used) if r.tools_used else 1
        # Cap at 5 for grouping
        hop = min(hop, 5)
        groups[hop].append(r)
    return dict(groups)


def compute_group_baselines(
    results: List[SolverResult],
) -> Dict[int, dict]:
    """
    Compute group-level baselines for each hop group.

    Returns per-hop-group stats: success rate, avg duration, count.
    These baselines are used to evaluate individual question difficulty
    relative to the group, reducing the need for per-question absolute
    evaluation.
    """
    groups = group_by_hop(results)
    baselines: Dict[int, dict] = {}
    for hop, group_results in groups.items():
        done = sum(1 for r in group_results if r.status == "done")
        rate = done / len(group_results) if group_results else 0.0
        avg_duration = sum(r.duration_ms for r in group_results) / len(group_results) if group_results else 0.0
        baselines[hop] = {
            "count": len(group_results),
            "success_rate": rate,
            "avg_duration_ms": avg_duration,
            "done_count": done,
        }
    return baselines


def evaluate_relative_difficulty(
    result: SolverResult,
    baselines: Dict[int, dict],
) -> dict:
    """
    Evaluate a single result relative to its hop-group baseline.

    Returns a dict with:
      - hop: estimated hop count
      - group_success_rate: baseline success rate for this hop group
      - relative_performance: "above" | "at" | "below" baseline
      - is_outlier: whether this result is significantly different from group
    """
    hop = len(result.tools_used) if result.tools_used else 1
    hop = min(hop, 5)
    baseline = baselines.get(hop, {"success_rate": 0.5, "count": 0})

    group_rate = baseline["success_rate"]
    result_success = 1.0 if result.status == "done" else 0.0

    # Relative performance: compare to group baseline
    if group_rate > 0.7:
        relative = "above" if result_success == 1.0 else "below"
    elif group_rate < 0.3:
        relative = "below" if result_success == 0.0 else "above"
    else:
        relative = "at"

    is_outlier = baseline["count"] >= 5 and abs(result_success - group_rate) > 0.5

    return {
        "hop": hop,
        "group_success_rate": group_rate,
        "group_count": baseline["count"],
        "relative_performance": relative,
        "is_outlier": is_outlier,
        "result_success": result_success,
    }


class HRPOTracker:
    """Tracks HRPO baselines over time for the evolution engine."""

    def __init__(self) -> None:
        self._all_results: List[SolverResult] = []
        self._baselines: Dict[int, dict] = {}

    def add_result(self, result: SolverResult) -> None:
        self._all_results.append(result)
        self._baselines = compute_group_baselines(self._all_results)

    def evaluate(self, result: SolverResult) -> dict:
        return evaluate_relative_difficulty(result, self._baselines)

    def get_baselines(self) -> Dict[int, dict]:
        return dict(self._baselines)

    def get_summary(self) -> dict:
        return {
            "total_results": len(self._all_results),
            "hop_groups": len(self._baselines),
            "baselines": self._baselines,
        }
