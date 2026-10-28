"""
Feature: brainstorming
Description: Structured brainstorming and design exploration for Stella. Explores user intent, requirements and design before implementation. Pure-Python, no external dependencies.
"""

from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "brainstorming",
    "aliases": ["brainstorming", "brainstorm", "design", "explore idea",
                "refine idea", "propose approaches", "design review",
                "creative work", "spec"],
    "description": (
        "Structured brainstorming and design exploration for Stella. Explores user "
        "intent, requirements and design before implementation. Asks clarifying "
        "questions one at a time, proposes 2-3 approaches with trade-offs, presents "
        "a design for approval, and produces a design-doc summary. Nothing is "
        "implemented until the user approves the design. Pure-Python, no external "
        "dependencies, runs on any surface."
    ),
    "triggers": [
        "brainstorm", "brainstorming", "explore idea", "refine idea", "design",
        "propose approaches", "design review", "creative work", "spec",
        "what should I build", "how should I design", "clarify requirements",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: explore | questions | approaches | design | checklist | sources. Defaults to sources.",
            },
            "topic": {
                "type": "STRING",
                "description": "The idea, feature or topic to brainstorm about.",
            },
            "context": {
                "type": "STRING",
                "description": "Additional project context or constraints.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum items to return. Defaults to 10.",
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
    "notes": "Pure-Python skill. No code is written or modified until the user approves a design. Follows the brainstorming hard-gate: explore -> clarify -> propose -> design -> approve.",
}

_CHECKLIST = [
    "Explore project context - check files, docs, recent commits",
    "Ask clarifying questions - one at a time, understand purpose/constraints/success criteria",
    "Propose 2-3 approaches - with trade-offs and a recommendation",
    "Present design - in sections scaled to complexity, get user approval after each section",
    "Write design doc - save to docs/superpowers/specs/ and self-review",
    "User reviews written spec - approve before proceeding",
    "Transition to implementation - invoke writing-plans skill to create implementation plan",
]

_APPROACHES = [
    {
        "name": "Minimal viable",
        "description": "Smallest change that satisfies the requirement.",
        "trade_off": "Fast to ship; may need refactoring later.",
    },
    {
        "name": "Well-factored",
        "description": "Clean modules, clear boundaries, tested.",
        "trade_off": "Takes longer upfront; easier to maintain.",
    },
    {
        "name": "Fully-featured",
        "description": "All edge cases, docs, and polish included.",
        "trade_off": "Slowest to deliver; highest effort.",
    },
]


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


def _op_explore(kwargs: dict) -> dict:
    topic = (kwargs.get("topic") or "").strip()
    context = (kwargs.get("context") or "").strip()
    if not topic:
        return _op("explore", False, None, "Provide a topic to explore (topic=...).")
    return _op("explore", True, {
        "topic": topic,
        "context": context or "(none provided)",
        "hard_gate": "Do NOT implement anything until the user approves the design.",
        "first_step": "Explore project context - check files, docs, recent commits.",
        "next": "Use operation='questions' to generate clarifying questions.",
    })


def _op_questions(kwargs: dict) -> dict:
    topic = (kwargs.get("topic") or "").strip()
    if not topic:
        return _op("questions", False, None, "Provide a topic (topic=...).")
    limit = _as_int(kwargs.get("limit"), 10)
    questions = [
        f"What is the purpose of {topic}?",
        f"Who will use {topic} and in what context?",
        f"What are the success criteria for {topic}?",
        f"What constraints apply to {topic} (time, platform, dependencies)?",
        f"What similar work already exists in the project?",
        f"What could go wrong with {topic}, and how would you detect it?",
    ]
    return _op("questions", True, {
        "topic": topic,
        "questions": questions[:limit],
        "count": len(questions[:limit]),
        "note": "Ask these one at a time; do not implement until answers are understood.",
    })


def _op_approaches(kwargs: dict) -> dict:
    topic = (kwargs.get("topic") or "").strip()
    if not topic:
        return _op("approaches", False, None, "Provide a topic (topic=...).")
    return _op("approaches", True, {
        "topic": topic,
        "approaches": _APPROACHES,
        "count": len(_APPROACHES),
        "note": "Present trade-offs; recommend one based on the project context.",
    })


def _op_design(kwargs: dict) -> dict:
    topic = (kwargs.get("topic") or "").strip()
    context = (kwargs.get("context") or "").strip()
    if not topic:
        return _op("design", False, None, "Provide a topic (topic=...).")
    return _op("design", True, {
        "topic": topic,
        "context": context or "(none provided)",
        "sections": [
            "Overview - what is being built and why",
            "Requirements - functional and non-functional",
            "Approach - chosen option and rationale",
            "Interface - APIs, CLI, or user-facing surface",
            "Data - models, storage, schema if any",
            "Risks - what could fail and how to mitigate",
            "Plan - steps to implement after approval",
        ],
        "note": "Present this design to the user and get approval before implementing.",
    })


def _op_checklist(kwargs: dict) -> dict:
    limit = _as_int(kwargs.get("limit"), 10)
    return _op("checklist", True, {
        "checklist": _CHECKLIST[:limit],
        "count": len(_CHECKLIST[:limit]),
        "hard_gate": "No implementation until design is approved by the user.",
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "brainstorming (pure-Python, adapted from shared-skills/brainstorming)",
        "dependencies": [],
        "note": "No external dependencies; runs on desktop and Android.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "explore": _op_explore,
    "questions": _op_questions,
    "approaches": _op_approaches,
    "design": _op_design,
    "checklist": _op_checklist,
}

_OPERATION_TITLES = {
    "sources": "Brainstorming Sources",
    "explore": "Explore Topic",
    "questions": "Clarifying Questions",
    "approaches": "Proposed Approaches",
    "design": "Design Outline",
    "checklist": "Brainstorming Checklist",
}

_ALIASES = {
    "explore_topic": "explore", "clarifying_questions": "questions",
    "propose_approaches": "approaches", "present_design": "design",
    "brainstorming_checklist": "checklist",
    "sources_list": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return value.get("note", "Brainstorming skill available.")
    if operation == "explore":
        return f"Exploring '{value.get('topic')}'. {value.get('first_step')}"
    if operation == "questions":
        return f"{value.get('count')} clarifying question(s) for '{value.get('topic')}'."
    if operation == "approaches":
        return f"{value.get('count')} approach(es) for '{value.get('topic')}'."
    if operation == "design":
        return f"Design outline for '{value.get('topic')}' with {len(value.get('sections') or [])} section(s)."
    if operation == "checklist":
        return f"{value.get('count')} checklist item(s). {value.get('hard_gate')}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one brainstorming operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Brainstorming",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Brainstorming",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Brainstorming",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Brainstorming error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Brainstorming"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
