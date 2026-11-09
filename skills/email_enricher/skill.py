from __future__ import annotations
from typing import Any, Dict
import os, requests

FEATURE_METADATA = {
    "name": "email_enricher",
    "description": "Enrich leads with email addresses using Hunter.io or fallback pattern.",
    "triggers": ["enrich email"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "company": {"type": "STRING"},
            "domain": {"type": "STRING", "description": "Company domain, optional"}
        },
        "required": ["name", "company"]
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("name")
    company = params.get("company")
    domain = params.get("domain")
    if not name or not company:
        return {"ok": False, "error": "Missing name or company"}
    hunter_key = os.getenv("HUNTER_API_KEY")
    if hunter_key and domain:
        try:
            url = f"https://api.hunter.io/v2/email-finder?domain={domain}&first_name={name.split()[0]}&last_name={' '.join(name.split()[1:])}&api_key={hunter_key}"
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            email = data.get("data", {}).get("email")
            if email:
                return {"ok": True, "name": name, "company": company, "email": email, "source": "hunter"}
        except Exception:
            pass
    # Fallback pattern
    email = f"{name.lower().replace(' ','.')}@{company.lower().replace(' ','')}.com"
    return {"ok": True, "name": name, "company": company, "email": email, "source": "pattern"}