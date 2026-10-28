#!/usr/bin/env python3
"""
recouple_skills.py — Recouple existing features/ skills into the new skills/ layer.

For each feature in features/:
  1. Reads manifest.json for metadata
  2. Creates SKILL.md with YAML frontmatter (name, description, category, source, version)
  3. Copies skill.py + SKILL.md into skills/<slug>/
  4. Updates skills-lock.json with the skill entry

Skills without an execute() function are noted but still copied (with a wrapper).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = REPO_ROOT / "features"
SKILLS_DIR = REPO_ROOT / "skills"
LOCK_FILE = SKILLS_DIR / "skills-lock.json"


def load_lock() -> dict:
    if LOCK_FILE.exists():
        try:
            return json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": 1, "skills": {}}


def save_lock(lock: dict) -> None:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps(lock, indent=2), encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def create_skill_md(manifest: dict, slug: str) -> str:
    """Generate SKILL.md frontmatter from manifest.json."""
    name = manifest.get("name", slug)
    description = manifest.get("description", "")
    category = manifest.get("category", "general")
    version = manifest.get("version", "1.0.0")
    source = "stella"

    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f"category: {category}",
        f"source: {source}",
        f"version: {version}",
        "---",
    ]
    return "\n".join(lines) + "\n"


def has_execute(skill_py: Path) -> bool:
    """Check if skill.py has a top-level execute() function."""
    try:
        text = skill_py.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("def execute("):
                return True
    except Exception:
        pass
    return False


def main() -> None:
    lock = load_lock()
    skills = lock.setdefault("skills", {})

    if not FEATURES_DIR.exists():
        print(f"Features directory not found: {FEATURES_DIR}")
        return

    feature_dirs = sorted([d for d in FEATURES_DIR.iterdir() if d.is_dir()])
    print(f"Found {len(feature_dirs)} feature skills")

    for feature_dir in feature_dirs:
        slug = feature_dir.name
        manifest_path = feature_dir / "manifest.json"
        skill_py_path = feature_dir / "skill.py"

        if not manifest_path.exists() or not skill_py_path.exists():
            print(f"  SKIP {slug}: missing manifest.json or skill.py")
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  SKIP {slug}: invalid manifest.json ({e})")
            continue

        # Check for execute()
        has_exec = has_execute(skill_py_path)
        if not has_exec:
            print(f"  WARN {slug}: no execute() function — will need wrapper")

        # Create skills/<slug>/ directory
        target_dir = SKILLS_DIR / slug
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy skill.py
        shutil.copy2(skill_py_path, target_dir / "skill.py")

        # Create SKILL.md
        skill_md = create_skill_md(manifest, slug)
        (target_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

        # Copy test_cases.json if present
        test_cases = feature_dir / "test_cases.json"
        if test_cases.exists():
            shutil.copy2(test_cases, target_dir / "test_cases.json")

        # Update lock
        skills[slug] = {
            "hash": file_hash(target_dir / "skill.py"),
            "version": manifest.get("version", "1.0.0"),
            "source": "features",
        }

        print(f"  OK   {slug} -> skills/{slug}/ (execute={has_exec})")

    save_lock(lock)
    print(f"\nRecoupled {len(skills)} skills. Lock file updated: {LOCK_FILE}")


if __name__ == "__main__":
    main()
