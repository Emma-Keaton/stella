"""agent/coerce.py - coercion + bounded results for tool outputs.

Tool results from untrusted sources (web, sub-agents, external APIs) are run
through coercion before the agent acts on them:

* ``coerce_result`` bounds a tool result: truncates oversized output, masks
  anything that looks like a secret, tags it with an activity class, and
  never fabricates a "done" when the source could not be confirmed.
* ``bound`` caps a value (bytes, count, duration) so a single call cannot
  inflate context or run away.
* ``sub_agent_fan_out`` runs one skill across a list of targets, collecting
  each result with its own honesty tag, so one failing target cannot poison
  the whole batch.
"""

from __future__ import annotations

import re
from typing import Any

from agent.tools import ToolResult, Honesty

_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|authorization\s*[:=]\s*['\"]?)"
    r"[A-Za-z0-9_\-]{6,}"
)


def coerce_result(name: str, output: str, ok: bool,
                  activity: str = "passive",
                  max_bytes: int = 8000) -> ToolResult:
    """Coerce one tool result into an honest ToolResult.

    * Truncates output at max_bytes.
    * Masks secret-looking substrings.
    * Honesty: ok + confirmed -> done; ok but not confirmed -> unverified;
      not ok -> failed.
    """
    text = output or ""
    masked = _SECRET_RE.sub(lambda m: m.group(0)[:2] + "***masked***", text)
    if len(masked.encode("utf-8", errors="replace")) > max_bytes:
        masked = masked[: max_bytes // 2] + " … [truncated] …"
    if not ok:
        return ToolResult(ok=False, error=masked or "tool returned nothing",
                          honesty=Honesty.FAILED)
    return ToolResult(ok=True, output=masked,
                      honesty=Honesty.DONE if activity == "passive" else Honesty.UNVERIFIED)


def bound(value: Any, ceiling: Any, kind: str = "count") -> Any:
    """Cap a value at a ceiling so nothing runs away.

    kind in {"count", "bytes", "seconds"}. Returns the ceiling when exceeded.
    Non-numeric values are returned unchanged (caller decides).
    """
    try:
        num = float(value)
        cap = float(ceiling)
    except (TypeError, ValueError):
        return value
    if num > cap:
        return ceiling
    return value


def sub_agent_fan_out(skills: list[tuple[str, dict]],
                      runner) -> list[dict[str, Any]]:
    """Run one (skill_name, args) pair per entry through `runner`.

    `runner(skill_name, args)` must return a dict with at least "ok".
    Each result is tagged with its source skill and honesty; failures are
    recorded as failed rather than dropped. One bad target cannot poison the
    batch.
    """
    results: list[dict[str, Any]] = []
    for skill_name, args in skills:
        try:
            outcome = runner(skill_name, args)
        except Exception as exc:
            results.append({
                "skill": skill_name, "args": args,
                "ok": False, "error": f"{type(exc).__name__}: {exc}",
                "honesty": "failed",
                "bounded": True,
            })
            continue
        results.append({
            "skill": skill_name, "args": args,
            "ok": bool(outcome.get("ok")) if isinstance(outcome, dict) else False,
            "output": (outcome or {}).get("summary") if isinstance(outcome, dict) else str(outcome),
            "honesty": "unverified" if isinstance(outcome, dict) and not outcome.get("ok") else "done",
            "bounded": True,
        })
    return results


__all__ = ["coerce_result", "bound", "sub_agent_fan_out"]
