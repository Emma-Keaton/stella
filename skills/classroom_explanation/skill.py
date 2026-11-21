"""Feature: classroom_explanation — Explain classroom questions with speech and board work.
Based on OpenMAIC's classroom-explanation skill.
Source: OpenMAIC (THU-MAIC/OpenMAIC)
"""
from __future__ import annotations

FEATURE_METADATA = {
    "name": "classroom_explanation",
    "aliases": ["classroom explanation", "explain lesson", "teach concept"],
    "description": "Explain a classroom question with concise speech and optional simple board work.",
    "triggers": ["explain", "classroom explanation", "teach this", "explain concept"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: explain | board_plan | sources.",
            },
            "question": {
                "type": "STRING",
                "description": "The learner's question or topic to explain.",
            },
            "subject": {
                "type": "STRING",
                "description": "Subject domain (math, physics, chemistry, biology).",
            },
            "grade_level": {
                "type": "STRING",
                "description": "Learner grade level.",
            },
            "use_board": {
                "type": "BOOLEAN",
                "description": "Whether to include simple board/diagram plan.",
            },
        },
        "required": ["operation"],
    },
    "source": "openmaic",
    "division": "education",
    "version": "1.0.0",
    "active": True,
}

def _op_explain(kwargs: dict) -> dict:
    question = (kwargs.get("question") or "").strip()
    subject = (kwargs.get("subject") or "general").strip()
    grade_level = (kwargs.get("grade_level") or "general").strip()
    use_board = bool(kwargs.get("use_board", False))
    if not question:
        return {"operation": "explain", "ok": False, "error": "Missing question to explain."}
    explanation = "Here's a clear explanation of: " + question + "\n"
    explanation += "\nSubject: " + subject + "\nLevel: " + grade_level + "\n"
    explanation += "\nKey points:\n- Start with the core idea.\n- Preserve conditions, units, reference frame.\n- State missing conditions instead of guessing.\n"
    if use_board:
        explanation += "\nBoard plan:\n- Draw one block at a time.\n- Label every arrow with explicit meaning.\n"
    spoken = "Explained " + question + " for " + grade_level + " level " + subject + "."
    return {"operation": "explain", "ok": True, "value": {"question": question, "subject": subject, "grade_level": grade_level, "explanation": explanation, "use_board": use_board, "spoken_narrative": spoken}}

def _op_board_plan(kwargs: dict) -> dict:
    question = (kwargs.get("question") or "").strip()
    if not question:
        return {"operation": "board_plan", "ok": False, "error": "Missing question for board plan."}
    plan = {"question": question, "elements": ["label", "arrow", "simple_geometry"], "rules": ["Finish one block before speaking next.", "Give every arrow explicit meaning with nearby label.", "Use only elements needed for relationships."]}
    return {"operation": "board_plan", "ok": True, "value": plan}

def _op_sources(kwargs: dict) -> dict:
    return {"operation": "sources", "ok": True, "value": {"sources": ["OpenMAIC classroom-explanation", "THU-MAIC/OpenMAIC"], "content": "OpenMAIC teaching SOP: concise speech + simple board work."}}

_OPERATIONS = {"explain": _op_explain, "board_plan": _op_board_plan, "sources": _op_sources}
_OPERATION_TITLES = {"explain": "Classroom Explanation", "board_plan": "Board Plan", "sources": "Classroom Sources"}
_ALIASES = {"explain_concept": "explain", "teach": "explain", "lesson": "explain", "diagram": "board_plan", "list_sources": "sources"}

def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "explain":
        return "Explained: " + value.get("question", "") + " (" + value.get("subject", "") + ", " + value.get("grade_level", "") + ")"
    if operation == "board_plan":
        return "Board plan for: " + value.get("question", "")
    if operation == "sources":
        sources = value.get("sources") or []
        return str(len(sources)) + " source(s): " + ", ".join(sources)
    return record.get("error") or "No operation ran."

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "explain").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "Classroom Explanation", "summary": "Unknown operation '" + operation + "'.", "spoken_narrative": "Unknown operation " + operation + ".", "ok": False, "operation": operation}
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {"title": "Classroom Explanation", "summary": "Bad arguments: " + str(exc), "spoken_narrative": "Bad arguments.", "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "Classroom Explanation", "summary": type(exc).__name__ + ": " + str(exc), "spoken_narrative": "Error: " + type(exc).__name__ + ".", "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "Classroom Explanation"), "summary": _summary(operation, record), "spoken_narrative": _summary(operation, record), "operation": operation, "ok": bool(record.get("ok")), "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))
_OPERATIONS = {}
_OPERATION_TITLES = {}
_ALIASES = {}
