"""core/self_knowledge.py - runtime self-knowledge with limits.

The agent can ask "what can I do?" and get an honest, bounded answer: which
tools exist, which it is permitted to run, which activity class each belongs
to, what its current budget consumption looks like, and what limits apply.
Nothing is fabricated: every entry names a real tool or a real configured
limit, and unknowns are reported as unknown rather than guessed.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent.tools import Registry
from core.user_paths import get_user_data_dir


@dataclass
class ToolSelfView:
    """What the agent knows about one tool - enough to choose honestly."""
    name: str
    description: str
    category: str
    cost_tier: int
    activity: str
    requires: list[str]
    read_only: bool
    destructive: bool
    permitted: bool
    brief: str


@dataclass
class SelfKnowledge:
    """The agent's model of itself: tools, limits, budget, platform."""

    agent_id: str
    platform: str
    python_version: str
    tools: list[ToolSelfView] = field(default_factory=list)
    budget: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "platform": self.platform,
            "python_version": self.python_version,
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "cost_tier": t.cost_tier,
                    "activity": t.activity,
                    "requires": t.requires,
                    "read_only": t.read_only,
                    "destructive": t.destructive,
                    "permitted": t.permitted,
                    "brief": t.brief,
                }
                for t in self.tools
            ],
            "tool_count": len(self.tools),
            "permitted_tool_count": sum(1 for t in self.tools if t.permitted),
            "budget": self.budget,
            "limits": self.limits,
            "capabilities": self.capabilities,
        }

    def summary(self) -> str:
        permitted = [t for t in self.tools if t.permitted]
        blocked = [t for t in self.tools if not t.permitted]
        lines = [
            f"agent={self.agent_id} platform={self.platform} python={self.python_version}",
            f"tools={len(self.tools)} permitted={len(permitted)} blocked={len(blocked)}",
            f"budget={self.budget}",
            f"limits={self.limits}",
        ]
        if blocked:
            lines.append("blocked=" + ", ".join(t.name for t in blocked[:8]))
        return "\n".join(lines)


def build_self_knowledge(
    registry: Registry,
    agent_id: str = "agent",
    budget_limits: dict[str, Any] | None = None,
    budget_spent: dict[str, Any] | None = None,
) -> SelfKnowledge:
    """Build the agent's honest self-view from a real registry + real limits."""
    tools: list[ToolSelfView] = []
    for tool in registry:
        tools.append(ToolSelfView(
            name=tool.name,
            description=tool.description,
            category=getattr(tool, "category", "general"),
            cost_tier=getattr(tool, "cost_tier", 1),
            activity=getattr(tool, "activity", "passive"),
            requires=list(tool.requires),
            read_only=bool(getattr(tool, "read_only", True)),
            destructive=bool(tool.destructive),
            permitted=registry.permitted(tool.name),
            brief=getattr(tool, "brief", ""),
        ))

    capabilities = sorted({getattr(t, "category", "general") for t in tools})

    return SelfKnowledge(
        agent_id=agent_id,
        platform=platform.platform(),
        python_version=sys.version.split()[0],
        tools=tools,
        budget=budget_spent or {},
        limits=budget_limits or {},
        capabilities=capabilities,
    )


def self_knowledge_text(sk: SelfKnowledge) -> str:
    """Human-readable (and model-readable) self-knowledge summary."""
    return sk.summary()


__all__ = [
    "ToolSelfView", "SelfKnowledge",
    "build_self_knowledge", "self_knowledge_text",
]
