"""
cve_lookup — Search NIST NVD / CISA CVE database for a keyword, product or CVE ID.
"""

from __future__ import annotations

from typing import Any, Dict

import os
import requests


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_lookup(kwargs: dict) -> dict:
    q = (kwargs.get("q") or "").strip()
    if not q:
        return _op("lookup", False, None, "Missing query parameter 'q'.")
    limit = max(1, min(int(kwargs.get("limit", 20)), 100))
    api_key = os.getenv("NVD_API_KEY", "")
    base = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    url = f"{base}?keywordSearch={requests.utils.quote(q)}&resultsPerPage={limit}"
    if api_key:
        url += f"&apiKey={api_key}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        return _op("lookup", False, None, f"CVE lookup failed: {exc}")
    vulns = []
    for item in data.get("vulnerabilities", []):
        cve = item.get("cve", {})
        cve_id = cve.get("id")
        metrics = cve.get("metrics", {})
        cvss = None
        try:
            cvss = metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {})
        except Exception:
            pass
        vulns.append({
            "id": cve_id,
            "description": cve.get("descriptions", [{}])[0].get("value"),
            "published": cve.get("published"),
            "cvss_base_score": cvss.get("baseScore") if cvss else None,
            "link": f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        })
    return _op("lookup", True, {
        "count": len(vulns),
        "query": q,
        "results": vulns[:limit],
        "source": "NVD",
        "auth_tier": "keyless" if not api_key else "keyed",
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "sources": ["NIST NVD"],
        "content": "CVE data from NIST National Vulnerability Database (services.nvd.nist.gov). Keyless rate-limited; optional NVD_API_KEY.",
    })


_OPERATIONS = {
    "lookup": _op_lookup,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "lookup": "CVE Lookup",
    "sources": "CVE Sources",
}

_ALIASES = {
    "cve": "lookup",
    "find_cve": "lookup",
    "search_cve": "lookup",
    "list_sources": "sources",
}


def _summary(operation: str, record: dict) -> str:
    value = record.get("value") or {}
    if operation == "lookup":
        results = value.get("results") or []
        return f"{value.get('count')} CVE(s) for '{value.get('query')}' — " + ", ".join(v.get("id", "") for v in results[:5])
    if operation == "sources":
        return f"{len(value.get('sources') or [])} source(s): {', '.join(value.get('sources') or [])}"
    return record.get("error") or "No operation ran."


def execute(**kwargs) -> dict:
    """Search NIST NVD / CISA CVE database for a keyword, product or CVE ID."""
    operation = (kwargs.get("operation") or "lookup").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "CVE Lookup",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "CVE Lookup",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "CVE Lookup",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"CVE error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "CVE Lookup"),
        "summary": _summary(operation, record),
        "spoken_narrative": _summary(operation, record),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="lookup", q="openssl"))