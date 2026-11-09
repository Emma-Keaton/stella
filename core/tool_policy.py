"""core/tool_policy.py - declarative, fail-closed policy for tool calls.

Design (from CopilotKit/openbot): every tool call the agent wants to make is
evaluated against a written rule *before* it runs, and the rule that decided is
recorded in the audit row. Deny is evaluated before allow, a missing policy
permits nothing for a gated activity class, and a broken rule refuses rather
than opens.

Activity classes (from theHarvester's model):

* ``passive``   - queries a third-party dataset; the target is never contacted
* ``dns``       - DNS queries about the target
* ``active``    - direct contact with the target (connections, requests, payloads)
* ``destructive``- changes the machine or deletes data; confirmation is separate

Rule file: `config/tool_policy.json` ships the defaults; a user copy at
`<user data>/config/tool_policy.json` shadows it. Rules are JSON so a user can
read exactly what Stella is allowed to do without reading code.
"""

from __future__ import annotations

import fnmatch
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("tool_policy")

#: Activity classes that never run without an explicit allow rule.
GATED_CLASSES = frozenset({"dns", "active", "destructive"})

#: Every known activity class.
ACTIVITY_CLASSES = ("passive", "dns", "active", "destructive")

_DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "name": "passive-observation-stays-open",
        "allow": ["*"],
        "activity": ["passive"],
        "reason": "Passive queries against public datasets do not touch a target.",
    },
]


@dataclass(frozen=True)
class PolicyDecision:
    """Why a tool call was allowed or refused - always carries the rule name."""

    allowed: bool
    rule: str
    reason: str
    activity: str = "passive"


def _repo_root() -> Path:
    # core/tool_policy.py -> core -> repo root
    return Path(__file__).resolve().parents[1]


def _user_policy_path() -> Path:
    try:
        from core.user_paths import get_user_data_dir

        return Path(get_user_data_dir()) / "config" / "tool_policy.json"
    except Exception:
        return Path("config") / "tool_policy.json"


def _policy_paths() -> list[Path]:
    return [
        _repo_root() / "config" / "tool_policy.json",
        _user_policy_path(),
    ]


def _default_path() -> Path:
    return _repo_root() / "config" / "tool_policy.json"


def ensure_default_policy_file() -> Path:
    """Write the shipped default policy file if it is missing."""
    path = _default_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"version": 1, "rules": _DEFAULT_RULES}, indent=2),
            encoding="utf-8",
        )
    return path


def _load_rules() -> tuple[list[dict[str, Any]], list[str]]:
    rules: list[dict[str, Any]] = []
    problems: list[str] = []
    for path in _policy_paths():
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            problems.append(f"{path.name}: unreadable ({type(exc).__name__})")
            continue
        for entry in data.get("rules") or []:
            if not isinstance(entry, dict):
                problems.append(f"{path.name}: rule is not an object")
                continue
            name = str(entry.get("name") or "").strip()
            if not name:
                problems.append(f"{path.name}: rule without a name")
                continue
            if "allow" not in entry and "deny" not in entry:
                problems.append(f"{name}: rule has neither allow nor deny")
                continue
            rules.append(entry)
    if not rules and not problems:
        # No policy file at all: ship the defaults in memory so a fresh
        # install behaves exactly like a written file.
        rules = [dict(r) for r in _DEFAULT_RULES]
    return rules, problems


def _matches(pattern: str, value: str) -> bool:
    pattern = (pattern or "").strip()
    if pattern in ("", "*"):
        return True
    return fnmatch.fnmatchcase((value or "").strip(), pattern)


def _rule_allows_tool(entry: dict, tool_name: str) -> bool:
    patterns = entry.get("allow") or entry.get("deny") or []
    if isinstance(patterns, str):
        patterns = [patterns]
    return any(_matches(str(p), tool_name) for p in patterns)


def _rule_covers_activity(entry: dict, activity: str) -> bool:
    classes = entry.get("activity") or ACTIVITY_CLASSES
    if isinstance(classes, str):
        classes = [classes]
    return activity in [str(c) for c in classes]


def _rule_covers_target(entry: dict, target: str) -> bool:
    patterns = entry.get("targets")
    if not patterns:
        return True
    if isinstance(patterns, str):
        patterns = [patterns]
    return any(_matches(str(p), (target or "").strip()) for p in patterns)


def evaluate(
    tool_name: str,
    activity: str = "passive",
    target: str = "",
    actor: str = "agent",
) -> PolicyDecision:
    """Decide whether a tool call may run, and name the rule that decided.

    Deny wins over allow. An unknown or broken rule refuses the call and says
    which rule was broken - a policy that cannot be read must not open a door.
    """
    activity = (activity or "passive").strip().lower()
    if activity not in ACTIVITY_CLASSES:
        return PolicyDecision(
            allowed=False,
            rule="unknown-activity",
            reason=f"'{activity}' is not an activity class; expected one of {', '.join(ACTIVITY_CLASSES)}.",
            activity=activity,
        )

    rules, problems = _load_rules()
    if problems:
        return PolicyDecision(
            allowed=False,
            rule="policy-unreadable",
            reason="The policy file could not be read correctly: " + "; ".join(problems),
            activity=activity,
        )

    denies = [r for r in rules if "deny" in r]
    allows = [r for r in rules if "allow" in r and "deny" not in r]

    for entry in denies:
        if not _rule_allows_tool(entry, tool_name):
            continue
        if not _rule_covers_activity(entry, activity):
            continue
        if not _rule_covers_target(entry, target):
            continue
        return PolicyDecision(
            allowed=False,
            rule=str(entry.get("name")),
            reason=str(entry.get("reason") or "Denied by policy."),
            activity=activity,
        )

    for entry in allows:
        if not _rule_allows_tool(entry, tool_name):
            continue
        if not _rule_covers_activity(entry, activity):
            continue
        if not _rule_covers_target(entry, target):
            continue
        return PolicyDecision(
            allowed=True,
            rule=str(entry.get("name")),
            reason=str(entry.get("reason") or "Allowed by policy."),
            activity=activity,
        )

    if activity in GATED_CLASSES:
        return PolicyDecision(
            allowed=False,
            rule="gated-class-default-deny",
            reason=(
                f"'{activity}' work needs an explicit allow rule naming the tool "
                f"'{tool_name}' and its target, because no rule matched this call."
            ),
            activity=activity,
        )

    return PolicyDecision(
        allowed=True,
        rule="no-rule-passive",
        reason="No rule matched and the activity class is passive.",
        activity=activity,
    )


def explain() -> dict[str, Any]:
    """The effective policy in plain terms - for the Settings surface."""
    rules, problems = _load_rules()
    return {
        "rules": rules,
        "problems": problems,
        "gated_classes": sorted(GATED_CLASSES),
        "sources": [str(p) for p in _policy_paths()],
    }


def allow(
    name: str,
    tools: list[str],
    activity: list[str],
    targets: Optional[list[str]] = None,
    reason: str = "",
) -> dict[str, Any]:
    """Build an allow rule (used by the approval flow and by tests)."""
    rule: dict[str, Any] = {
        "name": name,
        "allow": list(tools),
        "activity": list(activity),
        "reason": reason or "Explicitly allowed by the user.",
    }
    if targets:
        rule["targets"] = list(targets)
    return rule
