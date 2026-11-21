from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

FEATURE_METADATA = {
    "name": "skill_creator",
    "aliases": ["skill creator", "create skill", "build skill", "make skill", "new skill", "improve skill", "optimize skill", "evaluate skill", "test skill"],
    "description": "Create new skills, modify existing skills, and measure skill performance. Helps users design, implement, test, and optimize skills through iterative evaluation loops.",
    "triggers": ["create skill", "build skill", "make skill", "new skill", "skill creator", "improve skill", "optimize skill", "evaluate skill", "test skill", "skill development", "write skill"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "enum": ["design_skill","generate_skill","create_test_cases","run_evaluation","analyze_results","improve_skill","package_skill","optimize_description"]},
            "skill_name": {"type": "STRING", "description": "Name of the skill"},
            "skill_description": {"type": "STRING", "description": "Description of the skill"},
            "intent": {"type": "STRING", "description": "What the skill should do"},
            "existing_skill": {"type": "STRING", "description": "Existing skill to improve"},
            "test_cases": {"type": "ARRAY", "items": {"type": "OBJECT"}, "description": "Test cases for evaluation"},
            "evaluation_criteria": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Criteria for evaluation"},
            "feedback": {"type": "STRING", "description": "Feedback for improvement"}
        },
        "required": ["operation"]
    },
    "version": "1.0.0",
    "active": True,
    "optional_dependencies": [],
}

API_SOURCES = {
    "anthropic_skills": {"name": "Anthropic Skills Repo", "url": "https://github.com/anthropics/skills", "auth_tier": "github"},
}

def _op_result(title: str, summary: str, ok: bool, operation: str, data: Dict = None, narrative: str = None) -> Dict:
    return {
        "title": title,
        "summary": summary[:200],
        "spoken_narrative": narrative or summary[:200],
        "ok": ok,
        "operation": operation,
        "record": {"ok": ok, "content": summary, "data": data or {}},
    }
DESIGN_GUIDE = """**Skill Design Process**
1. **Capture Intent** - What should the skill do? When should it trigger?
2. **Define Operations** - What actions can it perform? Parameters? Returns?
3. **Write Metadata** - Name, description, triggers, examples, API sources
4. **Plan Evaluation** - How will you test it? What are success criteria?
5. **Iterate** - Build → Test → Evaluate → Improve"""

GENERATE_GUIDE = """**Skill Structure (Python)**
stella/skills/{category}/
├── SKILL.md              # Metadata with triggers, params, examples
├── skill.py              # Main implementation with execute()
└── data/                 # JSON guides, templates, configs (optional)

**Key Patterns:**
- Keep skill.py focused (use data/ for large configs)
- Operations: single execute() with switch on operation
- Return {title, summary, spoken_narrative, ok, operation, record}
- Follow existing skill patterns (see weather_live, pdf)"""

TEST_CASES_GUIDE = """**Test Case Design**
Create diverse test cases:
- **Happy path** - Normal usage
- **Edge cases** - Empty input, invalid params, missing data
- **Error cases** - Network failures, API limits, malformed responses
- **Adversarial** - Ambiguous requests, conflicting instructions

Format (JSON):
[
  { "name": "basic_weather", "params": { "operation": "get_weather", "location": "SF" }, "expect": { "ok": true } },
  { "name": "invalid_location", "params": { "operation": "get_weather", "location": "" }, "expect": { "ok": false, "error": "Location required" } }
]"""

EVAL_GUIDE = """**Evaluation Loop**
1. Generate test cases (JSON)
2. Run skill on each case (parallel if possible)
3. Grade outputs: assert ok/error, check narrative quality, verify data structure
4. Quantitative metrics: pass rate, latency, token usage
5. Qualitative review: human evaluates sample outputs
6. Iterate: fix failures, add test cases, re-run"""

IMPROVE_GUIDE = """**Skill Improvement Process**
1. Review failed test cases - what went wrong?
2. Check evaluation metrics - where are the gaps?
3. Common fixes:
   - Clarify parameter descriptions
   - Add missing error handling
   - Improve narrative quality
   - Fix trigger conditions
   - Add missing operations
4. Re-run evaluation
def _op_design_skill(kwargs: dict) -> dict:
    intent = kwargs.get("intent")
    if not intent:
        return _op_result("Skill Creator", "Intent required", False, "design_skill")
    return _op_result("Skill Creator", f"Designing skill for: {intent}", True, "design_skill",
                    {"intent": intent, "guide": DESIGN_GUIDE},
                    f"Designing skill from intent: {intent}\n\n{DESIGN_GUIDE}")

def _op_generate_skill(kwargs: dict) -> dict:
    name = kwargs.get("skill_name")
    desc = kwargs.get("skill_description")
    if not name or not desc:
        return _op_result("Skill Creator", "Name and description required", False, "generate_skill")
    return _op_result("Skill Creator", f"Generating skill: {name}", True, "generate_skill",
                    {"name": name, "description": desc, "guide": GENERATE_GUIDE},
                    f"Generating skill: {name}\n\n{GENERATE_GUIDE}")

def _op_create_test_cases(kwargs: dict) -> dict:
    name = kwargs.get("skill_name")
    intent = kwargs.get("intent")
    return _op_result("Skill Creator", f"Test cases for {name}", True, "create_test_cases",
                    {"name": name, "intent": intent, "guide": TEST_CASES_GUIDE},
                    f"Create test cases for {name}:\n\n{TEST_CASES_GUIDE}")

def _op_run_evaluation(kwargs: dict) -> dict:
    name = kwargs.get("skill_name")
    test_cases = kwargs.get("test_cases", [])
    return _op_result("Skill Creator", f"Running evaluation for {name}", True, "run_evaluation",
                    {"name": name, "test_count": len(test_cases)},
                    f"Running evaluation for {name} with {len(test_cases)} test cases.\n\n{EVAL_GUIDE}")

def _op_analyze_results(kwargs: dict) -> dict:
    name = kwargs.get("skill_name")
    feedback = kwargs.get("feedback", "")
    return _op_result("Skill Creator", f"Analyzing results for {name}", True, "analyze_results",
                    {"name": name, "feedback": feedback},
                    f"Analyzing results for {name}:\n\nFeedback: {feedback or 'None provided'}\n\nReview:\n- Failed test cases → root cause\n- Pass rate trends\n- Narrative quality scores\n- Latency outliers\n- Token efficiency")

def _op_improve_skill(kwargs: dict) -> dict:
    existing = kwargs.get("existing_skill")
    feedback = kwargs.get("feedback", "")
    if not existing:
        return _op_result("Skill Creator", "Existing skill name required", False, "improve_skill")
    return _op_result("Skill Creator", f"Improving skill: {existing}", True, "improve_skill",
                    {"existing": existing, "feedback": feedback},
                    f"Improving skill: {existing}\n\nFeedback: {feedback or 'None'}\n\n{IMPROVE_GUIDE}")

def _op_package_skill(kwargs: dict) -> dict:
    name = kwargs.get("skill_name")
    return _op_result("Skill Creator", f"Packaging skill: {name}", True, "package_skill",
                    {"name": name},
                    f"Packaging skill: {name}\n\n{PACKAGE_GUIDE}")

def _op_optimize_description(kwargs: dict) -> dict:
    name = kwargs.get("skill_name")
    return _op_result("Skill Creator", f"Optimizing description for {name}", True, "optimize_description",
                    {"name": name},
                    f"Optimizing description for {name}:\n\nProcess:\n1. Analyze current trigger accuracy\n2. Generate improved description\n3. Test against evaluation set\n4. Measure trigger precision/recall\n5. Iterate until optimal")

_OPERATIONS = {
    "design_skill": _op_design_skill,
    "generate_skill": _op_generate_skill,
    "create_test_cases": _op_create_test_cases,
    "run_evaluation": _op_run_evaluation,
    "analyze_results": _op_analyze_results,
    "improve_skill": _op_improve_skill,
    "package_skill": _op_package_skill,
    "optimize_description": _op_optimize_description,
}

def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Skill Creator",
            "summary": f"Unknown operation '{operation}'. Available: {', '.join(sorted(_OPERATIONS))}",
            "spoken_narrative": f"Unknown Skill Creator operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        return handler(kwargs)
    except Exception as exc:
        return {
            "title": "Skill Creator",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Skill Creator error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
5. Expand test suite for regression prevention"""

PACKAGE_GUIDE = """**Package Skill for Distribution**
1. Ensure all files in skill directory
2. Run validation: python -m stella validate skill_name
3. Package: python package_skill.py /path/to/skill
4. Output: {skill_name}.skill file
5. For updates: preserve original name, copy to /tmp/, edit, package from copy"""

def _resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p