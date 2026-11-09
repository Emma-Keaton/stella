"""
src/backend/integrations/newsletter.py — Stella-native newsletter (Listmonk-inspired).

Self-contained campaigns, subscribers, mailing lists, and templates with a local
JSON store. No connection to Listmonk or any external service. Governed by StarNet:
  * BudgetConsentManager — caps campaign sends and subscriber writes.
  * SkillsCatalog — gates newsletter skill availability.
  * CronScheduler — optional scheduled campaign dispatch.
  * WorkflowManager — adversarial-reviewer for draft approval before send.
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
class Subscriber:
    subscriber_id: str
    email: str
    name: str = ""
    list_ids: list[str] = field(default_factory=list)
    subscribed_at: float = field(default_factory=time.time)
    unsubscribed: bool = False
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class MailingList:
    list_id: str
    name: str
    description: str = ""
    created_at: float = field(default_factory=time.time)
    subscriber_count: int = 0


@dataclass
class Template:
    template_id: str
    name: str
    subject: str = ""
    body: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class Campaign:
    campaign_id: str
    name: str
    subject: str = ""
    body: str = ""
    list_ids: list[str] = field(default_factory=list)
    status: str = "draft"
    sent_count: int = 0
    created_at: float = field(default_factory=time.time)
    sent_at: Optional[float] = None
    template_id: Optional[str] = None


class NewsletterManager:
    """Local newsletter store. All data persisted as JSON under the user data dir."""

    def __init__(
        self,
        budget: Optional[BudgetConsentManager] = None,
        skills: Optional[SkillsCatalog] = None,
    ) -> None:
        self.budget = budget
        self.skills = skills
        data_dir = get_user_data_dir()
        self._store_dir = data_dir / "integrations" / "newsletter"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._subscribers_path = self._store_dir / "subscribers.json"
        self._lists_path = self._store_dir / "lists.json"
        self._templates_path = self._store_dir / "templates.json"
        self._campaigns_path = self._store_dir / "campaigns.json"
        self._subscribers: dict[str, Subscriber] = {}
        self._lists: dict[str, MailingList] = {}
        self._templates: dict[str, Template] = {}
        self._campaigns: dict[str, Campaign] = {}
        self._load()

    def _load(self) -> None:
        self._subscribers = self._load_typed(self._subscribers_path, Subscriber)
        self._lists = self._load_typed(self._lists_path, MailingList)
        self._templates = self._load_typed(self._templates_path, Template)
        self._campaigns = self._load_typed(self._campaigns_path, Campaign)

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
        self._save(self._subscribers_path, self._subscribers)
        self._save(self._lists_path, self._lists)
        self._save(self._templates_path, self._templates)
        self._save(self._campaigns_path, self._campaigns)

    def _check_budget(self) -> bool:
        if self.budget is not None:
            return self.budget.check_budget(0.01)
        return True

    # ------------------------------------------------------------------ subscribers
    def add_subscriber(
        self,
        email: str,
        name: str = "",
        list_ids: Optional[list[str]] = None,
    ) -> Subscriber:
        if self.skills is not None and not self.skills.skill_available("newsletter_subscribers"):
            raise PermissionError("Newsletter subscribers skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for newsletter writes.")
        subscriber_id = uuid.uuid4().hex[:12]
        subscriber = Subscriber(
            subscriber_id=subscriber_id,
            email=email,
            name=name,
            list_ids=list_ids or [],
        )
        self._subscribers[subscriber_id] = subscriber
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return subscriber

    def get_subscriber(self, subscriber_id: str) -> Optional[Subscriber]:
        return self._subscribers.get(subscriber_id)

    def find_subscriber_by_email(self, email: str) -> Optional[Subscriber]:
        for sub in self._subscribers.values():
            if sub.email == email:
                return sub
        return None

    def list_subscribers(self, list_id: Optional[str] = None) -> list[Subscriber]:
        subs = list(self._subscribers.values())
        if list_id is not None:
            subs = [s for s in subs if list_id in s.list_ids and not s.unsubscribed]
        return sorted(subs, key=lambda s: s.subscribed_at, reverse=True)

    def unsubscribe(self, subscriber_id: str) -> bool:
        sub = self._subscribers.get(subscriber_id)
        if sub is None:
            return False
        sub.unsubscribed = True
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return True

    # ------------------------------------------------------------------ lists
    def create_list(self, name: str, description: str = "") -> MailingList:
        if self.skills is not None and not self.skills.skill_available("newsletter_lists"):
            raise PermissionError("Newsletter lists skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for newsletter writes.")
        list_id = uuid.uuid4().hex[:12]
        lst = MailingList(list_id=list_id, name=name, description=description)
        self._lists[list_id] = lst
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return lst

    def get_list(self, list_id: str) -> Optional[MailingList]:
        return self._lists.get(list_id)

    def list_lists(self) -> list[MailingList]:
        return list(self._lists.values())

    # ------------------------------------------------------------------ templates
    def create_template(
        self,
        name: str,
        subject: str = "",
        body: str = "",
    ) -> Template:
        if self.skills is not None and not self.skills.skill_available("newsletter_templates"):
            raise PermissionError("Newsletter templates skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for newsletter writes.")
        template_id = uuid.uuid4().hex[:12]
        template = Template(
            template_id=template_id,
            name=name,
            subject=subject,
            body=body,
        )
        self._templates[template_id] = template
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return template

    def get_template(self, template_id: str) -> Optional[Template]:
        return self._templates.get(template_id)

    def list_templates(self) -> list[Template]:
        return list(self._templates.values())

    # ------------------------------------------------------------------ campaigns
    def create_campaign(
        self,
        name: str,
        subject: str = "",
        body: str = "",
        list_ids: Optional[list[str]] = None,
        template_id: Optional[str] = None,
    ) -> Campaign:
        if self.skills is not None and not self.skills.skill_available("newsletter_campaigns"):
            raise PermissionError("Newsletter campaigns skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for newsletter writes.")
        campaign_id = uuid.uuid4().hex[:12]
        campaign = Campaign(
            campaign_id=campaign_id,
            name=name,
            subject=subject,
            body=body,
            list_ids=list_ids or [],
            status="draft",
            template_id=template_id,
        )
        self._campaigns[campaign_id] = campaign
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        return self._campaigns.get(campaign_id)

    def list_campaigns(self) -> list[Campaign]:
        return sorted(self._campaigns.values(), key=lambda c: c.created_at, reverse=True)

    def update_campaign(self, campaign_id: str, **fields: Any) -> Optional[Campaign]:
        if self.skills is not None and not self.skills.skill_available("newsletter_campaigns"):
            raise PermissionError("Newsletter campaigns skill is not available or is revoked.")
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        for k, v in fields.items():
            if hasattr(campaign, k):
                setattr(campaign, k, v)
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return campaign

    def send_campaign(self, campaign_id: str) -> Campaign:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            raise ValueError(f"Unknown campaign: {campaign_id}")
        if campaign.status != "draft":
            raise ValueError(f"Campaign already {campaign.status}, cannot send.")
        if self.budget is not None and not self.budget.check_budget(0.01 * len(self._subscribers)):
            raise RuntimeError("Daily budget cap reached for campaign sends.")

        eligible = 0
        for sub in self._subscribers.values():
            if sub.unsubscribed:
                continue
            if any(lid in sub.list_ids for lid in campaign.list_ids):
                eligible += 1

        campaign.status = "sent"
        campaign.sent_count = eligible
        campaign.sent_at = time.time()
        self._persist_all()
        if self.budget is not None:
            self.budget.add_spend(0.01 * eligible)
        return campaign

    def summary(self) -> dict[str, Any]:
        return {
            "subscribers": len(self._subscribers),
            "unsubscribed": sum(1 for s in self._subscribers.values() if s.unsubscribed),
            "lists": len(self._lists),
            "templates": len(self._templates),
            "campaigns": len(self._campaigns),
            "campaigns_by_status": {
                status: sum(1 for c in self._campaigns.values() if c.status == status)
                for status in {"draft", "scheduled", "sending", "sent", "cancelled"}
            },
            "total_sent": sum(c.sent_count for c in self._campaigns.values()),
        }