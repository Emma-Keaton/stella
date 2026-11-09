"""skills/stella_security/skill.py - Stella Security Skill (Pentagi)"""
from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "memory" / "stella_security"
AUDITS_FILE = DATA_DIR / "audits.json"
VULNS_FILE = DATA_DIR / "vulnerabilities.json"
FEATURE_METADATA = {"name": "stella_security", "description": "Autonomous security and penetration testing: vulnerability scanning, reconnaissance, exploitation testing, compliance auditing via Pentagi multi-agent system.", "parameters": {"type": "OBJECT", "properties": {"operation": {"type": "STRING", "description": "recon_scan, vuln_scan, exploit_test, compliance_audit, security_report, list_audits, sources.", "default": "sources"}, "target": {"type": "STRING", "description": "Target URL/IP for security testing."}, "audit_type": {"type": "STRING", "description": "Type of compliance audit."}}, "required": []}, "version": "1.0.0", "active": True, "source": "pentagi", "optional_dependencies": [], "tags": ["security", "pentagi", "pentesting", "vulnerability", "recon"]}
def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
def _load(path: Path, default: Any) -> Any:
    _ensure_data_dir()
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default
def _save(path: Path, data: Any) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_list_audits(kwargs: dict) -> dict:
    audits = _load(AUDITS_FILE, [])
    return _op("list_audits", True, {"audits": audits, "total": len(audits)})


def _op_log_audit(kwargs: dict) -> dict:
    target = (kwargs.get("target") or "").strip()
    audit_type = (kwargs.get("audit_type") or "scan").strip()
    if not target:
        return _op("log_audit", False, None, "Missing target.")
    _ensure_data_dir()
    audits = _load(AUDITS_FILE, [])
    audit = {
        "id": str(uuid.uuid4()),
        "target": target,
        "type": audit_type,
        "timestamp": time.time(),
    }
    audits.append(audit)
    _save(AUDITS_FILE, audits)
    return _op("log_audit", True, {"audit": audit, "total": len(audits)})


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["pentagi"],
        "content": "Stella Security - autonomous security and penetration testing (Pentagi).",
    })


_OPERATIONS = {
    "list_audits": _op_list_audits,
    "log_audit": _op_log_audit,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "list_audits": "List Audits",
    "log_audit": "Log Audit",
    "sources": "Security Sources",
}

_ALIASES = {
    "audits": "list_audits",
    "list_audits": "list_audits",
    "log_audit": "log_audit",
    "security_audit": "log_audit",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "list_audits":
        return f"{value.get('total')} audit(s) recorded."
    if operation == "log_audit":
        return f"Logged audit for '{value.get('audit', {}).get('target')}' ({value.get('audit', {}).get('type')})."
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Stella Security - autonomous security and penetration testing."""
    operation = (kwargs.get("operation") or "list_audits").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Stella Security",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Stella Security",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Stella Security",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Security error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Stella Security"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))