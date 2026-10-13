"""agent/integration.py - bridge between Stella's UI/voice layer and the loop.

`main.py` already has its own function-calling path for the local brain. This
module does not replace it. It exposes the agentic loop as a single entry the
app can call when a request is genuinely open-ended ("find every config file
and summarise them") rather than a single well-formed tool call, which is the
case the existing one-shot path handles poorly.

Kept separate so main.py only needs one import and one method.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from agent.loop import Agent, RunResult
from agent.llm import default_backend
from agent.scratchpad import current_plan, reset
from agent.tools import build_default_registry


class StellaAgent:
    """One agent instance for the process, reused across goals.

    Reuse matters: the registry holds the workspace root, and rebuilding it
    per request would reset that (and re-import tools) every time.
    """

    def __init__(self, workspace: str | Path | None = None,
                 max_turns: int = 12) -> None:
        self.workspace = str(workspace) if workspace else None
        self.max_turns = max_turns
        self.registry = build_default_registry(self.workspace)
        self.backend = default_backend()
        self._lock = threading.Lock()

    def enabled(self) -> bool:
        """True when a model is actually reachable."""
        return self.backend.resolve() is not None

    def status_line(self) -> str:
        backend = self.backend.resolve()
        if backend is None:
            return "Agent: no model reachable"
        return f"Agent: {backend.name} ready"

    def run(self, goal: str,
            progress: Callable[[str], None] | None = None,
            max_turns: int | None = None) -> RunResult:
        """Execute one goal to completion. Thread-safe."""
        with self._lock:
            reset()
            agent = Agent(
                self.backend,
                self.registry,
                max_turns=max_turns or self.max_turns,
            )
            return agent.run(goal, progress=progress)

    def plan(self) -> list[dict]:
        return current_plan()["steps"]

    def set_workspace(self, workspace: str | Path | None) -> None:
        """Re-point filesystem tools at a new root."""
        self.workspace = str(workspace) if workspace else None
        self.registry = build_default_registry(self.workspace)

    def allow(self, tool_names: list[str]) -> None:
        """Restrict this session to a subset of tools (user preference)."""
        self.registry.allowed = set(tool_names)


_ACTIVE: StellaAgent | None = None


def get_agent(workspace: str | Path | None = None) -> StellaAgent:
    """Process-wide agent singleton."""
    global _ACTIVE
    if _ACTIVE is None:
        _ACTIVE = StellaAgent(workspace)
    elif workspace is not None and _ACTIVE.workspace != str(workspace):
        _ACTIVE.set_workspace(workspace)
    return _ACTIVE


def run_goal(goal: str, workspace: str | Path | None = None,
             progress: Callable[[str], None] | None = None) -> RunResult:
    """Module-level convenience wrapper."""
    return get_agent(workspace).run(goal, progress=progress)