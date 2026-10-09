from core.user_paths import get_user_data_dir
import json
import logging
import requests
import time
from pathlib import Path
from typing import Optional
from or_client import client as openrouter_client
from groq_client import client as groq_client

K2_NO_THINK_SUFFIX = (
    " Answer directly and concisely. Do not show any thinking, reasoning, "
    "or <ifm|think> blocks. Output only the final answer."
)

def _strip_k2_think(text: str) -> str:
    import re
    clean = re.sub(r"<ifm\|think>.*?</ifm\|think>", "", text or "", flags=re.DOTALL)
    return clean.strip()

def _k2_chat_completion(messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> Optional[str]:
    try:
        from core import k2_server
    except Exception as e:
        raise RuntimeError(f"K2 server manager unavailable: {e}")
    if not k2_server.ensure_running():
        raise RuntimeError("K2 local server failed to start. Check models/K2-Horizon-0.9B-Q4_K_M.gguf exists.")
    payload = {"model": "k2-horizon-0.9b", "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    deadline = time.time() + 180
    while True:
        try:
            resp = requests.post(f"{k2_server.base_url()}/v1/chat/completions", headers={"Content-Type": "application/json"}, json=payload, timeout=600)
            if resp.status_code == 200:
                content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                return _strip_k2_think(content) or None
            if resp.status_code == 503 and time.time() < deadline:
                time.sleep(3)
                continue
            logger.error(f"[LLM Client] K2 Error {resp.status_code}: {resp.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"[LLM Client] K2 Request Failed: {e}")
            return None

logger = logging.getLogger("llm_client")

def _get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR = _get_base_dir()
SETTINGS_PATH = get_user_data_dir() / "config" / "app_settings.json"

class UnifiedAIClient:
    def __init__(self):
        self._provider = "OpenRouter"
        self._local_url = "http://localhost:11434/v1"
        self._local_model = "llama3.2"
        self.reload_settings()

    def reload_settings(self):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            self._provider = data.get("default_ai_provider", "OpenRouter")
            self._local_url = data.get("local_ai_url", "http://localhost:11434/v1").rstrip("/")
            self._local_model = data.get("local_ai_model", "llama3.2")
            self._groq_model = data.get("groq_model", "openai/gpt-oss-120b")
        except Exception as e:
            logger.error(f"[LLM Client] Failed to load settings: {e}")

    def _local_chat_completion(self, messages: list[dict], temperature: float = 0.7, response_format: Optional[dict] = None) -> Optional[str]:
        payload = {
            "model": self._local_model,
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            payload["response_format"] = response_format

        endpoint = f"{self._local_url}/chat/completions"
        try:
            resp = requests.post(
                endpoint,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content.strip() if content else None
            else:
                logger.error(f"[LLM Client] Local AI Error {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"[LLM Client] Local AI Request Failed: {e}")
            return None

    def chat(self, prompt: str, system: str = "You are a helpful assistant.", history: Optional[list[dict]] = None, model: Optional[str] = None, max_tokens: int = 4096, temperature: float = 0.7) -> str:
        self.reload_settings()
        if self._provider == "Local":
            messages = [{"role": "system", "content": system}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": prompt})
            result = self._local_chat_completion(messages, temperature)
            if result:
                return result
            else:
                raise RuntimeError("Local AI request failed. Please check if Ollama or LM Studio is running.")
        elif self._provider == "Groq":
            return groq_client.chat(prompt, system, history, self._groq_model, max_tokens, temperature)
        elif self._provider == "K2":
            messages = [{"role": "system", "content": system + K2_NO_THINK_SUFFIX}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": prompt})
            result = _k2_chat_completion(messages, temperature, max_tokens)
            if result:
                return result
            raise RuntimeError("K2 local inference failed. Is the model file present in models/?")
        else:
            return openrouter_client.chat(prompt, system, history, model, max_tokens, temperature)

    def chat_json(self, prompt: str, system: str = "Return ONLY valid JSON.", model: Optional[str] = None, max_tokens: int = 4096) -> dict:
        self.reload_settings()
        if self._provider == "Local":
            messages = [
                {"role": "system", "content": system + " Output valid JSON only, without any markdown formatting."},
                {"role": "user", "content": prompt}
            ]
            raw = self._local_chat_completion(messages, temperature=0.2, response_format={"type": "json_object"})
            if not raw:
                raise RuntimeError("Local AI request failed.")
            
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
                raise ValueError(f"Local model returned unparseable JSON: {e}\nRaw output: {raw[:200]}")
        elif self._provider == "Groq":
            return groq_client.chat_json(prompt, system, self._groq_model, max_tokens)
        elif self._provider == "K2":
            messages = [
                {"role": "system", "content": system + K2_NO_THINK_SUFFIX + " Output valid JSON only, without any markdown formatting."},
                {"role": "user", "content": prompt}
            ]
            raw = _k2_chat_completion(messages, temperature=0.2, max_tokens=max_tokens)
            if not raw:
                raise RuntimeError("K2 local inference failed.")
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
                raise ValueError(f"K2 model returned unparseable JSON: {e}\nRaw output: {raw[:200]}")
        else:
            return openrouter_client.chat_json(prompt, system, model, max_tokens)

    def vision(self, prompt: str, image_b64: str, mime: str = "image/png", system: str = "Analyze the image.", model: Optional[str] = None, max_tokens: int = 1024) -> str:
        self.reload_settings()
        if self._provider == "Local":
            messages = [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            result = self._local_chat_completion(messages, temperature=0.2)
            if result:
                return result
            raise RuntimeError("Local AI vision request failed.")
        elif self._provider == "Groq":
            return groq_client.vision(prompt, image_b64, mime, system, self._groq_model, max_tokens)
        else:
            return openrouter_client.vision(prompt, image_b64, mime, system, model, max_tokens)

    def vision_from_file(self, prompt: str, image_path: str, system: str = "Analyze the image.", model: Optional[str] = None, max_tokens: int = 1024) -> str:
        self.reload_settings()
        if self._provider == "Local":
            import base64
            path = Path(image_path)
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
            mime = mime_map.get(path.suffix.lower(), "image/png")
            with open(path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")
            return self.vision(prompt, image_b64, mime, system, model, max_tokens)
        elif self._provider == "Groq":
            return groq_client.vision_from_file(prompt, image_path, system, self._groq_model, max_tokens)
        else:
            return openrouter_client.vision_from_file(prompt, image_path, system, model, max_tokens)

    def multi_turn(self, messages: list[dict], model: Optional[str] = None, max_tokens: int = 4096, temperature: float = 0.7) -> str:
        self.reload_settings()
        if self._provider == "Local":
            result = self._local_chat_completion(messages, temperature)
            if result:
                return result
            raise RuntimeError("Local AI request failed.")
        elif self._provider == "Groq":
            return groq_client.multi_turn(messages, self._groq_model, max_tokens, temperature)
        elif self._provider == "K2":
            result = _k2_chat_completion(messages, temperature, max_tokens)
            if result:
                return result
            raise RuntimeError("K2 local inference failed.")
        else:
            return openrouter_client.multi_turn(messages, model, max_tokens, temperature)

client = UnifiedAIClient()
LLMClient = UnifiedAIClient
