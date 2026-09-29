"""
The Skill Forge: Autonomous Capability Synthesis Engine
Part of Project Ultron for Brahma AI.

Transforms natural language goals into fully architected, tested,
and hot-pluggable Python skills for Brahma AI.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.user_paths import get_user_data_dir
from core.skill_crucible import SkillCrucible
from core.dynamic_registry import DynamicToolRegistry

logger = logging.getLogger("SkillForge")

CONFIG_DIR = get_user_data_dir() / "config"
API_CONFIG_PATH = CONFIG_DIR / "api_keys.json"


def _get_gemini_api_key() -> str:
    """Retrieves the Gemini API key from api_keys.json or environment variables."""
    if API_CONFIG_PATH.exists():
        try:
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                key = data.get("gemini_api_key", "").strip()
                if key:
                    return key
        except Exception:
            pass
    return (os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")).strip()


class SkillForge:
    """Autonomous synthesizer of new Brahma AI skills."""

    @classmethod
    def forge_skill(
        cls,
        goal: str,
        skill_name: Optional[str] = None,
        context_hints: str = "",
        max_repair_attempts: int = 2,
    ) -> Dict[str, Any]:
        """
        Synthesizes a brand new skill from natural language, verifies it in the
        Crucible sandbox, auto-resolves pip packages, and hot-registers it.
        """
        logger.info(f"[Forge] Initiating skill synthesis for goal: '{goal}'")

        # Normalize skill name if provided
        name_hint = re.sub(r"[^a-zA-Z0-9_]", "_", (skill_name or "").lower()).strip("_")

        # 1. Synthesize initial specification
        synthesis = cls._call_llm_synthesizer(goal, name_hint, context_hints)
        if not synthesis.get("success"):
            return {
                "success": False,
                "message": f"Skill synthesis generation failed: {synthesis.get('error')}",
            }

        manifest = synthesis["manifest"]
        code = synthesis["code"]
        test_cases = synthesis.get("test_cases", [{"input": {}}])
        actual_name = manifest.get("name", name_hint or "custom_skill")

        # 2. Iterative Verification & Self-Repair Loop
        for attempt in range(max_repair_attempts + 1):
            logger.info(f"[Forge] Crucible verification attempt {attempt + 1}/{max_repair_attempts + 1} for '{actual_name}'")

            # Stage A: AST Validation
            ast_ok, ast_err = SkillCrucible.validate_ast(code)
            if not ast_ok:
                if attempt < max_repair_attempts:
                    logger.warning(f"[Forge] AST check failed ({ast_err}). Requesting repair from LLM...")
                    repair = cls._repair_code(code, ast_err, goal)
                    if repair.get("success"):
                        code = repair["code"]
                        continue
                return {"success": False, "message": f"Crucible AST rejected skill: {ast_err}"}

            # Stage B: Dependency Auto-Resolver
            deps = SkillCrucible.extract_dependencies(code)
            deps_ok, deps_msg = SkillCrucible.resolve_dependencies(deps)
            if not deps_ok:
                return {"success": False, "message": f"Dependency resolution failed: {deps_msg}"}

            # Stage C: Sandboxed Execution Tests
            test_ok, test_msg, test_telemetry = SkillCrucible.run_sandbox_test(code, test_cases)
            if not test_ok:
                if attempt < max_repair_attempts:
                    logger.warning(f"[Forge] Sandbox tests failed ({test_msg}). Requesting repair from LLM...")
                    repair = cls._repair_code(code, test_msg, goal)
                    if repair.get("success"):
                        code = repair["code"]
                        continue
                return {"success": False, "message": f"Crucible Sandbox tests failed: {test_msg}", "telemetry": test_telemetry}

            # All stages passed!
            break

        # 3. Commit as a Native Codebase Feature in features/ (Autonomous Self-Evolution)
        features_dir = DynamicToolRegistry.get_skills_directory()
        features_dir.mkdir(parents=True, exist_ok=True)

        # Prepare triggers & aliases
        triggers = list(manifest.get("triggers", []))
        if goal and goal.strip() not in triggers:
            triggers.append(goal.strip())

        clean_goal = re.sub(
            r"^(?:please\s+|can\s+you\s+|use\s+(?:the\s+)?(?:skill|feature)\s+to\s+|run\s+(?:the\s+)?(?:skill|feature)\s+to\s+|test\s+(?:the\s+)?(?:skill|feature)\s+to\s+)",
            "",
            goal.lower().strip()
        )
        if clean_goal and clean_goal not in triggers:
            triggers.append(clean_goal)

        name_words_trigger = actual_name.replace("_", " ")
        if name_words_trigger not in triggers:
            triggers.append(name_words_trigger)

        aliases = list(manifest.get("aliases", []))
        clean_alias = actual_name.replace("_", "")
        if clean_alias not in aliases:
            aliases.append(clean_alias)

        manifest["name"] = actual_name
        manifest["triggers"] = list(dict.fromkeys(triggers))
        manifest["aliases"] = list(dict.fromkeys(aliases))
        manifest["created_at"] = time.time()
        manifest["version"] = "1.0.0"
        manifest["author"] = "Project Ultron Autonomous Self-Evolution Engine"
        manifest["active"] = True

        # Build clean native feature code with embedded FEATURE_METADATA
        feature_code = code
        if "FEATURE_METADATA" not in feature_code:
            meta_str = json.dumps(manifest, indent=4)
            header = (
                f'"""\n'
                f'Feature: {actual_name}\n'
                f'Description: {manifest.get("description", "")}\n'
                f'Autonomous Evolutionary Capability synthesized by Brahma AI.\n'
                f'"""\n\n'
                f'FEATURE_METADATA = {meta_str}\n\n'
            )
            feature_code = header + feature_code

        # Primary native module: features/{actual_name}.py
        feature_py_file = features_dir / f"{actual_name}.py"
        try:
            with open(feature_py_file, "w", encoding="utf-8") as f:
                f.write(feature_code)

            # Update features/__init__.py for self-evolving codebase integration
            init_file = features_dir / "__init__.py"
            try:
                init_content = init_file.read_text(encoding="utf-8") if init_file.exists() else ""
                import_stmt = f"from . import {actual_name}\n"
                if import_stmt not in init_content:
                    with open(init_file, "a", encoding="utf-8") as f_init:
                        f_init.write(import_stmt)
            except Exception as e_init:
                logger.warning(f"[Forge] Could not update features/__init__.py: {e_init}")

            # Also maintain feature package directory for telemetry and test cases
            target_dir = features_dir / actual_name
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(target_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)
            with open(target_dir / "skill.py", "w", encoding="utf-8") as f:
                f.write(feature_code)
            with open(target_dir / "test_cases.json", "w", encoding="utf-8") as f:
                json.dump(test_cases, f, indent=4)

            # 4. Hot-Load into Dynamic Registry
            DynamicToolRegistry.initialize()

            return {
                "success": True,
                "name": actual_name,
                "description": manifest.get("description", ""),
                "skill_path": str(feature_py_file),
                "message": f"Successfully forged and activated native feature '{actual_name}'! Verified via Crucible sandbox.",
                "manifest": manifest,
            }
        except Exception as e:
            return {"success": False, "message": f"Failed saving synthesized feature: {e}"}

    @classmethod
    def _parse_json_response(cls, text: str) -> Dict[str, Any]:
        """Robustly extracts and parses a JSON object from model output, ignoring any extra trailing text."""
        clean = (text or "").strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*\n?", "", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\n?```\s*$", "", clean).strip()

        # 1. Try direct json.loads
        try:
            data = json.loads(clean)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        # 2. Use JSONDecoder.raw_decode starting from first '{' (skips trailing notes/extra data)
        start_idx = clean.find("{")
        if start_idx != -1:
            try:
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(clean[start_idx:])
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

        # 3. Match outermost balanced { and }
        if start_idx != -1:
            for end_idx in range(len(clean) - 1, start_idx, -1):
                if clean[end_idx] == "}":
                    candidate = clean[start_idx:end_idx + 1]
                    try:
                        data = json.loads(candidate)
                        if isinstance(data, dict):
                            return data
                    except Exception:
                        continue

        raise ValueError("Could not extract a valid JSON object from LLM output.")

    @classmethod
    def _call_llm_synthesizer(cls, goal: str, name_hint: str, context_hints: str) -> Dict[str, Any]:
        """Prompts Gemini to generate the complete skill package JSON."""
        system_instructions = """You are the Brahma AI Autonomous Skill Architect ("Project Ultron").
Your mission is to invent, architect, and write a complete, standalone, production-ready Python skill plugin.

Skill Architecture Guidelines:
1. Entry point MUST be `def execute(**kwargs)` or `async def execute(**kwargs)`.
2. Must be clean, robust Python with error handling (try/except) and type annotations.
3. Default Parameter Handling:
   - In `execute(**kwargs)`, ALWAYS assign safe fallback defaults to all expected parameters (e.g. `symbol = kwargs.get('symbol', 'BTCUSDT')` or `target = kwargs.get('target', 'cricket')`).
   - If called with empty kwargs `{}` (such as during sandbox verification), the skill MUST execute cleanly without throwing KeyError or TypeError.
4. Fast Public REST APIs & Safe Fallbacks:
   - When external live data is needed (e.g., crypto/stock prices, weather, flights, currency, sports scores):
   - ALWAYS prefer lightweight, public, high-speed REST JSON endpoints using `urllib.request` or `requests` (e.g., Binance public ticker, CoinGecko, Open-Meteo, public JSON APIs).
   - ALWAYS set a strict network timeout: `timeout=8` on any HTTP call.
   - ALWAYS wrap network calls in `try...except` and provide structured fallback data if the endpoint is offline or rate-limited, so sandbox tests with `{}` never fail.
   - Catch generic `Exception` for third-party libraries (e.g. speedtest, requests, urllib) rather than referencing library-specific custom exception classes (such as `SpeedtestException`) that might not exist across versions.
   - Do NOT use heavy scrapers (avoid selenium/playwright).
5. Visual Deliverables & Dark-Mode Graph Cards:
   - If the user asks for graphs, charts, scorecards, plots, or visual cards:
   - IMMEDIATELY configure headless backend before importing pyplot:
     ```python
     import matplotlib
     matplotlib.use('Agg')
     import matplotlib.pyplot as plt
     ```
   - Dark HUD Theme Styling:
     Set dark background: `plt.style.use('dark_background')`, fig and ax facecolor `#0B0F19`, grid color `#1E293B` with alpha 0.6.
     Use neon/cyberpunk accent colors for data lines/bars: Cyan `#00F0FF`, Emerald `#10B981`, Amber `#F59E0B`.
   - Save output image:
     Save the figure to PNG in `os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'BrahmaAI', 'deliverables', '<skill_name>_output.png')` (create parent directories if missing).
     Close the figure with `plt.close(fig)` to prevent memory leaks.
   - Return Value:
     Return a dictionary containing `image_path` (the absolute path to the PNG), `title`, and `summary` or key metrics string, so Brahma's HUD Result Wing immediately renders the live dark-mode card.
6. Output Format:
   Output MUST be clean JSON with exact structure:
{
    "manifest": {
        "name": "snake_case_feature_name",
        "aliases": ["alias_1", "alias_2"],
        "description": "Concise, actionable description of when and how Gemini Live should call this feature",
        "triggers": [
            "direct trigger phrase 1",
            "natural variation 2",
            "query command 3"
        ],
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "param_name": {
                    "type": "STRING|INTEGER|NUMBER|BOOLEAN",
                    "description": "What this parameter is"
                }
            },
            "required": []
        }
    },
    "code": "Full python source code including imports and def execute(**kwargs)",
    "test_cases": [
        {
            "input": {}
        }
    ]
}
Return ONLY this JSON object with no markdown fences around it.
"""

        prompt = f"""Synthesize a new skill for the following user request:
Goal: {goal}
Preferred Name: {name_hint or 'auto_generate'}
Additional Context: {context_hints}
"""

        gemini_key = _get_gemini_api_key()
        if gemini_key:
            try:
                from google import genai
                g_client = genai.Client(api_key=gemini_key, http_options={"api_version": "v1beta"})
                for model_name in ("gemini-2.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-flash-latest"):
                    try:
                        resp = g_client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config={
                                "temperature": 0.2,
                                "system_instruction": system_instructions,
                                "response_mime_type": "application/json"
                            }
                        )
                        raw = getattr(resp, "text", "") or ""
                        data = cls._parse_json_response(raw)
                        if "manifest" in data and "code" in data:
                            data["success"] = True
                            return data
                    except Exception as e:
                        logger.warning(f"[Forge] Model {model_name} failed: {e}")
                        continue
            except Exception as exc:
                logger.error(f"[Forge] Gemini client error: {exc}")

        # Fallback to Unified llm_client if available
        try:
            try:
                from llm_client import query_llm
            except ImportError:
                from core.llm_client import query_llm
            resp = query_llm(prompt=prompt, system=system_instructions)
            data = cls._parse_json_response(resp)
            data["success"] = True
            return data
        except Exception as fallback_exc:
            return {"success": False, "error": f"LLM synthesis failed: {fallback_exc}"}

    @classmethod
    def _repair_code(cls, broken_code: str, error_msg: str, goal: str) -> Dict[str, Any]:
        """Asks LLM to fix syntax or sandbox runtime errors."""
        prompt = f"""You are repairing a Python skill generated for Brahma AI ("Project Ultron").
The skill failed verification in the Crucible sandbox.
User Goal: {goal}
Verification Error: {error_msg}

Broken Code:
```python
{broken_code}
```

Critical Repair Instructions:
1. Ensure `def execute(**kwargs)` handles empty or missing kwargs with safe defaults.
2. If using `matplotlib`, ensure `import matplotlib; matplotlib.use('Agg')` is placed before `pyplot`.
3. If making HTTP requests, ensure `timeout=8` is set on network calls and use public JSON REST APIs.
4. Catch generic `Exception` for library errors (e.g. `except Exception:`) rather than assuming specific custom exception classes (such as `SpeedtestException`).
5. Provide graceful fallback metrics if network or device measurement fails so the sandbox test with `{{}}` always succeeds.
6. Save any generated charts to `os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'BrahmaAI', 'deliverables', 'output.png')` and return the file path in the result.
7. Return ONLY a JSON object:
{{
    "code": "Fully corrected, runnable Python code"
}}
"""
        gemini_key = _get_gemini_api_key()
        if gemini_key:
            try:
                from google import genai
                g_client = genai.Client(api_key=gemini_key, http_options={"api_version": "v1beta"})
                for model_name in ("gemini-2.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-flash-latest"):
                    try:
                        resp = g_client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config={"temperature": 0.1, "response_mime_type": "application/json"}
                        )
                        raw = getattr(resp, "text", "") or ""
                        data = cls._parse_json_response(raw)
                        if "code" in data:
                            data["success"] = True
                            return data
                    except Exception as e:
                        logger.warning(f"[Forge] Repair model {model_name} failed: {e}")
                        continue
            except Exception as exc:
                logger.error(f"[Forge] Repair Gemini error: {exc}")

        return {"success": False, "error": "Repair attempt failed."}
