---
name: skill_add
description: Skill creator: builds new Stella skill packages from a spec. Generates manifest.json, skill.py, test_cases.json, and __init__.py following Stella's skill contract (FEATURE_METADATA + execute(**kwargs)). Supports built-in templates (read_only_tool, read_write_tool, passive_osint, active_audit) or a fully custom spec. Validates the spec before writing, previews what will be created, and never overwrites an existing skill. Writes into features/<name>/, so creating a skill needs authorized=true plus confirm=true plus a policy allow rule. No symlinks or external PC references - everything is written fresh inside this project.
category: system
source: stella
version: 1.0.0
---
