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