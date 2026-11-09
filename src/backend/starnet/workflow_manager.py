"""
src/backend/starnet/workflow_manager.py — Workflow / loop definitions (StarNet loops/ port).

Each loop is a reusable multi-step agent routine:
adversarial-reviewer, security-sweep, debt-burner, beginner-run,
red-green-closer, truth-auditor.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    steps: list[str]
    system_prompt: str


class WorkflowManager:
    """Registry of built-in multi-step agent workflows."""

    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(Workflow(
            id="adversarial-reviewer",
            name="Adversarial Reviewer",
            description="Critique your own output from an opposing viewpoint before finalizing.",
            steps=["Generate initial answer", "Adversarial critique", "Revise and finalize"],
            system_prompt=(
                "You are an adversarial reviewer. First produce an answer, "
                "then critique it from an opposing viewpoint, then produce a "
                "final revised answer."
            ),
        ))
        self.register(Workflow(
            id="security-sweep",
            name="Security Sweep",
            description="Scan code or configuration for security issues and suggest fixes.",
            steps=["Analyze input for vulnerabilities", "Identify risks", "Provide remediation steps"],
            system_prompt=(
                "You are a security auditor. Scan the provided input for security "
                "vulnerabilities, identify risks, and provide concrete remediation steps."
            ),
        ))
        self.register(Workflow(
            id="debt-burner",
            name="Debt Burner",
            description="Identify and prioritize technical debt for remediation.",
            steps=["Identify technical debt", "Assess impact", "Prioritize fixes", "Create action plan"],
            system_prompt=(
                "You are a technical debt analyst. Identify technical debt, assess "
                "its impact, prioritize remediation, and create an action plan."
            ),
        ))
        self.register(Workflow(
            id="beginner-run",
            name="Beginner Run",
            description="Step-by-step guided task execution for new users.",
            steps=["Understand the goal", "Break into steps", "Execute each step", "Verify results"],
            system_prompt=(
                "You are a beginner-friendly guide. Break tasks into simple steps, "
                "explain each one, and verify results before moving on."
            ),
        ))
        self.register(Workflow(
            id="red-green-closer",
            name="Red-Green Closer",
            description="TDD-style workflow: write failing test, make it pass, refactor.",
            steps=["Write failing test (red)", "Make test pass (green)", "Refactor", "Verify"],
            system_prompt=(
                "You are a TDD coach. Follow red-green-refactor: write a failing test, "
                "make it pass, refactor, and verify."
            ),
        ))
        self.register(Workflow(
            id="truth-auditor",
            name="Truth Auditor",
            description="Fact-check claims and flag uncertain statements.",
            steps=["Extract claims", "Verify each claim", "Flag uncertain statements", "Provide verdict"],
            system_prompt=(
                "You are a truth auditor. Extract factual claims, verify them, "
                "flag uncertain statements, and provide a confidence verdict."
            ),
        ))

    def register(self, workflow: Workflow) -> None:
        self._workflows[workflow.id] = workflow

    def get(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def all(self) -> list[Workflow]:
        return list(self._workflows.values())

    def available_ids(self) -> list[str]:
        return list(self._workflows.keys())