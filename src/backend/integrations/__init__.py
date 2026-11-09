"""
src/backend/integrations — Stella-native integrations (fresh implementations).

All modules are self-contained: no external API calls, no connections to
third-party services. Data is stored locally under the user data dir.
Governed by StarNet subsystems (BudgetConsentManager, SkillsCatalog,
CronScheduler, ApiAuthManager, CrewManager, CliHandler, WorkflowManager).
"""
from .crm import CRMManager, Contact, Deal, Company
from .newsletter import NewsletterManager, Campaign, Subscriber, MailingList, Template
from .jobs import JobsManager, JobListing
from .business_dir import BusinessDirManager, Business
from .agent_events import AgentEventManager, AgentEvent, AgentRoute
from .web_scrape import WebScrapeManager, ScrapedPage
from .email_verify import EmailVerifyManager, EmailVerifyResult

__all__ = [
    "CRMManager", "Contact", "Deal", "Company",
    "NewsletterManager", "Campaign", "Subscriber", "MailingList", "Template",
    "JobsManager", "JobListing",
    "BusinessDirManager", "Business",
    "AgentEventManager", "AgentEvent", "AgentRoute",
    "WebScrapeManager", "ScrapedPage",
    "EmailVerifyManager", "EmailVerifyResult",
]