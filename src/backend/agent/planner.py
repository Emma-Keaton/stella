"""
src/backend/agent/planner.py — Task planner.

Breaks goals into JSON tool steps. Injects learned rules and dynamic tools.
Gemini-based planning (can work with any LLM backend).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("stella.agent.planner")


class Planner:
    """
    Task planner: given a goal and available tools, produces a sequence of
    JSON tool-call steps that the executor can run.
    """

    def __init__(self, llm: Any, tool_declarations: List[dict]) -> None:
        self.llm = llm
        self.tool_declarations = tool_declarations
        self._learned_rules: List[str] = []

    def add_learned_rule(self, rule: str) -> None:
        """Add a learned behavioral rule (from self-evolution / reflection)."""
        self._learned_rules.append(rule)

    def plan(self, goal: str, context: Dict[str, Any]) -> List[dict]:
        """
        Break goal into ordered tool steps.

        Returns a list of {"action": str, "parameters": dict} steps.
        """
        try:
            plan_text = self._generate_plan(goal, context)
            return self._parse_steps(plan_text)
        except Exception as e:
            logger.error("Planning failed: %s", e)
            return []

    def _generate_plan(self, goal: str, context: Dict[str, Any]) -> str:
        tools_desc = self._format_tools()
        rules_desc = "\n".join(f"- {r}" for r in self._learned_rules) or "(none)"

        return (
            f"Goal: {goal}\n\n"
            f"Available tools:\n{tools_desc}\n\n"
            f"Learned rules:\n{rules_desc}\n\n"
            "Break this goal into ordered tool-call steps. Reply with JSON array:\n"
            '[{"action": "<tool_name>", "parameters": {...}}, ...]\n'
            "If no tools are needed, reply: []"
        )

    def _format_tools(self) -> str:
        lines = []
        for decl in self.tool_declarations:
            name = decl.get("name", "unknown")
            desc = decl.get("description", "")
            params = decl.get("parameters", {})
            props = params.get("properties", {})
            required = params.get("required", [])
            req_str = ", ".join(required) if required else "none"
            lines.append(f"  {name}: {desc} (params: {req_str})")
        return "\n".join(lines) if lines else "  (none)"

    def _parse_steps(self, text: str) -> List[dict]:
        """Parse the LLM's plan response into a list of steps."""
        text = text.strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            text = match.group(0)
        try:
            steps = json.loads(text)
            if isinstance(steps, list):
                return steps
        except json.JSONDecodeError:
            logger.warning("Failed to parse plan steps from: %s", text[:200])
        return []
