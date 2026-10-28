#!/usr/bin/env python3
"""
recouple_single_files.py — Recouple single-file features into skills/.

Single .py files at features/ root (e.g. check_current_stock_prices.py)
don't have manifest.json, so SKILL.md is created from the file docstring.
"""

from __future__ import annotations

import hashlib
import json
import re
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


def extract_description(text: str, slug: str) -> str:
    """Extract description from module docstring or use fallback."""
    # Try to find module docstring
    match = re.match(r'"""(.*?)"""', text, re.DOTALL)
    if match:
        doc = match.group(1).strip()
        # First non-empty line after stripping
        for line in doc.splitlines():
            line = line.strip()
            if line and not line.startswith("Usage") and not line.startswith("from") and not line.startswith("import"):
                return line[:200]
    return f"{slug} skill"


def main() -> None:
    lock = load_lock()
    skills = lock.setdefault("skills", {})

    single_files = [f for f in FEATURES_DIR.iterdir()
                    if f.suffix == ".py" and f.name != "__init__.py"]

    print(f"Found {len(single_files)} single-file features")

    for f in single_files:
        slug = f.stem  # filename without .py

        # Skip theme_tokens (helper library, no execute)
        text = f.read_text(encoding="utf-8", errors="ignore")
        if "def execute(" not in text:
            print(f"  SKIP {slug}: no execute() (helper library)")
            continue

        description = extract_description(text, slug)

        # Create skills/<slug>/ directory
        target_dir = SKILLS_DIR / slug
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy skill.py
        shutil.copy2(f, target_dir / "skill.py")

        # Create SKILL.md
        skill_md = f"""---
name: {slug}
description: {description}
category: general
source: stella
version: 1.0.0
---
"""
        (target_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

        # Update lock
        skills[slug] = {
            "hash": file_hash(target_dir / "skill.py"),
            "version": "1.0.0",
            "source": "features",
        }

        print(f"  OK   {slug} -> skills/{slug}/")

    save_lock(lock)
    print(f"\nDone. Lock file updated: {LOCK_FILE}")


if __name__ == "__main__":
    main()
