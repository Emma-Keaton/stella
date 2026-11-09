"""
src/backend/integrations/production_config.py — Open-source production configuration.

Zero external dependencies. All settings live in config/api_keys.json via
config_manager (already in the codebase). No paid services, no cloud APIs,
no proprietary software required.

Environment variables (all optional, all have sane defaults):
  STELLA_DATA_DIR       - Override user data directory
  STELLA_BUDGET_DAILY_CAP_USD  - Daily spend cap in USD (default: 5.00)
  STELLA_LOG_LEVEL      - DEBUG | INFO | WARNING | ERROR (default: INFO)
  STELLA_CRON_ENABLED   - "true" to enable background cron scheduler (default: "false")
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.backend.memory.config_manager import config_manager


# ── Environment-based configuration (all optional) ──
def data_dir() -> Path:
    """Resolve the Stella data directory for integrations."""
    override = os.getenv("STELLA_DATA_DIR")
    if override:
        return Path(override)
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "integrations"
    except Exception:
        return Path.home() / ".stella" / "integrations"


def daily_budget_cap_usd() -> float:
    return float(os.getenv("STELLA_BUDGET_DAILY_CAP_USD", "5.00"))


def log_level() -> str:
    return os.getenv("STELLA_LOG_LEVEL", "INFO").upper()


def cron_enabled() -> bool:
    return os.getenv("STELLA_CRON_ENABLED", "false").lower() in ("1", "true", "yes")


# ── Integration skill registry (all skills that gate integration access) ──
INTEGRATION_SKILLS = [
    # CRM skills
    "crm_contacts",
    "crm_companies",
    "crm_deals",
    # Newsletter skills
    "newsletter_subscribers",
    "newsletter_lists",
    "newsletter_templates",
    "newsletter_campaigns",
    # Jobs board
    "jobs_board",
    # Business directory
    "business_dir",
    # Agent events
    "agent_events",
    # Web scrape
    "web_scrape",
    # Email verify
    "email_verify",
]


def register_all_skills(skills_catalog) -> None:
    """Register every integration skill as available (not revoked)."""
    for skill_id in INTEGRATION_SKILLS:
        skills_catalog.register_skill(skill_id)


def revoke_skill(skills_catalog, skill_id: str) -> None:
    """Revoke a skill (makes it unavailable)."""
    skills_catalog._revoked.add(skill_id)


def unrevoke_skill(skills_catalog, skill_id: str) -> None:
    """Un-revoke a skill (makes it available again)."""
    skills_catalog._revoked.discard(skill_id)


# ── Production presets ──
PRESETS = {
    "minimal": {
        "description": "Core CRM + newsletter only",
        "skills": ["crm_contacts", "crm_companies", "crm_deals",
                   "newsletter_subscribers", "newsletter_lists",
                   "newsletter_templates", "newsletter_campaigns"],
        "daily_cap_usd": 2.00,
    },
    "standard": {
        "description": "Full CRM + newsletter + jobs + business dir",
        "skills": ["crm_contacts", "crm_companies", "crm_deals",
                   "newsletter_subscribers", "newsletter_lists",
                   "newsletter_templates", "newsletter_campaigns",
                   "jobs_board", "business_dir"],
        "daily_cap_usd": 5.00,
    },
    "full": {
        "description": "Everything including web scrape, email verify, agent events",
        "skills": INTEGRATION_SKILLS.copy(),
        "daily_cap_usd": 5.00,
    },
}


def apply_preset(preset_name: str, skills_catalog, budget_manager) -> dict:
    """Apply a named production preset. Returns the preset config."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(PRESETS.keys())}")
    preset = PRESETS[preset_name]
    for skill_id in preset["skills"]:
        skills_catalog.register_skill(skill_id)
    budget_manager.set_budget(0.0)
    # daily_cap_usd is set at construction; we can't change it post-init
    # but we can record the intended cap
    return preset
