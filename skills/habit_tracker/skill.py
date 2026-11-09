from __future__ import annotations
from typing import Any, Dict
import os, json, datetime, pathlib

FEATURE_METADATA = {
    "name": "habit_tracker",
    "aliases": ["habits"],
    "description": "Create, log and query habits stored locally.",
    "triggers": ["habit", "track habit"],
    "parameters": {"type":"OBJECT","properties":{"action":{"type":"STRING"},"name":{"type":"STRING"}},"required":["action"]}
}

DATA_PATH = pathlib.Path("E:\\Projects\\stella\\data\\habits.json")
DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

def _load():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text())
    return {}

def _save(data):
    DATA_PATH.write_text(json.dumps(data, indent=2))

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    action = str(params.get("action","")).lower()
    name = str(params.get("name","")).strip()
    data = _load()
    if action=="create":
        if not name: return {"ok":False,"error":"name required"}
        data[name] = {"created": datetime.date.today().isoformat(), "logs":[]}
        _save(data); return {"ok":True,"habit":name}
    if action=="log":
        if not name: return {"ok":False,"error":"name required"}
        if name not in data: return {"ok":False,"error":"not found"}
        data[name]["logs"].append(datetime.date.today().isoformat())
        _save(data); return {"ok":True,"habit":name,"logs":data[name]["logs"]}
    if action=="list":
        return {"ok":True,"habits":list(data.keys())}
    return {"ok":False,"error":"unknown action"}