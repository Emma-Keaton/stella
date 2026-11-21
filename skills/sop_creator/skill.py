"""Feature: sop_creator — Standard Operating Procedure creation.
Creates step-by-step SOPs for business processes, onboarding, compliance, and operations.
Source: claude-skills — Operations division.
"""
from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "sop_creator",
    "aliases": ["sop_creator", "sop", "standard_operating_procedure", "sop_skill", "process_documentation"],
    "description": "Creates Standard Operating Procedures (SOPs) for business processes, onboarding, compliance, and operations.",
    "triggers": ["sop", "standard operating procedure", "process documentation", "create sop", "write sop", "sop creator", "business process", "workflow documentation"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "enum": ["create_sop", "template", "review", "sources"],
                "description": "One of: create_sop | template | review | sources.",
            },
            "process_name": {
                "type": "STRING",
                "description": "Name of the process/procedure.",
            },
            "department": {
                "type": "STRING",
                "description": "Department or team (e.g., Engineering, Sales, Support).",
            },
            "steps": {
                "type": "ARRAY",
                "description": "List of steps in the procedure.",
            },
        },
        "required": ["operation"],
    },
    "source": "claude-skills",
    "division": "operations",
    "version": "1.0.0",
    "active": True,
}

_OPERATIONS = {}

def _op_create_sop(kwargs: dict) -> dict:
    process_name = kwargs.get("process_name", "")
    department = kwargs.get("department", "")
    steps = kwargs.get("steps", [])
    if not process_name:
        return {"ok": False, "value": None, "error": "process_name is required for create_sop"}
    sop = {
        "title": f"SOP: {process_name}",
        "department": department or "General",
        "version": "1.0",
        "effective_date": "2026-01-01",
        "owner": department or "Operations",
        "steps": steps or [
            "Step 1: Identify the objective",
            "Step 2: Gather required resources",
            "Step 3: Execute the procedure",
            "Step 4: Verify results",
            "Step 5: Document and report",
        ],
    }
    return {
        "ok": True,
        "value": sop,
    }

def _op_template(kwargs: dict) -> dict:
    process_name = kwargs.get("process_name", "")
    return {
        "ok": True,
        "value": {
            "operation": "template",
            "process_name": process_name,
            "template": f"""# SOP: {process_name or '[Process Name]'}

## 1. Purpose
[Brief description of why this procedure exists]

## 2. Scope
[Who and what this procedure applies to]

## 3. Responsibilities
[Who is responsible for each step]

## 4. Procedure
### Step 1: [Step Name]
[Detailed instructions]

### Step 2: [Step Name]
[Detailed instructions]

## 5. References
[Related documents, forms, tools]

## 6. Revision History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-01 | [Author] | Initial version |

""",
        },
    }

def _op_review(kwargs: dict) -> dict:
    process_name = kwargs.get("process_name", "")
    return {
        "ok": True,
        "value": {
            "operation": "review",
            "process_name": process_name,
            "completeness": 85,
            "suggestions": [
                "Add safety warnings where applicable",
                "Include escalation procedures",
                "Define success metrics",
                "Add troubleshooting section",
                "Specify review cycle (e.g., quarterly)",
            ],
            "approved": False,
        },
    }

def _op_sources(kwargs: dict) -> dict:
    return {
        "ok": True,
        "value": {
            "operation": "sources",
            "frameworks": ["ISO 9001", "ITIL", "Six Sigma", "Lean", "Industry Best Practices"],
            "note": "SOP creation follows standard process documentation frameworks.",
        },
    }

_OPERATIONS = {
    "create_sop": _op_create_sop,
    "template": _op_template,
    "review": _op_review,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "create_sop": "Create SOP",
    "template": "SOP Template",
    "review": "SOP Review",
    "sources": "SOP Sources",
}

_ALIASES = {
    "standard_operating_procedure": "create_sop",
    "process_doc": "create_sop",
}

_OPERATION_TITLES = {
    "create_sop": "Create SOP",
    "template": "SOP Template",
    "review": "SOP Review",
    "sources": "SOP Sources",
}

def execute(**kwargs) -> dict:
    """Run one SOP creator operation."""
    operation = (kwargs.get("operation") or "").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "SOP Creator",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown SOP creator operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "SOP Creator",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "SOP Creator",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"SOP creator error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "SOP Creator"),
        "summary": record.get("value", {}).get("title", record.get("value", {}).get("process_name", "Operation completed")),
        "spoken_narrative": record.get("value", {}).get("title", record.get("value", {}).get("process_name", "Operation completed")),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }

if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="create_sop", process_name="Employee Onboarding", department="HR"))
