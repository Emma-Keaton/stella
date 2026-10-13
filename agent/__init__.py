"""agent - Stella's agent runtime.

This package also holds pre-existing modules (planner, executor, task_queue,
error_handler) that main.py imports directly as `agent.<name>`. Those must keep
working exactly as before, so this __init__ deliberately does NOT import
anything eagerly: importing `agent.planner` must not drag in the LLM stack.
Exports are therefore resolved lazily via module __getattr__ (PEP 562).
"""

from __future__ import annotations

__all__ = [
    "Agent",
    "Backend",
    "LLM",
    "LLMResponse",
    "Registry",
    "RunResult",
    "SYSTEM_PREAMBLE",
    "Tool",
    "ToolResult",
    "build_default_registry",
    "current_plan",
    "default_backend",
    "progress_line",
    "run_goal",
]

_LAZY = {
    "Agent": "agent.loop",
    "RunResult": "agent.loop",
    "run_goal": "agent.loop",
    "Backend": "agent.llm",
    "LLM": "agent.llm",
    "LLMResponse": "agent.llm",
    "SYSTEM_PREAMBLE": "agent.llm",
    "default_backend": "agent.llm",
    "Registry": "agent.tools",
    "Tool": "agent.tools",
    "ToolResult": "agent.tools",
    "build_default_registry": "agent.tools",
    "current_plan": "agent.scratchpad",
    "progress_line": "agent.scratchpad",
}


def __getattr__(name: str):
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module 'agent' has no attribute {name!r}")
    from importlib import import_module
    return getattr(import_module(module), name)


def __dir__() -> list[str]:
    return sorted(set(list(globals()) + __all__))