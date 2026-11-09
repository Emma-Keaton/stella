"""
src/backend/integrations/production.py — Open-source production wiring.

Initializes all StarNet subsystems + all integration managers together,
registers all skills, sets budget caps, and provides health checks.

No external services, no paid APIs, no cloud dependencies. Everything runs
locally on the user's machine using only Python standard library + JSON.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.backend.memory.config_manager import config_manager
from src.backend.starnet import (
    CrewManager,
    CliHandler,
    SkillsCatalog,
    BudgetConsentManager,
    CronScheduler,
    ApiAuthManager,
    WorkflowManager,
    Agent as CrewAgent,
    Workflow,
    CronJob,
)
from src.backend.integrations import (
    CRMManager, Contact, Deal, Company,
    NewsletterManager, Campaign, Subscriber, MailingList, Template,
    JobsManager, JobListing,
    BusinessDirManager, Business,
    AgentEventManager, AgentEvent, AgentRoute,
    WebScrapeManager, ScrapedPage,
    EmailVerifyManager, EmailVerifyResult,
)
from src.backend.integrations.production_config import (
    data_dir, daily_budget_cap_usd, log_level, cron_enabled,
    register_all_skills, apply_preset, INTEGRATION_SKILLS,
)

logger = logging.getLogger("stella.integrations.production")


@dataclass
class ProductionIntegrations:
    """All integration managers wired together for production."""

    crew: CrewManager
    budget: BudgetConsentManager
    workflows: WorkflowManager
    api_auth: ApiAuthManager
    skills: SkillsCatalog
    cron: CronScheduler
    cli: CliHandler

    crm: CRMManager
    newsletter: NewsletterManager
    jobs: JobsManager
    business_dir: BusinessDirManager
    agent_events: AgentEventManager
    web_scrape: WebScrapeManager
    email_verify: EmailVerifyManager

    initialized_at: float = field(default_factory=time.time)
    preset: str = "standard"

    # ── Health checks ──
    def health(self) -> dict[str, Any]:
        """Return health status for every integration manager."""
        return {
            "status": "healthy",
            "initialized_at": self.initialized_at,
            "preset": self.preset,
            "starnet": {
                "crew_agents": len(self.crew.all()),
                "budget_usd": self.budget.budget(),
                "daily_cap_usd": self.budget.daily_cap(),
                "workflows": self.workflows.available_ids(),
                "consented_tools": sorted(self.budget.all_consented()),
                "api_token_length": len(self.api_auth.launch_token),
            },
            "integrations": {
                "crm": self.crm.summary(),
                "newsletter": self.newsletter.summary(),
                "jobs": self.jobs.summary(),
                "business_dir": self.business_dir.summary(),
                "agent_events": self.agent_events.summary(),
                "web_scrape": self.web_scrape.summary(),
                "email_verify": self.email_verify.summary(),
            },
        }

    def reset_all(self) -> dict[str, str]:
        """Reset all integration data (destructive — use with care)."""
        self.crm._contacts.clear()
        self.crm._companies.clear()
        self.crm._deals.clear()
        self.crm._persist_all()

        self.newsletter._subscribers.clear()
        self.newsletter._lists.clear()
        self.newsletter._templates.clear()
        self.newsletter._campaigns.clear()
        self.newsletter._persist_all()

        self.jobs._jobs.clear()
        self.jobs._persist()

        self.business_dir._businesses.clear()
        self.business_dir._persist()

        self.agent_events._events.clear()
        self.agent_events._routes.clear()
        self.agent_events._persist()

        self.web_scrape._pages.clear()
        self.web_scrape._persist()

        self.email_verify._results.clear()
        self.email_verify._persist()

        return {"status": "reset", "message": "All integration data cleared"}

    def register_default_crew(self) -> None:
        """Register default crew agents for production."""
        self.crew.register(CrewAgent(
            agent_id="lead",
            name="Lead",
            system_prompt="You are the Lead agent. Coordinate the crew and delegate tasks to specialists.",
            tools=[],
            model="default",
        ))
        self.crew.register(CrewAgent(
            agent_id="researcher",
            name="Researcher",
            system_prompt="You are a Researcher agent. Investigate topics thoroughly and report findings.",
            tools=[],
            model="default",
        ))
        self.crew.register(CrewAgent(
            agent_id="analyst",
            name="Analyst",
            system_prompt="You are an Analyst agent. Analyze data and provide insights.",
            tools=[],
            model="default",
        ))
        self.crew.register(CrewAgent(
            agent_id="crm_admin",
            name="CRM Admin",
            system_prompt="You manage the CRM: contacts, companies, and deals.",
            tools=["crm_contacts", "crm_companies", "crm_deals"],
            model="default",
        ))
        self.crew.register(CrewAgent(
            agent_id="newsletter_editor",
            name="Newsletter Editor",
            system_prompt="You manage email newsletters: subscribers, campaigns, templates, and sends.",
            tools=["newsletter_subscribers", "newsletter_lists", "newsletter_campaigns"],
            model="default",
        ))

    def setup_default_cron_jobs(self) -> None:
        """Set up default maintenance cron jobs (disabled by default — opt-in)."""
        self.cron.add_job(CronJob(
            id="daily_budget_reset",
            cron_expr="0 0 * * *",
            prompt="Reset daily budget counter for integrations",
            agent_id="lead",
            enabled=False,
        ))
        self.cron.add_job(CronJob(
            id="weekly_integrity_check",
            cron_expr="0 2 * * 0",
            prompt="Verify integrity of all integration JSON stores",
            agent_id="lead",
            enabled=False,
        ))

    @classmethod
    def build(
        cls,
        preset: str = "standard",
        register_default_crew_agents: bool = True,
        setup_cron: bool = True,
    ) -> "ProductionIntegrations":
        """Factory: build a fully wired production integration stack."""
        logger.info("Building Stella production integrations (preset=%s)", preset)

        # ── StarNet core ──
        budget = BudgetConsentManager(daily_cap_usd=daily_budget_cap_usd())
        skills = SkillsCatalog()
        register_all_skills(skills)
        apply_preset(preset, skills, budget)

        crew = CrewManager()
        workflows = WorkflowManager()
        api_auth = ApiAuthManager()
        cron = CronScheduler()
        cli = CliHandler(crew, budget, workflows, api_auth)

        # ── Integration managers ──
        crm = CRMManager(budget=budget, skills=skills)
        newsletter = NewsletterManager(budget=budget, skills=skills)
        jobs = JobsManager(budget=budget, skills=skills)
        business_dir = BusinessDirManager(budget=budget, skills=skills)
        agent_events = AgentEventManager(budget=budget, skills=skills)
        web_scrape = WebScrapeManager(budget=budget, skills=skills)
        email_verify = EmailVerifyManager(budget=budget, skills=skills)

        integrations = cls(
            crew=crew,
            budget=budget,
            workflows=workflows,
            api_auth=api_auth,
            skills=skills,
            cron=cron,
            cli=cli,
            crm=crm,
            newsletter=newsletter,
            jobs=jobs,
            business_dir=business_dir,
            agent_events=agent_events,
            web_scrape=web_scrape,
            email_verify=email_verify,
            preset=preset,
        )

        if register_default_crew_agents:
            integrations.register_default_crew()

        if setup_cron:
            integrations.setup_default_cron_jobs()

        logger.info("Production integrations built successfully (preset=%s)", preset)
        return integrations


# ── Singleton accessor ──
_production: Optional[ProductionIntegrations] = None


def get_production() -> ProductionIntegrations:
    """Get the singleton production integration stack, building it if needed."""
    global _production
    if _production is None:
        preset = os.getenv("STELLA_INTEGRATION_PRESET", "standard")
        _production = ProductionIntegrations.build(preset=preset)
    return _production


def reset_production() -> ProductionIntegrations:
    """Reset and rebuild the production stack (useful for testing/reconfig)."""
    global _production
    _production = None
    return get_production()