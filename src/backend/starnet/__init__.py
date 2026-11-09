"""
src/backend/starnet — StarNet features ported to the Stella Python backend.

Multi-agent crew, CLI command handler, skills catalog, budget/consent,
cron scheduler, API auth, and workflow definitions.
"""
from .crew import CrewManager, Agent
from .cli import CliHandler
from .skills_catalog import SkillsCatalog
from .budget_consent import BudgetConsentManager
from .cron_scheduler import CronScheduler, CronJob
from .api_auth import ApiAuthManager
from .workflow_manager import WorkflowManager, Workflow

__all__ = [
    "CrewManager",
    "Agent",
    "CliHandler",
    "SkillsCatalog",
    "BudgetConsentManager",
    "CronScheduler",
    "CronJob",
    "ApiAuthManager",
    "WorkflowManager",
    "Workflow",
]