"""
src/backend/integrations/business_dir.py — Stella-native business directory (Google Maps-inspired).

Self-contained local business data (name, address, phone, website, rating, lat/long)
stored locally as JSON. No connection to Google Maps or any external service.
Governed by StarNet:
  * BudgetConsentManager — caps business write operations.
  * SkillsCatalog — gates business directory skill availability.
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
class Business:
    business_id: str
    name: str
    address: str = ""
    phone: str = ""
    website: str = ""
    rating: float = 0.0
    reviews_count: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    category: str = ""
    email: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    custom_fields: dict[str, Any] = field(default_factory=dict)


class BusinessDirManager:
    """Local business directory store. All data persisted as JSON under the user data dir."""

    def __init__(
        self,
        budget: Optional[BudgetConsentManager] = None,
        skills: Optional[SkillsCatalog] = None,
    ) -> None:
        self.budget = budget
        self.skills = skills
        data_dir = get_user_data_dir()
        self._store_dir = data_dir / "integrations" / "business_dir"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._businesses_path = self._store_dir / "businesses.json"
        self._businesses: dict[str, Business] = {}
        self._load()

    def _load(self) -> None:
        self._businesses = self._load_typed(self._businesses_path, Business)

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

    def _persist(self) -> None:
        self._save(self._businesses_path, self._businesses)

    def _check_budget(self) -> bool:
        if self.budget is not None:
            return self.budget.check_budget(0.01)
        return True

    def add_business(
        self,
        name: str,
        address: str = "",
        phone: str = "",
        website: str = "",
        rating: float = 0.0,
        reviews_count: int = 0,
        latitude: float = 0.0,
        longitude: float = 0.0,
        category: str = "",
        email: str = "",
    ) -> Business:
        if self.skills is not None and not self.skills.skill_available("business_dir"):
            raise PermissionError("Business directory skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for business writes.")
        business_id = uuid.uuid4().hex[:12]
        business = Business(
            business_id=business_id,
            name=name,
            address=address,
            phone=phone,
            website=website,
            rating=rating,
            reviews_count=reviews_count,
            latitude=latitude,
            longitude=longitude,
            category=category,
            email=email,
        )
        self._businesses[business_id] = business
        self._persist()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return business

    def get_business(self, business_id: str) -> Optional[Business]:
        return self._businesses.get(business_id)

    def list_businesses(self, category: Optional[str] = None) -> list[Business]:
        businesses = list(self._businesses.values())
        if category:
            businesses = [b for b in businesses if b.category.lower() == category.lower()]
        return sorted(businesses, key=lambda b: b.updated_at, reverse=True)

    def search(self, query: str) -> list[Business]:
        q = query.lower()
        results = []
        for b in self._businesses.values():
            if (
                q in b.name.lower()
                or q in b.address.lower()
                or q in b.category.lower()
                or q in b.phone.lower()
                or q in b.website.lower()
            ):
                results.append(b)
        return sorted(results, key=lambda b: b.updated_at, reverse=True)

    def delete_business(self, business_id: str) -> bool:
        if self.skills is not None and not self.skills.skill_available("business_dir"):
            raise PermissionError("Business directory skill is not available or is revoked.")
        if business_id in self._businesses:
            del self._businesses[business_id]
            self._persist()
            if self.budget is not None:
                self.budget.add_spend(0.01)
            return True
        return False

    def summary(self) -> dict[str, Any]:
        return {
            "businesses": len(self._businesses),
            "categories": sorted({b.category for b in self._businesses.values() if b.category}),
            "with_email": sum(1 for b in self._businesses.values() if b.email),
        }