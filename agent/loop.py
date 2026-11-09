"""agent/loop.py - the agentic execute loop.

The loop is the whole point of this package, and it is deliberately small:

    think -> act -> observe -> verify -> repeat

What separates it from a naive "while the model asks for tools" loop:

* **Bounded.** Hard cap on turns, and a repeat-detector that breaks when the
  model asks for the same tool with the same arguments twice. Small models do
  this constantly, and without the guard it burns a local context window.
* **Plan-aware.** The scratchpad plan is injected every turn, so the model
  stays oriented instead of re-deriving the task from a growing transcript.
* **Failure-forward.** Tool errors go back to the model as observations with
  the error text, so it can adapt rather than retry blindly.
* **Honest reporting.** If the turn budget runs out, the summary says so and
  says what was unfinished. It never claims success it did not observe.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from agent.llm import SYSTEM_PREAMBLE, Backend, LLMResponse
from agent.frontier_router import FrontierRouter
from agent.findings import record_finding
from agent.scratchpad import current_plan, progress_line, reset
from agent.tools import Registry, ToolResult
from agent.verify import verify

Progress = Callable[[str], None]


@dataclass
class RunResult:
    """Everything a caller (UI, tests, logs) needs to know about one run."""

    answer: str = ""
    ok: bool = False
    turns: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stopped_because: str = ""
    elapsed: float = 0.0
    plan: list[dict] = field(default_factory=list)
    # Verification: did we observe the work get done, or just hear about it?
    verified: bool | None = None
    verification_notes: list[str] = field(default_factory=list)
    # Procedural memory: what a similar past task did.
    recalled: str = ""
    # Frontier routing: which backend the Phase 5 router selected and why.
    frontier_route: dict[str, Any] | None = None

    def summary(self) -> str:
        bits = [f"turns={self.turns}", f"tools={len(self.tool_calls)}"]
        if self.verified is not None:
            bits.append(f"verified={'yes' if self.verified else 'NO'}")
        if self.errors:
            bits.append(f"errors={len(self.errors)}")
        if self.stopped_because:
            bits.append(f"stop={self.stopped_because}")
        return ", ".join(bits)


class Agent:
    """Run a goal to completion against a tool registry."""

    def __init__(
        self,
        backend: Backend,
        registry: Registry,
        max_turns: int = 12,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        max_tools: int = 12,
        tool_budget_tier: int = 1,  # 1 = cheap tools only, 2 = moderate, 3 = all
    ) -> None:
        self.backend = backend
        self.registry = registry
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_tools = max_tools
        self.tool_budget_tier = tool_budget_tier

    def run(self, goal: str, progress: Progress | None = None,
            history: list[dict] | None = None,
            workspace: Path | None = None) -> RunResult:
        started = time.time()
        result = RunResult()
        say = progress or (lambda _m: None)
        reset()

        # Procedural memory: what worked last time for a similar request.
        # Injected up front so the model can follow a known-good path instead
        # of rediscovering it.
        try:
            from agent import procedural
            hint = procedural.recall(goal)
            if hint:
                result.recalled = hint
        except Exception:
            hint = ""

        # Phase 5 frontier routing: triage the goal to local vs frontier,
        # honoring the local-by-default policy. Record the decision so the
        # run record shows which backend class was chosen and why.
        try:
            from agent.frontier_router import FrontierRouter
            _router = FrontierRouter()
            route = _router.route(goal)
            result.frontier_route = {
                "backend": route.backend,
                "reason": route.reason,
                "confidence": route.confidence,
                "forced_local": route.forced_local,
                "opted_into_frontier": route.opted_into_frontier,
            }
        except Exception:
            route = None
            result.frontier_route = {
                "backend": "local",
                "reason": "router unavailable, defaulting to local",
                "confidence": 0.0,
                "forced_local": False,
                "opted_into_frontier": False,
            }

        schemas = self._select_tools(goal)
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PREAMBLE}]
        if hint:
            messages.append({
                "role": "system",
                "content": "Experience from similar past tasks:\n" + hint,
            })
        messages.extend(history or [])
        messages.append({
            "role": "user",
            "content": f"Goal: {goal}",
        })

        seen_calls: dict = {}
        pending_verdict = ""

        for turn in range(1, self.max_turns + 1):
            result.turns = turn
            # Keep the plan in front of the model every turn.
            plan = current_plan()
            plan_hint = progress_line() if plan["steps"] else ""
            if pending_verdict:
                # A failed verification is handed back so the model can fix it
                # inside the remaining budget instead of us reporting a lie.
                messages.append({
                    "role": "system",
                    "content": f"VERIFICATION FAILED - {pending_verdict}",
                })
                pending_verdict = ""
            elif plan_hint and turn > 1:
                messages.append({
                    "role": "system",
                    "content": f"Current plan: {plan_hint}",
                })

            say(f"thinking (turn {turn}/{self.max_turns})")
            resp: LLMResponse = self.backend.chat(
                messages, tools=schemas or None,
                max_tokens=self.max_tokens, temperature=self.temperature,
            )

            if not resp.ok:
                result.errors.append(resp.error)
                result.stopped_because = "backend_error"
                result.answer = resp.error
                result.elapsed = time.time() - started
                result.plan = current_plan()["steps"]
                return result

            messages.append({
                "role": "assistant",
                "content": resp.text or "",
                **({"tool_calls": resp.tool_calls} if resp.tool_calls else {}),
            })

            if not resp.tool_calls:
                verdict = verify(goal, resp.text or "", result.tool_calls,
                                result.errors, workspace)
                result.verified = verdict.ok
                result.verification_notes = verdict.reasons
                if verdict.ok:
                    result.answer = resp.text or "Done."
                    result.ok = bool(resp.text)
                    result.stopped_because = (
                        "completed" if resp.text else "stopped_without_text"
                    )
                    break
                # Not verified - give it one more chance if budget remains.
                if turn < self.max_turns:
                    pending_verdict = verdict.correction
                    continue
                result.answer = (
                    (resp.text or "").strip()
                    + "\n\n(I could not verify this was completed: "
                    + "; ".join(verdict.reasons) + ")"
                )
                result.ok = False
                result.stopped_because = "verification_failed"
                break

            # Independent calls run concurrently; dependent ones stay serial.
            for call, outcome in zip(
                resp.tool_calls,
                self._execute_calls(resp.tool_calls, seen_calls, result, say),
            ):
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", f"call_{turn}"),
                    "name": call.get("function", {}).get("name", "?"),
                    "content": outcome.as_message()[:4000],
                })
        else:
            result.stopped_because = "turn_budget_exhausted"
            result.answer = (
                "Stopped: ran out of turns before finishing."
                + (f" Last note: {result.answer}" if result.answer else "")
            )

        result.elapsed = time.time() - started
        result.plan = current_plan()["steps"]

        # Procedural memory: remember how this went, so the next similar task
        # starts smarter. Failures are stored too - knowing an approach failed
        # is worth as much as knowing one worked.
        try:
            from agent import procedural
            procedural.record(
                goal,
                [c["name"] for c in result.tool_calls],
                success=bool(result.ok),
                elapsed=result.elapsed,
            )
            if result.ok:
                procedural._bump_uses(goal)
        except Exception:
            pass
        return result

    # -- internals ----------------------------------------------------------

    def _select_tools(self, goal: str) -> list[dict]:
        """Pick the tools worth advertising to the model for this goal.

        A local 2k-context model cannot even accept the full catalogue: the
        schemas alone overflow it and the server rejects the request with
        HTTP 400. Beyond the hard limit, a small model is measurably worse at
        choosing correctly when it is shown 49 options at once.

        Tool budget tier filters out expensive tools:
        - tier 1: only cost_tier 1 (cheap/free) tools
        - tier 2: cost_tier 1 and 2
        - tier 3: all tools

        So we rank by lexical relevance to the goal, keep a floor of always-
        useful tools, and cap the total. Tools the registry permits are always
        a subset of what the caller allowed, so this narrows the menu without
        ever widening it.
        """
        import re

        stop = {
            "a", "an", "the", "is", "are", "to", "of", "and", "or", "in", "on",
            "for", "with", "about", "my", "i", "me", "it", "that", "this",
            "please", "can", "you", "do", "make", "create", "write", "get",
        }
        terms = {t for t in re.findall(r"[a-z0-9_]+", (goal or "").lower())
                 if t not in stop and len(t) > 2}

        permitted = [t for t in self.registry if self.registry.permitted(t.name)]

        # Apply tool budget tier filter
        budget_tier = self.tool_budget_tier
        permitted = [
            t for t in permitted
            if getattr(t, "cost_tier", 1) <= budget_tier
        ]

        budget = max(4, min(self.max_tools, len(permitted)))

        if len(permitted) <= budget:
            return [t.schema() for t in permitted]

        def score(tool) -> float:
            if not terms:
                return 0.0
            hay = f"{tool.name} {tool.description} " + " ".join(
                str(p) for p in (tool.parameters.get("properties") or {}).keys()
            )
            words = {w for w in re.findall(r"[a-z0-9_]+", hay.lower())}
            return len(terms & words)

        ranked = sorted(permitted, key=score, reverse=True)
        chosen = ranked[:budget]

        # Always keep the reasoning/utility tools that any goal may need.
        for must in ("calculate", "current_time", "read_file", "todo"):
            tool = self.registry.get(must)
            if tool is None or not self.registry.permitted(must):
                continue
            if getattr(tool, "cost_tier", 1) > budget_tier:
                continue
            if tool not in chosen and len(chosen) < budget + 3:
                chosen.append(tool)

        return [t.schema() for t in chosen]

    def _execute_calls(self, calls: list[dict], seen: dict,
                       result: RunResult, say: Progress):
        """Run this turn's tool calls, concurrently where it is safe.

        Concurrency is only safe for calls the model issued together, which by
        construction it believes are independent. Sequential fallback is used
        when any call touches the same tool, since those frequently contend
        (two writes to one path, a browser session, audio devices).
        """
        def one(call: dict) -> ToolResult:
            return self._invoke(call, seen, result, say)

        if len(calls) == 1:
            return [one(calls[0])]

        names = [(c.get("function", {}) or {}).get("name", "") for c in calls]
        contended = len(set(names)) != len(names)
        if contended:
            return [one(c) for c in calls]

        try:
            with ThreadPoolExecutor(max_workers=min(4, len(calls))) as pool:
                return list(pool.map(one, calls))
        except Exception:
            return [one(c) for c in calls]

    def _invoke(self, call: dict, seen: dict,
                result: RunResult, say: Progress) -> ToolResult:
        fn = call.get("function", {}) or {}
        name = fn.get("name", "")
        raw_args = fn.get("arguments") or "{}"

        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except json.JSONDecodeError:
            args = {}
            result.errors.append(f"{name}: arguments were not valid JSON")
            return ToolResult(ok=False, error="arguments were not valid JSON")

        # Repeat guard. Allow one stumble before intervening: small local
        # models legitimately re-issue a call after a failure, but a repeated
        # identical retry is a loop and the turn budget is better spent
        # elsewhere.
        fingerprint = f"{name}:{json.dumps(args, sort_keys=True, default=str)}"
        if fingerprint in seen:
            seen[fingerprint] += 1
            if seen[fingerprint] > 2:
                result.errors.append(f"{name}: repeated identical call, stopped")
                return ToolResult(
                    ok=False,
                    error="you already made this exact call and got this result "
                          "twice; change your approach or finish",
                )
        else:
            seen[fingerprint] = 1

        say(f"tool: {name}")
        outcome = self.registry.run(name, args)
        result.tool_calls.append({
            "name": name,
            "args": args,
            "ok": outcome.ok,
            "error": outcome.error,
            "elapsed": (outcome.data or {}).get("elapsed"),
        })
        if not outcome.ok:
            result.errors.append(f"{name}: {outcome.error}")
            # Record as a finding (Phase K P1 - findings/CVSS ledger)
            try:
                from agent import findings as findings_mod
                findings_mod.record_finding(
                    vuln_class="tool_failure",
                    target=name,
                    evidence=outcome.error or "tool returned ok=False",
                    vector="none",
                    confidence="low",
                    activity="passive",
                )
            except Exception:
                pass  # never fail the tool call on audit failure
        return outcome


def run_goal(goal: str, workspace: str | None = None,
             allowed_tools: list[str] | None = None,
             progress: Progress | None = None,
             max_turns: int = 12,
             tool_budget_tier: int = 1) -> RunResult:
    """Convenience entry point: build the default agent and run one goal."""
    from agent.llm import default_backend
    from agent.tools import build_default_registry

    registry = build_default_registry(workspace)
    if allowed_tools is not None:
        registry.allowed = set(allowed_tools)
    return Agent(default_backend(), registry, max_turns=max_turns,
                 tool_budget_tier=tool_budget_tier).run(
        goal, progress=progress
    )
