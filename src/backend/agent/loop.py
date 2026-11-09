"""
src/backend/agent/loop.py — Core agent loop: think → act → observe → verify.

Bounded turns, repeat detection, plan-aware, failure-forward.
Follows Mark-LVI's agent/loop.py pattern.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("stella.agent.loop")


class AgentLoop:
    """
    Core agent execution loop.

    think    → plan what to do
    act      → call tools
    observe  → read results
    verify   → check outcome (done / unverified / failed / ask / started)
    repeat   → bounded by max_turns, with repeat detection
    """

    def __init__(
        self,
        llm: Any,
        executor: Any,
        max_turns: int = 10,
        repeat_limit: int = 3,
    ) -> None:
        self.llm = llm
        self.executor = executor
        self.max_turns = max_turns
        self.repeat_limit = repeat_limit
        self._recent_actions: List[str] = []

    def run(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent loop for a given goal.

        Returns a result dict with:
          - status: done | unverified | failed | ask | started
          - summary: human-readable outcome
          - turns: number of turns taken
        """
        turns = 0
        self._recent_actions = []

        while turns < self.max_turns:
            turns += 1

            # Think: ask the LLM for the next action
            plan = self._think(goal, context)
            if not plan:
                return {"status": "ask", "summary": "No plan could be formed.", "turns": turns}

            action_name = plan.get("action")
            parameters = plan.get("parameters", {})

            # Repeat detection
            action_key = f"{action_name}:{sorted(parameters.items())}"
            if self._recent_actions.count(action_key) >= self.repeat_limit:
                logger.warning("Repeat detected for %s; breaking loop", action_name)
                return {
                    "status": "unverified",
                    "summary": f"Repeated action {action_name} without progress.",
                    "turns": turns,
                }
            self._recent_actions.append(action_key)

            # Act: execute the planned action
            result = self.executor.execute(action_name, parameters, context)

            # Observe: record the result
            context["last_result"] = result
            context["last_action"] = action_name

            # Verify: determine outcome
            outcome = self._verify(result, plan)
            if outcome in ("done", "failed", "ask"):
                return {
                    "status": outcome,
                    "summary": result,
                    "turns": turns,
                }

            # Continue loop with updated context
            context["turns"] = turns

        return {
            "status": "unverified",
            "summary": f"Max turns ({self.max_turns}) reached without completion.",
            "turns": turns,
        }

    def _think(self, goal: str, context: Dict[str, Any]) -> Optional[dict]:
        """Ask the LLM to plan the next action."""
        try:
            prompt = self._build_prompt(goal, context)
            response = self.llm.chat(prompt, system="You are an agent planning tool calls.")
            return self._parse_plan(response)
        except Exception as e:
            logger.error("Think phase failed: %s", e)
            return None

    def _build_prompt(self, goal: str, context: Dict[str, Any]) -> str:
        tools_desc = context.get("tool_descriptions", "No tools available.")
        last_result = context.get("last_result", "")
        last_action = context.get("last_action", "")
        turns = context.get("turns", 0)
        procedural = context.get("procedural_memory", "")

        prompt = (
            f"Goal: {goal}\n"
            f"Turn: {turns}\n"
            f"Last action: {last_action}\n"
            f"Last result: {last_result}\n\n"
            f"Available tools:\n{tools_desc}\n\n"
        )
        if procedural:
            prompt += f"Procedural memory (similar past executions):\n{procedural}\n\n"
        prompt += (
            "Decide the next single tool call. Reply with JSON:\n"
            '{"action": "<tool_name>", "parameters": {...}}\n'
            "If no tool is needed, reply: {\"action\": null, \"parameters\": {}}"
        )
        return prompt

    def _parse_plan(self, response: str) -> Optional[dict]:
        """Parse the LLM's plan response into an action dict."""
        import json
        import re

        text = response.strip()
        # Extract JSON from markdown fences if present
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            # Try to find a bare JSON object
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group(0)

        try:
            plan = json.loads(text)
            if not isinstance(plan, dict):
                return None
            return plan
        except json.JSONDecodeError:
            logger.warning("Failed to parse plan from: %s", response[:200])
            return None

    def _verify(self, result: str, plan: dict) -> str:
        """
        Verify the outcome of an action.

        Returns one of: done | unverified | failed | ask | started
        """
        result_lower = result.lower()
        if "done" in result_lower or "completed" in result_lower:
            return "done"
        if "failed" in result_lower or "error" in result_lower:
            return "failed"
        if "unverified" in result_lower or "cannot confirm" in result_lower:
            return "unverified"
        if "ask" in result_lower or "clarify" in result_lower:
            return "ask"
        if "started" in result_lower or "in progress" in result_lower:
            return "started"
        return "unverified"


class HonestyTracker:
    """Tracks tool outcomes using the five honesty words."""

    WORDS = {"done", "unverified", "failed", "ask", "started"}

    def __init__(self) -> None:
        self.history: List[dict] = []

    def record(self, action: str, outcome: str, detail: str = "") -> None:
        if outcome not in self.WORDS:
            outcome = "unverified"
        self.history.append({"action": action, "outcome": outcome, "detail": detail})

    def summary(self) -> str:
        if not self.history:
            return "No actions recorded."
        counts: Dict[str, int] = {}
        for entry in self.history:
            counts[entry["outcome"]] = counts.get(entry["outcome"], 0) + 1
        parts = [f"{k}: {v}" for k, v in sorted(counts.items())]
        return "; ".join(parts)
