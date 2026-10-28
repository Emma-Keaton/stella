"""
src/backend/agent/evolution/curriculum.py — Automated Curriculum.

Adjusts question difficulty based on solver success rate. As the solver
improves, the proposer generates harder yet solvable tasks — establishing
an automated curriculum (Dr. Zero's key insight).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .proposer import Proposer
from .solver import SolverResult

logger = logging.getLogger("stella.evolution.curriculum")


class Curriculum:
    """
    Automated curriculum manager.

    Tracks solver performance by category and difficulty, and recommends
    the next difficulty level for the proposer. Uses a success-rate
    threshold: if the solver is succeeding >80% of the time, increase
    difficulty; if <40%, decrease.
    """

    def __init__(self, proposer: Proposer, solver: Any) -> None:
        self.proposer = proposer
        self.solver = solver
        self._category_levels: Dict[str, int] = {}  # category -> current difficulty
        self._global_level = 1

    def update_from_result(self, result: SolverResult) -> None:
        """Update curriculum state from a solver result."""
        cat = result.category
        if cat not in self._category_levels:
            self._category_levels[cat] = result.difficulty

        # Track recent window per category
        # (simplified: just adjust global level based on overall success)
        self._maybe_adjust_level()

    def _maybe_adjust_level(self) -> None:
        """Adjust global difficulty based on recent solver performance."""
        recent = self.solver.get_recent_results(n=10)
        if len(recent) < 5:
            return

        done = sum(1 for r in recent if r.status == "done")
        rate = done / len(recent)

        if rate > 0.8 and self._global_level < 3:
            self._global_level += 1
            logger.info("Curriculum: increasing global difficulty to %d (success rate %.2f)", self._global_level, rate)
        elif rate < 0.4 and self._global_level > 1:
            self._global_level -= 1
            logger.info("Curriculum: decreasing global difficulty to %d (success rate %.2f)", self._global_level, rate)

    def get_recommended_difficulty(self, category: Optional[str] = None) -> int:
        """Get recommended difficulty for the next question batch."""
        if category and category in self._category_levels:
            return self._category_levels[category]
        return self._global_level

    def get_summary(self) -> dict:
        return {
            "global_level": self._global_level,
            "category_levels": dict(self._category_levels),
            "solver_success_rate": self.solver.get_success_rate(),
        }
