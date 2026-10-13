r"""Routing policy: which engine answers a request, and when Needle is trusted.

Pure functions only - no I/O, no engine handles, no network. That keeps the
decision logic testable in isolation and identical whether it is called from
the desktop chain or from a bundled build.

Origin
------
Vendored and adapted from the author's `tandem` project
(E:\Projects\tandem, ``tandem/policy.py``), which was written to arbitrate
between a Needle tool-calling engine and a general coder model. The control
flow, the confidence gate and the acceptance rules are that project's; this
file renames the aliases to Stella's naming and drops the upstream-only model
ids.

Why a gate at all: a small tool-calling engine is fast and cheap, but it is
also the thing most likely to confidently call the wrong tool. So its output is
never trusted on faith - it is accepted only when it actually produced a call,
did not withhold anything, and cleared a confidence threshold. Every refusal
and every low-confidence turn falls through to the main model.

Policies
--------
* ``hybrid`` (default) - a request carrying tools goes to Needle first;
  everything else goes straight to the main model.
* ``needle`` / ``qwen`` - pin one side, no arbitration.
"""

from __future__ import annotations

SOURCE_NEEDLE = "needle"
SOURCE_MAIN = "main"

# Stella's model ids, so a caller can name an engine explicitly.
ALIAS_AUTO = "stella"
ALIAS_COMBO = "stella-combo"
ALIAS_NEEDLE = "stella-needle"
ALIAS_MAIN = "stella-main"
ALIAS_EMBED = "stella-embed"

MODEL_IDS = [ALIAS_AUTO, ALIAS_COMBO, ALIAS_MAIN, ALIAS_NEEDLE, ALIAS_EMBED]

NEEDLE_POLICIES = ("needle", "needle-only", "needle_first")
MAIN_POLICIES = ("main", "main-only", "coder")


def target(model_id: str, policy_name: str = "hybrid") -> str | None:
    """A pinned source, or None when the policy must decide per request."""
    name = str(model_id or "").strip().lower()
    if name.startswith((f"{ALIAS_NEEDLE}", "needle")):
        return SOURCE_NEEDLE
    if name.startswith((f"{ALIAS_MAIN}", "main", "qwen", "tandem-qwen")):
        return SOURCE_MAIN
    if policy_name in NEEDLE_POLICIES:
        return SOURCE_NEEDLE
    if policy_name in MAIN_POLICIES:
        return SOURCE_MAIN
    return None


def first_target(has_tools: bool, policy_name: str = "hybrid") -> str:
    """Which engine answers first in hybrid mode."""
    if policy_name in NEEDLE_POLICIES:
        return SOURCE_NEEDLE
    if policy_name in MAIN_POLICIES:
        return SOURCE_MAIN
    # Tool-calling is the one job Needle is genuinely better at, so only take
    # that lane away from the main model. Prose stays with the main model.
    return SOURCE_NEEDLE if has_tools else SOURCE_MAIN


def trust_needle(envelope: dict, threshold: float) -> tuple[bool, str]:
    """(accept, reason) for one Needle envelope in hybrid mode.

    This is the whole safety story in one function, so every reason a call gets
    rejected is visible here rather than scattered through the call path.
    """
    if not isinstance(envelope, dict):
        return False, "needle returned no envelope"
    if envelope.get("type") != "call":
        return False, "needle finished the turn without a call"
    calls = envelope.get("function_calls") or []
    if not calls:
        # A refusal. Falling through lets the main model answer properly
        # instead of surfacing an empty tool call.
        return False, "needle made no call (refusal)"
    if envelope.get("suppressed_calls"):
        return False, "needle withheld a call"
    confidence = envelope.get("confidence")
    if confidence is None:
        # A fine-tuned archive with no calibrated head: the call is all we
        # have. Tandem accepted this case, and so do we.
        return True, "needle call accepted (no calibrated confidence)"
    if confidence < float(threshold):
        return False, "needle confidence %.2f below the %.2f gate" % (
            confidence, float(threshold))
    return True, "needle call accepted (confidence %.2f)" % confidence


def describe(policy_name: str, threshold: float, has_main: bool) -> str:
    """A one-line description for the UI, so the routing is never a mystery."""
    if not has_main:
        return "needle only (no main model loaded)"
    if policy_name in NEEDLE_POLICIES:
        return "needle first, main model fallback"
    if policy_name in MAIN_POLICIES:
        return "main model only"
    return ("hybrid: needle for tool calls (confidence >= %.2f), "
            "main model otherwise" % threshold)
