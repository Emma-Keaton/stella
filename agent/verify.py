"""agent/verify.py - check a claimed result before we believe it.

The failure mode this prevents
------------------------------
An agent that says "done" because it stopped talking is not an agent, it is a
confident narrator. The loop currently accepts the model's final text as proof
of success. Self-report is the single easiest thing for a model to fabricate -
and the eval suite exists precisely because we do not trust it.

What this does
--------------
Given the goal, the tools that ran, and the final answer, it derives cheap
*observable* checks and runs them. Only these:

  * every tool call errored out            -> the task almost certainly failed
  * the goal was to create/write a file    -> did that file actually appear?
  * the goal was to read a named file      -> does it exist?
  * the goal asked for a number            -> is a number present in the answer?
  * nothing ran but the goal demanded action -> it only described, it did not do

It never asks a model whether it succeeded. Every check is a fact about the
filesystem, the tool log, or the answer's shape.

The result is a verdict plus a correction prompt, so the loop can hand the
failure back to the model and let it retry inside the remaining turn budget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Verdict:
    ok: bool
    confidence: float = 1.0
    reasons: list[str] = field(default_factory=list)
    correction: str = ""

    def describe(self) -> str:
        if self.ok:
            return "verified"
        return "NOT verified: " + "; ".join(self.reasons)


_WRITE_GOALS = re.compile(
    r"\b(create|write|save|make|generate|build|add)\b", re.IGNORECASE
)
_READ_GOALS = re.compile(
    r"\b(read|open|show me|cat\b|contents of)\b", re.IGNORECASE
)
_NUMBER_GOALS = re.compile(
    r"\b(total|sum|count|how many|average|calculate|what is \d)\b", re.IGNORECASE
)
# Filenames/paths only. No spaces: a goal reads "create file hello.txt", and
# allowing spaces made the pattern swallow the verbs along with the name.
_FILE_RE = re.compile(r"\b([A-Za-z0-9_\-./\\]*[A-Za-z0-9_\-][A-Za-z0-9_\-./\\]*\.[A-Za-z0-9]{1,8})\b")
_COMMON_EXT = {
    "txt", "md", "py", "json", "csv", "log", "cfg", "ini", "yaml", "yml",
    "html", "css", "js", "png", "jpg", "pdf", "docx", "xlsx", "gguf",
}


def verify(goal: str, answer: str, tool_calls: list[dict],
           errors: list[str], workspace: Path | None = None) -> Verdict:
    """Run observable checks over one completed agent run."""
    reasons: list[str] = []
    answer = (answer or "").strip()
    successful_calls = [c for c in tool_calls if c.get("ok")]

    # 1. Total tool failure is an unambiguous failure.
    if tool_calls and not successful_calls:
        reasons.append("every tool call failed")
        return Verdict(False, 1.0, reasons,
                       "Every tool you used failed. Read the errors and try a "
                       "different approach, or explain clearly what blocked you.")

    # 2. The goal demanded a write; did a file actually appear?
    if _WRITE_GOALS.search(goal or ""):
        written = [c for c in successful_calls if c["name"] in
                   ("write_file", "file_controller", "claude_code")]
        if not written and workspace is not None:
            # Fall back to observable state: any new file in the workspace?
            try:
                before = set(workspace.rglob("*"))
                if not any(p.is_file() for p in before):
                    reasons.append(
                        "the goal asked to create something but no file exists "
                        "in the workspace and no write tool was used")
            except Exception:
                pass
        if not written and not reasons:
            reasons.append("goal looked like a write but no write tool ran")

    # 3. The goal named a file; make sure it exists.
    if workspace is not None:
        for name in _FILE_RE.findall(goal or ""):
            # Only act on things that really look like files the task concerns.
            if name.rsplit(".", 1)[-1].lower() not in _COMMON_EXT:
                continue
            candidate = (workspace / name.strip()).resolve()
            try:
                candidate.relative_to(workspace.resolve())
                in_scope = True
            except ValueError:
                in_scope = False
            if in_scope and not candidate.exists():
                reasons.append(f"the goal mentions {name} but it does not exist")

    # 4. The goal asked for a number and the answer contains none.
    if _NUMBER_GOALS.search(goal or "") and successful_calls:
        if not re.search(r"-?\d+(?:\.\d+)?", answer):
            reasons.append("a numeric answer was requested but none was given")

    # 5. Nothing happened for an action request.
    if not tool_calls and _WRITE_GOALS.search(goal or ""):
        reasons.append("the goal asked for action but no tool was used")
        return Verdict(False, 0.9, reasons,
                       "You described the task but did not perform it. Use the "
                       "available tools to actually do it, then report the result.")

    # 6. Empty answer.
    if not answer:
        reasons.append("no final answer was produced")

    if reasons:
        return Verdict(False, 0.8, reasons,
                       "Before finishing: " + "; ".join(reasons) +
                       ". Fix this, or state plainly what you could not do.")
    return Verdict(True)


def summarise(verdicts: list[Verdict]) -> dict:
    """Aggregate verdicts across an eval run."""
    total = len(verdicts)
    ok = sum(1 for v in verdicts if v.ok)
    return {
        "verified": ok,
        "total": total,
        "rate": round(ok / total, 3) if total else 0.0,
    }