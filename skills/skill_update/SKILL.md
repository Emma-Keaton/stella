---
name: skill_update
description: Context-aware skill updater. Tracks how the user interacts with each skill (what they asked, what the skill returned, whether it was correct), records preference signals (accept/reject/correct) plus free-form context, and applies those preferences to skill files. Safely edits manifest.json (description, triggers, aliases, version, category, surface, requires, parameters), bumps semantic versions, keeps a per-skill change history for rollback, and records interaction context so the agent can tune skills over time. Nothing is rewritten blindly: Python skill.py changes are flagged for manual review or done as safe targeted string replacements; every write is versioned and revertible. Writes to disk, so install/update needs authorized=true plus confirm=true plus a policy allow rule.
category: system
source: stella
version: 1.0.0
---
