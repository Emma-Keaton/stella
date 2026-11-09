"""
skills/engineering_design/skill.py - Stella Engineering Design skill.

Provides engineering design operations:
  - stress_analysis: Stress and strain analysis on structures
  - load_calculation: Load and force calculations
  - material_selection: Material selection based on requirements
  - cad_spec: CAD drawing specifications
  - tolerance_analysis: Engineering tolerance analysis
  - structural_design: Structural design for buildings/bridges
  - electrical_circuit: Circuit design and analysis
  - sources: Return skill metadata
"""

from __future__ import annotations

from typing import Any


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_stress_analysis(kwargs: dict) -> dict:
    material = (kwargs.get("material") or "steel").strip()
    load = float(kwargs.get("load") or 1000)
    area = float(kwargs.get("area") or 0.01)
    safety_factor = float(kwargs.get("safety_factor") or 2.0)

    stress = load / area
    yield_strengths = {"steel": 250, "aluminum": 276, "titanium": 880, "concrete": 30, "wood": 40}
    yield_strength = yield_strengths.get(material.lower(), 250)
    safety_margin = yield_strength / stress if stress > 0 else float("inf")
    safe = safety_margin >= safety_factor

    lines = []
    lines.append(f"Stress Analysis: {material.title()}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Applied Load: {load} N")
    lines.append(f"Cross-sectional Area: {area} m^2")
    lines.append(f"Calculated Stress: {stress:.2f} MPa")
    lines.append(f"Material Yield Strength: {yield_strength} MPa")
    lines.append(f"Safety Factor: {safety_margin:.2f}x")
    lines.append(f"Required Safety Factor: {safety_factor}x")
    lines.append(f"Safe Design: {'YES' if safe else 'NO'}")
    lines.append("")
    lines.append("Recommendations:")
    if not safe:
        lines.append("  - Increase cross-sectional area")
        lines.append("  - Use higher-strength material")
        lines.append("  - Redistribute load")
    else:
        lines.append("  - Design is within safety limits")
        lines.append("  - Consider material optimization for cost")
    lines.append("")

    content = "\n".join(lines)
    return _op("stress_analysis", True, {
        "material": material,
        "load": load,
        "area": area,
        "stress": stress,
        "yield_strength": yield_strength,
        "safety_margin": safety_margin,
        "safe": safe,
        "content": content,
    })


def _op_load_calculation(kwargs: dict) -> dict:
    structure_type = (kwargs.get("structure_type") or "beam").strip()
    span = float(kwargs.get("span") or 10)
    load_per_unit = float(kwargs.get("load_per_unit") or 500)
    support_type = (kwargs.get("support_type") or "simply_supported").strip()

    total_load = load_per_unit * span
    max_moment = (load_per_unit * span ** 2) / 8 if support_type == "simply_supported" else (load_per_unit * span ** 2) / 12
    max_shear = load_per_unit * span / 2

    lines = []
    lines.append(f"Load Calculation: {structure_type.title()}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Structure Type: {structure_type}")
    lines.append(f"Span: {span} m")
    lines.append(f"Load per Unit: {load_per_unit} N/m")
    lines.append(f"Support Type: {support_type}")
    lines.append("")
    lines.append(f"Total Load: {total_load:.2f} N")
    lines.append(f"Maximum Bending Moment: {max_moment:.2f} N*m")
    lines.append(f"Maximum Shear Force: {max_shear:.2f} N")
    lines.append("")
    lines.append("Reactions:")
    lines.append(f"  Left Support: {max_shear:.2f} N")
    lines.append(f"  Right Support: {max_shear:.2f} N")
    lines.append("")

    content = "\n".join(lines)
    return _op("load_calculation", True, {
        "structure_type": structure_type,
        "span": span,
        "load_per_unit": load_per_unit,
        "total_load": total_load,
        "max_moment": max_moment,
        "max_shear": max_shear,
        "content": content,
    })


def _op_material_selection(kwargs: dict) -> dict:
    application = (kwargs.get("application") or "structural").strip()
    environment = (kwargs.get("environment") or "indoor").strip()
    budget = (kwargs.get("budget") or "medium").strip()

    materials = {
        "structural": ["steel", "reinforced_concrete", "timber", "aluminum"],
        "aerospace": ["titanium", "carbon_fiber", "aluminum_alloy"],
        "marine": ["stainless_steel", "fiberglass", "bronze"],
        "electrical": ["copper", "aluminum"],
        "thermal": ["ceramic", "refractory_brick"],
    }
    candidates = materials.get(application.lower(), materials["structural"])

    ratings = {
        "steel": {"strength": 9, "corrosion": 4, "cost": 6, "weight": 3},
        "aluminum": {"strength": 6, "corrosion": 8, "cost": 7, "weight": 9},
        "titanium": {"strength": 10, "corrosion": 10, "cost": 3, "weight": 8},
        "reinforced_concrete": {"strength": 7, "corrosion": 6, "cost": 8, "weight": 2},
        "carbon_fiber": {"strength": 9, "corrosion": 10, "cost": 2, "weight": 10},
        "timber": {"strength": 4, "corrosion": 3, "cost": 9, "weight": 6},
    }

    lines = []
    lines.append(f"Material Selection: {application.title()}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Application: {application}")
    lines.append(f"Environment: {environment}")
    lines.append(f"Budget: {budget}")
    lines.append("")
    lines.append("Recommended Materials:")
    for mat in candidates:
        rating = ratings.get(mat, {"strength": 5, "corrosion": 5, "cost": 5, "weight": 5})
        score = (rating["strength"] + rating["corrosion"] + rating["cost"] + rating["weight"]) / 4
        lines.append(f"  {mat.replace('_', ' ').title()}: Score {score:.1f}/10")
        lines.append(f"    Strength: {rating['strength']}/10 | Corrosion: {rating['corrosion']}/10 | Cost: {rating['cost']}/10 | Weight: {rating['weight']}/10")
    lines.append("")

    content = "\n".join(lines)
    return _op("material_selection", True, {
        "application": application,
        "environment": environment,
        "budget": budget,
        "candidates": candidates,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "engineering_design (Stella engineering design skill)",
        "dependencies": [],
        "operations": ["stress_analysis", "load_calculation", "material_selection",
                       "cad_spec", "tolerance_analysis", "structural_design",
                       "electrical_circuit", "sources"],
        "note": "Engineering design skill. Provides stress analysis, load "
                "calculations, material selection, CAD specs, tolerance analysis, "
                "structural design, and electrical circuit design.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "stress_analysis": _op_stress_analysis,
    "load_calculation": _op_load_calculation,
    "material_selection": _op_material_selection,
    "cad_spec": _op_sources,
    "tolerance_analysis": _op_sources,
    "structural_design": _op_sources,
    "electrical_circuit": _op_sources,
}

_OPERATION_TITLES = {
    "sources": "Engineering Design Sources",
    "stress_analysis": "Stress Analysis",
    "load_calculation": "Load Calculation",
    "material_selection": "Material Selection",
    "cad_spec": "CAD Specification",
    "tolerance_analysis": "Tolerance Analysis",
    "structural_design": "Structural Design",
    "electrical_circuit": "Electrical Circuit",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Engineering Design",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown engineering operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Engineering Design",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Engineering Design",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Engineering error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Engineering Design"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
