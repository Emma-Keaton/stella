from core.user_paths import get_user_data_dir
import json
import re
import sys
from pathlib import Path
from enum import Enum


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = get_user_data_dir() / "config" / "api_keys.json"


class ErrorDecision(Enum):
    RETRY       = "retry"
    SKIP        = "skip"
    REPLAN      = "replan"
    ABORT       = "abort"


# ---------------------------------------------------------------------------
# Cloud analysis is OPTIONAL.
#
# This module exists to recover from failures, so it must never be the thing
# that fails. Gemini being uninstalled, offline, or un-keyed used to raise out
# of analyze_error() and take the whole recovery path down. Now it degrades to
# a deterministic local heuristic, which is also what an offline-first device
# actually wants.
# ---------------------------------------------------------------------------

_TRANSIENT = re.compile(
    r"timed? ?out|timeout|connection (reset|aborted|refused)|temporarily|"
    r"try again|rate limit|429|503|502|file is locked|being used by another",
    re.IGNORECASE,
)
_NOT_FOUND = re.compile(
    r"no such file|not found|does not exist|enoent", re.IGNORECASE
)


def _local_decision(step: dict, error: str, attempt: int, max_attempts: int) -> dict:
    """Offline heuristic used when no LLM can be consulted."""
    if attempt >= max_attempts:
        return {
            "decision":     ErrorDecision.REPLAN,
            "reason":       f"Failed {attempt} times: {error[:100]}",
            "fix_suggestion": "Try a different approach or tool",
            "max_retries":  0,
            "user_message": "Trying a different approach.",
        }

    if _NOT_FOUND.search(error):
        decision, retries, reason = (
            (ErrorDecision.REPLAN if step.get("critical") else ErrorDecision.SKIP),
            0, "The target does not exist",
        )
    elif _TRANSIENT.search(error) and attempt < max_attempts:
        decision, retries, reason = ErrorDecision.RETRY, 1, "Transient error"
    else:
        decision, retries, reason = ErrorDecision.REPLAN, 0, "The approach failed"

    return {
        "decision":       decision,
        "reason":         reason,
        "fix_suggestion": "Try an alternative approach or tool",
        "max_retries":    retries,
        "user_message":   "Encountered an issue, adjusting approach.",
    }


def _gemini(model_name: str, system_instruction: str | None = None):
    """Return a configured Gemini model, or None when unavailable."""
    from core.gemini_optional import gemini_model
    return gemini_model(model_name, system_instruction)


def _strip_fence(text: str) -> str:
    return re.sub(r"```(?:json|python)?", "", text or "").strip().rstrip("`").strip()


ERROR_ANALYST_PROMPT = """You are the error recovery module of Stella.

A task step has failed. Analyze the error and decide what to do.

DECISIONS:
- retry   : Transient error (network timeout, temporary file lock, race condition).
             The same step can succeed if tried again.
- skip    : This step is not critical and the task can succeed without it.
- replan  : The approach was wrong. A different tool or method should be tried.
- abort   : The task is fundamentally impossible or unsafe to continue.

Also provide:
- A brief explanation of WHY it failed (1 sentence)
- A fix suggestion if decision is replan (what to try instead)
- Max retries: how many times to retry if decision is retry (1 or 2)

Return ONLY valid JSON:
{
  "decision": "retry|skip|replan|abort",
  "reason": "why it failed",
  "fix_suggestion": "what to try instead (for replan)",
  "max_retries": 1,
  "user_message": "Short message to tell the user (max 15 words)"
}
"""


def _get_api_key() -> str:
    """Read the Gemini key, tolerating a missing/partial config."""
    from core.gemini_optional import get_api_key
    return get_api_key()


def analyze_error(
    step: dict,
    error: str,
    attempt: int = 1,
    max_attempts: int = 2
) -> dict:
    """
    Analyzes a failed step and returns a recovery decision.

    Args:
        step         : The step dict that failed
        error        : Error message/traceback
        attempt      : Current attempt number
        max_attempts : How many times we've already tried

    Returns:
        {
            "decision": ErrorDecision,
            "reason": str,
            "fix_suggestion": str,
            "max_retries": int,
            "user_message": str
        }
    """
    if attempt >= max_attempts:
        print(f"[ErrorHandler] Max attempts reached for step {step.get('step')} - forcing replan")
        return _local_decision(step, error, attempt, max_attempts)

    model = _gemini("gemini-3.1-flash-lite", ERROR_ANALYST_PROMPT)
    if model is None:
        # No cloud (offline / no key / package missing): decide locally.
        result = _local_decision(step, error, attempt, max_attempts)
        print(f"[ErrorHandler] No cloud analyst - local decision: {result['decision'].value}")
        return result

    prompt = f"""Failed step:
Tool: {step.get('tool')}
Description: {step.get('description')}
Parameters: {json.dumps(step.get('parameters', {}), indent=2)}
Critical: {step.get('critical', False)}

Error:
{error[:500]}

Attempt number: {attempt}"""

    try:
        response = model.generate_content(prompt)
        text     = response.text.strip()
        text     = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        result = json.loads(text)
        decision_str = result.get("decision", "replan").lower()
        decision_map = {
            "retry":  ErrorDecision.RETRY,
            "skip":   ErrorDecision.SKIP,
            "replan": ErrorDecision.REPLAN,
            "abort":  ErrorDecision.ABORT,
        }
        result["decision"] = decision_map.get(decision_str, ErrorDecision.REPLAN)


        if step.get("critical") and result["decision"] == ErrorDecision.SKIP:
            result["decision"]     = ErrorDecision.REPLAN
            result["user_message"] = "This step is critical - finding another approach."

        print(f"[ErrorHandler] Decision: {result['decision'].value} - {result.get('reason', '')}")
        return result

    except Exception as e:
        print(f"[ErrorHandler] Analysis failed: {e} - falling back to local decision")
        return _local_decision(step, error, attempt, max_attempts)


def generate_fix(step: dict, error: str, fix_suggestion: str) -> dict:
    """
    When decision is REPLAN and a fix suggestion exists,
    generates a replacement step using generated_code as fallback.

    Returns a modified step dict.
    """
    def _fallback() -> dict:
        return {
            "step":        step.get("step"),
            "tool":        "generated_code",
            "description": f"Fallback for: {step.get('description')}",
            "parameters":  {"description": step.get("description", "")},
            "depends_on":  step.get("depends_on", []),
            "critical":    step.get("critical", False),
        }

    model = _gemini("gemini-2.5-flash")
    if model is None:
        print("[ErrorHandler] No cloud available - using fallback step")
        return _fallback()

    prompt = f"""A task step failed. Generate a replacement step.

Original step:
Tool: {step.get('tool')}
Description: {step.get('description')}
Parameters: {json.dumps(step.get('parameters', {}), indent=2)}

Error: {error[:300]}
Fix suggestion: {fix_suggestion}

Write a Python script that accomplishes the same goal differently.
Return ONLY the Python code, no explanation."""

    try:
        response = model.generate_content(prompt)
        code = _strip_fence(response.text)
        if not code:
            return _fallback()

        return {
            "step":        step.get("step"),
            "tool":        "claude_code",
            "description": f"Auto-fix for: {step.get('description')}",
            "parameters": {
                "description": fix_suggestion,
            },
            "depends_on": step.get("depends_on", []),
            "critical":   step.get("critical", False)
        }

    except Exception as e:
        print(f"[ErrorHandler] Fix generation failed: {e}")
        return _fallback()