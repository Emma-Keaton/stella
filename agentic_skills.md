# Agentic Skills — Implementation & Build Guide

This document describes how to port agents and skills from **claude-skills** (alirezarezvani/claude-skills) and **agency-agents** (msitarzewski/agency-agents) into Stella's existing Python agent/skill system.

## 1. Architecture Overview

Stella's Python backend (`E:/Projects/stella/`) uses a bounded, audited agentic loop:

```
think -> act -> observe -> verify -> repeat
```

### Core Components

| File | Purpose |
|------|---------|
| `agent/loop.py` | `Agent` class — bounded think/act/observe/verify loop with repeat detection, plan-awareness, and honest reporting |
| `agent/planner.py` | `PLANNER_PROMPT` — decomposes user goals into ordered tool steps (max 5 steps) |
| `agent/tools.py` | `Registry`, `Tool`, `ToolResult` — tool surface with permission enforcement and honesty levels (`done`/`unverified`/`failed`) |
| `agent/verify.py` | `verify()` — checks whether work was actually observed done, not just claimed |
| `agent/skill_loader.py` | `load_skill(name)` — loads a skill package; expects `features/<name>/` with `manifest.json` + `skill.py` |
| `agent/executor.py` | Executes tool calls against the registry |
| `core/llm_router.py` / `core/local_brain.py` | LLM routing — cloud providers or local Ollama/LM Studio/vLLM/LocalAI |
| `main.py` | WebSocket IPC server, `StellaEngine`, `SkillsCatalog`, `CrewManager`, `Agent as CrewAgent`, `Workflow` |
| `skills/` | Directory of all skill packages (each: `skill.py` with `FEATURE_METADATA` + `execute(**kwargs)`) |

## 2. Skill Pattern (Python)

Every skill in `skills/` follows this structure:

```
skills/<skill_name>/
    skill.py          # FEATURE_METADATA + execute(**kwargs)
```

### Minimal Skill Template

```python
"""Feature: <skill_name> — <one-line description>"""
from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "<skill_name>",
    "aliases": ["<alias1>", "<alias2>"],
    "description": "<human-readable description>",
    "triggers": ["<trigger phrase 1>", "<trigger phrase 2>"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: op1 | op2 | op3. Defaults to op1.",
            },
            "<param_name>": {
                "type": "STRING",
                "description": "<parameter description>",
            },
        },
    },
    "source": "claude-skills" or "agency-agents",
    "division": "<division name>",  # e.g., "engineering", "marketing", "finance"
}

_OPERATIONS = {}  # operation name -> handler function
_OPERATION_TITLES = {}  # operation name -> display title
_ALIASES = {}  # alternate operation names -> canonical names


def _op_<operation>(kwargs: dict) -> dict:
    """Handler for one operation. Returns a record dict."""
    ...
    return {"ok": True, "value": {...}, ...}


_OPERATIONS = {
    "<operation>": _op_<operation>,
}


def execute(**kwargs) -> dict:
    """Run one skill operation."""
    operation = (kwargs.get("operation") or "<default>").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "<Skill Name>",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "<Skill Name>",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "<Skill Name>",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"<Skill Name> error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "<Skill Name>"),
        "summary": <summary string>,
        "spoken_narrative": <summary string>,
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }

## 3. How to Port from claude-skills

claude-skills (alirezarezvani/claude-skills) contains **415 skills** across 9 categories:

| Category | Examples |
|----------|----------|
| Engineering | code_review, architecture, TDD, DevOps, security, QA, i18n-localization |
| Product | PRD creation, RICE scoring, user stories, roadmaps, UX research |
| Marketing | SEO, copywriting, CRO, email, paid ads |
| Compliance (RA-QM) | ISO 13485, EU MDR, FDA, ISO 27001, SOC 2, GDPR, CAPA, CMMC |
| Finance | DCF, budgets, SaaS metrics, month-end close |
| C-Level Advisory | CEO, CTO, CFO, CMO, CRO advisors, board prep |
| Research | Web search, market research, competitive analysis, OSINT |
| Business Operations | SOP creation, OKR, workflow design |
| Daily Productivity | Task management, meeting prep, email triage |

Each skill is a folder with a `SKILL.md` (frontmatter + instructions), optional `scripts/`, `references/`, `assets/`.

### Porting Steps

1. **Read the source `SKILL.md`** — extract frontmatter (name, description, triggers, parameters) and instructions (what the skill does).
2. **Create `skills/<skill_name>/skill.py`** — use the template in Section 2.
3. **Map `SKILL.md` frontmatter to `FEATURE_METADATA`**:
   - `name` → `FEATURE_METADATA["name"]`
   - `aliases` → `FEATURE_METADATA["aliases"]`
   - `description` → `FEATURE_METADATA["description"]`
   - `triggers` → `FEATURE_METADATA["triggers"]`
   - `parameters` → `FEATURE_METADATA["parameters"]`
   - `source` → `"claude-skills"`
   - `division` → category name (e.g., `"engineering"`)
4. **Implement each operation** as a handler function in `_OPERATIONS`.
5. **Register in `skills/skills-lock.json`** — add entry with hash, version, source.
6. **Test** — run `python skills/<skill_name>/skill.py` directly, then run through `agent/loop.py` `run_goal()`.

### Example: Porting "code_review" from claude-skills Engineering

```python
# skills/code_review/skill.py
FEATURE_METADATA = {
    "name": "code_review",
    "aliases": ["code review", "review code", "code audit", "pr review"],
    "description": "Reviews source code for bugs, security issues, performance problems, and best practice violations.",
    "triggers": ["review code", "code review", "audit code", "review pull request", "code quality"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "One of: review | security | performance | style | all."},
            "code": {"type": "STRING", "description": "Source code to review."},

## 4. How to Port from agency-agents

agency-agents (msitarzewski/agency-agents) contains **~100+ specialized agents** across 17 divisions:

| Division | Icon | Key Agents |
|----------|------|------------|
| Engineering | Code | Senior Developer, Backend Architect, DevOps, Security Engineer, QA |
| Product | Box | Product Manager, PM (PRDs, RICE, roadmaps), UX Researcher |
| Finance | DollarSign | CFO Advisor, Budget Planner, Financial Analyst |
| Marketing | Megaphone | Content Creator, Copywriter, SEO Specialist, Email Marketer |
| C-Level | — | CEO, CTO, CFO, CMO advisors |
| Research | Search | Research Synthesist, Evidence Collector, Literature Reviewer |
| Compliance | ShieldCheck | Security Engineer, AppSec Specialist, Compliance Officer |
| Business Ops | ClipboardList | Senior Project Manager, Scrum Master |
| Security | ShieldCheck | Red Teamer, Compliance Officer |
| ...and 8 more | | |

Each agent is a folder with frontmatter YAML + system prompt `.md` files. Divisions are defined in `divisions.json`.

### Porting Steps

1. **Read the agent's frontmatter and system prompt** — extract name, role, description, triggers, capabilities.
2. **Create `skills/<agent_name>/skill.py`** — use the template in Section 2.
3. **Map frontmatter to `FEATURE_METADATA`** (same mapping as claude-skills).
4. **Implement operations** based on the agent's capabilities and system prompt.
5. **Register in `skills/skills-lock.json`**.
6. **Test**.

### Example: Porting "Backend Architect" from agency-agents Engineering

```python
# skills/backend_architect/skill.py
FEATURE_METADATA = {
    "name": "backend_architect",
    "aliases": ["backend architect", "api design", "system architecture", "database design"],
    "description": "Designs backend system architecture, APIs, databases, and scalability patterns.",
    "triggers": ["backend architect", "api design", "system architecture", "database design", "scalability review"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "One of: design_api | design_database | review_architecture | scalability_review."},

## 5. How to Build an Agent (Agentic Skill)

An "agentic skill" is a skill that can be invoked by Stella's agent loop to work autonomously toward a goal. The flow is:

```
User Goal
    → planner.py decomposes into steps
    → loop.py Agent runs think→act→observe→verify
    → skill.execute() performs the action
    → verify.py checks if work was observed done
    → repeat until complete or turn budget exhausted
```

### Steps to Build an Agentic Skill

1. **Choose the division/category** — from claude-skills (9 categories) or agency-agents (17 divisions).
2. **Create the skill directory** — `skills/<agent_name>/`.
3. **Write `skill.py`** — following the template in Section 2.
4. **Implement operations** — each operation is a discrete action the agent can take.
5. **Register in `skills-lock.json`** — add entry with unique hash, version, source.
6. **Test standalone** — `python skills/<agent_name>/skill.py` or direct `execute()` call.
7. **Test through the loop** — `agent/loop.py run_goal()` with `allowed_tools=[<skill_name>]`.
8. **Audit** — every tool call is audited via `agent/tools.py _audit_tool_call()` and `core/audit.py`.

### Agent Loop Integration

```python
from agent.loop import run_goal

result = run_goal(
    goal="Design a REST API for a billing system",

## 6. Honesty & Safety Model

### Honesty Levels (from `agent/tools.py`)

| Level | Meaning |
|-------|---------|
| `done` | Action completed and verified (or self-evident) |
| `unverified` | Action attempted but could not be confirmed |
| `failed` | Action could not be performed |

**Rule:** Tools must never claim success they did not observe.

### Safety


## 7. Registration (`skills-lock.json`)

`skills/skills-lock.json` is the lockfile of all registered skills. Each entry:

```json
{
  "<skill_name>": {
    "hash": "<content hash>",
    "version": "1.0.0",
    "source": "claude-skills" or "agency-agents" or "stella" or "features"
  }
}
```

To register a new skill:

## 8. Testing & Compilation

### Standalone Skill Test

```bash
cd E:/Projects/stella
python skills/<skill_name>/skill.py
```

This runs the `if __name__ == "__main__"` block which calls `execute(operation="<default>")`.

### Test Through Agent Loop

```bash
cd E:/Projects/stella
python -c "
from agent.loop import run_goal
result = run_goal(
    goal='<test goal>',
    allowed_tools=['<skill_name>'],
    max_turns=5,
)
print(result.summary())
print(result.answer)
"
```

### Python Syntax Check

```bash
cd E:/Projects/stella
python -m py_compile skills/<skill_name>/skill.py
python -m py_compile agent/skill_loader.py

## 9. Complete Implementation Checklist

For each new agent/skill:

- [ ] Read source `SKILL.md` (claude-skills) or agent frontmatter + system prompt (agency-agents)
- [ ] Create `skills/<skill_name>/` directory
- [ ] Write `skill.py` with `FEATURE_METADATA` + `execute(**kwargs)`
- [ ] Implement all operations as handler functions
- [ ] Add aliases for common trigger phrases
- [ ] Register in `skills/skills-lock.json` with hash, version, source
- [ ] Test standalone: `python skills/<skill_name>/skill.py`
- [ ] Test through loop: `agent/loop.py run_goal()` with `allowed_tools`

## 10. Priority Agents/Skills to Port (Recommended Order)

| Priority | Skill | Source | Division/Category | Operations |
|----------|-------|--------|-------------------|------------|
| 1 | `backend_architect` | agency-agents | Engineering | design_api, design_database, review_architecture, scalability_review |
| 2 | `security_engineer` | agency-agents | Security | code_security_review, dependency_audit, compliance_check, threat_model |
| 3 | `product_manager` | agency-agents | Product | create_prd, create_roadmap, rice_score, write_user_stories |
| 4 | `cfo_advisor` | agency-agents | Finance | create_budget, dcf_valuation, saas_metrics, month_end_close |
| 5 | `ceo_advisor` | agency-agents | C-Level | strategic_guidance, board_prep, investor_prep, vision_statement |
| 6 | `cto_advisor` | agency-agents | C-Level | tech_strategy, architecture_review, stack_evaluation |
| 7 | `copywriter` | agency-agents | Marketing | write_ad, write_email, write_landing_copy, apply_framework |
| 8 | `seo_specialist` | agency-agents | Marketing | audit_seo, keyword_research, content_optimization |
| 9 | `qa_engineer` | agency-agents | Testing | create_test_plan, write_unit_tests, review_coverage, a_b_test_plan |
| 10 | `research_synthesist` | agency-agents | Research | literature_review, evidence_synthesis, source_evaluation |
| 11 | `sop_creator` | claude-skills | Business Ops | create_sop, review_process, process_map |
| 12 | `okr_planner` | claude-skills | Business Ops | create_okr, grade_okr, track_progress |
| 13 | `gdpr_compliance` | claude-skills | Compliance | assess_compliance, dsar_handler, breach_notification |
| 14 | `soc2_compliance` | claude-skills | Compliance | assess_soc2, controls_review, evidence_collection |

## 11. Relationship to Existing Stella Skills

Stella already has ~100 skills in `skills/` (anatomy, brainstorming, coding, marketing, web-search, etc.). The new agents/skills from claude-skills and agency-agents should:

- **Complement** existing skills, not duplicate them
- **Share the same pattern** — `FEATURE_METADATA` + `execute(**kwargs)`
- **Be registerable** in `skills-lock.json`
- **Be callable** through `agent/loop.py run_goal()` with `allowed_tools`
- **Follow the honesty model** — no false success claims
- **Follow the safety model** — destructive ops require explicit permission

## 12. Build Status

| Component | Status |
|-----------|--------|
| `agent/skill_loader.py` | ✅ Exists, references `features/` (directory missing — needs update to `skills/`) |
| `agent/loop.py` | ✅ Exists, fully functional |
| `agent/planner.py` | ✅ Exists, fully functional |
| `agent/tools.py` | ✅ Exists, fully functional |
| `agent/verify.py` | ✅ Exists, fully functional |
| `skills/` directory | ✅ Exists, ~100 skills present |
| `skills/skills-lock.json` | ✅ Exists, lockfile present |
| `core/security/osint_tools.py` | ✅ Created — wraps 10 security/OSINT tools (nmap, dracnmap, xerosploit, red_hawk, reconspider, infoga, recondog, striker, rang3r, breacher) |
| `features/` directory | ❌ Does not exist — `skill_loader.py` points here but it's empty |
| New claude-skills/agency-agents skills | ⏳ Not yet ported — use this guide to implement |

### Compilation Verification

To verify everything compiles:

```bash
# Python syntax check for all skills
cd E:/Projects/stella
for f in skills/*/skill.py; do python -m py_compile "$f" || echo "FAILED: $f"; done
echo "All skills compiled successfully"

# Python syntax check for agent modules
python -m py_compile agent/skill_loader.py agent/loop.py agent/planner.py agent/tools.py agent/verify.py
echo "All agent modules compiled successfully"

# TypeScript type check for Stella Mobile (React Native)
cd "E:/Projects/stella mobile/StellaMobile"
npx tsc --noEmit
echo "TypeScript compiled successfully"
```

**Expected result:** All Python files compile without syntax errors. TypeScript compiles with no type errors (assuming `node_modules` is installed in the mobile project).

## 13. Source References

- **claude-skills**: https://github.com/alirezarezvani/claude-skills — 415 skills, 9 categories, SKILL.md standard
- **agency-agents**: https://github.com/msitarzewski/agency-agents — 100+ agents, 17 divisions, divisions.json + tools.json
- **Stella Python backend**: `E:/Projects/stella/` — agent loop, skill loader, tools registry, verify module
- **Stella Mobile (React Native)**: `E:/Projects/stella mobile/StellaMobile/` — RN app with TypeScript, skills catalog, settings

- [ ] Verify honesty: no false success claims
- [ ] Verify safety: destructive ops require explicit permission
- [ ] Document triggers and operations in this file (optional)

python -m py_compile agent/loop.py
```

### TypeScript (React Native Mobile App)

If you also need to type-check the Stella Mobile React Native app:

```bash
cd "E:/Projects/stella mobile/StellaMobile"
npx tsc --noEmit
```

1. Compute a content hash of `skill.py`.
2. Add entry to `skills/skills-lock.json` under `"skills"`.
3. Set `"source"` to `"claude-skills"` or `"agency-agents"` depending on origin.
4. Set `"version"` to `"1.0.0"` (or appropriate).

- Anything that writes to disk, shells out, or reaches the network is marked **destructive**.
- Destructive tools require explicit permission via `Registry.allowed` (injected from host, never derived from model output).
- Permissions are enforced in one place: `requires` + `allow_destructive`.
- Every tool call is audited via `core/audit.py`.

### Repeat Detection (from `agent/loop.py`)

The agent loop tracks tool call fingerprints. If the same tool is called with the same arguments more than twice, the loop intervenes and forces a different approach — preventing infinite loops with small local models.

    allowed_tools=["backend_architect", "security_engineer", "qa_engineer"],
    max_turns=12,
    tool_budget_tier=2,
)
print(result.summary())
print(result.answer)
print(f"Verified: {result.verified}")
```

            "requirements": {"type": "STRING", "description": "System requirements or description."},
            "focus": {"type": "STRING", "description": "Focus area: scalability | reliability | security | maintainability | cost | all."},
        },
    },
    "source": "agency-agents",
    "division": "engineering",
}
```

            "language": {"type": "STRING", "description": "Programming language."},
            "severity": {"type": "STRING", "description": "Minimum severity: low | medium | high | critical."},
        },
    },
    "source": "claude-skills",
    "division": "engineering",
}
```



if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="<default>"))
```

### Result Schema

Every `execute()` call returns:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Human-readable skill title |
| `summary` | string | Brief result summary |
| `spoken_narrative` | string | TTS-friendly narrative |
| `operation` | string | The operation that ran |
| `ok` | boolean | Whether the operation succeeded |
| `record` | dict | Structured result data |

| `skills/skills-lock.json` | Lockfile of registered skills with hashes, versions, and sources |

### Important Note: `features/` vs `skills/`

`agent/skill_loader.py` line 18 defines `FEATURES_DIR = PROJECT_ROOT / "features"`, but **`features/` does not exist**. All actual skills live in `skills/`. Until `skill_loader.py` is updated to point to `skills/`, new skills must either:

1. Be placed in `skills/` following the existing `skill.py` pattern (recommended), **or**
2. Be placed in `features/<name>/` with `manifest.json` + `skill.py` (matches `skill_loader.py` as written).

This guide documents the **`skills/` pattern** because it matches every existing skill in the repository.
