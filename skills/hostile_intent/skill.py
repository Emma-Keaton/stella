"""
Feature: hostile_intent
Description: Analyse text for hostile intent using Anthropic Claude.
"""

from __future__ import annotations
from typing import Any, Dict
import os
import requests

FEATURE_METADATA = {
    "name": "hostile_intent",
    "aliases": ["threat analysis", "hostile intent"],
    "description": "Analyse a piece of text for hostile intent and return risk level and indicators.",
    "triggers": ["hostile intent", "threat analysis"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {"type": "STRING", "description": "Text to analyse"},
            "model": {"type": "STRING", "description": "Anthropic model", "default": "claude-3-5-sonnet-20241022"}
        },
        "required": ["text"]
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    text = str(params.get("text", "")).strip()
    if not text:
        return {"ok": False, "error": "Missing text"}
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"ok": False, "error": "ANTHROPIC_API_KEY not set", "auth_tier": "keyed"}
    payload = {
        "model": params.get("model", "claude-3-5-sonnet-20241022"),
        "messages": [{"role": "user", "content": f"Analyse the following text for hostile intent and return JSON with risk_level (low/medium/high), indicators[], summary. Text: {text}"}],
        "max_tokens": 500
    }
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, json=payload, timeout=30)
        r.raise_for_status()
        content = r.json()
        # simple extraction
        return {"ok": True, "result": content, "source": "Anthropic"}
    except Exception as e:
        return {"ok": False, "error": str(e)}