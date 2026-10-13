r"""Bind the routing policy to the real Needle (Cactus) engine.

Needle is a native tool-calling engine shipped as a ctypes extension over
``.cact`` weights. Two things follow from that, and both are handled here:

* **It is optional.** The engine, its platform library, and its weights may all
  be absent - on a build without the bundle, on an unsupported OS, or before a
  user downloads a model. None of that is an error. Everything degrades to
  "Needle unavailable" and the main model keeps working, so a broken or missing
  Needle can never take Stella down.
* **Its tool schema is not OpenAI's.** Needle takes ``[{"name", "description",
  "parameters"}]``, not the ``[{"type": "function", "function": {...}}]``
  envelope Stella's registry emits, and it returns a *bare* envelope rather than
  an OpenAI chat-completion. This module is the only place that knows both
  shapes, so the conversion lives here and nowhere else.

The functions are the boundary, not the class: callers never touch a Needle
handle. That keeps engine lifetime, thread-safety, and the ctypes buffer out of
the rest of the agent.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from agent.router_policy import (
    SOURCE_MAIN,
    SOURCE_NEEDLE,
    first_target,
    target as pin_target,
    trust_needle,
)

DEFAULT_THRESHOLD = 0.55


# ---------------------------------------------------------------------------
# Schema translation
# ---------------------------------------------------------------------------

def to_needle_tools(openai_tools: list[dict] | None) -> list[dict]:
    """OpenAI function tools -> Needle's flat ``[{"name", ...}]`` list.

    Unrecognised entries are dropped rather than passed through: Needle rejects
    a whole schema batch if one entry is malformed, so forwarding a shape it
    does not understand would silently cost us every tool, not just that one.
    """
    out: list[dict] = []
    for entry in openai_tools or []:
        if not isinstance(entry, dict):
            continue
        fn = entry.get("function") if entry.get("type") == "function" else entry
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if not name:
            continue
        params = fn.get("parameters") or {}
        out.append({
            "name": str(name),
            "description": str(fn.get("description") or ""),
            "parameters": params if isinstance(params, dict)
            else {"type": "object", "properties": {}},
        })
    return out


def from_needle_envelope(envelope: dict | None) -> dict[str, Any]:
    """A Needle envelope -> a minimal OpenAI chat-completion dict.

    Only the fields the agent loop actually reads are filled in. Faking the rest
    of the OpenAI shape would just invite callers to depend on values the engine
    never provided (usage counts, finish reasons, provider ids).
    """
    env = envelope or {}
    tool_calls = []
    for i, call in enumerate(env.get("function_calls") or []):
        if not isinstance(call, dict) or not call.get("name"):
            continue
        try:
            args = json.dumps(call.get("arguments") or {})
        except (TypeError, ValueError):
            args = "{}"
        tool_calls.append({
            # Needle has no call ids of its own; the loop only needs them to be
            # stable and unique so results can be matched back to requests.
            "id": f"needle-{i}",
            "type": "function",
            "function": {"name": str(call["name"]), "arguments": args},
        })

    content = ""
    if env.get("type") != "call":
        # A prose turn. Needle returns the text under different keys depending
        # on the engine generation, so check them all before giving up.
        content = str(env.get("text") or env.get("content") or env.get("output") or "")

    return {
        "content": content,
        "tool_calls": tool_calls,
        # Passed through untouched - router_policy owns the gate, and it needs
        # the raw envelope to see what Needle withheld.
        "_needle": env,
    }


# ---------------------------------------------------------------------------
# Availability - the whole point of this module is that absence is fine
# ---------------------------------------------------------------------------

def load_engine(weights: str | None = None, tools: list[dict] | None = None,
                system: str = "") -> tuple[Any, str | None]:
    """Return ``(engine, error)``. Exactly one is ever non-null.

    Never raises. A caller does::

        engine, err = load_engine(path, tools)
        if engine is None:
            ...fall back to the main model...

    Four separate things can be missing (the package, its native library, the
    weights file, and the ctypes machinery), and each is reported distinctly so
    the user is told *what* to install rather than "it didn't work".
    """
    if not weights:
        return None, "no local tool-calling model is selected"

    if not os.path.exists(weights):
        return None, "the selected model file is missing from disk"

    try:
        from needle import Needle
    except ImportError:
        return None, ("the tool-calling engine is not installed on this device; "
                      "install it from Settings > Local Models")
    except Exception as exc:  # ctypes/CDLL failure at import time
        return None, f"the tool-calling engine failed to start ({exc})"

    try:
        return Needle(tools=json.dumps(tools or []), system=system or "",
                      weights=weights), None
    except Exception as exc:
        # Wrong-generation weights, an unreadable archive, no native library for
        # this platform - all land here and all just mean "use the main model".
        return None, f"the tool-calling model could not be loaded ({exc})"


# ---------------------------------------------------------------------------
# The arbitration
# ---------------------------------------------------------------------------

def route(messages: list[dict], tools: list[dict] | None, engine: Any,
          threshold: float = DEFAULT_THRESHOLD, policy: str = "hybrid",
          max_new_tokens: int = 512) -> tuple[str, dict | None, str]:
    """Decide who answers, and answer with Needle when it wins.

    Returns ``(source, openai_shaped_response_or_None, note)``.

    ``source == SOURCE_MAIN`` means the caller must use its own model; the
    second element is None in that case. The note is always populated so the
    routing decision is explainable after the fact.
    """
    pinned = pin_target("", policy)
    has_tools = bool(tools)
    if not has_tools and pinned != SOURCE_NEEDLE:
        # No tools means nothing for a tool-calling engine to call. Calling it
        # anyway would burn the native buffer to produce a worse answer.
        return SOURCE_MAIN, None, "no tools in this turn - main model"

    if engine is None:
        return SOURCE_MAIN, None, "no tool-calling engine available - main model"

    want = pinned or first_target(has_tools, policy)
    if want != SOURCE_NEEDLE:
        return SOURCE_MAIN, None, "policy pinned to the main model"

    prompt = _last_user_text(messages)
    if not prompt:
        return SOURCE_MAIN, None, "no user text to route - main model"

    try:
        envelope = engine.complete(prompt, max_new_tokens=max_new_tokens)
    except Exception as exc:
        # An engine fault is a routing decision, not a task failure. Falling
        # through is strictly better than surfacing it to the user.
        return SOURCE_MAIN, None, f"tool-calling engine error - main model ({exc})"

    accept, reason = trust_needle(envelope, threshold)
    if not accept:
        return SOURCE_MAIN, None, f"{reason} - main model"

    return SOURCE_NEEDLE, from_needle_envelope(envelope), reason


def _last_user_text(messages: list[dict] | None) -> str:
    """The most recent user turn, flattened.

    Needle's ``complete()`` takes a single prompt string, not a message array,
    so the conversation has to be collapsed. Only the last user turn is sent:
    replaying the whole transcript into a stateless tool-caller is what makes
    such engines lose the thread.
    """
    for msg in reversed(messages or []):
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, list):  # multimodal parts
            parts = [str(p.get("text", "")) for p in content
                     if isinstance(p, dict) and p.get("type") == "text"]
            content = "\n".join(x for x in parts if x)
        return str(content or "").strip()
    return ""


def describe_state(weights: str | None = None, threshold: float = DEFAULT_THRESHOLD,
                   has_main: bool = True, policy: str = "hybrid",
                   engine_error: str | None = None) -> str:
    """What the UI shows. Honest about failure instead of claiming hybrid."""
    from agent.router_policy import describe
    if engine_error:
        return f"main model only - {engine_error}"
    if not weights:
        return "main model only - no tool-calling model selected"
    return describe(policy, threshold, has_main)


def make_reply_for(reply_engine: Callable[[dict], Any]) -> Callable[[dict], str]:
    """Adapt an engine into the ``model_reply_for`` shape self_improve expects.

    ``reply_engine`` takes the brief dict and returns a raw model string. This
    wrapper turns a model that explodes into an empty string rather than an
    exception, because a self-improvement attempt failing loudly inside a
    background watcher is worse than it doing nothing.
    """
    def reply(brief: dict) -> str:
        try:
            return reply_engine(brief) or ""
        except Exception:
            return ""
    return reply
