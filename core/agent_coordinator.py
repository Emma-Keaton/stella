"""
core/agent_coordinator.py - Agent Coordinator for parent/child agent lifecycle.

Modeled after strix's AgentCoordinator (strix/core/agents.py). Manages a graph of
Stella agents: root agent, child agents, sub-agents. Tracks agent state
(running/waiting/completed/stopped/crashed/failed/budget_paused), parent-child
relationships, mailbox messaging, budget pause/resume, and snapshot/restore.

Agent lifecycle:
  CREATED   - Agent registered, not yet started
  RUNNING   - Agent's event loop is active
  WAITING   - Agent is parked (waiting for message/input/budget)
  COMPLETED - Agent finished its task successfully
  STOPPED   - Agent was gracefully stopped
  CRASHED   - Agent's task raised an unhandled exception
  FAILED    - Agent failed verification or validation
  BUDGET_PAUSED - Agent paused due to budget/turn limit exhaustion

Terminal states: COMPLETED, STOPPED, CRASHED, FAILED.
Active states: RUNNING, WAITING, BUDGET_PAUSED.

Agent hierarchy:
  ROOT agent owns the session. CHILD agents are spawned by the root or by other
  child agents. Each agent has exactly one parent (except root, which has None).
  When an agent stops/crashes, its descendants are also stopped (cascade down).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from core.user_paths import get_user_data_dir


class AgentStatus(str):
    """Agent lifecycle status values."""
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    STOPPED = "stopped"
    CRASHED = "crashed"
    FAILED = "failed"
    BUDGET_PAUSED = "budget_paused"

    @classmethod
    def terminal_states(cls) -> set[str]:
        return {cls.COMPLETED, cls.STOPPED, cls.CRASHED, cls.FAILED}

    @classmethod
    def active_states(cls) -> set[str]:
        return {cls.RUNNING, cls.WAITING, cls.BUDGET_PAUSED}


@dataclass
class AgentInfo:
    """Immutable record of an agent's identity and configuration."""
    agent_id: str
    name: str
    parent_id: Optional[str]
    role: str = "general"          # root, worker, specialist, coordinator, voice, memory, etc.
    status: AgentStatus = AgentStatus.CREATED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    budget_paused: bool = False
    turn_count: int = 0
    max_turns: int = 12
    task: Optional[str] = None
    result: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class AgentStateStore:
    """In-memory agent state store with async persistence hooks."""

    def __init__(self):
        self._agents: dict[str, AgentInfo] = {}
        self._children: dict[str, set[str]] = {}  # parent_id -> set of child_ids
        self._root_id: Optional[str] = None
        self._mailboxes: dict[str, list[dict]] = {}  # agent_id -> list of messages

    def register(self, agent: AgentInfo) -> None:
        self._agents[agent.agent_id] = agent
        if agent.parent_id:
            self._children.setdefault(agent.parent_id, set()).add(agent.agent_id)
        if agent.parent_id is None:
            self._root_id = agent.agent_id
        self._mailboxes.setdefault(agent.agent_id, [])

    def get(self, agent_id: str) -> Optional[AgentInfo]:
        return self._agents.get(agent_id)

    def get_children(self, parent_id: str) -> list[str]:
        return list(self._children.get(parent_id, set()))

    def get_root(self) -> Optional[str]:
        return self._root_id

    def set_status(self, agent_id: str, status: AgentStatus) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = status
            if status in (AgentStatus.RUNNING,):
                agent.started_at = time.time()
            if status in AgentStatus.terminal_states():
                agent.completed_at = time.time()

    def set_error(self, agent_id: str, error: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.error = error
            agent.status = AgentStatus.FAILED
            agent.completed_at = time.time()

    def send_message(self, target_id: str, message: dict) -> bool:
        """Send a message to an agent's mailbox. Returns False if target missing."""
        if target_id not in self._agents:
            return False
        self._mailboxes.setdefault(target_id, []).append({
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "message": message,
        })
        return True

    def consume_messages(self, agent_id: str) -> list[dict]:
        """Drain and return all pending messages for an agent."""
        if agent_id not in self._mailboxes:
            return []
        messages = list(self._mailboxes[agent_id])
        self._mailboxes[agent_id] = []
        return messages

    def snapshot(self) -> dict:
        """Serialize full agent state to a JSON-serializable dict."""
        return {
            "root_id": self._root_id,
            "agents": {
                aid: {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "parent_id": a.parent_id,
                    "role": a.role,
                    "status": a.status,
                    "created_at": a.created_at,
                    "started_at": a.started_at,
                    "completed_at": a.completed_at,
                    "error": a.error,
                    "budget_paused": a.budget_paused,
                    "turn_count": a.turn_count,
                    "max_turns": a.max_turns,
                    "task": a.task,
                    "result": a.result,
                    "metadata": a.metadata,
                }
                for aid, a in self._agents.items()
            },
            "children": {pid: list(cids) for pid, cids in self._children.items()},
        }

    @classmethod
    def restore(cls, data: dict) -> "AgentStateStore":
        store = AgentStateStore()
        store._root_id = data.get("root_id")
        for aid, adata in data.get("agents", {}).items():
            agent = AgentInfo(
                agent_id=adata["agent_id"],
                name=adata["name"],
                parent_id=adata.get("parent_id"),
                role=adata.get("role", "general"),
                status=AgentStatus(adata.get("status", "created")),
                created_at=adata.get("created_at", time.time()),
                started_at=adata.get("started_at"),
                completed_at=adata.get("completed_at"),
                error=adata.get("error"),
                budget_paused=adata.get("budget_paused", False),
                turn_count=adata.get("turn_count", 0),
                max_turns=adata.get("max_turns", 12),
                task=adata.get("task"),
                result=adata.get("result"),
                metadata=adata.get("metadata", {}),
            )
            store._agents[aid] = agent
            if adata.get("parent_id"):
                store._children.setdefault(adata["parent_id"], set()).add(aid)
            store._mailboxes.setdefault(aid, [])
        return store


class AgentCoordinator:
    """
    AgentCoordinator - the central coordinator for all Stella agents.

    Manages the full lifecycle of agents: spawn, monitor, stop, resume,
    message passing, and hierarchy. Modeled after strix's AgentCoordinator
    (strix/core/agents.py).

    Usage:
        coord = AgentCoordinator()
        root = coord.spawn_root_agent("root-1", "Stella Root")
        child = coord.spawn_child_agent("child-1", "Worker-1", parent_id="root-1",
                                        task="Analyze this file")
        coord.send_message("child-1", {"type": "task", "payload": {...}})
        result = coord.get_agent("child-1")
    """

    def __init__(self, store: Optional[AgentStateStore] = None):
        self.store = store or AgentStateStore()
        self._tasks: dict[str, asyncio.Task] = {}  # agent_id -> asyncio.Task
        self._callbacks: dict[str, list[Callable[[AgentInfo], None]]] = {}  # agent_id -> callbacks
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ spawn

    def spawn_root_agent(self, agent_id: Optional[str] = None,
                         name: str = "Stella Root",
                         metadata: dict | None = None) -> str:
        """Create the root agent for a new session."""
        aid = agent_id or str(uuid.uuid4())
        agent = AgentInfo(
            agent_id=aid,
            name=name,
            parent_id=None,
            role="root",
            status=AgentStatus.CREATED,
            metadata=metadata or {},
        )
        self.store.register(agent)
        return aid

    def spawn_child_agent(self, agent_id: Optional[str] = None,
                          name: str = "Stella Child",
                          parent_id: Optional[str] = None,
                          role: str = "worker",
                          task: Optional[str] = None,
                          max_turns: int = 12,
                          metadata: dict | None = None) -> str:
        """Spawn a child agent under a parent. Returns the new agent_id."""
        aid = agent_id or str(uuid.uuid4())
        if parent_id is None:
            parent_id = self.store.get_root()
            if parent_id is None:
                raise ValueError("No root agent exists; spawn a root agent first")

        agent = AgentInfo(
            agent_id=aid,
            name=name,
            parent_id=parent_id,
            role=role,
            status=AgentStatus.CREATED,
            max_turns=max_turns,
            task=task,
            metadata=metadata or {},
        )
        self.store.register(agent)
        return aid

    # ------------------------------------------------------------------ lifecycle

    async def start_agent(self, agent_id: str,
                          callback: Optional[Callable[[AgentInfo], None]] = None) -> bool:
        """Start an agent's execution loop. Returns False if agent missing."""
        agent = self.store.get(agent_id)
        if agent is None:
            return False
        if agent.status == AgentStatus.RUNNING:
            return True

        self.store.set_status(agent_id, AgentStatus.RUNNING)

        # Wrap the user callback so we can capture completion
        async def _wrapped():
            try:
                if callback:
                    await callback(agent)
                self.store.set_status(agent_id, AgentStatus.COMPLETED)
            except Exception as exc:
                self.store.set_error(agent_id, str(exc))
            finally:
                # Cascade stop to children on terminal state
                await self._cascade_stop(agent_id)

        task = asyncio.create_task(_wrapped())
        self._tasks[agent_id] = task

        # Register callbacks
        cbs = []
        if callback:
            cbs.append(callback)
        self.store._callbacks[agent_id] = cbs  # type: ignore[attr-defined]

        return True

    async def stop_agent(self, agent_id: str, cascade: bool = True) -> bool:
        """Stop an agent. If cascade, stop all descendants first."""
        agent = self.store.get(agent_id)
        if agent is None:
            return False

        if cascade:
            await self._cascade_stop(agent_id)

        task = self._tasks.get(agent_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self._tasks.pop(agent_id, None)

        self.store.set_status(agent_id, AgentStatus.STOPPED)
        return True

    async def _cascade_stop(self, agent_id: str) -> None:
        """Stop all descendants of an agent (leaves first)."""
        children = self.store.get_children(agent_id)
        for child_id in list(children):
            await self._cascade_stop(child_id)
        # Stop the children themselves
        for child_id in list(children):
            task = self._tasks.get(child_id)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                self._tasks.pop(child_id, None)
            self.store.set_status(child_id, AgentStatus.STOPPED)

    async def pause_agent(self, agent_id: str) -> bool:
        """Pause an agent (budget pause)."""
        agent = self.store.get(agent_id)
        if agent is None or agent.status != AgentStatus.RUNNING:
            return False
        self.store.set_status(agent_id, AgentStatus.BUDGET_PAUSED)
        return True

    async def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent."""
        agent = self.store.get(agent_id)
        if agent is None or agent.status != AgentStatus.BUDGET_PAUSED:
            return False
        return await self.start_agent(agent_id)

    # ------------------------------------------------------------------ messaging

    def send_message(self, target_id: str, message: dict) -> bool:
        """Send a message to an agent's mailbox."""
        return self.store.send_message(target_id, message)

    def consume_messages(self, agent_id: str) -> list[dict]:
        """Drain and return all pending messages for an agent."""
        return self.store.consume_messages(agent_id)

    # ------------------------------------------------------------------ queries

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        return self.store.get(agent_id)

    def get_children(self, parent_id: str) -> list[AgentInfo]:
        return [self.store.get(cid) for cid in self.store.get_children(parent_id)
                if self.store.get(cid) is not None]

    def get_root(self) -> Optional[AgentInfo]:
        root_id = self.store.get_root()
        if root_id is None:
            return None
        return self.store.get(root_id)

    def list_agents(self) -> list[AgentInfo]:
        return list(self.store._agents.values())

    def snapshot(self) -> dict:
        return self.store.snapshot()

    @classmethod
    def restore(cls, data: dict) -> "AgentCoordinator":
        store = AgentStateStore.restore(data)
        return cls(store)


# ---------------------------------------------------------------------------
# Default singleton coordinator
# ---------------------------------------------------------------------------

_coordinator: Optional[AgentCoordinator] = None


def get_coordinator() -> AgentCoordinator:
    """Get the global agent coordinator singleton."""
    global _coordinator
    if _coordinator is None:
        _coordinator = AgentCoordinator()
    return _coordinator


def reset_coordinator() -> AgentCoordinator:
    """Reset the global coordinator (useful for testing)."""
    global _coordinator
    _coordinator = AgentCoordinator()
    return _coordinator
