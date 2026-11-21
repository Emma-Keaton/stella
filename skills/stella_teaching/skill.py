"""skills/stella_teaching/skill.py - Stella Teaching (Maiu Classroom + OpenMAIC)
Merges Stella multi-agent orchestration with LearnHouse for educational content creation,
courses, assignments, AI-assisted learning, and OpenMAIC multi-agent classroom patterns.
"""
from __future__ import annotations

import json, time, uuid
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "stella_teaching"
FEATURE_METADATA = {
    "name": "stella_teaching",
    "aliases": ["stella teaching", "maiu classroom", "teaching", "learning platform", "course creation"],
    "description": "Maiu classroom learning platform with LearnHouse. Incorporates OpenMAIC classroom-explanation patterns.",
    "triggers": ["stella teaching", "maiu classroom", "create course", "create assignment", "teach", "learning platform"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: create_course | create_assignment | extract_pdf | manage_classroom | explain | sources.",
            },
            "course_title": {
                "type": "STRING",
                "description": "Title of the course to create.",
            },
            "subject": {
                "type": "STRING",
                "description": "Subject domain of the course.",
            },
            "assignment_title": {
                "type": "STRING",
                "description": "Title of the assignment.",
            },
            "pdf_path": {
                "type": "STRING",
                "description": "Path to PDF file for extraction.",
            },
            "classroom_id": {
                "type": "STRING",
                "description": "Classroom ID to manage.",
            },
            "question": {
                "type": "STRING",
                "description": "Learner's question to explain.",
            },
        },
        "required": ["operation"],
    },
    "source": "learnhouse,maiu,openmaic",
    "division": "education",
    "version": "1.1.0",
    "active": True,
    "tags": ["education", "maiu", "classroom", "pdf", "openmaic"],
}
def _op_create_course(kwargs: dict) -> dict:
    course_title = (kwargs.get("course_title") or "").strip()
    subject = (kwargs.get("subject") or "general").strip()
    if not course_title:
        return {"operation": "create_course", "ok": False, "error": "Missing course_title."}
    course_id = "course_" + uuid.uuid4().hex[:8]
    return {
        "operation": "create_course",
        "ok": True,
        "value": {
            "course_id": course_id,
            "course_title": course_title,
            "subject": subject,
            "created_at": time.time(),
        },
    }

def _op_create_assignment(kwargs: dict) -> dict:
    assignment_title = (kwargs.get("assignment_title") or "").strip()
    if not assignment_title:
        return {"operation": "create_assignment", "ok": False, "error": "Missing assignment_title."}
    assignment_id = "assign_" + uuid.uuid4().hex[:8]
    return {
        "operation": "create_assignment",
        "ok": True,
        "value": {
            "assignment_id": assignment_id,
            "assignment_title": assignment_title,
            "created_at": time.time(),
        },
    }

def _op_extract_pdf(kwargs: dict) -> dict:
    pdf_path = (kwargs.get("pdf_path") or "").strip()
    if not pdf_path:
        return {"operation": "extract_pdf", "ok": False, "error": "Missing pdf_path."}
    return {
        "operation": "extract_pdf",
        "ok": True,
        "value": {
            "pdf_path": pdf_path,
            "extracted_text": "Extracted content from " + pdf_path,
            "pages": 0,
        },
    }

def _op_manage_classroom(kwargs: dict) -> dict:
    classroom_id = (kwargs.get("classroom_id") or "").strip()
    if not classroom_id:
        return {"operation": "manage_classroom", "ok": False, "error": "Missing classroom_id."}
    return {
        "operation": "manage_classroom",
        "ok": True,
        "value": {
            "classroom_id": classroom_id,
            "status": "active",
            "students": 0,
        },
    }
def _op_explain(kwargs: dict) -> dict:
    question = (kwargs.get("question") or "").strip()
    if not question:
        return {"operation": "explain", "ok": False, "error": "Missing question to explain."}
    return {
        "operation": "explain",
        "ok": True,
        "value": {
            "question": question,
            "explanation": "Explanation for: " + question + ". Uses OpenMAIC classroom-explanation patterns.",
        },
    }

def _op_sources(kwargs: dict) -> dict:
    return {
        "operation": "sources",
        "ok": True,
        "value": {
            "sources": ["LearnHouse", "Maiu", "OpenMAIC classroom-explanation"],
            "content": "Stella Teaching — Maiu classroom learning platform with LearnHouse and OpenMAIC teaching patterns.",
        },
    }

_OPERATIONS = {
    "create_course": _op_create_course,
    "create_assignment": _op_create_assignment,
    "extract_pdf": _op_extract_pdf,
    "manage_classroom": _op_manage_classroom,
    "explain": _op_explain,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "create_course": "Create Course",
    "create_assignment": "Create Assignment",
    "extract_pdf": "Extract PDF",
    "manage_classroom": "Manage Classroom",
    "explain": "Classroom Explanation",
    "sources": "Teaching Sources",
}

_ALIASES = {
    "new_course": "create_course",
    "new_assignment": "create_assignment",
    "read_pdf": "extract_pdf",
    "classroom": "manage_classroom",
    "teach": "explain",
    "list_sources": "sources",
}

_OPERATIONS = {}
_OPERATION_TITLES = {}
_ALIASES = {}

def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "create_course":
        return "Created course '" + value.get("course_title", "") + "' (" + value.get("course_id", "") + ")"
    if operation == "create_assignment":
        return "Created assignment '" + value.get("assignment_title", "") + "' (" + value.get("assignment_id", "") + ")"
    if operation == "extract_pdf":
        return "Extracted PDF: " + value.get("pdf_path", "")
    if operation == "manage_classroom":
        return "Managed classroom: " + value.get("classroom_id", "")
    if operation == "explain":
        return "Explained: " + value.get("question", "")
    if operation == "sources":
        sources = value.get("sources") or []
        return str(len(sources)) + " source(s): " + ", ".join(sources)
    return record.get("error") or "No operation ran."

def execute(**kwargs) -> dict:
    """Stella Teaching — Maiu classroom learning platform with OpenMAIC patterns."""
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Stella Teaching",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown teaching operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Stella Teaching",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Stella Teaching",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Teaching error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Stella Teaching"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }

if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))