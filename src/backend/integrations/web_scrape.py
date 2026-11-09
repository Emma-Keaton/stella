"""
src/backend/integrations/web_scrape.py — Stella-native web scraper (Firecrawl-inspired).

Self-contained page fetching and text extraction. No connection to Firecrawl or
any external service — uses only Python standard library. Results stored locally
as JSON. Governed by StarNet:
  * BudgetConsentManager — caps scrape operations.
  * SkillsCatalog — gates web scrape skill availability.
"""

from __future__ import annotations

import html
import json
import re
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from core.user_paths import get_user_data_dir
from src.backend.starnet.budget_consent import BudgetConsentManager
from src.backend.starnet.skills_catalog import SkillsCatalog


@dataclass
class ScrapedPage:
    page_id: str
    url: str
    title: str = ""
    markdown: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)
    fetched_at: float = field(default_factory=time.time)
    status_code: int = 0
    error: Optional[str] = None


class WebScrapeManager:
    """Local web scraper. Uses urllib only — no external dependencies."""

    USER_AGENT = "StellaBot/1.0 (+https://stella.local)"

    def __init__(
        self,
        budget: Optional[BudgetConsentManager] = None,
        skills: Optional[SkillsCatalog] = None,
    ) -> None:
        self.budget = budget
        self.skills = skills
        data_dir = get_user_data_dir()
        self._store_dir = data_dir / "integrations" / "web_scrape"
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._pages_path = self._store_dir / "pages.json"
        self._pages: dict[str, ScrapedPage] = {}
        self._load()

    def _load(self) -> None:
        self._pages = self._load_typed(self._pages_path, ScrapedPage)

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
        self._save(self._pages_path, self._pages)

    def _check_budget(self) -> bool:
        if self.budget is not None:
            return self.budget.check_budget(0.01)
        return True

    @staticmethod
    def _html_to_text(raw_html: str) -> str:
        text = raw_html
        text = re.sub(r"<script.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"</(p|div|h[1-6]|li|tr|blockquote|pre)>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    @staticmethod
    def _extract_title(raw_html: str) -> str:
        m = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.DOTALL | re.IGNORECASE)
        if m:
            return html.unescape(m.group(1)).strip()
        return ""

    @staticmethod
    def _extract_links(raw_html: str, base_url: str) -> list[str]:
        links = []
        for m in re.finditer(r'href=["\']([^"\']+)["\']', raw_html, re.IGNORECASE):
            href = m.group(1)
            try:
                absolute = urllib.parse.urljoin(base_url, href)
                links.append(absolute)
            except Exception:
                pass
        seen: set[str] = set()
        out: list[str] = []
        for link in links:
            if link not in seen:
                seen.add(link)
                out.append(link)
        return out[:100]

    def scrape(self, url: str) -> ScrapedPage:
        if self.skills is not None and not self.skills.skill_available("web_scrape"):
            raise PermissionError("Web scrape skill is not available or is revoked.")
        if not self._check_budget():
            raise RuntimeError("Daily budget cap reached for web scrape operations.")

        page_id = uuid.uuid4().hex[:12]
        page = ScrapedPage(page_id=page_id, url=url)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                page.status_code = resp.status
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type.lower():
                    page.text = raw.decode("utf-8", errors="replace")[:50000]
                    page.markdown = page.text
                else:
                    html_text = raw.decode("utf-8", errors="replace")
                    page.title = self._extract_title(html_text)
                    page.text = self._html_to_text(html_text)
                    page.markdown = page.text
                    page.links = self._extract_links(html_text, url)
        except Exception as exc:
            page.error = str(exc)
            page.status_code = 0

        self._pages[page_id] = page
        self._persist()
        if self.budget is not None:
            self.budget.add_spend(0.01)
        return page

    def get_page(self, page_id: str) -> Optional[ScrapedPage]:
        return self._pages.get(page_id)

    def list_pages(self, limit: int = 50) -> list[ScrapedPage]:
        return sorted(self._pages.values(), key=lambda p: p.fetched_at, reverse=True)[:limit]

    def search_pages(self, query: str) -> list[ScrapedPage]:
        q = query.lower()
        results = []
        for p in self._pages.values():
            if q in p.title.lower() or q in p.text.lower() or q in p.url.lower():
                results.append(p)
        return sorted(results, key=lambda p: p.fetched_at, reverse=True)[:50]

    def delete_page(self, page_id: str) -> bool:
        if self.skills is not None and not self.skills.skill_available("web_scrape"):
            raise PermissionError("Web scrape skill is not available or is revoked.")
        if page_id in self._pages:
            del self._pages[page_id]
            self._persist()
            if self.budget is not None:
                self.budget.add_spend(0.01)
            return True
        return False

    def summary(self) -> dict[str, Any]:
        return {
            "pages": len(self._pages),
            "errors": sum(1 for p in self._pages.values() if p.error),
            "total_links": sum(len(p.links) for p in self._pages.values()),
        }