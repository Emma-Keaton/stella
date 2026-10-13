"""agent/scratchpad.py - the working plan for the current task.

Strong agent harnesses keep an explicit, inspectable plan rather than letting
it dissolve into the transcript. That buys three things: the model can revise
its own plan mid-task, the user can see what is being attempted, and a crash
leaves a record of what was in flight.

Kept in-process plus a JSON mirror on disk, so a UI can render progress
without replaying the whole conversation.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

_PLAN: dict[str, Any] = {"steps": [], "note": "", "updated": 0.0}


def _mirror() -> Path:
    base = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
    d = Path(base) / "StellaAI" / "memory"
    d.mkdir(parents=True, exist_ok=True)
    return d / "plan.json"


def current_plan() -> dict:
    """The live plan (a copy - callers must not mutate internal state)."""
    return json.loads(json.dumps(_PLAN))


def write_plan(steps: list, note: str = "") -> "ToolResult":  # type: ignore[name-defined]
    """Replace the plan. Accepts the shapes models actually emit.

    Models return either [{"step": "...", "status": "..."}] or plain strings,
    sometimes wrapped one level deeper than the schema suggests. Normalising
    here keeps the failure in one small function instead of the loop.
    """
    from agent.tools import ToolResult

    normalised: list[dict] = []
    for raw in steps or []:
        if isinstance(raw, str):
            normalised.append({"step": raw, "status": "pending"})
            continue
        if isinstance(raw, dict):
            text = raw.get("step") or raw.get("task") or raw.get("text") or ""
            if not text:
                continue
            status = str(raw.get("status", "pending")).lower()
            if status not in ("pending", "doing", "done", "failed"):
                status = "pending"
            normalised.append({"step": str(text), "status": status})
    if not normalised:
        return ToolResult(ok=False, error="no usable steps in plan")

    _PLAN["steps"] = normalised
    _PLAN["note"] = note
    _PLAN["updated"] = time.time()
    try:
        _mirror().write_text(json.dumps(_PLAN, indent=2), encoding="utf-8")
    except OSError:
        pass  # the mirror is best-effort; the in-memory plan is authoritative

    done = sum(1 for s in normalised if s["status"] == "done")
    return ToolResult(
        ok=True,
        output=f"plan updated ({done}/{len(normalised)} done)",
        data={"steps": len(normalised), "done": done},
    )


def progress_line() -> str:
    """One-line summary for prompts: '2/5 done - current: <step>'."""
    steps = _PLAN.get("steps") or []
    if not steps:
        return "no plan yet"
    done = sum(1 for s in steps if s.get("status") == "done")
    active = next((s["step"] for s in steps if s.get("status") == "doing"), None)
    if active is None:
        active = next((s["step"] for s in steps if s.get("status") == "pending"), "")
    return f"{done}/{len(steps)} done - current: {active}"


def reset() -> None:
    _PLAN["steps"] = []
    _PLAN["note"] = ""
    _PLAN["updated"] = 0.0