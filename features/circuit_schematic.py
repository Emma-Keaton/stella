"""
Feature: Holographic Hardware Assembler & Interactive Circuit HUD
Description: Analyzes electronic components on screen or from voice, resolves pin-to-pin wiring,
and launches the interactive Holographic Circuit HUD display.
Uses theme tokens from themes.json (no hardcoded colours). Gracefully degrades when the circuit assembler is unavailable.
"""

from typing import Any, Dict

FEATURE_METADATA = {
    "name": "circuit_schematic",
    "aliases": ["circuit_assembler", "hardware_assembler", "arduino_circuit", "circuit_wiring", "circuit_hud"],
    "description": (
        "Analyzes electronic components (Arduino, ESP32, sensors, actuators, resistors) on screen or from voice, "
        "calculates pin-to-pin wiring diagrams, safety warnings, and step-by-step assembly guides, "
        "and displays the interactive Holographic Circuit HUD. Reports unavailability when the circuit assembler "
        "backend cannot be loaded."
    ),
    "triggers": [
        "see the arduino parts on my screen",
        "how to assemble these arduino parts",
        "how to connect these parts",
        "how to assemble it",
        "how to assemble these",
        "show circuit diagram",
        "show wiring diagram",
        "assemble circuit",
        "wire arduino",
        "how to connect arduino",
        "connect dht11 to arduino",
        "connect ultrasonic sensor to arduino",
        "connect servo to arduino",
        "circuit schematic",
        "hardware wiring diagram",
        "circuit assembler",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "analyze_screen | assemble_components | show_schematic (default: assemble_components)",
            },
            "components": {
                "type": "STRING",
                "description": "Comma-separated list or description of electronic components (e.g. 'Arduino Pro Mini, DHT11, 10k resistor')",
            },
            "query": {
                "type": "STRING",
                "description": "Specific project goal or wiring instructions (e.g. 'how to connect humidity sensor to arduino')",
            },
        },
    },
}


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _load_circuit_assembler():
    """Load the circuit assembler defensively."""
    try:
        from actions.circuit_assembler import circuit_assembler
        return circuit_assembler, None
    except Exception as exc:
        return None, exc


def execute(**kwargs) -> Dict[str, Any]:
    """Executes Circuit Assembler action and returns the formatted result."""
    circuit_assembler, load_error = _load_circuit_assembler()

    if circuit_assembler is None:
        return {
            "title": "Circuit Assembler Unavailable",
            "summary": (
                "The circuit assembler backend could not be loaded on this machine. "
                "Install/configure the circuit assembler integration to enable hardware wiring analysis."
            ),
            "spoken_narrative": "Circuit assembler is not available on this machine.",
            "error": str(load_error) if load_error else "backend not available",
        }

    action = kwargs.get("action", "assemble_components")
    components = kwargs.get("components", "")
    query = kwargs.get("query", "")

    player = kwargs.get("player")
    speak = kwargs.get("speak")
    try:
        return circuit_assembler(action=action, components=components, query=query, player=player, speak=speak)
    except Exception as exc:
        return {
            "title": "Circuit Assembler Error",
            "summary": f"Circuit assembler action '{action}' failed: {exc}",
            "spoken_narrative": f"Circuit assembler action {action} failed.",
            "error": str(exc),
        }
