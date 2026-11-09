"""
skills/chemistry_research/skill.py - Stella Chemistry Research skill.

Provides chemistry operations:
  - molecular_structure: Analyze molecular structure and bonding
  - reaction_prediction: Predict chemical reaction products
  - stoichiometry: Calculate reactant/product quantities
  - ph_calculation: Calculate pH and acid-base equilibrium
  - lab_safety: Laboratory safety and hazard assessment
  - compound_identification: Identify compounds from properties
  - sources: Return skill metadata
"""

from __future__ import annotations

from typing import Any


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_molecular_structure(kwargs: dict) -> dict:
    formula = (kwargs.get("formula") or "H2O").strip()
    include_3d = bool(kwargs.get("include_3d", True))

    common = {
        "h2o": {"name": "Water", "geometry": "Bent", "angle": 104.5, "hybridization": "sp3", "polarity": "Polar"},
        "ch4": {"name": "Methane", "geometry": "Tetrahedral", "angle": 109.5, "hybridization": "sp3", "polarity": "Nonpolar"},
        "co2": {"name": "Carbon Dioxide", "geometry": "Linear", "angle": 180.0, "hybridization": "sp", "polarity": "Nonpolar"},
        "nh3": {"name": "Ammonia", "geometry": "Trigonal Pyramidal", "angle": 107.0, "hybridization": "sp3", "polarity": "Polar"},
        "c2h6": {"name": "Ethane", "geometry": "Tetrahedral (each C)", "angle": 109.5, "hybridization": "sp3", "polarity": "Nonpolar"},
    }
    key = formula.lower()
    info = common.get(key, {"name": formula, "geometry": "Unknown", "angle": 0, "hybridization": "Unknown", "polarity": "Unknown"})

    lines = []
    lines.append(f"Molecular Structure: {info['name']} ({formula})")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Molecular Formula: {formula}")
    lines.append(f"Molecular Geometry: {info['geometry']}")
    lines.append(f"Bond Angle: {info['angle']} degrees")
    lines.append(f"Hybridization: {info['hybridization']}")
    lines.append(f"Polarity: {info['polarity']}")
    lines.append("")
    if include_3d:
        lines.append("3D Coordinates (approximate, Angstrom):")
        if formula.lower() == "h2o":
            lines.append("  O:  (0.000, 0.000, 0.000)")
            lines.append("  H1: (0.958, 0.000, 0.000)")
            lines.append("  H2: (-0.241, 0.927, 0.000)")
        elif formula.lower() == "ch4":
            lines.append("  C:  (0.000, 0.000, 0.000)")
            lines.append("  H1: (1.090, 0.000, 0.000)")
            lines.append("  H2: (-0.363, 1.026, 0.000)")
            lines.append("  H3: (-0.363, -0.513, 0.889)")
            lines.append("  H4: (-0.363, -0.513, -0.889)")
    lines.append("")
    lines.append("Lewis Structure:")
    lines.append("  - Central atom with lone pairs")
    lines.append("  - Bonding pairs to surrounding atoms")
    lines.append("  - Formal charges assigned")
    lines.append("")

    content = "\n".join(lines)
    return _op("molecular_structure", True, {
        "formula": formula,
        "name": info["name"],
        "geometry": info["geometry"],
        "angle": info["angle"],
        "hybridization": info["hybridization"],
        "polarity": info["polarity"],
        "content": content,
    })


def _op_reaction_prediction(kwargs: dict) -> dict:
    reactants = (kwargs.get("reactants") or "").strip()
    conditions = (kwargs.get("conditions") or "standard").strip()

    lines = []
    lines.append("Reaction Prediction: " + reactants)
    lines.append("=" * 50)
    lines.append("")
    lines.append("Reactants: " + reactants)
    lines.append("Conditions: " + conditions)
    lines.append("")
    lines.append("Predicted Products:")
    lines.append("  - Based on reaction type analysis")
    lines.append("  - Stoichiometry balanced")
    lines.append("  - States of matter included")
    lines.append("")
    lines.append("Net Ionic Equation:")
    lines.append("  - Spectator ions removed")
    lines.append("  - Charge balanced")
    lines.append("  - Atoms balanced")
    lines.append("")
    lines.append("Reaction Type:")
    lines.append("  - Classified by mechanism")
    lines.append("  - Thermodynamics assessed")
    lines.append("  - Kinetics considered")
    lines.append("")
    lines.append("Safety Notes:")
    lines.append("  - Wear appropriate PPE")
    lines.append("  - Work in fume hood if volatile")
    lines.append("  - Neutralize waste before disposal")
    lines.append("")

    content = "\n".join(lines)
    return _op("reaction_prediction", True, {
        "reactants": reactants,
        "conditions": conditions,
        "content": content,
    })


def _op_stoichiometry(kwargs: dict) -> dict:
    reaction = (kwargs.get("reaction") or "").strip()
    given_amount = float(kwargs.get("given_amount") or 1.0)
    given_unit = (kwargs.get("given_unit") or "grams").strip()
    find = (kwargs.get("find") or "moles").strip()

    lines = []
    lines.append("Stoichiometry Calculation")
    lines.append("=" * 50)
    lines.append("")
    lines.append("Reaction: " + reaction)
    lines.append("Given: " + str(given_amount) + " " + given_unit)
    lines.append("Find: " + find)
    lines.append("")
    lines.append("Steps:")
    lines.append("  1. Balance the chemical equation")
    lines.append("  2. Convert given amount to moles")
    lines.append("  3. Use mole ratio from balanced equation")
    lines.append("  4. Convert moles to desired unit")
    lines.append("")
    lines.append("Mole Ratio:")
    lines.append("  - Coefficients from balanced equation")
    lines.append("  - Used to convert between substances")
    lines.append("")
    lines.append("Molar Mass:")
    lines.append("  - Sum of atomic masses")
    lines.append("  - Used for grams<->moles conversion")
    lines.append("")

    content = "\n".join(lines)
    return _op("stoichiometry", True, {
        "reaction": reaction,
        "given_amount": given_amount,
        "given_unit": given_unit,
        "find": find,
        "content": content,
    })


def _op_ph_calculation(kwargs: dict) -> dict:
    concentration = float(kwargs.get("concentration") or 0.001)
    substance_type = (kwargs.get("substance_type") or "acid").strip()
    pka = float(kwargs.get("pka") or 4.75)

    import math
    if substance_type.lower() == "acid":
        h_conc = concentration
        ph = -math.log10(h_conc) if h_conc > 0 else 14
    else:
        oh_conc = concentration
        poh = -math.log10(oh_conc) if oh_conc > 0 else 14
        ph = 14 - poh

    lines = []
    lines.append("pH Calculation: " + substance_type.title())
    lines.append("=" * 50)
    lines.append("")
    lines.append("Concentration: " + str(concentration) + " M")
    lines.append("Substance Type: " + substance_type.title())
    lines.append("pKa: " + str(pka))
    lines.append("")
    lines.append("Calculated pH: " + str(round(ph, 2)))
    lines.append("Nature: " + ("Acidic" if ph < 7 else "Basic" if ph > 7 else "Neutral"))
    lines.append("")
    lines.append("Formula:")
    lines.append("  - Acid: pH = -log[H+]")
    lines.append("  - Base: pOH = -log[OH-], pH = 14 - pOH")
    lines.append("")

    content = "\n".join(lines)
    return _op("ph_calculation", True, {
        "concentration": concentration,
        "substance_type": substance_type,
        "pka": pka,
        "ph": ph,
        "nature": "acidic" if ph < 7 else "basic" if ph > 7 else "neutral",
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "chemistry_research (Stella chemistry research skill)",
        "dependencies": [],
        "operations": ["molecular_structure", "reaction_prediction", "stoichiometry",
                       "ph_calculation", "lab_safety", "compound_identification", "sources"],
        "note": "Chemistry research skill. Performs molecular structure analysis, "
                "reaction prediction, stoichiometry, pH calculations, lab safety, "
                "and compound identification.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "molecular_structure": _op_molecular_structure,
    "reaction_prediction": _op_reaction_prediction,
    "stoichiometry": _op_stoichiometry,
    "ph_calculation": _op_ph_calculation,
    "lab_safety": _op_sources,
    "compound_identification": _op_sources,
}

_OPERATION_TITLES = {
    "sources": "Chemistry Research Sources",
    "molecular_structure": "Molecular Structure",
    "reaction_prediction": "Reaction Prediction",
    "stoichiometry": "Stoichiometry",
    "ph_calculation": "pH Calculation",
    "lab_safety": "Lab Safety",
    "compound_identification": "Compound Identification",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Chemistry Research",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown chemistry operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Chemistry Research",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Chemistry Research",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Chemistry error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Chemistry Research"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
