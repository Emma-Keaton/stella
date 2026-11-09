"""
src/backend/starnet/skills_catalog.py — Skills catalog (StarNet skills-catalog/ port).

Loads originals.json (full skill definitions keyed by skill id) and
revoked.json (list of revoked skill ids that must never be loaded).
skill_available(id) returns True only when the skill exists in originals
and is not revoked.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SkillsCatalog:
    """Read-only skill catalog backed by originals.json / revoked.json files."""

    def __init__(self) -> None:
        self._originals: dict[str, dict[str, Any]] = {}
        self._revoked: set[str] = set()

    def load_from_dir(self, directory: str | Path) -> None:
        """Load originals.json and revoked.json from `directory`."""
        dir_path = Path(directory)
        origs_file = dir_path / "originals.json"
        revoked_file = dir_path / "revoked.json"

        if origs_file.exists():
            try:
                obj = json.loads(origs_file.read_text(encoding="utf-8"))
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, dict):
                            self._originals[key] = value
            except Exception:
                pass

        if revoked_file.exists():
            try:
                arr = json.loads(revoked_file.read_text(encoding="utf-8"))
                if isinstance(arr, list):
                    for item in arr:
                        if isinstance(item, str):
                            self._revoked.add(item)
            except Exception:
                pass

    def skill_available(self, skill_id: str) -> bool:
        return skill_id in self._originals and skill_id not in self._revoked

    def get_skill(self, skill_id: str) -> dict[str, Any] | None:
        return self._originals.get(skill_id)

    def all_skills(self) -> list[str]:
        return [sid for sid in self._originals if self.skill_available(sid)]

    def is_revoked(self, skill_id: str) -> bool:
        return skill_id in self._revoked

    def register_skill(self, skill_id: str, definition: Optional[dict[str, Any]] = None) -> None:
        """Register a skill as available (not revoked)."""
        self._originals[skill_id] = definition or {
            "id": skill_id, "name": skill_id, "enabled": True,
        }