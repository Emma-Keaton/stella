"""
src/backend/agent/executor.py — AgentExecutor.

Executes planned steps via _call_tool dispatcher, with retries, error recovery,
and HUD deliverables. Follows Mark-LVI's agent/executor.py pattern.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from ..core.action_loader import ActionRegistry
from ..core.plugin_loader import PluginRegistry
from .procedural import record as proc_record
from .tools import Registry, Tool, invoke
from .skill_loader import SkillLoader

logger = logging.getLogger("stella.agent.executor")


class AgentExecutor:
    """
    Executes agent actions. Dispatches to:
      1. Built-in tools (agent/tools.py Registry)
      2. Actions (actions/ TOOL dicts via ActionRegistry)
      3. Plugins (plugins/ PLUGIN dicts via PluginRegistry)
      4. Skills (skills/ SKILL.md + skill.py via SkillLoader)
    """

    def __init__(
        self,
        tool_registry: Registry,
        action_registry: ActionRegistry,
        plugin_registry: PluginRegistry,
        skill_loader: Optional[SkillLoader] = None,
        get_plugin_enabled: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.action_registry = action_registry
        self.plugin_registry = plugin_registry
        self.skill_loader = skill_loader
        self.get_plugin_enabled = get_plugin_enabled or (lambda name: True)
        self._retry_limit = 2

    def _is_success(self, result: str) -> bool:
        """Heuristic: a result is successful unless it clearly signals failure."""
        low = result.lower()
        return not (
            low.startswith("error")
            or low.startswith("unknown action")
            or "failed after retries" in low
            or "not found" in low
            or "no such" in low
        )

    def execute(self, action_name: str, parameters: dict, ctx: dict) -> str:
        """
        Execute an action by name. Dispatches to the appropriate layer.

        Resolution order: built-in tools → actions → plugins → skills.
        """
        start = time.time()
        # 1. Built-in tools
        tool = self.tool_registry.get(action_name)
        if tool:
            result = self._execute_with_retry(tool, parameters, ctx)
            elapsed = time.time() - start
            proc_record(ctx.get("goal", ""), [action_name], self._is_success(result), elapsed)
            return result

        # 2. Actions (discovered from actions/)
        if self.action_registry.has(action_name):
            result = self.action_registry.run(action_name, parameters, ctx)
            elapsed = time.time() - start
            proc_record(ctx.get("goal", ""), [action_name], self._is_success(result), elapsed)
            return result

        # 3. Plugins (discovered from plugins/)
        if self.plugin_registry.has(action_name):
            result = self.plugin_registry.run(action_name, parameters, ctx, self.get_plugin_enabled)
            elapsed = time.time() - start
            proc_record(ctx.get("goal", ""), [action_name], self._is_success(result), elapsed)
            return result

        # 4. Skills (packaged from skills/)
        if self.skill_loader and self.skill_loader._skills.get(action_name):
            result = self.skill_loader.execute(action_name, parameters)
            elapsed = time.time() - start
            proc_record(ctx.get("goal", ""), [action_name], self._is_success(result), elapsed)
            return result

        return f"Unknown action: {action_name}"

    def _execute_with_retry(self, tool: Tool, parameters: dict, ctx: dict) -> str:
        last_error = ""
        for attempt in range(self._retry_limit + 1):
            try:
                return invoke(tool, parameters, ctx)
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Tool %s attempt %d/%d failed: %s",
                    tool.name, attempt + 1, self._retry_limit + 1, e,
                )
        return f"Tool {tool.name} failed after retries: {last_error}"

    def get_all_declarations(self) -> List[dict]:
        """Get all tool declarations from all layers for the LLM."""
        declarations = []
        declarations.extend(self.tool_registry.get_declarations())
        declarations.extend(self.action_registry.get_tool_declarations())
        declarations.extend(self.plugin_registry.get_tool_declarations(self.get_plugin_enabled))
        if self.skill_loader:
            declarations.extend(self.skill_loader.load_all())
        return declarations

    def list_all_tools(self) -> List[dict]:
        """Full listing for UI tool management."""
        result = []
        result.extend(self.tool_registry.list_for_ui())
        for name in self.action_registry.names():
            tool = self.action_registry.get_tool(name)
            if tool:
                result.append({
                    "name": tool.get("name", name),
                    "description": tool.get("description", ""),
                    "behavior": tool.get("behavior", "BLOCKING"),
                    "scheduling": tool.get("scheduling"),
                    "tier": tool.get("tier", "core"),
                    "brief": tool.get("brief"),
                    "permissions": [],
                    "layer": "action",
                })
        for name in self.plugin_registry.names():
            plugin = self.plugin_registry._plugins[name]  # access internal for UI
            result.append({
                "name": plugin.get("name", name),
                "description": plugin.get("description", ""),
                "behavior": plugin.get("behavior", "BLOCKING"),
                "scheduling": plugin.get("scheduling"),
                "tier": plugin.get("tier", "extra"),
                "brief": plugin.get("brief"),
                "permissions": [],
                "layer": "plugin",
            })
        return result
