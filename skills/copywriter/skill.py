"""Feature: copywriter — Copywriting for ads, email, landing pages, social media.
Uses proven frameworks: AIDA, PAS, BAB, FFF.
Source: agency-agents — Marketing division.
"""
from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "copywriter",
    "aliases": ["copywriter", "ad copy", "marketing copy", "sales copy", "email copy", "landing page copy"],
    "description": "Writes persuasive marketing copy for ads, emails, landing pages, and social media using proven frameworks (AIDA, PAS, BAB, FFF).",
    "triggers": ["write copy", "copywriting", "ad copy", "marketing copy", "sales copy", "email copy", "landing page copy", "persuasive copy"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: ad | email | landing | social | framework | sources.",
            },
            "product": {
                "type": "STRING",
                "description": "Product or service name.",
            },
            "audience": {
                "type": "STRING",
                "description": "Target audience.",
            },
            "offer": {
                "type": "STRING",
                "description": "Main offer or value proposition.",
            },
            "tone": {
                "type": "STRING",
                "description": "Tone: professional | casual | urgent | friendly | luxury.",
            },
            "framework": {
                "type": "STRING",
                "description": "Copywriting framework: AIDA | PAS | BAB | FFF.",
            },
        },
        "required": ["operation"],
    },
    "source": "agency-agents",
    "division": "marketing",
    "version": "1.0.0",
    "active": True,
}

_OPERATIONS = {}
_OPERATION_TITLES = {}
_ALIASES = {}