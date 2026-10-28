"""agent/outcome.py - the five words a tool may claim (mark-LVI pattern).

A tool that drives something outside itself answers in one of five words, and
the model is told what each may and may not be spoken as:

* ``done``       - it happened, and it was checked - never assumed from a code
* ``unverified`` - the request went out and the result could not be confirmed
* ``failed``     - it did not happen, and here is why
* ``ask``        - nothing was done, because doing it would have been a guess
* ``started``    - it is under way; the outcome follows separately

`unverified` is never spoken as a success. That single rule is the difference
between an assistant that reports what it checked and one that reports what it
attempted.
"""

from __future__ import annotations

from typing import Any

DONE = "done"
UNVERIFIED = "unverified"
FAILED = "failed"
ASK = "ask"
STARTED = "started"

VOCABULARY = (DONE, UNVERIFIED, FAILED, ASK, STARTED)

#: How the model is allowed to speak each word aloud.
SPEAKABLE: dict[str, str] = {
    DONE: "say it happened and that you confirmed it",
    UNVERIFIED: "say you could not confirm it - do not round it up to done",
    FAILED: "say it failed and give the reason",
    ASK: "ask the user what they want instead of guessing",
    STARTED: "say it is running and you will report when it finishes",
}

SPEAKING_INSTRUCTION = (
    "Every tool that changes something outside itself reports one of: done, "
    "unverified, failed, ask, started. 'done' means you checked the result. "
    "'unverified' means the request went out but could not be confirmed - never "
    "speak it as a success."
)


def normalise(value: Any) -> str:
    """Map any value onto the vocabulary; unknown values become 'unverified'."""
    text = str(value or "").strip().lower()
    if text in VOCABULARY:
        return text
    return UNVERIFIED


def from_tool_result(ok: bool, honesty: str, confirmed: bool = True) -> str:
    """Translate a tool result into the vocabulary."""
    word = normalise(honesty)
    if not ok:
        return FAILED
    if word == DONE and not confirmed:
        return UNVERIFIED
    return word


def instruction(compact: bool = False) -> str:
    """The rule text injected into the system prompt."""
    if compact:
        return (
            "Tool outcomes are: done / unverified / failed / ask / started. "
            "Never speak 'unverified' as a success."
        )
    rows = "\n".join(f"- {word}: {SPEAKABLE[word]}" for word in VOCABULARY)
    return f"{SPEAKING_INSTRUCTION}\n{rows}"
