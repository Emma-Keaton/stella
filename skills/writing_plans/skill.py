"""
Feature: writing_plans
Description: Writing plans - creates step-by-step implementation plans. Pure-Python, no external dependencies.
"""

from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "writing_plans",
    "aliases": ["writing_plans", "writing plan", "create plan",
                "implementation plan", "task list", "step by step plan",
                "project plan", "roadmap"],
    "description": (
        "Writing plans: creates step-by-step implementation plans for features, "
        "tasks, or projects. Breaks a goal into ordered steps with statuses "
        "(pending/doing/done/failed), notes on why the plan changed, and "
        "dependencies. Pure-Python, no external dependencies, runs on any "
        "surface."
    ),
    "triggers": [
        "writing plan", "writing_plans", "create plan", "implementation plan",
        "task list", "step by step plan", "project plan", "roadmap",
        "plan this", "break down", "steps to implement",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: create | list | update | sources. Defaults to sources.",
            },
            "goal": {
                "type": "STRING",
                "description": "The goal or feature to plan.",
            },
            "steps": {
                "type": "STRING",
                "description": "JSON array of step descriptions (create/update).",
            },
            "note": {
                "type": "STRING",
                "description": "Why the plan changed, if it did.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum plans to return. Defaults to 10.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "development",
    "surface": "both",
    "requires": [],
    "optional_dependencies": [],
    "notes": "Pure-Python skill. Plans are held in memory for the session; nothing is written to disk unless paired with write_note or document_ops.",
}

_PLANS: list[dict[str, Any]] = []


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _as_int(value, default: int = 10, ceiling: int = 100) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


def _parse_steps(steps_raw: Any) -> list[str]:
    if steps_raw is None:
        return []
    if isinstance(steps_raw, list):
        return [str(s) for s in steps_raw]
    if isinstance(steps_raw, str):
        import json
        try:
            parsed = json.loads(steps_raw)
            if isinstance(parsed, list):
                return [str(s) for s in parsed]
        except json.JSONDecodeError:
            pass
        return [s.strip() for s in steps_raw.split("\n") if s.strip()]
    return [str(steps_raw)]


def _op_create(kwargs: dict) -> dict:
    operation = "create"
    goal = (kwargs.get("goal") or "").strip()
    if not goal:
        return _op(operation, False, None, "Provide a goal (goal=...).")
    steps_raw = kwargs.get("steps")
    steps = _parse_steps(steps_raw) if steps_raw else []
    note = kwargs.get("note") or ""
    plan = {
        "id": len(_PLANS) + 1,
        "goal": goal,
        "steps": [{"step": s, "status": "pending"} for s in steps],
        "note": note,
        "created": True,
    }
    _PLANS.append(plan)
    return _op(operation, True, {
        "plan": plan,
        "note": f"Plan created for '{goal}' with {len(steps)} step(s).",
    })


def _op_list(kwargs: dict) -> dict:
    operation = "list"
    limit = _as_int(kwargs.get("limit"), 10)
    return _op(operation, True, {
        "plans": _PLANS[:limit],
        "count": min(len(_PLANS), limit),
        "total": len(_PLANS),
        "note": "Plans are held in memory for this session.",
    })


def _op_update(kwargs: dict) -> dict:
    operation = "update"
    goal = (kwargs.get("goal") or "").strip()
    if not goal:
        return _op(operation, False, None, "Provide a goal to update (goal=...).")
    steps_raw = kwargs.get("steps")
    steps = _parse_steps(steps_raw) if steps_raw else []
    note = kwargs.get("note") or ""
    for plan in _PLANS:
        if plan["goal"] == goal:
            plan["steps"] = [{"step": s, "status": "pending"} for s in steps]
            plan["note"] = note
            return _op(operation, True, {
                "plan": plan,
                "note": f"Plan updated for '{goal}'.",
            })
    return _op(operation, False, None, f"No plan found for goal '{goal}'.")


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "writing_plans (pure-Python, adapted from shared-skills/writing-plans)",
        "dependencies": [],
        "operations": ["create", "list", "update"],
        "note": "No external dependencies; runs on desktop and Android.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "create": _op_create,
    "list": _op_list,
    "update": _op_update,
}

_OPERATION_TITLES = {
    "sources": "Writing Plans Sources",
    "create": "Create Plan",
    "list": "List Plans",
    "update": "Update Plan",
}

_ALIASES = {
    "create_plan": "create", "list_plans": "list", "update_plan": "update",
    "sources_list": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return value.get("note", "Writing plans skill available.")
    if operation == "create":
        return f"Plan for '{value.get('plan', {}).get('goal')}' with {len(value.get('plan', {}).get('steps', []))} step(s)."
    if operation == "list":
        return f"{value.get('count')} plan(s) listed ({value.get('total')} total)."
    if operation == "update":
        return value.get("note", "Plan updated.")
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one writing-plans operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Writing Plans",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Writing Plans",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Writing Plans",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Writing plans error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Writing Plans"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
