"""
src/backend/integrations/agent_events.py — Stella-native agent event system (Huginn-inspired).

Self-contained agent-to-agent event graph. Agents emit events that are routed
to subscribed agents through a directed graph. No connection to Huginn or any
external service. Governed by StarNet:
  * BudgetConsentManager — caps event emissions.
  * SkillsCatalog — gates agent event skill availability.
  * CronScheduler — optional scheduled event processing ticks.
  * CrewManager — crew agents can act as event sources/subscribers.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Optional

from core.user_paths import get_user_data_dir
from src.backend.starnet.budget_consent import BudgetConsentManager
from src.backend.starnet.skills_catalog import SkillsCatalog


@dataclass
class AgentEvent:
    event_id: str
    source_agent: str
    event_type: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    processed: bool = False
    routed_to: list[str] = field(default_factory=list)


@dataclass
class AgentRoute:
    route_id: str
    source_agent: str
    event_type: str
    target_agent: str
    enabled: bool = True
    created_at: float = field(default_factory=time.time)


class AgentEventManager:
    """Local agent event store with a routing graph. All data persisted as JSON."""

    def __init__(
        self,
        budget: Optional[BudgetConsentManager] = None,
        skills: Optional[SkillsCatalog] = None,
    ) -> None:
        self.budget = budget
        self.skills = skills
        self._handlers: dict[str, Callable[[AgentEvent], None]] = {}
        data_dir = get_user_data_dir()
        self._store_dir = data_dir / "integrations" / "agent_events"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self._store_dir / "events.json"
        self._routes_path = self._store_dir / "routes.json"
        self._events: dict[str, AgentEvent] = {}
        self._routes: dict[str, AgentRoute] = {}
        self._load()

    def _load(self) -> None:
        self._events = self._load_typed(self._events_path, AgentEvent)
        self._routes = self._load_typed(self._routes_path, AgentRoute)

    def _load_typed(self, path: Path, cls: type) -> dict[str, Any]:
        try:
            if not path.exists():
                return {}
            raw = json.loads(path.read_text(encoding="utf-8"))
            out: dict[str, Any] = {}
            for key, value in raw.items():
                if isinstance(value, dict):
                    out[key] = cls(**value)
            return out
        except Exception:
            return {}

    def _save(self, path: Path, data: dict[str, Any]) -> None:
        serializable = {k: asdict(v) for k, v in data.items()}
        path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")

    def _persist(self) -> None:
        self._save(self._events_path, self._events)
        self._save(self._routes_path, self._routes)

    def _check_budget(self) -> bool:
        if self.budget is not None:
            return self.budget.check_budget(0.01)
        return True

    def register_handler(self, agent_id: str, handler: Callable[[AgentEvent], None]) -> None:
        if self.skills is not None and not self.skills.skill_available("agent_events"):
            raise PermissionError("Agent events skill is not available or is revoked.")
        self._handlers[agent_id] = handler

    def add_route(
        self,
        source_agent: str,
        event_type: str,
        target_agent: str,
    ) -> AgentRoute:
        if self.skills is not None and not self.skills.skill_available("agent_events"):
            raise PermissionError("Agent events skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for event route writes.")
        route_id = uuid.uuid4().hex[:12]
        route = AgentRoute(
            route_id=route_id,
            source_agent=source_agent,
            event_type=event_type,
            target_agent=target_agent,
        )
        self._routes[route_id] = route
        self._persist()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return route

    def remove_route(self, route_id: str) -> bool:
        if route_id in self._routes:
            del self._routes[route_id]
            self._persist()
            if self.budget is not None:
                self.budget.add_spend(0.01)
            return True
        return False

    def list_routes(self) -> list[AgentRoute]:
        return list(self._routes.values())

    def emit(
        self,
        source_agent: str,
        event_type: str,
        payload: Optional[dict[str, Any]] = None,
    ) -> AgentEvent:
        if self.skills is not None and not self.skills.skill_available("agent_events"):
            raise PermissionError("Agent events skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for event emissions.")
        event_id = uuid.uuid4().hex[:12]
        event = AgentEvent(
            event_id=event_id,
            source_agent=source_agent,
            event_type=event_type,
            payload=payload or {},
        )
        self._events[event_id] = event
        self._route_event(event)
        self._persist()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return event

    def _route_event(self, event: AgentEvent) -> None:
        matching_routes = [
            r for r in self._routes.values()
            if r.enabled and r.source_agent == event.source_agent and r.event_type == event.event_type
        ]
        for route in matching_routes:
            event.routed_to.append(route.target_agent)
            handler = self._handlers.get(route.target_agent)
            if handler is not None:
                try:
                    handler(event)
                except Exception:
                    pass
        event.processed = True

    def get_event(self, event_id: str) -> Optional[AgentEvent]:
        return self._events.get(event_id)

    def list_events(self, source_agent: Optional[str] = None, event_type: Optional[str] = None) -> list[AgentEvent]:
        events = list(self._events.values())
        if source_agent:
            events = [e for e in events if e.source_agent == source_agent]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return sorted(events, key=lambda e: e.timestamp, reverse=True)

    def summary(self) -> dict[str, Any]:
        return {
            "events": len(self._events),
            "routes": len(self._routes),
            "handlers": len(self._handlers),
            "processed_events": sum(1 for e in self._events.values() if e.processed),
            "unprocessed_events": sum(1 for e in self._events.values() if not e.processed),
        }