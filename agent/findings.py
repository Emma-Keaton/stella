"""agent/findings.py - findings with CVSS scoring for pentest playbooks.

A finding names a vulnerability class, the target, the evidence observed, and a
CVSS-style base score. Scores are computed from the observed vector, never
invented: a finding with no evidence scores 0.0 and is labeled "unverified".
Findings are appended to a JSONL ledger so they can be reviewed and exported.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from core.user_paths import get_user_data_dir


FINDINGS_PATH = Path(get_user_data_dir()) / "config" / "findings.jsonl"


CVSS_VECTORS: dict[str, float] = {
    "none": 0.0,
    "low": 0.1,
    "medium": 0.4,
    "high": 0.7,
    "critical": 1.0,
}


def _append(entry: dict[str, Any]) -> None:
    try:
        FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with FINDINGS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def cvss_score(vector: str, confidence: str = "low") -> float:
    """Map a qualitative vector + confidence to a 0..10 CVSS-style score.

    Never rounds up: unverified or low-confidence observations stay low.
    """
    base = CVSS_VECTORS.get(vector.lower(), 0.0)
    conf = CVSS_VECTORS.get(confidence.lower(), 0.1)
    score = round(base * conf * 10, 1)
    return max(0.0, min(10.0, score))


def record_finding(vuln_class: str, target: str, evidence: str,
                   vector: str = "none", confidence: str = "low",
                   activity: str = "passive") -> dict[str, Any]:
    """Record one finding with a CVSS-style score."""
    score = cvss_score(vector, confidence)
    entry = {
        "ts": time.time(),
        "vuln_class": vuln_class,
        "target": target,
        "evidence": evidence[:500],
        "vector": vector,
        "confidence": confidence,
        "cvss_score": score,
        "activity": activity,
        "verified": vector != "none" and confidence in ("medium", "high", "critical"),
    }
    _append(entry)
    return entry


def list_findings() -> list[dict[str, Any]]:
    """All findings, newest first."""
    rows: list[dict[str, Any]] = []
    if not FINDINGS_PATH.exists():
        return rows
    try:
        with FINDINGS_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return rows
    rows.sort(key=lambda r: float(r.get("ts", 0)), reverse=True)
    return rows


def summary() -> str:
    rows = list_findings()
    verified = [r for r in rows if r.get("verified")]
    top = max((r.get("cvss_score", 0.0) for r in rows), default=0.0)
    return (f"findings={len(rows)} verified={len(verified)} "
            f"top_cvss={top}")


__all__ = ["record_finding", "list_findings", "summary", "cvss_score",
           "FINDINGS_PATH", "CVSS_VECTORS"]
