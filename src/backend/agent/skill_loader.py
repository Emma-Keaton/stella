"""
src/backend/agent/skill_loader.py — Loads skills from skills/ (SKILL.md + skill.py).

Follows OpenBot's skill packaging pattern: each skill is a folder with
SKILL.md (YAML frontmatter) + skill.py (execute(**kwargs)). Versioned via
skills-lock.json. Disabled skills live in skills-disabled/.
"""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("stella.agent.skill_loader")


def _parse_skill_md(path: Path) -> Optional[dict]:
    """Parse YAML frontmatter from SKILL.md."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Cannot read %s: %s", path, e)
        return None

    if not text.startswith("---"):
        return None

    end = text.find("\n---", 3)
    if end == -1:
        return None

    front = text[3:end]
    data: dict = {}
    for line in front.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip().strip('"').strip("'")
    return data


class SkillLoader:
    """Loads skills from the skills/ directory."""

    def __init__(self, skills_dir: Path, lock_file: Path) -> None:
        self.skills_dir = skills_dir
        self.lock_file = lock_file
        self._skills: Dict[str, dict] = {}
        self._lock: Dict[str, Any] = {}

    def load_all(self) -> List[dict]:
        """Load all enabled skills. Returns list of skill declarations."""
        self._load_lock()
        declarations = []

        if not self.skills_dir.exists():
            logger.warning("Skills directory does not exist: %s", self.skills_dir)
            return declarations

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith("_"):
                continue
            if skill_dir.name == "skills-disabled":
                continue

            skill = self._load_skill(skill_dir)
            if skill:
                self._skills[skill["slug"]] = skill
                declarations.append(self._declaration(skill))

        logger.info("Loaded %d skills", len(self._skills))
        return declarations

    def _load_lock(self) -> None:
        """Load skills-lock.json for version hashes."""
        if self.lock_file.exists():
            try:
                self._lock = json.loads(self.lock_file.read_text(encoding="utf-8"))
            except Exception:
                self._lock = {}
        else:
            self._lock = {}

    def _load_skill(self, skill_dir: Path) -> Optional[dict]:
        """Load a single skill: SKILL.md + skill.py."""
        skill_md = skill_dir / "SKILL.md"
        skill_py = skill_dir / "skill.py"

        if not skill_md.exists() or not skill_py.exists():
            logger.warning("Skill %s missing SKILL.md or skill.py", skill_dir.name)
            return None

        front = _parse_skill_md(skill_md)
        if not front:
            return None

        slug = skill_dir.name
        name = front.get("name", slug)

        # Import skill.py dynamically
        try:
            spec = importlib.util.spec_from_file_location(f"stella.skills.{slug}", skill_py)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error("Failed to import skill %s: %s", slug, e)
            return None

        execute = getattr(module, "execute", None)
        if not callable(execute):
            logger.warning("Skill %s has no callable execute()", slug)
            return None

        # Compute file hash for lock
        import hashlib
        h = hashlib.sha256(skill_py.read_bytes()).hexdigest()[:12]
        lock_entry = self._lock.get(slug, {})
        lock_entry["hash"] = h
        lock_entry["version"] = lock_entry.get("version", "1.0.0")

        return {
            "slug": slug,
            "name": name,
            "description": front.get("description", ""),
            "category": front.get("category", "general"),
            "source": front.get("source", "stella"),
            "version": lock_entry.get("version", "1.0.0"),
            "hash": h,
            "execute": execute,
            "path": str(skill_dir),
        }

    def _declaration(self, skill: dict) -> dict:
        """Convert skill to declaration for the agent."""
        return {
            "name": skill["slug"],
            "description": skill["description"],
            "parameters": {
                "type": "OBJECT",
                "properties": {},
                "required": [],
            },
            "tier": "extra",
            "brief": skill["description"],
        }

    def execute(self, slug: str, parameters: dict) -> str:
        """Execute a skill by slug."""
        skill = self._skills.get(slug)
        if not skill:
            raise KeyError(f"Unknown skill: {slug}")
        execute = skill["execute"]
        try:
            result = execute(**parameters) if parameters else execute()
        except TypeError:
            result = execute(parameters=parameters)
        if result is None:
            return ""
        return str(result)

    def list_skills(self) -> List[dict]:
        """List all loaded skills with metadata."""
        return [
            {
                "slug": s["slug"],
                "name": s["name"],
                "description": s["description"],
                "category": s["category"],
                "source": s["source"],
                "version": s["version"],
                "enabled": True,
            }
            for s in self._skills.values()
        ]

    def save_lock(self) -> None:
        """Persist skills-lock.json."""
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.write_text(json.dumps(self._lock, indent=2), encoding="utf-8")
