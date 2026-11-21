"""Feature: product_manager — Product management: PRDs, roadmaps, OKRs, user stories.
Source: agency-agents — Product division.
"""
from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "product_manager",
    "aliases": ["product manager", "pm", "prd", "roadmap", "user stories", "rice scoring"],
    "description": "Product management skill for creating PRDs, roadmaps, user stories, and RICE scoring for feature prioritization.",
    "triggers": ["product manager", "prd", "product requirements", "roadmap", "user stories", "rice scoring", "feature prioritization"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: create_prd | create_roadmap | user_stories | rice_score | success_metrics.",
            },
            "title": {
                "type": "STRING",
                "description": "Product or feature name.",
            },
            "problem": {
                "type": "STRING",
                "description": "Problem statement the product solves.",
            },
            "goals": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Goals and objectives.",
            },
            "audience": {
                "type": "STRING",
                "description": "Target users or personas.",
            },
            "reach": {
                "type": "NUMBER",
                "description": "RICE: number of people reached.",
            },
            "impact": {
                "type": "NUMBER",
                "description": "RICE: impact score (1-3).",
            },
            "confidence": {
                "type": "NUMBER",
                "description": "RICE: confidence score (0-100%).",
            },
            "effort": {
                "type": "NUMBER",
                "description": "RICE: effort in person-months.",
            },
        },
        "required": ["operation"],
    },
    "source": "agency-agents",
    "division": "product",
    "version": "1.0.0",
    "active": True,
}

_OPERATIONS = {}
_OPERATION_TITLES = {}
_ALIASES = {}

def _op_create_prd(kwargs: dict) -> dict:
    title = kwargs.get("title", "")
    problem = kwargs.get("problem", "")
    goals = kwargs.get("goals", [])
    audience = kwargs.get("audience", "")

    if not title:
        return {"ok": False, "value": None, "error": "title is required for create_prd"}

    prd = {
        "title": title,
        "problem": problem or "To be defined",
        "goals": goals or [],
        "audience": audience or "TBD",
    }

    return {
        "ok": True,
        "value": {
            "operation": "create_prd",
            "prd": prd,
        },
    }

def _op_create_roadmap(kwargs: dict) -> dict:
    title = kwargs.get("title", "")
    quarters = kwargs.get("quarters", 4)

    if not title:
        return {"ok": False, "value": None, "error": "title is required for create_roadmap"}

    roadmap = {
        "title": title,
        "quarters": quarters,
        "themes": ["Foundation", "Growth", "Scale", "Optimize"][:quarters],
    }

    return {
        "ok": True,
        "value": {
            "operation": "create_roadmap",
            "roadmap": roadmap,
        },
    }

def _op_user_stories(kwargs: dict) -> dict:
    title = kwargs.get("title", "")
    audience = kwargs.get("audience", "end user")

    if not title:
        return {"ok": False, "value": None, "error": "title is required for user_stories"}

    stories = [
        f"As a {audience}, I want to use {title} so that I can accomplish my goals efficiently.",
        f"As a {audience}, I want to see clear status updates so that I know what's happening.",
        f"As a {audience}, I want to export my data so that I can use it elsewhere.",
    ]

    return {
        "ok": True,
        "value": {
            "operation": "user_stories",
            "title": title,
            "stories": stories,
        },
    }

def _op_rice_score(kwargs: dict) -> dict:
    reach = kwargs.get("reach", 0)
    impact = kwargs.get("impact", 0)
    confidence = kwargs.get("confidence", 0)
    effort = kwargs.get("effort", 0)

    if effort == 0:
        return {"ok": False, "value": None, "error": "effort must be non-zero for RICE score"}

    score = (reach * impact * confidence) / effort

    return {
        "ok": True,
        "value": {
            "operation": "rice_score",
            "reach": reach,
            "impact": impact,
            "confidence": confidence,
            "effort": effort,
            "rice_score": score,
        },
    }


_OPERATIONS = {
    "create_prd": _op_create_prd,
    "create_roadmap": _op_create_roadmap,
    "user_stories": _op_user_stories,
    "rice_score": _op_rice_score,
    "success_metrics": _op_success_metrics,
}

_OPERATION_TITLES = {
    "create_prd": "Product Requirements Document",
    "create_roadmap": "Product Roadmap",
    "user_stories": "User Stories",
    "rice_score": "RICE Score",
    "success_metrics": "Success Metrics",
}

_ALIASES = {
    "prd": "create_prd",
    "roadmap": "create_roadmap",
    "stories": "user_stories",
    "rice": "rice_score",
    "metrics": "success_metrics",
}

def execute(**kwargs) -> dict:
    """Run one product manager operation."""
    operation = (kwargs.get("operation") or "").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Product Manager",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown product manager operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Product Manager",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Product Manager",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Product manager error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Product Manager"),
        "summary": record.get("value", {}).get("title", "Operation completed"),
        "spoken_narrative": record.get("value", {}).get("title", "Operation completed"),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }

if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="create_prd", title="Mobile App", problem="Users need offline access"))
def _op_success_metrics(kwargs: dict) -> dict:
    title = kwargs.get("title", "")

    if not title:
        return {"ok": False, "value": None, "error": "title is required for success_metrics"}

    metrics = [
        "Monthly Active Users (MAU)",
        "Customer Satisfaction Score (CSAT)",
        "Net Promoter Score (NPS)",
        "Feature adoption rate",
        "Churn rate",
        "Revenue per user",
    ]

    return {
        "ok": True,
        "value": {
            "operation": "success_metrics",
            "title": title,
            "metrics": metrics,
        },
    }
