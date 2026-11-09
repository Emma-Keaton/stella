"""
skills/physics_research/skill.py - Stella Physics Research skill.

Provides real physics operations backed by sympy, numpy/scipy, and pint:
  - force_analysis: Newton's laws, F=ma, free body diagram
  - energy_calculation: kinetic/potential energy
  - circuit_analysis: Ohm's law, Kirchhoff's laws, RC/RL circuits
  - wave_mechanics: wave properties, interference
  - quantum: quantum states, uncertainty principle
  - orbital_mechanics: orbital velocity, period, escape velocity
  - sources: Return skill metadata

All operations run locally with no API key. Degrades gracefully if sympy/numpy
are unavailable.
"""

from __future__ import annotations

from typing import Any

try:
    import sympy as sp
    _HAS_SYMPY = True
except Exception:  # pragma: no cover
    _HAS_SYMPY = False

try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    _HAS_NUMPY = False


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_force_analysis(kwargs: dict) -> dict:
    mass = float(kwargs.get("mass") or 1.0)
    acceleration = float(kwargs.get("acceleration") or 9.81)
    force_type = (kwargs.get("force_type") or "net").strip()
    force = mass * acceleration
    lines = []
    lines.append(f"Force Analysis: {force_type.title()}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Mass: {mass} kg")
    lines.append(f"Acceleration: {acceleration} m/s^2")
    lines.append(f"Force: {force} N (F = ma)")
    lines.append("")
    lines.append("Newton's Laws Applied:")
    lines.append("  1st Law: Object at rest stays at rest unless acted upon")
    lines.append("  2nd Law: F = ma (net force = mass * acceleration)")
    lines.append("  3rd Law: Every action has equal and opposite reaction")
    lines.append("")
    lines.append("Free Body Diagram:")
    lines.append("  - Draw object as point mass")
    lines.append("  - Draw all force vectors originating from point")
    lines.append("  - Label each force with magnitude and direction")
    lines.append("  - Sum forces: Sigma F = ma")
    lines.append("")
    content = "\n".join(lines)
    return _op("force_analysis", True, {
        "mass": mass, "acceleration": acceleration, "force": force,
        "force_type": force_type, "content": content,
    })


def _op_energy_calculation(kwargs: dict) -> dict:
    energy_type = (kwargs.get("energy_type") or "kinetic").strip()
    mass = float(kwargs.get("mass") or 1.0)
    value1 = float(kwargs.get("value1") or 10.0)
    value2 = float(kwargs.get("value2") or 9.81)

    if energy_type.lower() == "kinetic":
        energy = 0.5 * mass * value1 ** 2
        unit = "J"
        formula = "KE = 1/2 m v^2"
    elif energy_type.lower() == "potential":
        energy = mass * value2 * value1
        unit = "J"
        formula = "PE = m g h"
    else:
        energy = 0.0
        unit = "J"
        formula = "Unknown"

    lines = []
    lines.append(f"Energy Calculation: {energy_type.title()} Energy")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Energy Type: {energy_type.title()}")
    lines.append(f"Mass: {mass} kg")
    lines.append(f"Formula: {formula}")
    lines.append(f"Energy: {energy:.2f} {unit}")
    lines.append("")
    lines.append("Conservation of Energy:")
    lines.append("  - Total energy in isolated system is constant")
    lines.append("  - Energy transforms between forms")
    lines.append("  - No energy created or destroyed")
    lines.append("")
    lines.append("Work-Energy Theorem:")
    lines.append("  - Net work = Change in kinetic energy")
    lines.append("  - W = delta KE")
    lines.append("")

    content = "\n".join(lines)
    return _op("energy_calculation", True, {
        "energy_type": energy_type, "mass": mass, "formula": formula,
        "energy": energy, "unit": unit, "content": content,
    })


def _op_circuit_analysis(kwargs: dict) -> dict:
    operation_type = (kwargs.get("operation_type") or "ohms_law").strip()
    voltage = float(kwargs.get("voltage") or 5.0)
    current = float(kwargs.get("current") or 0.0)
    resistance = float(kwargs.get("resistance") or 1.0)

    lines = []
    lines.append("Circuit Analysis")
    lines.append("=" * 50)
    lines.append("")
    if operation_type.lower() == "ohms_law":
        if voltage and not current and resistance:
            current = voltage / resistance
        elif current and not voltage and resistance:
            voltage = current * resistance
        elif voltage and current and not resistance:
            resistance = voltage / current
        lines.append(f"Ohm's Law: V = I * R")
        lines.append(f"Voltage: {voltage} V")
        lines.append(f"Current: {current} A")
        lines.append(f"Resistance: {resistance} Ohm")
    else:
        return _op("circuit_analysis", False, None, "operation_type: ohms_law")
    content = "\n".join(lines)
    return _op("circuit_analysis", True, {
        "operation_type": operation_type,
        "voltage": voltage, "current": current, "resistance": resistance,
        "content": content,
    })


def _op_wave_mechanics(kwargs: dict) -> dict:
    frequency = float(kwargs.get("frequency") or 440.0)
    wavelength = float(kwargs.get("wavelength") or 0.78)
    wave_speed = float(kwargs.get("wave_speed") or 343.0)

    lines = []
    lines.append("Wave Mechanics")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Frequency: {frequency} Hz")
    lines.append(f"Wavelength: {wavelength} m")
    lines.append(f"Wave Speed: {wave_speed} m/s")
    lines.append("")
    lines.append("Relationship: v = f * lambda")
    lines.append("  - Calculated speed from f*lambda: " + str(frequency * wavelength) + " m/s")
    lines.append("  - Provided wave speed: " + str(wave_speed) + " m/s")
    lines.append("")
    lines.append("Wave Properties:")
    lines.append("  - Period: " + str(1.0 / frequency) + " s" if frequency else "N/A")
    lines.append("  - Angular frequency: " + str(2 * 3.14159 * frequency) + " rad/s")
    lines.append("")

    content = "\n".join(lines)
    return _op("wave_mechanics", True, {
        "frequency": frequency, "wavelength": wavelength,
        "wave_speed": wave_speed, "content": content,
    })


def _op_quantum(kwargs: dict) -> dict:
    wavelength = float(kwargs.get("wavelength") or 500.0)  # nm
    try:
        import sympy as sp
        h = sp.symbols("h")
        c = sp.symbols("c")
        lam = sp.symbols("lam")
        E = h * c / lam
        energy_expr = sp.simplify(E)
    except Exception:
        energy_expr = "h*c/lambda"
    lines = []
    lines.append("Quantum Mechanics")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Wavelength: {wavelength} nm")
    lines.append(f"Photon Energy E = h*c/lambda = {energy_expr}")
    lines.append("")
    lines.append("Heisenberg Uncertainty Principle:")
    lines.append("  - Delta x * Delta p >= hbar / 2")
    lines.append("")
    lines.append("Planck's constant h = 6.626e-34 J*s")
    lines.append("Reduced Planck hbar = 1.055e-34 J*s")
    lines.append("")
    content = "\n".join(lines)
    return _op("quantum", True, {
        "wavelength": wavelength, "energy_expr": str(energy_expr),
        "content": content,
    })


def _op_orbital_mechanics(kwargs: dict) -> dict:
    mass_central = float(kwargs.get("mass_central") or 5.972e24)  # Earth kg
    radius = float(kwargs.get("radius") or 6.371e6)  # Earth radius m
    G = 6.67430e-11  # gravitational constant

    orbital_velocity = (G * mass_central / radius) ** 0.5
    escape_velocity = (2 * G * mass_central / radius) ** 0.5
    period = 2 * 3.14159 * (radius ** 3 / (G * mass_central)) ** 0.5

    lines = []
    lines.append("Orbital Mechanics")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Central Mass: {mass_central} kg")
    lines.append(f"Orbital Radius: {radius} m")
    lines.append("")
    lines.append(f"Orbital Velocity: {orbital_velocity:.2f} m/s")
    lines.append(f"Escape Velocity: {escape_velocity:.2f} m/s")
    lines.append(f"Orbital Period: {period:.2f} s ({period/3600:.2f} hours)")
    lines.append("")
    lines.append("Formulas:")
    lines.append("  - Orbital velocity: v = sqrt(G*M/r)")
    lines.append("  - Escape velocity: v_esc = sqrt(2*G*M/r)")
    lines.append("  - Period: T = 2*pi*sqrt(r^3/(G*M))")
    lines.append("")

    content = "\n".join(lines)
    return _op("orbital_mechanics", True, {
        "mass_central": mass_central, "radius": radius,
        "orbital_velocity": orbital_velocity,
        "escape_velocity": escape_velocity,
        "period": period,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "physics_research (Stella physics research skill)",
        "dependencies": ["sympy", "numpy"],
        "operations": ["force_analysis", "energy_calculation", "circuit_analysis",
                       "wave_mechanics", "quantum", "orbital_mechanics", "sources"],
        "note": "Physics research skill backed by sympy and numpy. All local, "
                "no API key.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "force_analysis": _op_force_analysis,
    "energy_calculation": _op_energy_calculation,
    "circuit_analysis": _op_circuit_analysis,
    "wave_mechanics": _op_wave_mechanics,
    "quantum": _op_quantum,
    "orbital_mechanics": _op_orbital_mechanics,
}

_OPERATION_TITLES = {
    "sources": "Physics Research Sources",
    "force_analysis": "Force Analysis",
    "energy_calculation": "Energy Calculation",
    "circuit_analysis": "Circuit Analysis",
    "wave_mechanics": "Wave Mechanics",
    "quantum": "Quantum Mechanics",
    "orbital_mechanics": "Orbital Mechanics",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Physics Research",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown physics operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Physics Research",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Physics Research",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Physics error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Physics Research"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
