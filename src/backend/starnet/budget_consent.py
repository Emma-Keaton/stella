"""
src/backend/starnet/budget_consent.py — Budget / consent tracking (StarNet budget model port).

Daily spend cap in USD. Tool consent is granted/revoked via CLI or UI.
checkBudget(estimated_usd) returns False when the daily cap would be exceeded.
"""

from __future__ import annotations


class BudgetConsentManager:
    """Tracks daily spend and per-tool consent grants."""

    def __init__(self, daily_cap_usd: float = 5.0) -> None:
        self._budget_usd: float = 0.0
        self._daily_cap_usd: float = daily_cap_usd
        self._consent_granted: set[str] = set()

    def set_budget(self, usd: float) -> None:
        self._budget_usd = float(usd)

    def budget(self) -> float:
        return self._budget_usd

    def daily_cap(self) -> float:
        return self._daily_cap_usd

    def check_budget(self, estimated_usd: float) -> bool:
        return self._budget_usd + float(estimated_usd) <= self._daily_cap_usd

    def add_spend(self, usd: float) -> None:
        self._budget_usd += float(usd)

    def grant_consent(self, tool_name: str) -> None:
        self._consent_granted.add(tool_name)

    def revoke_consent(self, tool_name: str) -> None:
        self._consent_granted.discard(tool_name)

    def has_consent(self, tool_name: str) -> bool:
        return tool_name in self._consent_granted

    def all_consented(self) -> set[str]:
        return set(self._consent_granted)