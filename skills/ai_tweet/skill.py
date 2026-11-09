from __future__ import annotations
from typing import Any, Dict
import os, requests

FEATURE_METADATA = {"name":"ai_tweet","description":"Generate tweet text using Stella's internal model router.","triggers":["tweet"],"parameters":{"type":"OBJECT","properties":{"prompt":{"type":"STRING"}},"required":["prompt"]}}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    prompt = params.get("prompt")
    if not prompt:
        return {"ok": False, "error": "Missing prompt"}
    # Stella internal model endpoint (local or cloud) – no external key needed
    endpoint = os.getenv("STELLA_MODEL_ENDPOINT", "http://localhost:8000/model/chat")
    try:
        r = requests.post(endpoint, json={"prompt": f"Write a concise tweet (<=280 chars) about: {prompt}"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        # Accept both { "response": "..."} and raw text
        tweet = data.get("response") or data.get("text") or str(data)
        return {"ok": True, "tweet": tweet}
    except Exception as e:
        return {"ok": False, "error": str(e)}