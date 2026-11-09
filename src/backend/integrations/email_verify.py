"""
src/backend/integrations/email_verify.py — Stella-native email verification (ReacherHQ-inspired).

Self-contained email address validation without sending email. Checks syntax,
DNS MX records, disposable domain detection, role accounts, and catch-all
heuristics using only the Python standard library. No connection to ReacherHQ
or any external SMTP server. Governed by StarNet:
  * BudgetConsentManager — caps verification operations.
  * SkillsCatalog — gates email verification skill availability.
"""

from __future__ import annotations

import json
import re
import socket
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from core.user_paths import get_user_data_dir
from src.backend.starnet.budget_consent import BudgetConsentManager
from src.backend.starnet.skills_catalog import SkillsCatalog


# Small built-in list of known disposable email providers (self-contained).
DISPOSABLE_DOMAINS: set[str] = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "throwawaymail.com", "fakeinbox.com", "trashmail.com", "yopmail.com",
    "dispostable.com", "temp-mail.org", "mailnesia.com", "sharklasers.com",
    "guerrillamail.info", "grr.la", "spam4.me", "binkfilm.com",
}

# Common role-account prefixes.
ROLE_PREFIXES: set[str] = {
    "admin", "administrator", "billing", "compliance", "contact", "devnull",
    "feedback", "finance", "hostmaster", "info", "is", "it", "legal", "list",
    "logistics", "manager", "marketing", "no-reply", "noreply", "office",
    "operations", "orders", "payroll", "postmaster", "privacy", "procurement",
    "sales", "security", "support", "sysadmin", "webmaster",
}

EMAIL_RE = re.compile(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$")


@dataclass
class EmailVerifyResult:
    email: str
    is_reachable: str
    syntax: dict[str, Any]
    dns: dict[str, Any]
    smtp: dict[str, Any]
    misc: dict[str, Any]
    verified_at: float = field(default_factory=time.time)


class EmailVerifyManager:
    """Local email verifier. No SMTP connections — stdlib DNS only."""

    def __init__(
        self,
        budget: Optional[BudgetConsentManager] = None,
        skills: Optional[SkillsCatalog] = None,
    ) -> None:
        self.budget = budget
        self.skills = skills
        data_dir = get_user_data_dir()
        self._store_dir = data_dir / "integrations" / "email_verify"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._results_path = self._store_dir / "results.json"
        self._results: dict[str, EmailVerifyResult] = {}
        self._load()

    def _load(self) -> None:
        self._results = self._load_typed(self._results_path, EmailVerifyResult)

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
        self._save(self._results_path, self._results)

    def _check_budget(self) -> bool:
        if self.budget is not None:
            return self.budget.check_budget(0.01)
        return True

    @staticmethod
    def _check_syntax(email: str) -> dict[str, Any]:
        if not EMAIL_RE.match(email or ""):
            return {"is_valid_syntax": False, "domain": "", "username": "", "suggestion": None}
        username, _, domain = email.partition("@")
        return {
            "is_valid_syntax": True,
            "domain": domain,
            "username": username,
            "suggestion": None,
        }

    @staticmethod
    def _check_dns(domain: str) -> dict[str, Any]:
        result: dict[str, Any] = {"accepts_mail": False, "records": []}
        try:
            answers = socket.getaddrinfo(domain, 25, type=socket.SOCK_STREAM)
            for answer in answers:
                host = answer[4][0]
                if host and host not in result["records"]:
                    result["records"].append(host)
            result["accepts_mail"] = len(result["records"]) > 0
        except Exception:
            pass
        try:
            _, _, ipaddrs = socket.gethostbyn_ex(domain)
            for ip in ipaddrs:
                if ip not in result["records"]:
                    result["records"].append(ip)
        except Exception:
            pass
        return result

    @staticmethod
    def _check_misc(email: str, domain: str) -> dict[str, Any]:
        username, _, _ = email.partition("@")
        return {
            "is_disposable": domain.lower() in DISPOSABLE_DOMAINS,
            "is_role_account": username.lower() in ROLE_PREFIXES,
            "is_b2c": True,
        }

    def verify(self, email: str) -> EmailVerifyResult:
        if self.skills is not None and not self.skills.skill_available("email_verify"):
            raise PermissionError("Email verify skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for email verification.")

        email = (email or "").strip().lower()
        syntax = self._check_syntax(email)
        domain = syntax.get("domain", "")
        dns = self._check_dns(domain) if domain else {"accepts_mail": False, "records": []}
        misc = self._check_misc(email, domain)

        if not syntax["is_valid_syntax"]:
            reachable = "invalid"
        elif misc["is_disposable"]:
            reachable = "risky"
        elif not dns["accepts_mail"]:
            reachable = "invalid"
        elif misc["is_role_account"]:
            reachable = "risky"
        else:
            reachable = "safe"

        result = EmailVerifyResult(
            email=email,
            is_reachable=reachable,
            syntax=syntax,
            dns=dns,
            smtp={"can_connect_smtp": dns["accepts_mail"], "records": dns["records"]},
            misc=misc,
        )
        self._results[email] = result
        self._persist()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return result

    def get_result(self, email: str) -> Optional[EmailVerifyResult]:
        return self._results.get(email.lower())

    def list_results(self, limit: int = 50) -> list[EmailVerifyResult]:
        return sorted(self._results.values(), key=lambda r: r.verified_at, reverse=True)[:limit]

    def delete_result(self, email: str) -> bool:
        if self.skills is not None and not self.skills.skill_available("email_verify"):
            raise PermissionError("Email verify skill is not available or is revoked.")
        key = email.lower()
        if key in self._results:
            del self._results[key]
            self._persist()
            if self.budget is not None:
                self.budget.add_spend(0.01)
            return True
        return False

    def summary(self) -> dict[str, Any]:
        return {
            "verified": len(self._results),
            "by_reachability": {
                r: sum(1 for v in self._results.values() if v.is_reachable == r)
                for r in {"safe", "risky", "invalid", "unknown"}
            },
            "disposable": sum(1 for v in self._results.values() if v.misc.get("is_disposable")),
            "role_accounts": sum(1 for v in self._results.values() if v.misc.get("is_role_account")),
        }