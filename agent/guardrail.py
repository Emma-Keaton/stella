"""agent/guardrail.py - the self-improvement loop's guardrail (Phase 3).

Design constraint from AGI_ROADMAP.md Phase 3:

    Guardrail: the loop may only edit its playbook, never its safety rules.

The reflection job, skill_update, and any other self-modifying component may
write to playbook files (procedural memory, skill packages, tool catalogues)
but must never touch safety-critical files (tool policy, approvals, content
boundary, outcome vocabulary, audit configuration).

This module is the single enforcement point. Any component that proposes a
file write calls `may_write(path)` first; if the path is safety-critical, the
write is refused with a named rule.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Paths the self-improvement loop may write. These are "playbook" files:
#: procedures, skills, tool catalogues, reflection reports, eval results.
PLAYBOOK_PREFIXES: tuple[str, ...] = (
    "agent/procedural.py",
    "agent/procedural.jsonl",
    "features/",
    "evals/",
    "agent/coverage.py",
    "agent/findings.py",
    "agent/skill_loader.py",
    "agent/skill_catalog.py",
)

#: Paths the self-improvement loop may NEVER write. These encode safety rules
#: and must only be changed by a human (or a separate, audited process).
SAFETY_PREFIXES: tuple[str, ...] = (
    "core/tool_policy.py",
    "core/approvals.py",
    "core/content_boundary.py",
    "agent/outcome.py",
    "agent/tools.py",          # the Tool/Registry definitions themselves
    "core/audit.py",
    "core/confirm.py",
    "core/undo.py",
    "config/tool_policy.json",
    "config/approvals.json",
)


def _rel_path(path: str | Path) -> str:
    p = Path(path)
    try:
        rel = p.relative_to(PROJECT_ROOT)
    except ValueError:
        rel = p
    # Normalise to forward slashes so prefix matching works on Windows too.
    return str(rel).replace("\\", "/")


def is_safety_critical(path: str | Path) -> bool:
    """True if `path` is a safety-critical file the loop must not touch."""
    rel = _rel_path(path)
    return any(rel.startswith(prefix) for prefix in SAFETY_PREFIXES)


def is_playbook(path: str | Path) -> bool:
    """True if `path` is a playbook file the loop is allowed to touch."""
    rel = _rel_path(path)
    return any(rel.startswith(prefix) for prefix in PLAYBOOK_PREFIXES)


def may_write(path: str | Path) -> tuple[bool, str]:
    """Decide whether the self-improvement loop may write to `path`.

    Returns (allowed, reason). If the path is safety-critical, the write is
    refused regardless of anything else. If it is a playbook path, the write
    is allowed. Anything else is refused by default (default-deny).
    """
    rel = _rel_path(path)
    if is_safety_critical(rel):
        return False, (
            f"guardrail: '{rel}' is a safety-critical file. The self-improvement "
            "loop may only edit playbook files, never safety rules."
        )
    if is_playbook(rel):
        return True, "playbook path"
    return False, (
        f"guardrail: '{rel}' is not a recognised playbook path. "
        "The self-improvement loop may only write to playbook files."
    )


def may_edit_skill(skill_name: str) -> tuple[bool, str]:
    """Convenience: may the loop edit a skill package under features/<name>/?"""
    return may_write(f"features/{skill_name}/")


def may_edit_procedural() -> tuple[bool, str]:
    """Convenience: may the loop write to agent/procedural.py?"""
    return may_write("agent/procedural.py")


__all__ = [
    "is_safety_critical",
    "is_playbook",
    "may_write",
    "may_edit_skill",
    "may_edit_procedural",
    "PLAYBOOK_PREFIXES",
    "SAFETY_PREFIXES",
]
