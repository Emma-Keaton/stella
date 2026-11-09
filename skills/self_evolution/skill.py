"""
Feature: self_evolution
Description: Self-evolving agent loop inspired by Dr. Zero. Proposes questions/problems,
solves them using available tools, and evolves through iteration - no training data
required. Reports progress, findings, and self-improvement metrics. Nothing is symlinked
or read from another folder; everything is written inside this project.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

FEATURE_METADATA = {
    "name": "self_evolution",
    "aliases": ["self_evolution", "self_evolve", "self improve", "self improvement",
                "self evolve", "self evolve agent", "auto improve", "auto improve agent",
                "self evolve loop", "proposer solver", "self train", "self train agent",
                "self learn", "self learn agent"],
    "description": (
        "Self-evolving agent loop inspired by Dr. Zero. Proposes questions/problems, "
        "solves them using available tools, and evolves through iteration - no training "
        "data required. Reports progress, findings, and self-improvement metrics. "
        "Nothing is symlinked or read from another folder; everything is written inside "
        "this project."
    ),
    "triggers": [
        "self evolve", "self evolution", "self improve", "self improvement",
        "self-improvement", "self evolving", "self evolve agent", "auto improve",
        "auto improve agent", "self evolve loop", "proposer solver", "self train",
        "self train agent", "self learn", "self learn agent",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: sources | sources_list | backends | evolve | evolve_once | run_evolution | self_evolve | sources_list. Defaults to sources.",
            },
            "concept": {
                "type": "STRING",
                "description": "Topic/concept to evolve a question about (for evolve operation).",
            },
            "domain": {
                "type": "STRING",
                "description": "Knowledge domain for evolve operation (e.g. science, coding, security, math).",
            },
            "skill": {
                "type": "STRING",
                "description": "Skill name to evolve with (for evolve operation).",
            },
            "max_iterations": {
                "type": "INTEGER",
                "description": "Maximum evolution iterations. Defaults to 3.",
            },
            "authorized": {
                "type": "BOOLEAN",
                "description": "Must be true for operations that contact external sources or write to disk.",
            },
            "confirm": {
                "type": "BOOLEAN",
                "description": "Must be true to actually run evolution (not just preview).",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum items to return. Defaults to 20.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "system",
    "surface": "both",
    "requires": [],
    "optional_dependencies": [],
    "notes": "Read-only sources/manifest queries are free. Evolving requires authorized=true + confirm=true. Nothing is symlinked or read from another folder; everything is written inside this project.",
}

_DEFAULT_LIMIT = 20


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _flag(**kwargs) -> bool:
    return kwargs.get("authorized") in (True, "true", "True", 1, "1") and \
        kwargs.get("confirm") in (True, "true", "True", 1, "1")


def _as_int(value, default: int = 20, ceiling: int = 200) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    if number <= 0:
        number = default
    return min(number, ceiling)


# ---------------------------------------------------------------- read-only ops

def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "operations": [
            "sources", "sources_list", "backends", "evolve", "evolve_once",
            "run_evolution", "self_evolve",
        ],
        "note": "Read-only source listing. Evolving requires authorized=true + confirm=true.",
    })


def _op_list(kwargs: dict) -> dict:
    return _op("sources_list", True, {
        "operations": [
            "sources", "sources_list", "backends", "evolve", "evolve_once",
            "run_evolution", "self_evolve",
        ],
        "note": "Read-only source listing.",
    })


def _op_backends(kwargs: dict) -> dict:
    return _op("backends", True, {
        "backends": [
            {"name": "local", "tier": 1, "description": "Local K2/LLM backend"},
            {"name": "ollama", "tier": 1, "description": "Local Ollama backend"},
            {"name": "lmstudio", "tier": 2, "description": "LM Studio backend"},
            {"name": "groq", "tier": 2, "description": "Groq API backend"},
            {"name": "gemini", "tier": 3, "description": "Gemini API backend"},
            {"name": "openai", "tier": 3, "description": "OpenAI API backend"},
        ],
        "note": "Model ladder backends available for evolution.",
    })


def _op_evolve(kwargs: dict) -> dict:
    operation = "evolve"
    if not _flag(**kwargs):
        return _op(operation, False, None, (
            "Evolving writes to disk and runs tool calls, so it needs "
            "authorized=true AND confirm=true."))
    if not _flag(**kwargs):
        return _op(operation, False, None, "Missing authorized/confirm.")

    concept = (kwargs.get("concept") or "").strip()
    domain = (kwargs.get("domain") or "").strip()
    skill_name = (kwargs.get("skill") or "").strip()
    max_iterations = _as_int(kwargs.get("max_iterations"), 3)

    from agent import self_evolution as se

    try:
        result = se.run_evolution_cycle(
            concept=concept or None,
            domain=domain or None,
            skill_name=skill_name or None,
            max_iterations=max_iterations,
        )
    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"{type(exc).__name__}: {exc}")

    return _op(operation, True, {
        "goal": result.get("goal", ""),
        "initial_score": result.get("initial_score", 0.0),
        "final_score": result.get("final_score", 0.0),
        "improvement": result.get("improvement", 0.0),
        "iterations": result.get("iterations", 0),
        "turns": result.get("turns", 0),
        "tool_calls": result.get("tool_calls", 0),
        "tools_used": result.get("tools_used", []),
        "lessons_learned": result.get("lessons_learned", []),
        "note": "Evolution complete. Use sources/manifest to review all changes.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "sources_list": _op_list,
    "backends": _op_backends,
    "evolve": _op_evolve,
    "evolve_once": _op_evolve,
    "run_evolution": _op_evolve,
    "self_evolve": _op_evolve,
}

_OPERATION_TITLES = {
    "sources": "Self-Evolution Sources",
    "sources_list": "Self-Evolution Sources List",
    "backends": "Available Backends",
    "evolve": "Evolve",
    "evolve_once": "Evolve Once",
    "run_evolution": "Run Evolution",
    "self_evolve": "Self Evolve",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        return value.get("note", "Self-evolution skill available.")
    if operation == "sources_list":
        return f"{len(value.get('operations') or [])} operation(s) available."
    if operation == "backends":
        return f"{len(value.get('backends') or [])} backend(s) available."
    if operation in ("evolve", "evolve_once", "run_evolution", "self_evolve"):
        return (
            f"{value.get('skill', 'unknown')}: "
            f"{value.get('initial_score', 0):.2f} -> {value.get('final_score', 0):.2f} "
            f"({value.get('improvement', 0):+.2f}) over {value.get('iterations', 0)} iteration(s)"
        )
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Run one self-evolution operation."""
    operation = (kwargs.get("operation") or "sources").strip().lower()

    # Map aliases
    aliases = {
        "self_evolve": "evolve",
        "run_evolution": "evolve",
        "evolve_once": "evolve",
        "sources_list": "sources",
    }
    operation = aliases.get(operation, operation)

    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Self-Evolution",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }

    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Self-Evolution",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Self-Evolution",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Self-evolution error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }

    return {
        "title": _OPERATION_TITLES.get(operation, "Self-Evolution"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
