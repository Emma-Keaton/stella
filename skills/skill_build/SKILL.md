---
name: skill_build
description: Skill builder: validates, compiles, and runs test_cases for a Stella skill package. Checks manifest.json validity, FEATURE_METADATA/manifest agreement, compiles skill.py with py_compile, and runs the skill's test_cases.json against its execute(). Reports per-test pass/fail with reasons. Reads only - never writes to skill files. Use skill_add to create and skill_update to modify; skill_build is the verify step in the add → build → update lifecycle. No symlinks or external PC references.
category: system
source: stella
version: 1.0.0
---
