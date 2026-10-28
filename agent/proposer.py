"""agent/proposer.py - Proposer for self-evolution (from Phase K / drzero).

The proposer generates challenging questions/problems from a domain/topic.
It names the target question and what will be probed, reports honestly when
no concept is provided, and never fabricates questions beyond its domain.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any

from core.content_boundary import ContentBoundary
from core.user_paths import get_user_data_dir


_PROPOSALS_PATH = Path(get_user_data_dir()) / "config" / "proposer_proposals.jsonl"


# Verified question templates per domain. Nothing is invented; each template
# describes a concrete probe that the solver can attempt with real tools.
_DOMAIN_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "system": [
        ("permissions", "List all running processes on this system and report which ones are listening on network ports."),
        ("network", "List all network interfaces and their IP addresses on this machine."),
        ("files", "List all files in the current workspace directory and report their sizes."),
    ],
    "osint": [
        "domain", "List DNS records (A, AAAA, MX, TXT, NS) for example.com.",
        "whois", "Perform a WHOIS lookup for example.com and report registration details.",
        "geo", "Perform IP geolocation lookup for 8.8.8.8 and report country, city, and ASN.",
    ],
    "security": [
        "port_scan", "Scan common ports on 127.0.0.1 and report which are open.",
        "tls_audit", "Perform a TLS audit on example.com:443 and report protocol version and cipher suite.",
        "header_audit", "Perform an HTTP security header audit on example.com and report missing headers.",
    ],
    "general": [
        "general", "Explain how a pin-tumbler lock works, step by step.",
        "general", "Explain how a cache key that skips work when nothing changed can be implemented.",
        "general", "Explain the difference between a cache and a buffer with examples.",
    ],
}

_DEFAULT_DOMAIN = "general"


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _append(entry: dict[str, Any]) -> None:
    """Append one proposal row to the JSONL log. Failure to log never fails."""
    try:
        _PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _PROPOSALS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _domains() -> list[str]:
    return sorted(_DOMAIN_TEMPLATES.keys())


def propose(domain: str | None = None, count: int = 1) -> dict[str, Any]:
    """Propose one or more questions for a domain.

    Returns a dict with:
      - domain: the domain used
      - questions: list of {"id", "question", "target", "activity"} dicts
    """
    domain = (domain or _DEFAULT_DOMAIN).strip().lower()
    if domain not in _DOMAIN_TEMPLATES:
        domain = _DEFAULT_DOMAIN

    templates = _DOMAIN_TEMPLATES[domain]
    count = max(1, min(int(count), len(templates)))
    selected = random.sample(templates, k=count)

    questions = []
    for i, (trigger, question) in enumerate(selected):
        qid = f"{domain}-{int(time.time())}-{i}"
        questions.append({
            "id": qid,
            "question": question,
            "target": trigger,
            "activity": "passive",
        })

    result = {
        "domain": domain,
        "questions": questions,
        "count": len(questions),
        "note": "Questions are read-only proposals. Use the solver to attempt them.",
    }

    _append({
        "ts": time.time(),
        "operation": "propose",
        "domain": domain,
        "count": len(questions),
        "questions": [q["question"] for q in questions],
    })

    return result


def probe(question: str, target: str, activity: str = "passive") -> dict[str, Any]:
    """Run one proposed question through the content boundary.

    Returns a verdict dict. If cleared, the content can be passed to the model
    as a solvable question. If blocked, it names the rule that tripped.
    """
    boundary = ContentBoundary()
    verdict = boundary.check(question, source="proposer")

    return {
        "question": question,
        "target": target,
        "activity": activity,
        "boundary": verdict.boundary,
        "ok": verdict.ok,
        "reason": verdict.reason,
        "byte_size": verdict.byte_size,
        "rules_tripped": verdict.rules_tripped,
        "preview": verdict.preview,
    }


__all__ = [
    "_op",
    "_append",
    "_domains",
    "propose",
    "probe",
    "_PROPOSALS_PATH",
    "_DEFAULT_DOMAIN",
    "_DOMAIN_TEMPLATES",
]
