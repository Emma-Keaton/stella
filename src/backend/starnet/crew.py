"""
src/backend/starnet/crew.py — Multi-agent crew system (StarNet crew-call.js port).

Provides CrewManager: register named agents, detect delegation intent in free
text via crew_call_note(), and detect "seat me in this chat" intent via
seat_call_note(). Follows the StarNet crew-call pattern adapted to Python.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Agent:
    """A named crew member that can be dispatched to handle part of a request."""
    agent_id: str
    name: str
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    model: str = "default"


class CrewManager:
    """Registers crew agents and detects delegation / seating intent in text."""

    def __init__(self) -> None:
        self._crew: dict[str, dict[str, Any]] = {}

    def register(self, agent: Agent) -> None:
        self._crew[agent.agent_id] = {
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "tools": list(agent.tools),
            "model": agent.model,
        }

    def unregister(self, agent_id: str) -> None:
        self._crew.pop(agent_id, None)

    def get(self, agent_id: str) -> Optional[Agent]:
        j = self._crew.get(agent_id)
        if j is None:
            return None
        tools = j.get("tools") or []
        return Agent(
            agent_id=agent_id,
            name=j.get("name", ""),
            system_prompt=j.get("system_prompt", ""),
            tools=list(tools),
            model=j.get("model", "default"),
        )

    def all(self) -> list[Agent]:
        return [self.get(aid) for aid in self._crew if self.get(aid) is not None]

    # ------------------------------------------------------------- crew_call_note
    def crew_call_note(
        self,
        text: str,
        lead_id: str,
        dispatch: bool = True,
        seat: bool = False,
    ) -> str:
        """
        Detect delegation intent ("ask Ada to research...") in `text`.

        Returns a crew-call instruction string when delegation is detected,
        or an empty string when none is found.
        """
        t = text.strip()
        if not t or not self._crew:
            return ""

        # Disqualifiers: negation, uncertainty, self-handling, conditionals
        qualified = re.compile(
            r"""\b(?:no|not|never|don't|doesn't|won't|shouldn't|unless|maybe|perhaps|instead|actually|wait|scratch\s+that|never\s*mind|on\s+second\s+thought|changed\s+my\s+mind)\b|i\.(?:ll|d)\s+(?:do|handle|take)\s+(?:it|this|that)\b|do\s+it\s+yourself\b|\bif\s+(?:needed|necessary|required|possible|it\s+helps|you\s+(?:want|like|need|can|think|prefer))\b|[“”`]""",
            re.IGNORECASE,
        )
        t_no_rush = re.sub(r"\bno\s+(?:rush|hurry|pressure|worries)\b", " ", t)
        if qualified.search(t_no_rush):
            return ""

        # Affirmative delegation cues
        ask = re.compile(
            r"""(?:have|ask|get|tell|let|send|use|put|dispatch|task|loop in|bring in|(?:delegate|assign|hand|give)(?:\s+(?:this|it|the task))?\s+to)""",
            re.IGNORECASE,
        )

        # Build member cue list from registered agents (excluding the lead)
        members: list[dict[str, str]] = []
        for agent_id, ident in self._crew.items():
            if agent_id == lead_id:
                continue
            name = ident.get("name", "")
            cues: list[str] = []
            if len(name) >= 3:
                cues.append(name)
            if len(agent_id) >= 3 and agent_id.lower() != name.lower():
                cues.append(agent_id)
            if cues:
                members.append({"agent_id": agent_id, "name": name, "cues": ",".join(cues)})

        if not members:
            return ""

        # Sort cues by length descending so longer names match first
        all_cues = sorted(
            {c for m in members for c in m["cues"].split(",")},
            key=len,
            reverse=True,
        )
        pattern = re.compile(
            r"(?:\s+the\s+)?" + "|".join(re.escape(c) for c in all_cues) + r"(?=$|[^A-Za-z0-9_-])",
            re.IGNORECASE,
        )

        action = re.search(ask.pattern + r"\s+(" + pattern.pattern + r")", t)
        if action is None:
            return ""

        targets: set[str] = set()
        for m in pattern.finditer(t):
            targets.add(m.group(1).lower())

        named = [
            m for m in members
            if any(c.lower() in targets for c in m["cues"].split(","))
        ]
        if not named:
            return ""

        if not dispatch:
            return ""

        who = ", ".join(
            m["name"] if m["name"] == m["agent_id"] else f'{m["name"]} (agentId {m["agent_id"]})'
            for m in named
        )[:4]
        workers = ", ".join(
            f'{{agentId:\\"{m["agent_id"]}\\", prompt:\\"<their part>\\"}}'
            for m in named
        )[:4]

        return (
            "\n\n[CREW CALL] The Commander named " + who + " in this request. Hand that part to them with team.dispatch, "
            + "workers:[" + workers + "], and build your answer from what they return. "
            + "Do it yourself only if the dispatch is refused."
        )

    # ------------------------------------------------------------- seat_call_note
    def seat_call_note(self, text: str, lead_id: str, seat_granted: bool) -> str:
        """
        Detect "bring <agent> into this chat" intent when seat_granted is True.

        Returns a seating instruction string, or empty string when none found.
        """
        if not seat_granted:
            return ""
        t = text.strip()
        if not t or not self._crew:
            return ""

        seat_ask = re.compile(
            r"""(?:get|bring|add|have|invite|loop in)\s+(.+?)\s+(?:in|into|to)\s+(?:this\s+)?(?:chat|conversation|here)""",
            re.IGNORECASE,
        )
        m = seat_ask.search(t)
        if m is None:
            return ""

        names_part = m.group(1)

        # Match any registered agent whose name or id appears in names_part
        all_cues: list[tuple[str, str]] = []
        for aid, agent in self._crew.items():
            name = agent.get("name", "")
            all_cues.append((name, aid))
            all_cues.append((aid, aid))

        matched = [
            (nm, aid) for nm, aid in all_cues
            if nm.lower() in names_part.lower()
        ]

        if not matched:
            return ""

        named = matched[:4]
        who = ", ".join(
            aid if nm == aid else f"{nm} (agentId {aid})"
            for nm, aid in named
        )

        agent_ids_json = ",".join(f'"{aid}"' for _, aid in named)

        return (
            "\n\n[CREW CALL] The Commander wants " + who + " IN THIS CHAT with them. Seat them with station.control "
            + f"{{\"action\": \"group.add\", \"args\": {{\"agents\": [{agent_ids_json}]}}}} "
            + "(tool_search \"group add\" if it is not in your list); team.dispatch never puts anyone in this chat."
        )