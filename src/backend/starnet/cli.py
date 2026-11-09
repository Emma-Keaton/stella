"""
src/backend/starnet/cli.py — CLI command handler (StarNet CLI port).

Commands:
    ls                  - list registered crew agents
    approve <tool>      - grant consent for a tool
    deny <tool>         - revoke consent for a tool
    watch               - show local server status
    flow                - list available workflows
    -p | port           - show server ports
    token               - show the per-launch API token
    status              - show engine status
"""

from __future__ import annotations

from .crew import CrewManager
from .budget_consent import BudgetConsentManager
from .workflow_manager import WorkflowManager
from .api_auth import ApiAuthManager


class CliHandler:
    """Handles Stella CLI-style commands."""

    PORT_UPSTREAM = 11434
    PORT_K2 = 11435

    def __init__(
        self,
        crew: CrewManager,
        budget: BudgetConsentManager,
        workflows: WorkflowManager,
        api_auth: ApiAuthManager,
        crm=None,
        newsletter=None,
        jobs=None,
        business_dir=None,
        agent_events=None,
        web_scrape=None,
        email_verify=None,
    ) -> None:
        self.crew = crew
        self.budget = budget
        self.workflows = workflows
        self.api_auth = api_auth
        self.crm = crm
        self.newsletter = newsletter
        self.jobs = jobs
        self.business_dir = business_dir
        self.agent_events = agent_events
        self.web_scrape = web_scrape
        self.email_verify = email_verify

    def handle(
        self,
        cmd: str,
        engine_running: bool = False,
        engine_mode: str = "LOCAL",
    ) -> str:
        parts = [p for p in cmd.strip().split() if p]
        if not parts:
            return "Usage: stella <command> [args]"

        c = parts[0].lower()

        if c == "ls":
            agents = ", ".join(f"{a.name} ({a.agent_id})" for a in self.crew.all())
            return f"Agents: {agents if agents else 'none'}"

        if c == "approve":
            if len(parts) > 1:
                self.budget.grant_consent(parts[1])
                return f"Approved: {parts[1]}"
            return "Usage: approve <tool>"

        if c == "deny":
            if len(parts) > 1:
                self.budget.revoke_consent(parts[1])
                return f"Denied: {parts[1]}"
            return "Usage: deny <tool>"

        if c == "watch":
            state = "up" if engine_running else "down"
            return f"Watching local engine on port {self.PORT_K2}: {state}"

        if c == "flow":
            wfs = ", ".join(self.workflows.available_ids())
            return f"Workflows: {wfs}"

        if c in ("-p", "port"):
            return f"Upstream llama-server: {self.PORT_UPSTREAM}, K2/MBZUAI llama-server: {self.PORT_K2}"

        if c == "token":
            return self.api_auth.launch_token

        if c == "status":
            state = "running" if engine_running else "stopped"
            return f"Engine: {state} | Mode: {engine_mode} | Port: {self.PORT_K2}"

        # ── Integration commands ──
        if c == "health":
            lines = [
                "=== Stella Integration Health ===",
                f"Budget: ${self.budget.budget():.2f} / ${self.budget.daily_cap():.2f}",
                f"Consented: {', '.join(sorted(self.budget.all_consented())) or 'none'}",
                "",
                "CRM:",
                f"  {self.crm.summary() if self.crm else 'N/A'}",
                "Newsletter:",
                f"  {self.newsletter.summary() if self.newsletter else 'N/A'}",
                "Jobs:",
                f"  {self.jobs.summary() if self.jobs else 'N/A'}",
                "Business Dir:",
                f"  {self.business_dir.summary() if self.business_dir else 'N/A'}",
                "Agent Events:",
                f"  {self.agent_events.summary() if self.agent_events else 'N/A'}",
                "Web Scrape:",
                f"  {self.web_scrape.summary() if self.web_scrape else 'N/A'}",
                "Email Verify:",
                f"  {self.email_verify.summary() if self.email_verify else 'N/A'}",
            ]
            return "\n".join(lines)

        if c == "crm":
            return f"CRM: {self.crm.summary()}" if self.crm else "CRM not available"

        if c == "newsletter":
            return f"Newsletter: {self.newsletter.summary()}" if self.newsletter else "Newsletter not available"

        if c == "jobs":
            return f"Jobs: {self.jobs.summary()}" if self.jobs else "Jobs not available"

        if c == "business":
            return f"Business: {self.business_dir.summary()}" if self.business_dir else "Business dir not available"

        if c == "events":
            return f"Events: {self.agent_events.summary()}" if self.agent_events else "Events not available"

        if c == "scrape":
            return f"Scrape: {self.web_scrape.summary()}" if self.web_scrape else "Scrape not available"

        if c == "email":
            return f"Email: {self.email_verify.summary()}" if self.email_verify else "Email verify not available"

        if c == "budget":
            return f"Budget: ${self.budget.budget():.2f} / ${self.budget.daily_cap():.2f} | Consented: {', '.join(sorted(self.budget.all_consented())) or 'none'}"

        return f"Unknown command: {c}"