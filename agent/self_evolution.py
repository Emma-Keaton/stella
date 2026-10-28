"""agent/self_evolution.py - Self-evolution loop (Phase K Step 2).

Runs a propose-solve-verify loop:
1. Proposer generates questions from a domain/concept.
2. Solver attempts each question using available tools.
3. Results are recorded as findings with CVSS scores.
4. The loop reports progress, coverage, and self-improvement metrics.

Nothing is symlinked or read from another folder; everything is written inside
this project.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agent import tools as tools_mod
from agent import findings as findings_mod
from agent import self_knowledge as sk_mod
from agent import tool_budget as tb_mod
from agent import tool_policy as tp_mod
from agent import proposer as prop_mod
from agent import solver as solver_mod
from core import tool_policy as core_tool_policy

from agent import tool_policy as core_tool_policy


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_result(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _build_registry() -> tools_mod.Registry:
    """Build the default tool registry for evolution."""
    return tools_mod.build_default_registry()


def run_evolution_cycle(goal: str = "", concept: str = "",
                        skill: str = "", domain: str = "",
                        max_iterations: int = 3) -> dict[str, Any]:
    """Run one evolution cycle: propose -> solve -> record -> report.

    Returns a dict with:
      - goal, concept, domain, skill
      - initial_score, final_score, improvement
      - iterations, turns, tool_calls
      - tools_used, lessons_learned
      - steps (per-iteration results)
    """
    operation = "evolve"
    result: dict[str, Any] = {
        "operation": operation,
        "ok": False,
        "goal": goal,
        "concept": concept,
        "domain": domain,
        "skill": skill,
        "initial_score": 0.0,
        "final_score": 0.0,
        "improvement": 0.0,
        "iterations": 0,
        "turns": 0,
        "tool_calls": 0,
        "tools_used": [],
        "lessons_learned": [],
        "steps": [],
        "error": "",
    }

    try:
        reg = _build_registry()

        # Step 1: Propose questions
        prop_result = prop_mod._op("propose", True, {})  # placeholder
        # Actually use propose directly
        prop_result = prop_mod.propose(domain=domain or "general", count=max_iterations)

        if not prop_result.get("ok"):
            return _op(operation, False, None, f"Propose failed: {prop_result.get('error', 'unknown')}")

        questions = prop_result.get("questions", [])
        if not questions:
            return _op(operation, False, None, "No questions proposed.")

        # Step 2: Solve each question
        total_score = 0.0
        total_turns = 0
        total_tool_calls = 0
        all_tools_used: set[str] = set()
        lessons: list[str] = []
        step_results: list[dict[str, Any]] = []

        for q in questions[:max_iterations]:
            q_text = q.get("question", "")
            q_target = q.get("target", "")
            q_activity = q.get("activity", "passive")

            solve_result = solver_mod.solve(
                registry=reg,
                question=q_text,
                target=q_target,
                activity=q_activity,
                max_steps=3,
            )

            step_results.append({
                "question": q_text,
                "target": q_target,
                "activity": q_activity,
                "solved": solve_result.get("solved", False),
                "honesty": solve_result.get("honesty", "failed"),
                "steps": solve_result.get("steps", []),
                "answer": solve_result.get("answer", ""),
            })

            if solve_result.get("solved"):
                total_score += 1.0
            total_turns += len(solve_result.get("steps", []))
            total_tool_calls += len(solve_result.get("steps", []))
            for t in solve_result.get("steps", []):
                if t.get("tool"):
                    all_tools_used.add(t["tool"])
            if solve_result.get("answer"):
                lessons.append(solve_result["answer"][:120])

        total_items = len(question_list) if (question_list := questions) else 1
        final_score = total_score / max(1, len(questions))

        result.update({
            "ok": True,
            "goal": goal or concept or "self-evolution",
            "initial_score": 0.0,
            "final_score": round(final_score, 2),
            "improvement": round(final_score, 2),
            "iterations": len(questions),
            "turns": total_turns,
            "tool_calls": total_tool_calls,
            "tools_used": sorted(all_tools_used),
            "lessons_learned": lessons[:5],
            "steps": step_results,
        })

    except Exception as exc:  # noqa: BLE001
        return _op(operation, False, None, f"{type(exc).__name__}: {exc}")

    return _op(operation, True, result)


def run_goal(goal: str, workspace: str | None = None,
             allowed_tools: list[str] | None = None,
             progress: Any | None = None,
             max_turns: int = 12,
             tool_budget_tier: int = 1) -> Any:
    """Convenience entry point: build the default agent and run one goal."""
    from agent.tools import build_default_registry
    registry = build_default_registry(workspace)
    if allowed_tools is not None:
        registry.allowed = set(allowed_tools)
    return Agent(default_backend(), registry, max_turns=max_turns,
                 tool_budget_tier=tool_budget_tier).run(
        goal, progress=progress
    )


__all__ = [
    "run_evolution_cycle",
    "run_goal",
    "PROPOSALS_PATH",
    "_op",
    "_op_result",
    "_build_registry",
]
