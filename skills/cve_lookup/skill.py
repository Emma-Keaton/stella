"""
Feature: cve_lookup
Description: Search NIST NVD / CISA CVE database for a keyword, product or CVE ID.
"""

from __future__ import annotations
from typing import Any, Dict
import os
import requests

FEATURE_METADATA = {
    "name": "cve_lookup",
    "aliases": ["cve search", "find cve", "lookup cve"],
    "description": "Search the NIST National Vulnerability Database for CVEs matching a query term and return IDs, severity and link.",
    "triggers": ["cve", "find cve", "lookup cve"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "q": {"type": "STRING", "description": "Keyword, product name or CVE ID"},
            "limit": {"type": "INTEGER", "description": "Maximum number of results", "default": 20}
        },
        "required": ["q"]
    }
}

def _http_get(url: str, timeout: float = 15.0) -> Dict[str, Any]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    q = str(params.get("q", "")).strip()
    if not q:
        return {"ok": False, "error": "Missing query parameter 'q'."}
    limit = int(params.get("limit", 20))
    # NIST NVD v2 API (keyless, rate limited). If an API key is set, use it.
    api_key = os.getenv("NVD_API_KEY", "")
    base = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    url = f"{base}?keywordSearch={requests.utils.quote(q)}&resultsPerPage={min(limit, 100)}"
    if api_key:
        url += f"&apiKey={api_key}"
    resp = _http_get(url)
    if not resp["ok"]:
        return {"ok": False, "error": resp["error"], "source": "NVD"}
    data = resp["data"]
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
    return {
        "ok": True,
        "count": len(vulns),
        "query": q,
        "results": vulns[:limit],
        "source": "NVD",
        "auth_tier": "keyless" if not api_key else "keyed"
    }