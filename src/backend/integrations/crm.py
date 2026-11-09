"""
src/backend/integrations/crm.py — Stella-native CRM (Twenty-inspired).

Self-contained contact, deal, and company management with a local JSON store.
No connection to Twenty or any external service. Governed by StarNet:
  * BudgetConsentManager — caps write operations (counts toward daily cap).
  * SkillsCatalog — gates CRM skill availability.
  * CronScheduler — optional scheduled sync/cleanup jobs.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from core.user_paths import get_user_data_dir
from src.backend.starnet.budget_consent import BudgetConsentManager
from src.backend.starnet.skills_catalog import SkillsCatalog


@dataclass
class Contact:
    contact_id: str
    name: str
    email: str
    phone: str = ""
    company: str = ""
    role: str = ""
    notes: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class Company:
    company_id: str
    name: str
    domain: str = ""
    industry: str = ""
    size: str = ""
    address: str = ""
    website: str = ""
    notes: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class Deal:
    deal_id: str
    name: str
    contact_id: str = ""
    company_id: str = ""
    amount: float = 0.0
    stage: str = "lead"
    owner: str = ""
    notes: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    custom_fields: dict[str, Any] = field(default_factory=dict)


class CRMManager:
    """Local CRM store. All data persisted as JSON under the user data dir."""

    def __init__(
        self,
        budget: Optional[BudgetConsentManager] = None,
        skills: Optional[SkillsCatalog] = None,
    ) -> None:
        self.budget = budget
        self.skills = skills
        data_dir = get_user_data_dir()
        self._store_dir = data_dir / "integrations" / "crm"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._contacts_path = self._store_dir / "contacts.json"
        self._companies_path = self._store_dir / "companies.json"
        self._deals_path = self._store_dir / "deals.json"
        self._contacts: dict[str, Contact] = {}
        self._companies: dict[str, Company] = {}
        self._deals: dict[str, Deal] = {}
        self._load()

    def _load(self) -> None:
        self._contacts = self._load_typed(self._contacts_path, Contact)
        self._companies = self._load_typed(self._companies_path, Company)
        self._deals = self._load_typed(self._deals_path, Deal)

    def _load_typed(self, path: Path, cls: type) -> dict[str, Any]:
        try:
            if not path.exists():
                return {}
            raw = json.loads(path.read_text(encoding="utf-8"))
            out: dict[str, Any] = {}
            for key, value in raw.items():
                if isinstance(value, dict):
                    out[key] = cls(**value)
            return out
        except Exception:
            return {}

    def _save(self, path: Path, data: dict[str, Any]) -> None:
        serializable = {k: asdict(v) for k, v in data.items()}
        path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")

    def _persist_all(self) -> None:
        self._save(self._contacts_path, self._contacts)
        self._save(self._companies_path, self._companies)
        self._save(self._deals_path, self._deals)

    def _check_budget(self) -> bool:
        if self.budget is not None:
            return self.budget.check_budget(0.01)
        return True

    def create_contact(
        self,
        name: str,
        email: str,
        phone: str = "",
        company: str = "",
        role: str = "",
        notes: str = "",
        tags: Optional[list[str]] = None,
    ) -> Contact:
        if self.skills is not None and not self.skills.skill_available("crm_contacts"):
            raise PermissionError("CRM contacts skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for CRM writes.")
        contact_id = uuid.uuid4().hex[:12]
        contact = Contact(
            contact_id=contact_id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            role=role,
            notes=notes,
            tags=tags or [],
        )
        self._contacts[contact_id] = contact
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return contact

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        return self._contacts.get(contact_id)

    def list_contacts(self) -> list[Contact]:
        return sorted(self._contacts.values(), key=lambda c: c.updated_at, reverse=True)

    def update_contact(self, contact_id: str, **fields: Any) -> Optional[Contact]:
        if self.skills is not None and not self.skills.skill_available("crm_contacts"):
            raise PermissionError("CRM contacts skill is not available or is revoked.")
        contact = self._contacts.get(contact_id)
        if contact is None:
            return None
        for k, v in fields.items():
            if hasattr(contact, k):
                setattr(contact, k, v)
        contact.updated_at = time.time()
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return contact

    def delete_contact(self, contact_id: str) -> bool:
        if self.skills is not None and not self.skills.skill_available("crm_contacts"):
            raise PermissionError("CRM contacts skill is not available or is revoked.")
        if contact_id in self._contacts:
            del self._contacts[contact_id]
            self._persist_all()
            if self.budget is not None:
                self.budget.add_spend(0.01)
            return True
        return False

    def create_company(
        self,
        name: str,
        domain: str = "",
        industry: str = "",
        size: str = "",
        address: str = "",
        website: str = "",
        notes: str = "",
    ) -> Company:
        if self.skills is not None and not self.skills.skill_available("crm_companies"):
            raise PermissionError("CRM companies skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for CRM writes.")
        company_id = uuid.uuid4().hex[:12]
        company = Company(
            company_id=company_id,
            name=name,
            domain=domain,
            industry=industry,
            size=size,
            address=address,
            website=website,
            notes=notes,
        )
        self._companies[company_id] = company
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return company

    def get_company(self, company_id: str) -> Optional[Company]:
        return self._companies.get(company_id)

    def list_companies(self) -> list[Company]:
        return sorted(self._companies.values(), key=lambda c: c.updated_at, reverse=True)

    def create_deal(
        self,
        name: str,
        amount: float = 0.0,
        stage: str = "lead",
        contact_id: str = "",
        company_id: str = "",
        owner: str = "",
        notes: str = "",
    ) -> Deal:
        if self.skills is not None and not self.skills.skill_available("crm_deals"):
            raise PermissionError("CRM deals skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for CRM writes.")
        deal_id = uuid.uuid4().hex[:12]
        deal = Deal(
            deal_id=deal_id,
            name=name,
            amount=amount,
            stage=stage,
            contact_id=contact_id,
            company_id=company_id,
            owner=owner,
            notes=notes,
        )
        self._deals[deal_id] = deal
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return deal

    def get_deal(self, deal_id: str) -> Optional[Deal]:
        return self._deals.get(deal_id)

    def list_deals(self) -> list[Deal]:
        return sorted(self._deals.values(), key=lambda d: d.updated_at, reverse=True)

    def update_deal_stage(self, deal_id: str, stage: str) -> Optional[Deal]:
        deal = self._deals.get(deal_id)
        if deal is None:
            return None
        deal.stage = stage
        deal.updated_at = time.time()
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return deal

    def summary(self) -> dict[str, Any]:
        return {
            "contacts": len(self._contacts),
            "companies": len(self._companies),
            "deals": len(self._deals),
            "deal_stages": {
                stage: sum(1 for d in self._deals.values() if d.stage == stage)
                for stage in {"lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"}
            },
        }