"""
src/backend/agent/frontier_router.py - Phase 5: frontier routing.

Task triage: classifies a goal as local (runs on-device model) or frontier
(needs a cloud model such as Gemini/Groq/OpenAI). Local-by-default: unless the
user opts into frontier or the task is clearly beyond a small local model,
Stella keeps everything on the user's machine.

Design (from AGI_ROADMAP.md Phase 5):

* Task triage at request time — classify before picking a backend.
* Cost/latency/privacy policy — local by default, frontier on explicit opt-in.
* Frontier handles: deep reasoning, long synthesis, unfamiliar code.
* Local handles: everything touching personal data, always.

Honesty: the router never pretends a local model answered when a frontier
model did, and never pretends a frontier model answered locally. The backend
used is recorded in the run result and the audit trail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

#: Keywords that suggest a task needs a frontier (larger) model. A single
#: strong keyword is enough to route to frontier; weak keywords need two or
#: more.
STRONG_FRONTIER_KEYWORDS: tuple[str, ...] = (
    "write code", "program", "debug", "refactor", "architecture", "system design",
    "reasoning", "logic puzzle", "complex", "advanced", "expert", "phd",
    "research paper", "thesis", "dissertation", "legal contract", "medical",
    "law", "regulation", "compliance", "audit", "investigation",
)

WEAK_FRONTIER_KEYWORDS: tuple[str, ...] = (
    "summarize", "summary", "explain", "compare", "analyze", "analysis",
    "essay", "report", "article", "blog post", "story", "poem", "creative",
    "translate", "translation", "draft", "rewrite", "polish",
)

#: Tasks that must ALWAYS stay local — they touch personal data or the local
#: machine and must never be sent to a cloud model.
FORCE_LOCAL_KEYWORDS: tuple[str, ...] = (
    "my file", "my files", "local file", "read_file", "write_file", "remember",
    "recall", "my memory", "vault", "notes", "my notes", "personal", "private",
    "my computer", "this machine", "localhost", "local model",
)

LOCAL = "local"
FRONTIER = "frontier"


@dataclass
class RouteDecision:
    backend: str  # "local" or "frontier"
    reason: str
    confidence: float  # 0.0 .. 1.0
    forced_local: bool
    opted_into_frontier: bool


class FrontierRouter:
    """Decides whether a goal runs on the local model or a frontier backend.

    Default is local. Frontier is used only when:
      * the user explicitly opts in (frontier=True), or
      * the task contains strong frontier keywords and no force-local keyword,
      * OR the task contains two or more weak frontier keywords and no force-local
        keyword.
    """

    def __init__(self, force_local_keywords: tuple[str, ...] | None = None,
                 strong_keywords: tuple[str, ...] | None = None,
                 weak_keywords: tuple[str, ...] | None = None):
        self.force_local_keywords = tuple(force_local_keywords or FORCE_LOCAL_KEYWORDS)
        self.strong_keywords = tuple(strong_keywords or STRONG_FRONTIER_KEYWORDS)
        self.weak_keywords = tuple(weak_keywords or WEAK_FRONTIER_KEYWORDS)

    def route(self, goal: str, frontier: bool = False,
              user_opted_frontier: bool = False) -> RouteDecision:
        """Classify `goal` as local or frontier.

        `frontier` is the model-level flag (e.g. from settings). `user_opted_frontier`
        is an explicit per-request opt-in. Either one enables frontier consideration,
        but force-local keywords always win.
        """
        goal_l = (goal or "").lower()

        # Force-local keywords always win — personal data never leaves the device.
        if any(k in goal_l for k in self.force_local_keywords):
            return RouteDecision(
                backend=LOCAL,
                reason="force-local: task touches personal/local data",
                confidence=1.0,
                forced_local=True,
                opted_into_frontier=bool(user_opted_frontier),
            )

        # Count keyword matches.
        strong_hits = [k for k in self.strong_keywords if k in goal_l]
        weak_hits = [k for k in self.weak_keywords if k in goal_l]

        wants_frontier = bool(frontier or user_opted_frontier)

        if strong_hits:
            # One strong keyword is enough; confidence scales with count.
            confidence = min(0.9, 0.55 + 0.08 * len(strong_hits))
            backend = FRONTIER if wants_frontier else LOCAL
            reason = ("strong frontier keyword(s): " + ", ".join(strong_hits[:4])
                      + (" — user opted into frontier" if wants_frontier
                         else " — local-by-default, frontier not opted in"))
            return RouteDecision(
                backend=backend, reason=reason, confidence=confidence,
                forced_local=False, opted_into_frontier=wants_frontier,
            )

        if len(weak_hits) >= 2:
            confidence = min(0.8, 0.45 + 0.06 * len(weak_hits))
            backend = FRONTIER if wants_frontier else LOCAL
            reason = ("multiple weak frontier keywords: " + ", ".join(weak_hits[:4])
                      + (" — user opted into frontier" if wants_frontier
                         else " — local-by-default"))
            return RouteDecision(
                backend=backend, reason=reason, confidence=confidence,
                forced_local=False, opted_into_frontier=wants_frontier,
            )

        # Default: local.
        reason = "local-by-default: no frontier trigger, no explicit opt-in"
        if wants_frontier:
            reason = "local-by-default: user opted into frontier but no trigger matched"
        return RouteDecision(
            backend=LOCAL, reason=reason, confidence=0.7,
            forced_local=False, opted_into_frontier=wants_frontier,
        )

    def summary(self) -> str:
        return (f"frontier_router: local_by_default, "
                f"{len(self.strong_keywords)} strong + "
                f"{len(self.weak_keywords)} weak keyword(s), "
                f"{len(self.force_local_keywords)} force-local keyword(s)")


__all__ = [
    "FrontierRouter", "RouteDecision", "LOCAL", "FRONTIER",
    "STRONG_FRONTIER_KEYWORDS", "WEAK_FRONTIER_KEYWORDS", "FORCE_LOCAL_KEYWORDS",
]
