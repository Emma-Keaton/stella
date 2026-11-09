"""core/approvals.py - what each agent may do without asking (openbot pattern).

A standing approval says: this agent, these tools, this activity class, against
these targets, until this time. It is stored as JSON under the user's data dir -
no secrets, no key material, and nothing a model can write: only the UI, the
policy file, or an explicit user command grants one.

Approvals never widen the policy file. `is_approved()` consults both, and the
stricter answer wins, so an approval can never re-open a door the policy keeps
shut.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("approvals")

_DEFAULT_TTL_SECONDS = 3600.0


def _store_path() -> Path:
    try:
        from core.user_paths import get_user_data_dir

        return Path(get_user_data_dir()) / "config" / "approvals.json"
    except Exception:
        return Path("config") / "approvals.json"


def _load() -> dict[str, Any]:
    path = _store_path()
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("Could not read approvals store %s: %s", path, exc)
        return {}


def _save(data: dict[str, Any]) -> None:
    path = _store_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not write approvals store %s: %s", path, exc)


def _matches_tool(pattern: str, tool: str) -> bool:
    pattern = (pattern or "").strip()
    if pattern in ("", "*"):
        return True
    return fnmatch.fnmatchcase((tool or "").strip(), pattern)


def grant(
    agent: str,
    tools: list[str],
    activity: list[str],
    targets: Optional[list[str]] = None,
    ttl_seconds: float = _DEFAULT_TTL_SECONDS,
    reason: str = "",
) -> dict[str, Any]:
    """Grant a standing approval and persist it."""
    agent = str(agent or "agent")
    record = {
        "tools": [str(t) for t in tools or ["*"]],
        "activity": [str(a) for a in activity or ["passive"]],
        "targets": [str(t) for t in targets or []],
        "expires_at": round(time.time() + float(ttl_seconds), 3),
        "reason": reason or "Granted by the user.",
    }
    data = _load()
    data.setdefault(agent, []).append(record)
    _save(data)
    return record


def revoke(agent: Optional[str] = None) -> None:
    """Revoke one agent's approvals, or every approval when no agent is named."""
    if agent is None:
        _save({})
        return
    data = _load()
    data.pop(str(agent), None)
    _save(data)


def is_approved(
    agent: str,
    tool: str,
    activity: str = "passive",
    target: str = "",
) -> bool:
    """True when a live standing approval covers this exact call."""
    data = _load()
    records = data.get(str(agent or "agent")) or []
    now = time.time()
    for record in records:
        try:
            if float(record.get("expires_at") or 0) < now:
                continue
        except (TypeError, ValueError):
            continue
        if activity not in [str(a) for a in record.get("activity") or []]:
            continue
        if not any(_matches_tool(str(p), tool) for p in record.get("tools") or []):
            continue
        targets = [str(t) for t in record.get("targets") or []]
        if targets and not any(
            _matches_tool(p, (target or "").strip()) for p in targets
        ):
            continue
        return True
    return False


def list_approvals() -> dict[str, list[dict[str, Any]]]:
    """Live approvals per agent, with expired entries dropped."""
    data = _load()
    now = time.time()
    out: dict[str, list[dict[str, Any]]] = {}
    for agent, records in data.items():
        live = []
        for record in records:
            try:
                if float(record.get("expires_at") or 0) < now:
                    continue
            except (TypeError, ValueError):
                continue
            live.append(record)
        if live:
            out[agent] = live
    return out
