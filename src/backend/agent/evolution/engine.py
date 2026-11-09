"""
src/backend/agent/evolution/engine.py — Dr. Zero Evolution Engine.

Orchestrates the self-evolution loop:

  proposer.generate_questions() → solver.attempt(questions) →
  curriculum.update(results) → hrpo.evaluate(results) → repeat

The engine runs in the background and continuously improves Stella's
agent capabilities without any external training data.

Zero-data initialization: starts with zero training data, generates all
training questions internally via the proposer + LLM.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .proposer import Proposer
from .solver import Solver
from .curriculum import Curriculum
from .hrpo import HRPOTracker
from ..integration import AgentIntegration

logger = logging.getLogger("stella.evolution.engine")


class EvolutionEngine:
    """
    Dr. Zero self-evolution engine.

    Runs the proposer → solver → curriculum → HRPO loop in the background.
    Stella trains, learns, and evolves without training data dumps.
    """

    def __init__(
        self,
        integration: AgentIntegration,
        emit: Optional[Callable[[str, Any], None]] = None,
        batch_size: int = 5,
        interval_seconds: int = 300,
        enabled: bool = True,
    ) -> None:
        self.integration = integration
        self.emit = emit
        self.batch_size = batch_size
        self.interval_seconds = interval_seconds
        self.enabled = enabled

        self.proposer = Proposer(llm=integration.planner.llm, difficulty=1)
        self.solver = Solver(integration=integration)
        self.curriculum = Curriculum(proposer=self.proposer, solver=self.solver)
        self.hrpo = HRPOTracker()

        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._iteration = 0

    def start(self) -> None:
        """Start the evolution loop (background task)."""
        if not self.enabled:
            logger.info("Evolution engine disabled; skipping start")
            return
        if self._running:
            return
        # Ensure proposer has the resolved LLM from integration
        if self.integration and self.integration.planner and self.integration.planner.llm:
            self.proposer.llm = self.integration.planner.llm
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Evolution engine started")

    async def stop(self) -> None:
        """Stop the evolution loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Evolution engine stopped")

    async def _loop(self) -> None:
        """Main evolution loop: propose → solve → evaluate → repeat."""
        while self._running:
            try:
                await self._iteration_step()
                self._iteration += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Evolution iteration error: %s", e)
                if self.emit:
                    self.emit("log", {"level": "error", "message": f"Evolution error: {e}", "source": "evolution"})

            await asyncio.sleep(self.interval_seconds)

    async def _iteration_step(self) -> None:
        """Single evolution iteration."""
        self._iteration += 1
        logger.info("Evolution iteration %d starting", self._iteration)

        # 1. Curriculum recommends difficulty
        difficulty = self.curriculum.get_recommended_difficulty()
        self.proposer.difficulty = difficulty

        # 2. Proposer generates questions
        questions = self.proposer.generate_questions(count=self.batch_size)
        if not questions:
            logger.warning("Proposer generated no questions; skipping iteration")
            return

        # 3. Solver attempts each question
        results = self.solver.attempt_batch(questions)

        # 4. Update curriculum and HRPO
        for r in results:
            self.proposer.record_outcome(r.question_id, r.status == "done", r.category, r.difficulty)
            self.curriculum.update_from_result(r)
            self.hrpo.add_result(r)

        # 5. Emit progress
        summary = self.get_summary()
        if self.emit:
            self.emit("evolution", summary)

        logger.info(
            "Evolution iteration %d complete: %d questions, success rate %.2f",
            self._iteration, len(results), summary["solver_success_rate"],
        )

    def run_once(self, count: Optional[int] = None) -> List[dict]:
        """
        Run a single evolution step synchronously (for testing/on-demand).

        Returns a list of result summaries.
        """
        count = count or self.batch_size
        difficulty = self.curriculum.get_recommended_difficulty()
        self.proposer.difficulty = difficulty

        questions = self.proposer.generate_questions(count=count)
        results = self.solver.attempt_batch(questions)

        summaries = []
        for r in results:
            self.proposer.record_outcome(r.question_id, r.status == "done", r.category, r.difficulty)
            self.curriculum.update_from_result(r)
            self.hrpo.add_result(r)
            summaries.append({
                "question_id": r.question_id,
                "question": r.question[:80],
                "category": r.category,
                "difficulty": r.difficulty,
                "status": r.status,
                "duration_ms": r.duration_ms,
            })
        return summaries

    def get_summary(self) -> dict:
        return {
            "iteration": self._iteration,
            "enabled": self.enabled,
            "proposer_difficulty": self.proposer.difficulty,
            "curriculum": self.curriculum.get_summary(),
            "hrpo": self.hrpo.get_summary(),
            "solver_results": len(self.solver.get_history()),
        }

    def is_running(self) -> bool:
        return self._running
