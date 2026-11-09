from __future__ import annotations
from typing import Any, Dict
import json, pathlib, datetime

FEATURE_METADATA = {"name":"crm_tracker","description":"CRUD leads.","triggers":["crm"],"parameters":{"type":"OBJECT","properties":{"action":{"type":"STRING"},"lead":{"type":"OBJECT"}},"required":["action"]}}

DB = pathlib.Path("E:\\Projects\\stella\\data\\crm.json")
DB.parent.mkdir(parents=True, exist_ok=True)
def _load():
    return json.loads(DB.read_text()) if DB.exists() else {}
def _save(d):
    DB.write_text(json.dumps(d, indent=2))

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    action = params.get("action")
    data = _load()
    if action=="create":
        lead = params.get("lead",{})
        lead_id = lead.get("email") or lead.get("name")
        data[lead_id] = {"created":datetime.date.today().isoformat(), **lead}
        _save(data); return {"ok":True,"id":lead_id}
    if action=="list":
        return {"ok":True,"leads":list(data.values())}
    return {"ok":False,"error":"unknown action"}