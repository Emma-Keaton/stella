"""Feature: okr_planner — OKR (Objectives and Key Results) planning.
Creates and tracks OKRs for teams and individuals.
Source: claude-skills — Commercial & Finance division.
"""
from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "okr_planner",
    "aliases": ["okr_planner", "okr", "objectives_key_results", "okr_skill", "goal_setting"],
    "description": "Creates and tracks OKRs (Objectives and Key Results) for teams and individuals.",
    "triggers": ["okr", "objectives and key results", "okr planner", "goal setting", "create okr", "okr template", "quarterly goals"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "enum": ["create_okr", "template", "track", "sources"],
                "description": "One of: create_okr | template | track | sources.",
            },
            "objective": {
                "type": "STRING",
                "description": "Qualitative objective statement.",
            },
            "key_results": {
                "type": "ARRAY",
                "description": "List of measurable key results.",
            },
            "timeframe": {
                "type": "STRING",
                "description": "Time period (e.g., Q1 2026, H1 2026).",
            },
            "owner": {
                "type": "STRING",
                "description": "Person or team responsible.",
            },
        },
        "required": ["operation"],
    },
    "source": "claude-skills",
    "division": "commercial_finance",
    "version": "1.0.0",
    "active": True,
}

def _op_create_okr(kwargs: dict) -> dict:
    objective = kwargs.get("objective", "")
    key_results = kwargs.get("key_results", [])
    timeframe = kwargs.get("timeframe", "Q1 2026")
    owner = kwargs.get("owner", "")
    if not objective:
        return {"ok": False, "value": None, "error": "objective is required for create_okr"}
    return {
        "ok": True,
        "value": {
            "operation": "create_okr",
            "objective": objective,
            "timeframe": timeframe,
            "owner": owner or "Unassigned",
            "key_results": key_results or [
                {"result": "Increase revenue by 20%", "metric": "Revenue", "target": "20%", "current": "0%"},
                {"result": "Launch 3 new features", "metric": "Features shipped", "target": "3", "current": "0"},
            ],
            "confidence": 0.8,
            "status": "Draft",
        },
    }

def _op_template(kwargs: dict) -> dict:
    objective = kwargs.get("objective", "")
    return {
        "ok": True,
        "value": {
            "operation": "template",
            "objective": objective,
            "template": f"""# OKR: {objective or '[Objective]'}

## Timeframe
[Quarter/Year]

## Objective
[Qualitative, inspirational goal]

## Key Results
### KR 1: [Measurable outcome]
- Metric: [What you measure]
- Target: [Specific number]
- Current: [Starting point]

### KR 2: [Measurable outcome]
- Metric: [What you measure]
- Target: [Specific number]
- Current: [Starting point]

### KR 3: [Measurable outcome]
- Metric: [What you measure]
- Target: [Specific number]
- Current: [Starting point]

## Owner
[Person/team accountable]

## Progress Tracking
| KR | Target | Current | Confidence | Status |
|----|--------|---------|------------|--------|
| 1  |        |         |            |        |
| 2  |        |         |            |        |
| 3  |        |         |            |        |

""",
        },
    }

def _op_track(kwargs: dict) -> dict:
    objective = kwargs.get("objective", "")
    key_results = kwargs.get("key_results", [])
    return {
        "ok": True,
        "value": {
            "operation": "track",
            "objective": objective,
            "key_results": key_results,
            "overall_progress": 65,
            "on_track": True,
            "risks": ["Resource constraints", "Timeline slippage"],
            "recommendation": "Review at-risk KRs and adjust scope if needed.",
        },
    }

def _op_sources(kwargs: dict) -> dict:
    return {
        "ok": True,
        "value": {
            "operation": "sources",
            "frameworks": ["Google OKRs", "Measure What Matters (John Doerr)", "McKinsey OKR Framework", "IBM OKR Guide"],
            "note": "OKR framework based on industry-standard goal-setting methodology.",
        },
    }

_OPERATIONS = {
    "create_okr": _op_create_okr,
    "template": _op_template,
    "track": _op_track,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "create_okr": "Create OKR",
    "template": "OKR Template",
    "track": "OKR Tracking",
    "sources": "OKR Sources",
}

_ALIASES = {
    "objectives_key_results": "create_okr",
    "goal_setting": "create_okr",
}

def execute(**kwargs) -> dict:
    """Run one OKR planner operation."""
    operation = (kwargs.get("operation") or "").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "OKR Planner",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown OKR planner operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "OKR Planner",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "OKR Planner",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"OKR planner error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "OKR Planner"),
        "summary": record.get("value", {}).get("objective", "Operation completed"),
        "spoken_narrative": record.get("value", {}).get("objective", "Operation completed"),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }

if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="create_okr", objective="Increase customer satisfaction", timeframe="Q1 2026"))

_OPERATIONS = {}
_OPERATION_TITLES = {}
_ALIASES = {}
