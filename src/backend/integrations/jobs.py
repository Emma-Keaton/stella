"""
src/backend/integrations/jobs.py — Stella-native job board (Remote Jobs-inspired).

Self-contained remote company directory with job listings stored locally as JSON.
No connection to remoteintech or any external service. Governed by StarNet:
  * BudgetConsentManager — caps job write operations.
  * SkillsCatalog — gates job board skill availability.
  * CronScheduler — optional scheduled refresh/cleanup jobs.
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
class JobListing:
    job_id: str
    company: str
    title: str
    url: str = ""
    location: str = "Remote"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    posted_at: float = field(default_factory=time.time)
    source: str = "stella"
    custom_fields: dict[str, Any] = field(default_factory=dict)


class JobsManager:
    """Local job board store. All data persisted as JSON under the user data dir."""

    def __init__(
        self,
        budget: Optional[BudgetConsentManager] = None,
        skills: Optional[SkillsCatalog] = None,
    ) -> None:
        self.budget = budget
        self.skills = skills
        data_dir = get_user_data_dir()
        self._store_dir = data_dir / "integrations" / "jobs"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._jobs_path = self._store_dir / "jobs.json"
        self._jobs: dict[str, JobListing] = {}
        self._load()

    def _load(self) -> None:
        self._jobs = self._load_typed(self._jobs_path, JobListing)

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
        self._save(self._jobs_path, self._jobs)

    def _check_budget(self) -> bool:
        if self.budget is not None:
            return self.budget.check_budget(0.01)
        return True

    def add_listing(
        self,
        company: str,
        title: str,
        url: str = "",
        location: str = "Remote",
        description: str = "",
        tags: Optional[list[str]] = None,
        source: str = "stella",
    ) -> JobListing:
        if self.skills is not None and not self.skills.skill_available("jobs_board"):
            raise PermissionError("Jobs board skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for job writes.")
        job_id = uuid.uuid4().hex[:12]
        listing = JobListing(
            job_id=job_id,
            company=company,
            title=title,
            url=url,
            location=location,
            description=description,
            tags=tags or [],
            source=source,
        )
        self._jobs[job_id] = listing
        self._persist()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return listing

    def get_listing(self, job_id: str) -> Optional[JobListing]:
        return self._jobs.get(job_id)

    def list_listings(self, tag: Optional[str] = None, company: Optional[str] = None) -> list[JobListing]:
        listings = list(self._jobs.values())
        if tag:
            listings = [j for j in listings if tag in j.tags]
        if company:
            listings = [j for j in listings if company.lower() in j.company.lower()]
        return sorted(listings, key=lambda j: j.posted_at, reverse=True)

    def search(self, query: str) -> list[JobListing]:
        q = query.lower()
        results = []
        for j in self._jobs.values():
            if q in j.title.lower() or q in j.company.lower() or q in j.description.lower():
                results.append(j)
        return sorted(results, key=lambda j: j.posted_at, reverse=True)

    def delete_listing(self, job_id: str) -> bool:
        if self.skills is not None and not self.skills.skill_available("jobs_board"):
            raise PermissionError("Jobs board skill is not available or is revoked.")
        if job_id in self._jobs:
            del self._jobs[job_id]
            self._persist()
            if self.budget is not None:
                self.budget.add_spend(0.01)
            return True
        return False

    def summary(self) -> dict[str, Any]:
        return {
            "jobs": len(self._jobs),
            "companies": len({j.company for j in self._jobs.values()}),
            "tags": sorted({t for j in self._jobs.values() for t in j.tags}),
        }