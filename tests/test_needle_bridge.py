"""Tests for the Needle router: schema translation, arbitration, and absence.

The bridge exists to make Needle *optional*. Every test here pins one of two
things: either a routing decision is correct, or a missing/broken engine
degrades to the main model without raising.
"""

import pytest

from agent import needle_bridge as nb
from agent import router_policy as rp

OPENAI_TOOLS = [{
    "type": "function",
    "function": {
        "name": "set_thermostat",
        "description": "Set the target temperature",
        "parameters": {"type": "object", "properties": {"temp": {"type": "integer"}}},
    },
}]


def engine_returning(envelope):
    class _Engine:
        def complete(self, prompt, max_new_tokens=512):
            return envelope
    return _Engine()


CALL = {"type": "call", "confidence": 0.93, "function_calls":
        [{"name": "set_thermostat", "arguments": {"temp": 20}}]}


# --- schema translation ----------------------------------------------------

def test_openai_envelope_becomes_needle_shape():
    got = nb.to_needle_tools(OPENAI_TOOLS)
    assert got == [{"name": "set_thermostat",
                    "description": "Set the target temperature",
                    "parameters": OPENAI_TOOLS[0]["function"]["parameters"]}]


def test_malformed_entries_are_dropped_not_forwarded():
    """Needle rejects a whole batch if one entry is malformed, so bad entries
    must be dropped - otherwise one junk tool silently costs us all of them."""
    got = nb.to_needle_tools(OPENAI_TOOLS + [
        {"type": "function"},            # no function body
        {"function": {"name": None}},    # no name
        "not a dict",                    # wrong type
        {"type": "image", "url": "x"},   # wrong kind
    ])
    assert len(got) == 1
    assert got[0]["name"] == "set_thermostat"


def test_flat_tools_are_accepted_too():
    """A caller passing Needle's own shape must not lose its tools.

    `description` is filled in when missing because Needle's loader requires
    the key, but the tool itself must survive untouched.
    """
    got = nb.to_needle_tools([{"name": "a", "parameters": {"type": "object"}}])
    assert len(got) == 1
    assert got[0]["name"] == "a"
    assert got[0]["parameters"] == {"type": "object"}
    assert "description" in got[0]


def test_empty_and_none_tool_lists():
    assert nb.to_needle_tools(None) == []
    assert nb.to_needle_tools([]) == []
