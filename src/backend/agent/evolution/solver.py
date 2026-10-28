"""
src/backend/agent/evolution/solver.py — Dr. Zero Solver.

The solver is Stella's own agent loop applied to synthetic questions generated
by the proposer. It uses existing tools (web_search, read_file, etc.) to attempt
to answer each question, and records outcomes (done / unverified / failed / ask /
started) for the curriculum and HRPO evaluation.

Zero-data: the solver learns solely from its own attempts on proposer-generated
questions — no external training data.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from ..integration import AgentIntegration

logger = logging.getLogger("stella.evolution.solver")


class SolverResult:
    """Result of a solver attempt on a single question."""

    def __init__(
        self,
        question_id: str,
        question: str,
        category: str,
        difficulty: int,
        status: str,  # done | unverified | failed | ask | started
        answer: str,
        tools_used: List[str],
        duration_ms: float,
    ) -> None:
        self.question_id = question_id
        self.question = question
        self.category = category
        self.difficulty = difficulty
        self.status = status
        self.answer = answer
        self.tools_used = tools_used
        self.duration_ms = duration_ms
        self.timestamp = time.time()


class Solver:
    """
    Solver agent: attempts to answer proposer-generated questions using Stella's
    own agent runtime (loop → planner → executor → tools).

    The solver is initialized from Stella's base agent and improves through
    self-evolution on synthetic questions.
    """

    def __init__(
        self,
        integration: AgentIntegration,
        max_turns_per_question: int = 8,
    ) -> None:
        self.integration = integration
        self.max_turns_per_question = max_turns_per_question
        self._history: List[SolverResult] = []

    def attempt(self, question: dict) -> SolverResult:
        """
        Attempt to answer a single question using Stella's agent loop.

        Returns a SolverResult with the honesty status.
        """
        start = time.time()
        qid = question["id"]
        text = question["question"]
        category = question.get("category", "general")
        difficulty = question.get("difficulty", 1)

        context: Dict[str, Any] = {
            "evolution_mode": True,
            "question_id": qid,
            "category": category,
            "difficulty": difficulty,
            "max_turns": self.max_turns_per_question,
        }

        try:
            response = self.integration.send(text, context)
            duration_ms = (time.time() - start) * 1000

            # Determine honesty status from the integration's tracker
            # Default to unverified if we can't determine
            status = "unverified"
            tools_used: List[str] = []

            result = SolverResult(
                question_id=qid,
                question=text,
                category=category,
                difficulty=difficulty,
                status=status,
                answer=response,
                tools_used=tools_used,
                duration_ms=duration_ms,
            )
            self._history.append(result)
            logger.info(
                "Solver attempt %s: %s (difficulty %d, %.0fms)",
                qid, status, difficulty, duration_ms,
            )
            return result

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.error("Solver attempt %s failed: %s", qid, e)
            result = SolverResult(
                question_id=qid,
                question=text,
                category=category,
                difficulty=difficulty,
                status="failed",
                answer=str(e),
                tools_used=[],
                duration_ms=duration_ms,
            )
            self._history.append(result)
            return result

    def attempt_batch(self, questions: List[dict]) -> List[SolverResult]:
        """Attempt a batch of questions sequentially."""
        results = []
        for q in questions:
            results.append(self.attempt(q))
        return results

    def get_history(self) -> List[SolverResult]:
        return list(self._history)

    def get_success_rate(self, category: Optional[str] = None, difficulty: Optional[int] = None) -> float:
        """Get success rate (status == 'done') filtered by category/difficulty."""
        results = self._history
        if category:
            results = [r for r in results if r.category == category]
        if difficulty is not None:
            results = [r for r in results if r.difficulty == difficulty]
        if not results:
            return 0.0
        done = sum(1 for r in results if r.status == "done")
        return done / len(results)

    def get_recent_results(self, n: int = 10) -> List[SolverResult]:
        return self._history[-n:]
