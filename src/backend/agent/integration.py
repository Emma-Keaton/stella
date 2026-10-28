"""
src/backend/agent/integration.py — Bridge between UI/voice layer and agent loop.

Connects the frontend (Electron/SolidJS or any UI) to the agent runtime.
Provides a simple send() method that accepts user input and returns the agent's
response, orchestrating loop → planner → executor → tools.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from .loop import AgentLoop, HonestyTracker
from .planner import Planner
from .executor import AgentExecutor
from .procedural import recall as proc_recall
from .tools import Registry
from .frontier_router import FrontierRouter

logger = logging.getLogger("stella.agent.integration")


class AgentIntegration:
    """
    High-level bridge for the UI/voice layer.

    Methods:
      send(text, context) -> str        # Process user input, return response
      get_tools() -> list[dict]          # All tool declarations for the LLM
      register_tool(tool)                # Register a built-in tool
      set_learned_rule(rule)             # Add a learned behavioral rule
    """

    def __init__(
        self,
        llm: Any,
        tool_registry: Optional[Registry] = None,
        action_registry: Optional[Any] = None,
        plugin_registry: Optional[Any] = None,
        skill_loader: Optional[Any] = None,
        get_plugin_enabled: Optional[Callable[[str], bool]] = None,
        frontier_router: Optional[FrontierRouter] = None,
    ) -> None:
        self.tool_registry = tool_registry or Registry()
        self.action_registry = action_registry
        self.plugin_registry = plugin_registry
        self.skill_loader = skill_loader
        self.frontier_router = frontier_router or FrontierRouter()

        self.executor = AgentExecutor(
            tool_registry=self.tool_registry,
            action_registry=self.action_registry,
            plugin_registry=self.plugin_registry,
            skill_loader=self.skill_loader,
            get_plugin_enabled=get_plugin_enabled,
        )
        self.planner = Planner(llm=llm, tool_declarations=self.executor.get_all_declarations())
        self.loop = AgentLoop(llm=llm, executor=self.executor)
        self.honesty = HonestyTracker()

        # Register built-in tools into the registry
        from .tools import BUILTIN_TOOLS
        for tool in BUILTIN_TOOLS:
            self.tool_registry.register(tool)

    def send(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process user input through the agent loop.

        Returns the agent's spoken/text response.
        """
        ctx = context or {}
        ctx["user_input"] = text
        ctx["goal"] = text
        ctx["tool_descriptions"] = self._format_tools()

        # Phase 5: Frontier routing — classify before picking a backend
        route = self.frontier_router.route(text)
        ctx["frontier_route"] = {
            "backend": route.backend,
            "reason": route.reason,
            "confidence": route.confidence,
            "forced_local": route.forced_local,
            "opted_into_frontier": route.opted_into_frontier,
        }
        logger.info("Route decision: %s -> %s (%.2f)", text[:50], route.backend, route.confidence)

        # Inject recalled procedural memory (Phase 2)
        recalled = proc_recall(text)
        if recalled:
            ctx["procedural_memory"] = recalled
        else:
            ctx["procedural_memory"] = ""

        result = self.loop.run(goal=text, context=ctx)
        status = result.get("status", "unverified")
        summary = result.get("summary", "")

        # Record honesty outcome
        self.honesty.record(text[:50], status, summary)

        # Compose final response
        if status == "done":
            return summary
        if status == "failed":
            return f"I couldn't complete that: {summary}"
        if status == "unverified":
            return f"I attempted that but can't confirm it succeeded: {summary}"
        if status == "ask":
            return f"I need more information: {summary}"
        if status == "started":
            return f"That's under way: {summary}"
        return summary or "I'm not sure how to help with that."

    def _format_tools(self) -> str:
        lines = []
        for decl in self.executor.get_all_declarations():
            name = decl.get("name", "unknown")
            desc = decl.get("description", "")
            lines.append(f"  {name}: {desc}")
        return "\n".join(lines) if lines else "  (no tools available)"

    def get_tools(self) -> List[dict]:
        """All tool declarations from all layers."""
        return self.executor.get_all_declarations()

    def register_tool(self, name: str, description: str, parameters: dict, handler) -> None:
        """Register a new built-in tool at runtime."""
        from .tools import Tool
        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
        )
        self.tool_registry.register(tool)
        # Rebuild planner declarations
        self.planner.tool_declarations = self.executor.get_all_declarations()

    def set_learned_rule(self, rule: str) -> None:
        """Add a learned behavioral rule."""
        self.planner.add_learned_rule(rule)

    def get_honesty_summary(self) -> str:
        return self.honesty.summary()
