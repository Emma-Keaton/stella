from __future__ import annotations
from typing import Any, Dict

FEATURE_METADATA = {
    "name": "outreach_orchestrator",
    "description": "Orchestrate full outreach workflow: find leads, enrich emails, store in CRM, send mail.",
    "triggers": ["outreach"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Search query for leads"},
            "max_results": {"type": "INTEGER", "default": 10}
        },
        "required": ["query"]
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get("query")
    max_results = int(params.get("max_results", 10))
    if not query:
        return {"ok": False, "error": "Missing query"}
    # Return a structured plan; actual execution would be handled by the agent runtime
    return {
        "ok": True,
        "plan": [
            {"skill": "lead_finder", "params": {"query": query, "max_results": max_results}},
            {"skill": "email_enricher", "params": {"name": "<lead.name>", "company": "<lead.company>", "domain": "<lead.domain>"}},
            {"skill": "crm_tracker", "params": {"action": "create", "lead": "<enriched_lead>"}},
            {"skill": "mail_sender", "params": {"to": "<lead.email>", "template": "intro"}}
        ],
        "query": query
    }