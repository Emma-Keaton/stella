"""core/session.py - session continuity.

A session is one conversation's durable record: the goal, the tools used, the
turn budget, the verdicts, and enough context to resume after a restart.
Sessions are stored as JSONL under the user data dir so a repo wipe never
destroys a conversation.

Design:
* `Session` holds id, started_at, goal, turns, tool_calls, verdicts, budget.
* `SessionStore` appends one JSONL row per session event and can replay the
  most recent session for continuity.
* `resume()` rebuilds a session's state from its log so the agent can pick up
  where it left off.

Honesty: resumed sessions report exactly what was logged - no inferred
outcomes, no fabricated tool results.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.user_paths import get_user_data_dir


SESSIONS_DIR_NAME = "sessions"
SESSION_LOG_NAME = "sessions.jsonl"


@dataclass
class SessionEvent:
    """One row in a session's log."""
    ts: float
    kind: str  # "started" | "tool_call" | "verdict" | "budget" | "stopped"
    data: dict[str, Any]


@dataclass
class Session:
    """Reconstructable session state."""
    session_id: str
    started_at: float
    goal: str
    turns: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    verdicts: list[dict[str, Any]] = field(default_factory=list)
    budget_events: list[dict[str, Any]] = field(default_factory=list)
    stopped_because: str | None = None
    ok: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "goal": self.goal,
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "verdicts": self.verdicts,
            "budget_events": self.budget_events,
            "stopped_because": self.stopped_because,
            "ok": self.ok,
        }


class SessionStore:
    """Append-only JSONL session log. One file, all sessions, newest last."""

    def __init__(self, sessions_dir: Path | None = None):
        if sessions_dir is None:
            sessions_dir = Path(get_user_data_dir()) / SESSIONS_DIR_NAME
        self.dir = sessions_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / SESSION_LOG_NAME

    def _append(self, session_id: str, kind: str, data: dict[str, Any]) -> None:
        entry = {
            "ts": time.time(),
            "session_id": session_id,
            "kind": kind,
            "data": data,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def start_session(self, session_id: str, goal: str) -> None:
        self._append(session_id, "started", {"goal": goal})

    def record_tool_call(self, session_id: str, call: dict[str, Any]) -> None:
        self._append(session_id, "tool_call", call)

    def record_verdict(self, session_id: str, verdict: dict[str, Any]) -> None:
        self._append(session_id, "verdict", verdict)

    def record_budget(self, session_id: str, event: dict[str, Any]) -> None:
        self._append(session_id, "budget", event)

    def stop_session(self, session_id: str, stopped_because: str, ok: bool) -> None:
        self._append(session_id, "stopped", {
            "stopped_because": stopped_because, "ok": ok,
        })

    def _rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def sessions(self) -> list[str]:
        """All session ids in chronological order (first seen)."""
        seen: list[str] = []
        for row in self._rows():
            sid = row.get("session_id")
            if sid and sid not in seen:
                seen.append(sid)
        return seen

    def resume(self, session_id: str) -> Session | None:
        """Rebuild a session's state from its log. Returns None if unknown."""
        rows = self._rows()
        session_rows = [r for r in rows if r.get("session_id") == session_id]
        if not session_rows:
            return None

        session: Session | None = None
        for row in session_rows:
            kind = row.get("kind")
            data = row.get("data") or {}
            if kind == "started":
                session = Session(
                    session_id=session_id,
                    started_at=row.get("ts", time.time()),
                    goal=str(data.get("goal", "")),
                )
            elif kind == "tool_call" and session is not None:
                session.tool_calls.append(data)
                session.turns += 1
            elif kind == "verdict" and session is not None:
                session.verdicts.append(data)
            elif kind == "budget" and session is not None:
                session.budget_events.append(data)
            elif kind == "stopped" and session is not None:
                session.stopped_because = data.get("stopped_because")
                session.ok = bool(data.get("ok", False))
        return session

    def latest(self) -> Session | None:
        """Resume the most recent session, or None if there are none."""
        ids = self.sessions()
        if not ids:
            return None
        return self.resume(ids[-1])

    def summary(self, session_id: str) -> dict[str, Any] | None:
        s = self.resume(session_id)
        if s is None:
            return None
        return {
            "session_id": s.session_id,
            "goal": s.goal,
            "turns": s.turns,
            "tool_call_count": len(s.tool_calls),
            "verdict_count": len(s.verdicts),
            "budget_event_count": len(s.budget_events),
            "stopped_because": s.stopped_because,
            "ok": s.ok,
            "started_at": s.started_at,
        }


def new_session_id() -> str:
    return "sess_" + uuid.uuid4().hex[:12]


__all__ = [
    "Session", "SessionEvent", "SessionStore",
    "SESSIONS_DIR_NAME", "SESSION_LOG_NAME", "new_session_id",
]
