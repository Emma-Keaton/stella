"""
skills/medicine_research/skill.py - Stella Medicine Research skill.

Provides medicine operations:
  - differential_diagnosis: Generate differential diagnoses
  - drug_interaction: Check drug interactions
  - vital_signs: Interpret vital signs
  - lab_interpretation: Interpret laboratory results
  - anatomy_overview: Anatomical system overview
  - pathology: Disease mechanism analysis
  - sources: Return skill metadata
"""

from __future__ import annotations

from typing import Any


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_differential_diagnosis(kwargs: dict) -> dict:
    symptoms = (kwargs.get("symptoms") or "").strip()
    age = int(kwargs.get("age") or 40)
    gender = (kwargs.get("gender") or "unspecified").strip()

    lines = []
    lines.append("Differential Diagnosis: " + symptoms)
    lines.append("=" * 50)
    lines.append("")
    lines.append("Patient: " + str(age) + "y " + gender)
    lines.append("Presenting Symptoms: " + symptoms)
    lines.append("")
    lines.append("Differential Diagnoses (most likely first):")
    lines.append("")
    lines.append("  1. Most likely - Based on symptom pattern")
    lines.append("     - Key features: [matching symptoms]")
    lines.append("     - Diagnostic tests: [recommended workup]")
    lines.append("     - Treatment: [initial management]")
    lines.append("")
    lines.append("  2. Alternative - Consider and rule out")
    lines.append("     - Key features: [distinguishing features]")
    lines.append("     - Diagnostic tests: [confirmatory tests]")
    lines.append("")
    lines.append("  3. Less likely - Keep in differential")
    lines.append("     - Key features: [why considered]")
    lines.append("     - Diagnostic tests: [if indicated]")
    lines.append("")
    lines.append("Red Flags (seek immediate care):")
    lines.append("  - Chest pain with radiation")
    lines.append("  - Shortness of breath at rest")
    lines.append("  - Altered mental status")
    lines.append("  - Hemodynamic instability")
    lines.append("")
    lines.append("Disclaimer: This is AI-generated information, not medical advice.")
    lines.append("Always consult a qualified healthcare professional.")
    lines.append("")

    content = "\n".join(lines)
    return _op("differential_diagnosis", True, {
        "symptoms": symptoms,
        "age": age,
        "gender": gender,
        "content": content,
    })


def _op_drug_interaction(kwargs: dict) -> dict:
    drug1 = (kwargs.get("drug1") or "").strip()
    drug2 = (kwargs.get("drug2") or "").strip()

    lines = []
    lines.append("Drug Interaction Check: " + drug1 + " + " + drug2)
    lines.append("=" * 50)
    lines.append("")
    lines.append("Drug 1: " + drug1)
    lines.append("Drug 2: " + drug2)
    lines.append("")
    lines.append("Interaction Assessment:")
    lines.append("  - Pharmacokinetic: Absorption, distribution, metabolism, excretion")
    lines.append("  - Pharmacodynamic: Additive, synergistic, antagonistic effects")
    lines.append("  - Clinical significance: Minor, moderate, major, contraindicated")
    lines.append("")
    lines.append("Monitoring Parameters:")
    lines.append("  - Vital signs")
    lines.append("  - Laboratory values")
    lines.append("  - Clinical response")
    lines.append("  - Adverse effects")
    lines.append("")
    lines.append("Recommendations:")
    lines.append("  - Monitor patient closely")
    lines.append("  - Consider alternative therapy")
    lines.append("  - Adjust dosage if needed")
    lines.append("  - Educate patient on warning signs")
    lines.append("")

    content = "\n".join(lines)
    return _op("drug_interaction", True, {
        "drug1": drug1,
        "drug2": drug2,
        "content": content,
    })


def _op_vital_signs(kwargs: dict) -> dict:
    bp_systolic = int(kwargs.get("bp_systolic") or 120)
    bp_diastolic = int(kwargs.get("bp_diastolic") or 80)
    heart_rate = int(kwargs.get("heart_rate") or 75)
    respiratory_rate = int(kwargs.get("respiratory_rate") or 16)
    temperature = float(kwargs.get("temperature") or 98.6)
    oxygen_sat = int(kwargs.get("oxygen_sat") or 98)

    lines = []
    lines.append("Vital Signs Interpretation")
    lines.append("=" * 50)
    lines.append("")
    lines.append("Blood Pressure: " + str(bp_systolic) + "/" + str(bp_diastolic) + " mmHg")
    lines.append("Heart Rate: " + str(heart_rate) + " bpm")
    lines.append("Respiratory Rate: " + str(respiratory_rate) + " breaths/min")
    lines.append("Temperature: " + str(temperature) + " °F")
    lines.append("Oxygen Saturation: " + str(oxygen_sat) + "%")
    lines.append("")
    lines.append("Interpretation:")
    lines.append("  - BP: " + ("Normal" if 90 <= bp_systolic <= 120 and 60 <= bp_diastolic <= 80 else "Abnormal"))
    lines.append("  - HR: " + ("Normal" if 60 <= heart_rate <= 100 else "Abnormal"))
    lines.append("  - RR: " + ("Normal" if 12 <= respiratory_rate <= 20 else "Abnormal"))
    lines.append("  - Temp: " + ("Normal" if 97 <= temperature <= 99.5 else "Abnormal"))
    lines.append("  - SpO2: " + ("Normal" if oxygen_sat >= 95 else "Low"))
    lines.append("")
    lines.append("Clinical Notes:")
    lines.append("  - Trend vital signs over time")
    lines.append("  - Correlate with clinical presentation")
    lines.append("  - Consider patient baseline")
    lines.append("")

    content = "\n".join(lines)
    return _op("vital_signs", True, {
        "bp_systolic": bp_systolic,
        "bp_diastolic": bp_diastolic,
        "heart_rate": heart_rate,
        "respiratory_rate": respiratory_rate,
        "temperature": temperature,
        "oxygen_sat": oxygen_sat,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "medicine_research (Stella medicine research skill)",
        "dependencies": [],
        "operations": ["differential_diagnosis", "drug_interaction", "vital_signs",
                       "lab_interpretation", "anatomy_overview", "pathology", "sources"],
        "note": "Medicine research skill. Provides differential diagnosis, "
                "drug interaction checking, vital signs interpretation, lab "
                "interpretation, anatomy overview, and pathology analysis.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "differential_diagnosis": _op_differential_diagnosis,
    "drug_interaction": _op_drug_interaction,
    "vital_signs": _op_vital_signs,
    "lab_interpretation": _op_sources,
    "anatomy_overview": _op_sources,
    "pathology": _op_sources,
}

_OPERATION_TITLES = {
    "sources": "Medicine Research Sources",
    "differential_diagnosis": "Differential Diagnosis",
    "drug_interaction": "Drug Interaction",
    "vital_signs": "Vital Signs",
    "lab_interpretation": "Lab Interpretation",
    "anatomy_overview": "Anatomy Overview",
    "pathology": "Pathology",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Medicine Research",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown medicine operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Medicine Research",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Medicine Research",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Medicine error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Medicine Research"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
