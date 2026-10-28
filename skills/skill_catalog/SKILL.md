---
name: skill_catalog
description: Stella's skill catalog: the 'skill find' capability. Lists every skill available on this machine (features/ plus the user-data skills dir), finds skills by keyword, name, alias or trigger, installs a skill package from a local path or inline definition, registers a loaded skill into the dynamic registry, and runs a skill operation. Nothing is symlinked or referenced from outside this project - every installed skill is written into features/ or the user-data skills dir so Stella runs identically on any device. Installs and writes require authorized=true plus confirm=true plus a policy allow rule.
category: system
source: stella
version: 1.0.0
---
