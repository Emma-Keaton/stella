"""Feature: openmaic_classroom — OpenMAIC assistant for multi-agent interactive classrooms.
Based on OpenMAIC's openmaic skill.
Source: OpenMAIC (THU-MAIC/OpenMAIC)
"""
from __future__ import annotations

FEATURE_METADATA = {
    "name": "openmaic_classroom",
    "aliases": ["openmaic", "multi-agent classroom", "interactive classroom", "maic", "generate classroom"],
    "description": "OpenMAIC assistant for setting up, generating, and extending multi-agent interactive classrooms.",
    "triggers": ["openmaic", "multi-agent classroom", "interactive classroom", "generate classroom", "setup openmaic"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: sources | live_demo | local_setup | generate | extend | health_check.",
            },
            "access_code": {
                "type": "STRING",
                "description": "OpenMAIC access code (starts with sk-) for Live Demo.",
            },
            "requirement": {
                "type": "STRING",
                "description": "Classroom generation requirement.",
            },
            "material_ids": {
                "type": "STRING",
                "description": "Comma-separated material IDs.",
            },
            "repo_dir": {
                "type": "STRING",
                "description": "Local OpenMAIC repo directory path.",
            },
            "url": {
                "type": "STRING",
                "description": "OpenMAIC service URL (e.g., http://localhost:3000).",
            },
        },
        "required": ["operation"],
    },
    "source": "openmaic",
    "division": "education",
    "version": "1.0.0",
    "active": True,
}

def _op_sources(kwargs: dict) -> dict:
    return {"operation": "sources", "ok": True, "value": {"sources": ["OpenMAIC (THU-MAIC/OpenMAIC)", "https://github.com/THU-MAIC/OpenMAIC"], "content": "OpenMAIC — Open Multi-Agent Interactive Classroom."}}

def _op_live_demo(kwargs: dict) -> dict:
    access_code = (kwargs.get("access_code") or "").strip()
    if not access_code:
        return {"operation": "live_demo", "ok": False, "error": "Missing access_code. Get one at https://open.maic/chat."}
    return {"operation": "live_demo", "ok": True, "value": {"mode": "live_demo", "base_url": "https://open.maic.chat", "access_code": access_code, "classroom_url": "https://open.maic.chat/classroom/{id}", "instructions": "Use Authorization: Bearer <access-code> header. 10 generations/day quota."}}

def _op_local_setup(kwargs: dict) -> dict:
    repo_dir = (kwargs.get("repo_dir") or "").strip()
    url = (kwargs.get("url") or "http://localhost:3000").strip()
    return {"operation": "local_setup", "ok": True, "value": {"mode": "local", "repo_dir": repo_dir or "/path/to/OpenMAIC", "url": url, "commands": ["git clone https://github.com/THU-MAIC/OpenMAIC.git", "cd OpenMAIC", "pnpm install"], "steps": ["Clone or reuse checkout.", "Configure provider keys.", "Verify GET {url}/api/health.", "Generate classroom."]}}

def _op_generate(kwargs: dict) -> dict:
    requirement = (kwargs.get("requirement") or "").strip()
    material_ids = (kwargs.get("material_ids") or "").strip()
    if not requirement:
        return {"operation": "generate", "ok": False, "error": "Missing requirement."}
    ids = [x.strip() for x in material_ids.split(",") if x.strip()] if material_ids else []
    return {"operation": "generate", "ok": True, "value": {"requirement": requirement, "material_ids": ids, "endpoint": "POST /api/generate-classroom", "fields": ["requirement", "materialIds"], "instructions": "Submit job, then poll until success or failure."}}

def _op_extend(kwargs: dict) -> dict:
    return {"operation": "extend", "ok": True, "value": {"mode": "extend", "description": "Secondary development.", "rules": ["Read before edit.", "pnpm@10.28.0 and Node >=22.19.0 required.", "Consume @openmaic/* packages as-is.", "dist/ is gitignored; rebuild after changes."], "routes": ["extend-cookbook.md — Customize OpenMAIC product.", "extend-sdk.md — Use @openmaic/* SDK."]}}

def _op_health_check(kwargs: dict) -> dict:
    url = (kwargs.get("url") or "http://localhost:3000").strip()
    return {"operation": "health_check", "ok": True, "value": {"url": url, "endpoint": "GET " + url + "/api/health", "instructions": "Verify OpenMAIC service is healthy."}}

_OPERATIONS = {"sources": _op_sources, "live_demo": _op_live_demo, "local_setup": _op_local_setup, "generate": _op_generate, "extend": _op_extend, "health_check": _op_health_check}
_OPERATION_TITLES = {"sources": "OpenMAIC Sources", "live_demo": "OpenMAIC Live Demo", "local_setup": "OpenMAIC Local Setup", "generate": "OpenMAIC Classroom Generation", "extend": "OpenMAIC Extend", "health_check": "OpenMAIC Health Check"}
_ALIASES = {"setup": "local_setup", "start": "local_setup", "gen": "generate", "classroom": "generate", "secondary_dev": "extend", "health": "health_check", "list_sources": "sources"}

def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "sources":
        sources = value.get("sources") or []
        return str(len(sources)) + " source(s): " + ", ".join(sources)
    if operation == "live_demo":
        return "Live Demo mode ready at " + value.get("base_url", "")
    if operation == "local_setup":
        return "Local setup: " + value.get("repo_dir", "") + " at " + value.get("url", "")
    if operation == "generate":
        return "Generate classroom: " + value.get("requirement", "")[:60] + "..."
    if operation == "extend":
        return "OpenMAIC secondary development guidance"
    if operation == "health_check":
        return "Health check: GET " + value.get("endpoint", "")
    return record.get("error") or "No operation ran."

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {"title": "OpenMAIC Classroom", "summary": "Unknown operation '" + operation + "'.", "spoken_narrative": "Unknown operation " + operation + ".", "ok": False, "operation": operation}
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {"title": "OpenMAIC Classroom", "summary": "Bad arguments: " + str(exc), "spoken_narrative": "Bad arguments.", "ok": False, "operation": operation}
    except Exception as exc:
        return {"title": "OpenMAIC Classroom", "summary": type(exc).__name__ + ": " + str(exc), "spoken_narrative": "Error: " + type(exc).__name__ + ".", "ok": False, "operation": operation}
    return {"title": _OPERATION_TITLES.get(operation, "OpenMAIC Classroom"), "summary": _summary(operation, record), "spoken_narrative": _summary(operation, record), "operation": operation, "ok": bool(record.get("ok")), "record": record}

if __name__ == "__main__":
    import pprint
    pprint.pprint(execute(operation="sources"))
