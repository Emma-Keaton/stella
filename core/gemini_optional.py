"""core/gemini_optional.py - construct a Gemini model, or return None.

Almost every agent module wants a Gemini model, and almost none of them can
function without one. Importing `google.generativeai` unguarded means a
machine without the package (or without a key, or offline) raises straight out
of whatever feature happened to need it - including the error-recovery and
replanning paths that exist precisely to handle failure.

The rule for the whole codebase:
    model = gemini_model("gemini-2.5-flash")
    if model is None:
        return <offline fallback>

Returning None instead of raising lets each caller decide its own degradation,
and makes "cloud unavailable" an ordinary, testable state.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def _config_path() -> Path:
    base = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
    return Path(base) / "StellaAI" / "config" / "api_keys.json"


def get_api_key() -> str:
    """Gemini key from the app config, or "" when unavailable."""
    # Env first: makes CI and headless runs possible without a config file.
    env_key = (os.environ.get("GEMINI_API_KEY")
               or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if env_key:
        return env_key
    try:
        with _config_path().open("r", encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("gemini_api_key", "") or ""
    except Exception:
        return ""


def genai_available() -> bool:
    try:
        import google.generativeai  # noqa: F401
    except Exception:
        return False
    return True


def gemini_model(model_name: str = "gemini-2.5-flash",
                 system_instruction: str | None = None,
                 api_key: str | None = None) -> Any | None:
    """Return a configured GenerativeModel, or None if unavailable offline."""
    try:
        key = api_key if api_key is not None else get_api_key()
        if not key:
            return None
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            import google.generativeai as genai
        genai.configure(api_key=key)
        kwargs: dict = {"model_name": model_name}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        return genai.GenerativeModel(**kwargs)
    except Exception:
        return None


def first_available(candidates: list[str],
                    system_instruction: str | None = None) -> tuple[Any | None, str]:
    """Try each model name in order; return (model, name_used)."""
    for name in candidates:
        model = gemini_model(name, system_instruction)
        if model is not None:
            return model, name
    return None, ""