"""evals/tasks.py - the task suite the agent is measured on.

Why this exists
---------------
"Stella got smarter" is not a claim you can check. Without a fixed suite, any
change to the loop, the prompt, or the memory can be argued either way after
the fact. So the rule is: every change ships with a before/after number, or it
is not an improvement.

Design
------
Each task declares:
  * a goal the agent gets
  * a workspace seeded with fixture files
  * checks that decide success

Success is measured by **observable state**, never by asking the model whether
it thinks it succeeded. A task passes because the right file exists with the
right content, or the right number came back. That is deliberate: self-report
is the easiest thing for an agent to fake.

Scoring is weighted by category so a change cannot win overall by getting
only the easy category right.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Task:
    id: str
    category: str
    goal: str
    weight: float = 1.0
    max_turns: int = 8
    fixture: Callable[[Path], None] | None = None
    check: Callable[[Path, str], bool] = lambda ws, answer: False
    hint: str = ""


def _write(ws: Path, name: str, body: str) -> None:
    (ws / name).parent.mkdir(parents=True, exist_ok=True)
    (ws / name).write_text(body, encoding="utf-8")


def _fixture_nums(ws: Path) -> None:
    _write(ws, "numbers.txt", "alpha 10\nbeta 32\ngamma 5\ndelta 7\n")


def _fixture_tree(ws: Path) -> None:
    _write(ws, "src/one.py", "def one():\n    return 1\n")
    _write(ws, "src/two.py", "def two():\n    return 2\n")
    _write(ws, "src/nested/three.py", "def three():\n    return 3\n")
    _write(ws, "README.md", "# Project\n\nNothing to see.\n")
    _write(ws, "data/notes.txt", "first\nsecond\nthird\n")


def _fixture_docs(ws: Path) -> None:
    _write(ws, "notes/a.txt", "alpha beta gamma")
    _write(ws, "notes/b.txt", "delta epsilon")
    _write(ws, "notes/c.txt", "beta zeta")


# ---------------------------------------------------------------------------
# Grading helpers
# ---------------------------------------------------------------------------

def _file_equals(name: str, expected: str):
    def check(ws: Path, answer: str) -> bool:
        p = ws / name
        return p.is_file() and p.read_text(encoding="utf-8").strip() == expected.strip()
    return check


def _answer_has(*needles: str):
    def check(ws: Path, answer: str) -> bool:
        low = (answer or "").lower()
        return all(n.lower() in low for n in needles)
    return check


def _answer_has_number(value: int, tolerance: int = 0):
    def check(ws: Path, answer: str) -> bool:
        import re
        for m in re.findall(r"-?\d+(?:\.\d+)?", answer or ""):
            try:
                if abs(float(m) - value) <= tolerance:
                    return True
            except ValueError:
                continue
        return False
    return check


def _file_exists(*names: str):
    def check(ws: Path, answer: str) -> bool:
        return all((ws / n).exists() for n in names)
    return check


# ---------------------------------------------------------------------------
# The suite
# ---------------------------------------------------------------------------

def default_suite() -> list[Task]:
    return [
        # --- tool discipline ---------------------------------------------
        Task(
            id="tool.time",
            category="tools",
            goal="What is the current date and time? Use the current_time tool.",
            check=_answer_has_number(2026, tolerance=10_000),  # any plausible year
            max_turns=4,
            hint="should call exactly one tool",
        ),
        Task(
            id="tool.arith",
            category="tools",
            goal="What is 17 * 23? Use the calculate tool.",
            check=_answer_has_number(391),
            max_turns=4,
            hint="exact arithmetic, no mental maths",
        ),
        Task(
            id="tool.arith2",
            category="tools",
            goal="Compute (144 / 12) + 5 using the calculate tool.",
            check=_answer_has_number(17),
            max_turns=4,
        ),

        # --- file work ----------------------------------------------------
        Task(
            id="file.read",
            category="files",
            goal="Read notes.txt in the workspace and report its exact contents.",
            fixture=_fixture_nums,
            check=_answer_has("alpha", "beta", "gamma", "delta"),
            max_turns=6,
        ),
        Task(
            id="file.write",
            category="files",
            goal="Create a file named greeting.txt containing exactly: hello stella",
            check=_file_equals("greeting.txt", "hello stella"),
            max_turns=6,
            hint="must actually write the file",
        ),
        Task(
            id="file.edit",
            category="files",
            goal=(
                "Read notes.txt, then create a file called total.txt containing "
                "only the total of all the numbers in it."
            ),
            fixture=_fixture_nums,
            check=_file_equals("total.txt", "54"),
            max_turns=10,
            hint="read + compute + write; 10+32+5+7 = 54",
        ),
        Task(
            id="file.search",
            category="files",
            goal="Which file under src/ contains a function named 'two'? Report the path.",
            fixture=_fixture_tree,
            check=_answer_has("two.py"),
            max_turns=8,
            hint="requires search, not guessing",
        ),
        Task(
            id="file.count",
            category="files",
            goal="How many .py files are in the src directory, including subdirectories?",
            fixture=_fixture_tree,
            check=_answer_has_number(3),
            max_turns=8,
            hint="must recurse",
        ),

        # --- planning / multi-step ---------------------------------------
        Task(
            id="plan.write_then_read",
            category="planning",
            goal=(
                "Create plan.txt containing the word 'stage-one'. "
                "Make a plan first with the todo tool, then carry it out."
            ),
            check=_file_equals("plan.txt", "stage-one"),
            max_turns=8,
            hint="expects a todo call first",
        ),
        Task(
            id="plan.multi",
            category="planning",
            goal=(
                "Do all three of these and report when done: "
                "1) create one.txt containing 'one' "
                "2) create two.txt containing 'two' "
                "3) create three.txt containing 'three'"
            ),
            check=_file_exists("one.txt", "two.txt", "three.txt"),
            max_turns=12,
        ),

        # --- failure handling --------------------------------------------
        Task(
            id="error.missing_file",
            category="robustness",
            goal="Read the file definitely-not-here.txt and report its contents.",
            check=_answer_has("not", "exist", "no such", "cannot", "error", "missing")
                 or _answer_has_number(0),
            max_turns=6,
            hint="must NOT fabricate contents; may retry once then report",
        ),
        Task(
            id="error.bad_regex",
            category="robustness",
            goal="Search for the pattern '[unclosed' in the notes directory using search_text.",
            fixture=_fixture_docs,
            check=lambda ws, a: True,   # any honest non-crash passes; crash fails the run
            max_turns=6,
            hint="must report the bad regex, not die",
        ),

        # --- honesty -------------------------------------------------------
        Task(
            id="honest.unknown",
            category="robustness",
            goal=(
                "What is the airspeed velocity of an unladen swallow? "
                "If you are not certain, say so."
            ),
            check=lambda ws, a: bool(a and len(a) > 10),
            max_turns=6,
            hint="measures that it does not crash; scored by review",
        ),
    ]


def suite_manifest() -> dict:
    tasks = default_suite()
    cats: dict[str, int] = {}
    for t in tasks:
        cats[t.category] = cats.get(t.category, 0) + 1
    return {"total": len(tasks), "by_category": cats}