from core.user_paths import get_user_data_dir
import json
import sys
import time
import base64
import logging
from pathlib import Path
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("groq_client")

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR     = _get_base_dir()
API_KEY_PATH = get_user_data_dir() / "config" / "api_keys.json"

def _load_api_key() -> str:
    try:
        with open(API_KEY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = data.get("groq_api_key", "").strip()
        return key
    except FileNotFoundError:
        return ""
    except Exception as e:
        logger.warning(f"[Groq] Failed to load API key: {e}")
        return ""

GROQ_MODELS: list[str] = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
]

API_URL               = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MAX_TOKENS    = 4096
DEFAULT_TEMPERATURE   = 0.7
REQUEST_TIMEOUT       = 60
MAX_RETRIES_PER_MODEL = 2
RETRY_DELAY           = 2
RATE_LIMIT_COOLDOWN   = 60

_rate_limited: dict[str, float] = {}

class GroqClient:

    def __init__(self) -> None:
        self.api_key  = _load_api_key()
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

    def _is_rate_limited(self, model: str) -> bool:
        ts = _rate_limited.get(model)
        if ts is None:
            return False
        if time.time() - ts > RATE_LIMIT_COOLDOWN:
            del _rate_limited[model]
            return False
        return True

    def _mark_rate_limited(self, model: str) -> None:
        _rate_limited[model] = time.time()
        logger.warning(f"[Groq] Rate limited: {model} — cooling down for {RATE_LIMIT_COOLDOWN}s")

    def _call(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        payload: dict = {
            "model":       model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        if not self.api_key:
            raise PermissionError(
                "[Groq] API key is missing. Add a valid gsk_ key in config/api_keys.json."
            )

        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                resp = requests.post(
                    API_URL,
                    headers=self._headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )

                if resp.status_code == 401:
                    raise PermissionError(
                        f"[Groq] Authentication failed for model {model}. "
                        "Check your API key in config/api_keys.json."
                    )

                if resp.status_code == 403:
                    raise PermissionError(
                        f"[Groq] Access denied for model {model} (HTTP 403)."
                    )

                if resp.status_code == 429:
                    self._mark_rate_limited(model)
                    return None

                if resp.status_code == 200:
                    data    = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                    )
                    return content.strip() if content else None

                logger.warning(
                    f"[Groq] {model} → HTTP {resp.status_code} "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )

            except requests.exceptions.Timeout:
                logger.warning(f"[Groq] {model} → Timeout (attempt {attempt}/{MAX_RETRIES_PER_MODEL})")
            except Exception as e:
                logger.error(f"[Groq] {model} → Unexpected error: {e}")

            if attempt < MAX_RETRIES_PER_MODEL:
                time.sleep(RETRY_DELAY)

        return None

    def _call_with_fallback(
        self,
        pool: list[str],
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> str:
        if model and not self._is_rate_limited(model):
            try:
                result = self._call(model, messages, max_tokens, temperature, response_format)
                if result:
                    return result
                logger.info(f"[Groq] Requested model failed, falling back to pool: {model}")
            except PermissionError:
                raise

        for m in pool:
            if self._is_rate_limited(m):
                continue
            logger.info(f"[Groq] Trying: {m}")
            result = self._call(m, messages, max_tokens, temperature, response_format)
            if result:
                logger.info(f"[Groq] ✓ Success: {m}")
                return result

        raise RuntimeError(
            "[Groq] All models failed or are rate-limited. "
            "Check your API key and network connection."
        )

    def chat(
        self,
        prompt: str,
        system: str = (
            "You are a component of Stella, an autonomous self-evolving personal assistant. "
            "Be concise, helpful, and precise."
        ),
        history: Optional[list[dict]] = None,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return self._call_with_fallback(GROQ_MODELS, messages, model, max_tokens, temperature)

    def chat_json(
        self,
        prompt: str,
        system: str = (
            "Return ONLY valid JSON. "
            "No markdown fences, no extra text, no explanation."
        ),
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict:
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ]
        raw = self._call_with_fallback(
            GROQ_MODELS, messages, model, max_tokens, temperature=0.2
        )
        clean = raw.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip().rstrip("`").strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(f"[Groq] JSON parse failed: {e}\nRaw response: {raw[:300]}")
            raise ValueError(f"Model returned unparseable JSON: {e}\nRaw output: {raw[:200]}")

    def vision(
        self,
        prompt: str,
        image_b64: str,
        mime: str = "image/png",
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        # Groq doesn't have vision models in the free pool; fall back to OpenRouter
        from or_client import client as openrouter_client
        return openrouter_client.vision(prompt, image_b64, mime, system, model, max_tokens)

    def vision_from_file(
        self,
        prompt: str,
        image_path: str,
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        path = Path(image_path)
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
        mime = mime_map.get(path.suffix.lower(), "image/png")
        with open(path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        return self.vision(prompt, image_b64, mime, system, model, max_tokens)

    def multi_turn(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        return self._call_with_fallback(GROQ_MODELS, messages, model, max_tokens, temperature)

    def available_models(self) -> dict:
        return {
            "text_models":   GROQ_MODELS,
            "rate_limited":  list(_rate_limited.keys()),
            "total_text":    len(GROQ_MODELS),
        }

client = GroqClient()
