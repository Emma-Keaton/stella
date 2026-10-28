"""
src/backend/agent/evolution/proposer.py — Dr. Zero Proposer.

Generates diverse, challenging-yet-solvable questions to drive the solver's
self-improvement. Uses domain templates + the LLM (no training data needed).

As the solver evolves, the proposer is incentivized to produce increasingly
difficult yet solvable tasks — establishing an automated curriculum.
"""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("stella.evolution.proposer")

# ── Domain templates for zero-data question generation ──
# Each template has a category, difficulty range, and a prompt skeleton.

_DOMAIN_TEMPLATES: List[dict] = [
    {
        "category": "web_research",
        "difficulty": 1,
        "prompt": "Find a specific factual answer about {topic} that requires visiting at least one website.",
    },
    {
        "category": "web_research",
        "difficulty": 2,
        "prompt": "Compare two conflicting sources of information about {topic} and determine which is more reliable.",
    },
    {
        "category": "web_research",
        "difficulty": 3,
        "prompt": "Investigate a recent development in {topic} and summarize the key players, timeline, and implications.",
    },
    {
        "category": "file_analysis",
        "difficulty": 1,
        "prompt": "Read a local file and extract specific information requested by the user.",
    },
    {
        "category": "file_analysis",
        "difficulty": 2,
        "prompt": "Analyze multiple local files to find connections or discrepancies between them.",
    },
    {
        "category": "file_analysis",
        "difficulty": 3,
        "prompt": "Process a set of local files and generate a structured report with findings and recommendations.",
    },
    {
        "category": "multi_step",
        "difficulty": 2,
        "prompt": "Complete a task that requires first searching for information, then using that information to act on a local file or application.",
    },
    {
        "category": "multi_step",
        "difficulty": 3,
        "prompt": "Execute a multi-step workflow involving web research, file processing, and verification of results.",
    },
    {
        "category": "verification",
        "difficulty": 2,
        "prompt": "Verify a claim about {topic} by cross-referencing at least two independent sources.",
    },
    {
        "category": "verification",
        "difficulty": 3,
        "prompt": "Investigate a controversial claim about {topic}, weigh evidence from multiple sources, and reach a reasoned conclusion.",
    },
]


class Proposer:
    """
    Proposer agent: generates diverse questions to train the solver.

    The proposer starts with domain templates and uses the LLM to generate
    concrete questions. As the solver improves, the proposer increases
    difficulty (automated curriculum driven by the Curriculum class).
    """

    def __init__(
        self,
        llm: Any,
        difficulty: int = 1,
        max_questions_per_batch: int = 5,
    ) -> None:
        self.llm = llm
        self.difficulty = difficulty
        self.max_questions_per_batch = max_questions_per_batch
        self._generated_history: List[dict] = []
        self._success_by_category: Dict[str, List[bool]] = {}

    def generate_questions(
        self,
        count: Optional[int] = None,
        min_difficulty: Optional[int] = None,
        max_difficulty: Optional[int] = None,
        categories: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        Generate a batch of diverse questions.

        Returns a list of question dicts with keys:
          - id: unique question id
          - category: domain category
          - difficulty: 1-3
          - question: the question text
          - expected_tools: list of tools likely needed
        """
        count = count or self.max_questions_per_batch
        min_d = min_difficulty or max(1, self.difficulty - 1)
        max_d = max_difficulty or min(3, self.difficulty + 1)
        cats = categories or [t["category"] for t in _DOMAIN_TEMPLATES]

        # Filter templates by difficulty and category
        eligible = [
            t
            for t in _DOMAIN_TEMPLATES
            if min_d <= t["difficulty"] <= max_d and t["category"] in cats
        ]
        if not eligible:
            eligible = _DOMAIN_TEMPLATES

        questions: List[dict] = []
        used_templates = random.sample(eligible, min(count, len(eligible)))

        for i, template in enumerate(used_templates):
            question_text = self._generate_concrete_question(template)
            qid = f"q{len(self._generated_history) + i + 1:04d}"
            questions.append({
                "id": qid,
                "category": template["category"],
                "difficulty": template["difficulty"],
                "question": question_text,
                "expected_tools": self._infer_tools(template["category"]),
            })

        self._generated_history.extend(questions)
        logger.info("Proposer generated %d questions (difficulty %d-%d)", len(questions), min_d, max_d)
        return questions

    def _generate_concrete_question(self, template: dict) -> str:
        """Use the LLM to turn a template into a concrete question."""
        try:
            prompt = (
                f"Turn this template into a specific, concrete question:\n"
                f"Template: {template['prompt']}\n"
                f"Category: {template['category']}\n"
                f"Difficulty: {template['difficulty']}/3\n\n"
                "Write one clear question. No preamble, no explanation, just the question."
            )
            response = self.llm.chat(prompt, system="You are a question generator.")
            question = response.strip().strip('"').strip("'")
            if not question:
                question = template["prompt"].format(topic="current events")
            return question
        except Exception as e:
            logger.warning("LLM question generation failed: %s; using template", e)
            return template["prompt"].format(topic="current events")

    def _infer_tools(self, category: str) -> List[str]:
        """Infer which tools are likely needed for a category."""
        mapping = {
            "web_research": ["web_search"],
            "file_analysis": ["read_file", "search_text"],
            "multi_step": ["web_search", "read_file", "write_file"],
            "verification": ["web_search"],
        }
        return mapping.get(category, ["web_search"])

    def record_outcome(self, question_id: str, success: bool, category: str, difficulty: int) -> None:
        """Record whether the solver succeeded on a question. Feeds curriculum."""
        if category not in self._success_by_category:
            self._success_by_category[category] = []
        self._success_by_category[category].append(success)

        # Track recent success rate per category
        recent = self._success_by_category[category][-10:]
        if recent:
            rate = sum(recent) / len(recent)
            logger.debug("Category %s recent success rate: %.2f", category, rate)

    def get_difficulty_recommendation(self) -> int:
        """Recommend difficulty based on recent solver performance."""
        if not self._success_by_category:
            return self.difficulty

        # Overall recent success rate
        all_recent: List[bool] = []
        for cat_results in self._success_by_category.values():
            all_recent.extend(cat_results[-5:])

        if not all_recent:
            return self.difficulty

        rate = sum(all_recent) / len(all_recent)
        if rate > 0.8:
            return min(3, self.difficulty + 1)  # solver is doing well, increase difficulty
        if rate < 0.4:
            return max(1, self.difficulty - 1)  # solver struggling, decrease difficulty
        return self.difficulty
