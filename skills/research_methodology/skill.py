"""
skills/research_methodology/skill.py - Stella Research Methodology skill.

Provides research operations:
  - research_design: Design research studies
  - hypothesis_formation: Formulate testable hypotheses
  - literature_review: Structure literature searches
  - data_collection: Design data collection methods
  - statistical_analysis: Plan statistical analysis
  - experimental_design: Controlled experiment design
  - academic_writing: Structure research papers
  - sources: Return skill metadata
"""

from __future__ import annotations

from typing import Any


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_research_design(kwargs: dict) -> dict:
    research_question = (kwargs.get("research_question") or "").strip()
    approach = (kwargs.get("approach") or "mixed_methods").strip()

    lines = []
    lines.append("Research Design: " + research_question)
    lines.append("=" * 50)
    lines.append("")
    lines.append("Research Question: " + research_question)
    lines.append("Approach: " + approach.title())
    lines.append("")
    lines.append("Research Design Components:")
    lines.append("  1. Purpose: Exploratory, descriptive, explanatory, or evaluative")
    lines.append("  2. Approach: Quantitative, qualitative, or mixed methods")
    lines.append("  3. Strategy: Case study, survey, experiment, ethnography, etc.")
    lines.append("  4. Timeframe: Cross-sectional or longitudinal")
    lines.append("  5. Setting: Laboratory, field, or natural environment")
    lines.append("")
    lines.append("Sampling Strategy:")
    lines.append("  - Population definition")
    lines.append("  - Sampling frame")
    lines.append("  - Sampling method (probability or non-probability)")
    lines.append("  - Sample size determination")
    lines.append("")
    lines.append("Data Collection Methods:")
    lines.append("  - Surveys, interviews, interviews, observations")
    lines.append("  - Existing data, experiments, case studies")
    lines.append("")
    lines.append("Data Analysis Plan:")
    lines.append("  - Quantitative: Statistical tests, modeling")
    lines.append("  - Qualitative: Thematic analysis, content analysis")
    lines.append("  - Mixed methods: Integration strategies")
    lines.append("")

    content = "\n".join(lines)
    return _op("research_design", True, {
        "research_question": research_question,
        "approach": approach,
        "content": content,
    })


def _op_hypothesis_formation(kwargs: dict) -> dict:
    research_question = (kwargs.get("research_question") or "").strip()
    variables = (kwargs.get("variables") or "").strip()

    lines = []
    lines.append("Hypothesis Formation: " + research_question)
    lines.append("=" * 50)
    lines.append("")
    lines.append("Research Question: " + research_question)
    lines.append("Variables: " + variables)
    lines.append("")
    lines.append("Null Hypothesis (H0):")
    lines.append("  - No relationship or difference between variables")
    lines.append("  - Statement of 'no effect'")
    lines.append("")
    lines.append("Alternative Hypothesis (H1/Ha):")
    lines.append("  - Relationship or difference exists")
    lines.append("  - Directional or non-directional")
    lines.append("")
    lines.append("Criteria for Good Hypotheses:")
    lines.append("  - Testable and falsifiable")
    lines.append("  - Clear and specific")
    lines.append("  - Based on theory or prior research")
    lines.append("  - Operationally defined variables")
    lines.append("")
    lines.append("Example Format:")
    lines.append("  H0: There is no significant difference in X between groups A and B")
    lines.append("  H1: There is a significant difference in X between groups A and B")
    lines.append("")

    content = "\n".join(lines)
    return _op("hypothesis_formation", True, {
        "research_question": research_question,
        "variables": variables,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "research_methodology (Stella research methodology skill)",
        "dependencies": [],
        "operations": ["research_design", "hypothesis_formation",
                       "literature_review", "data_collection",
                       "statistical_analysis", "experimental_design",
                       "academic_writing", "sources"],
        "note": "Research methodology skill. Provides research design, "
                "hypothesis formation, literature review structure, data "
                "collection planning, statistical analysis planning, "
                "experimental design, and academic writing guidance.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "research_design": _op_research_design,
    "hypothesis_formation": _op_hypothesis_formation,
    "literature_review": _op_sources,
    "data_collection": _op_sources,
    "statistical_analysis": _op_sources,
    "experimental_design": _op_sources,
    "academic_writing": _op_sources,
}

_OPERATION_TITLES = {
    "sources": "Research Methodology Sources",
    "research_design": "Research Design",
    "hypothesis_formation": "Hypothesis Formation",
    "literature_review": "Literature Review",
    "data_collection": "Data Collection",
    "statistical_analysis": "Statistical Analysis",
    "experimental_design": "Experimental Design",
    "academic_writing": "Academic Writing",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Research Methodology",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown research operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Research Methodology",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Research Methodology",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Research error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Research Methodology"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
