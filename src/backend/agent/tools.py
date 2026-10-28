"""
src/backend/agent/tools.py — Tool system for the agent runtime.

Tool dataclass, Registry with permission/policy/audit, built-in tools.
Follows Mark-LVI's agent/tools.py pattern.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("stella.agent.tools")


@dataclass
class Tool:
    """A single callable tool with metadata for the agent."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema shape
    handler: Callable
    behavior: str = "BLOCKING"  # BLOCKING | NON_BLOCKING
    scheduling: Optional[str] = None  # WHEN_IDLE | SILENT | INTERRUPT
    tier: str = "core"  # core | extra (for tool budgeting)
    brief: Optional[str] = None  # short description for tight budgets
    permissions: List[str] = field(default_factory=list)

    def to_declaration(self) -> dict:
        """Gemini-compatible function declaration (meta keys stripped)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class Registry:
    """Tool registry with permission/policy/audit tracking."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._order: List[str] = []

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning("Tool %r already registered; skipping", tool.name)
            return
        self._tools[tool.name] = tool
        self._order.append(tool.name)
        logger.info("Registered tool: %r", tool.name)

    def names(self) -> List[str]:
        return list(self._order)

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_declarations(self) -> List[dict]:
        """Return all tool declarations for the LLM."""
        return [self._tools[n].to_declaration() for n in self._order]

    def get_enabled_declarations(self, enabled: set) -> List[dict]:
        """Return declarations only for enabled tool names."""
        return [self._tools[n].to_declaration() for n in self._order if n in enabled]

    def list_for_ui(self) -> List[dict]:
        """Full listing for UI tool management."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "behavior": t.behavior,
                "scheduling": t.scheduling,
                "tier": t.tier,
                "brief": t.brief,
                "permissions": t.permissions,
            }
            for t in (self._tools[n] for n in self._order)
        ]


def invoke(tool: Tool, parameters: dict, ctx: dict) -> str:
    """Invoke a tool handler with introspected context kwargs (Mark-LVI pattern)."""
    sig = inspect.signature(tool.handler)
    kwargs: Dict[str, Any] = {"parameters": parameters}
    for param_name in sig.parameters:
        if param_name == "parameters":
            continue
        if param_name in ctx:
            kwargs[param_name] = ctx[param_name]
    try:
        result = tool.handler(**kwargs)
    except TypeError as e:
        logger.warning("Tool %s failed with full ctx, retrying params-only: %s", tool.name, e)
        result = tool.handler(parameters=parameters)
    if result is None:
        return ""
    return str(result)


# ── Built-in tools ──


def _read_file(parameters: dict) -> str:
    from pathlib import Path
    path = Path(parameters.get("path", ""))
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading {path}: {e}"


def _write_file(parameters: dict) -> str:
    from pathlib import Path
    path = Path(parameters.get("path", ""))
    content = parameters.get("content", "")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


def _list_dir(parameters: dict) -> str:
    from pathlib import Path
    path = Path(parameters.get("path", "."))
    try:
        entries = [p.name for p in path.iterdir()]
        return "\n".join(sorted(entries)) or "(empty)"
    except Exception as e:
        return f"Error listing {path}: {e}"


def _search_text(parameters: dict) -> str:
    from pathlib import Path
    path = Path(parameters.get("path", "."))
    pattern = parameters.get("pattern", "")
    try:
        matches = []
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    if pattern in text:
                        matches.append(str(p))
                except Exception:
                    pass
        return "\n".join(matches) or "No matches found"
    except Exception as e:
        return f"Error searching: {e}"


def _current_time(parameters: dict) -> str:
    from datetime import datetime
    return datetime.now().isoformat()


def _system_info(parameters: dict) -> str:
    import platform
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def _calculate(parameters: dict) -> str:
    expression = parameters.get("expression", "")
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"


BUILTIN_TOOLS = [
    Tool(
        name="read_file",
        description="Read the contents of a file at the given path.",
        parameters={
            "type": "OBJECT",
            "properties": {"path": {"type": "STRING", "description": "File path to read"}},
            "required": ["path"],
        },
        handler=_read_file,
    ),
    Tool(
        name="write_file",
        description="Write content to a file at the given path.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "File path to write"},
                "content": {"type": "STRING", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
        handler=_write_file,
    ),
    Tool(
        name="list_dir",
        description="List entries in a directory.",
        parameters={
            "type": "OBJECT",
            "properties": {"path": {"type": "STRING", "description": "Directory path"}},
            "required": ["path"],
        },
        handler=_list_dir,
    ),
    Tool(
        name="search_text",
        description="Search for text pattern in files under a directory.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "Directory path"},
                "pattern": {"type": "STRING", "description": "Text pattern to search"},
            },
            "required": ["path", "pattern"],
        },
        handler=_search_text,
    ),
    Tool(
        name="current_time",
        description="Get the current date and time.",
        parameters={"type": "OBJECT", "properties": {}, "required": []},
        handler=_current_time,
    ),
    Tool(
        name="system_info",
        description="Get basic system information.",
        parameters={"type": "OBJECT", "properties": {}, "required": []},
        handler=_system_info,
    ),
    Tool(
        name="calculate",
        description="Evaluate a mathematical expression.",
        parameters={
            "type": "OBJECT",
            "properties": {"expression": {"type": "STRING", "description": "Math expression"}},
            "required": ["expression"],
        },
        handler=_calculate,
    ),
]
