from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, Optional

import requests

from native_tools import run_native_tool_conversation, NativeToolResult
from or_client import client as openrouter_client
from groq_client import client as groq_client

logger = logging.getLogger("llm_client")

K2_NO_THINK_SUFFIX = (
    " Answer directly and concisely. Do not show any thinking, reasoning, "
    "or <ifm|think> blocks. Output only the final answer."
)
def _strip_k2_think(text: str) -> str:
    clean = re.sub(r"<ifm\|think>.*?</ifm\|think>", "", text or "", flags=re.DOTALL)
    return clean.strip()

def _detect_gguf_architecture(model_path: Path) -> str:
    try:
        from core.engine_runtime import gguf_architecture
        return gguf_architecture(model_path) or "unknown"
    except Exception:
        return "unknown"

def _is_k2_architecture(model_path: Path | None) -> bool:
    if model_path is None:
        return False
    try:
        return _detect_gguf_architecture(model_path) == "k2-horizon"
    except Exception:
        return False

def _stella_local_error(model_path: Path | None = None, detail: str | None = None) -> str:
    parts = ["Stella Local AI unavailable."]
    if detail:
        parts.append(f"Detail: {detail}")
    if model_path and model_path.exists():
        parts.append(f"Model found at {model_path} but could not be loaded.")
        parts.append("Try restarting Stella, or check that the model file is a valid GGUF.")
    elif model_path:
        parts.append(f"Model not found: {model_path}")
        parts.append("Download a GGUF model via the Stella Model Manager, or place one in models/.")
    else:
        parts.append("No local model configured. Set default_ai_provider or add a model in models/.")
    message = " ".join(parts)
    logger.error(f"[LLM Client] {message}")
    return message

def _stella_ollama_error(detail: str | None = None) -> str:
    parts = ["Stella cannot reach Ollama."]
    if detail:
        parts.append(f"Detail: {detail}")
    parts.append("Make sure Ollama is running (ollama serve) and the model is pulled (ollama pull <model>).")
    message = " ".join(parts)
    logger.error(f"[LLM Client] {message}")
def _local_chat_completion(
    messages: list[dict],
    model_path: Path | None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: Optional[dict] = None,
) -> Optional[str]:
    try:
        from core import server as _srv
    except Exception as e:
        logger.error(f"[LLM Client] Local server manager unavailable: {e}")
        return _stella_local_error(model_path, str(e))

    if model_path is None or not model_path.exists():
        return _stella_local_error(model_path)

    if not _srv.ensure_running(model_path=model_path):
        return _stella_local_error(model_path)

    try:
        port_num = _srv.port_for_model(model_path)
    except Exception:
        port_num = 11434

    endpoint = f"http://127.0.0.1:{port_num}/v1/chat/completions"

    is_k2 = _is_k2_architecture(model_path)
    if is_k2 and messages and messages[0].get("role") == "system":
        messages = [
            {**messages[0], "content": messages[0]["content"] + K2_NO_THINK_SUFFIX}
        ] + messages[1:]

    payload = {
        "model": model_path.stem,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    try:
        resp = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if is_k2:
                content = _strip_k2_think(content)
            return content.strip() if content else None
        elif resp.status_code == 503:
            try:
                _srv.auto_restart(model_path=model_path)
                resp = requests.post(endpoint, headers={"Content-Type": "application/json"}, json=payload, timeout=120)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if is_k2:
                        content = _strip_k2_think(content)
                    return content.strip() if content else None
            except Exception:
                pass
        else:
            logger.error(f"[LLM Client] Local AI Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        logger.error(f"[LLM Client] Local AI Request Failed: {e}")
def _ollama_health_check() -> bool:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def _ollama_chat_completion(
    messages: list[dict],
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: Optional[dict] = None,
) -> Optional[str]:
    endpoint = "http://localhost:11434/api/chat"

    ollama_messages = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        ollama_messages.append({"role": role, "content": content})

    payload = {
        "model": model,
        "messages": ollama_messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if response_format:
        payload["format"] = "json"

    try:
        resp = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("message", {}).get("content", "").strip() or None
        else:
            logger.error(f"[LLM Client] Ollama Error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"[LLM Client] Ollama Request Failed: {e}")
        return None

def _k2_chat_completion(
    messages: list[dict],
    model_path: Path | None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Optional[str]:
    if model_path is None:
        try:
            from core import server as _srv
            model_path = _srv.resolve_model_path()
        except Exception:
            return _stella_local_error(None)

    if model_path is None or not model_path.exists():
        return _stella_local_error(model_path)

    if not _is_k2_architecture(model_path):
        logger.warning(
            f"[LLM Client] {model_path} is not K2 architecture; "
            "routing to upstream server instead."
        )
        return _local_chat_completion(messages, model_path, temperature, max_tokens)

class UnifiedAIClient:
    def __init__(self):
        self._provider = "OpenRouter"
        self._local_url = "http://localhost:11434/v1"
        self._local_model = "llama3.2"
        self._ollama_model = "llama3.2"
        self._groq_model = "openai/gpt-oss-120b"
        self.reload_settings()

    def reload_settings(self):
        try:
            from core.user_paths import get_user_data_dir
            settings_path = get_user_data_dir() / "config" / "app_settings.json"
        except Exception:
            settings_path = Path(__file__).resolve().parent.parent.parent / "config" / "app_settings.json"

        try:
            with open(settings_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            self._provider = data.get("default_ai_provider", "OpenRouter")
            self._local_url = data.get("local_ai_url", "http://localhost:11434/v1").rstrip("/")
            self._local_model = data.get("local_ai_model", "llama3.2")
            self._ollama_model = data.get("ollama_model", "llama3.2")
            self._groq_model = data.get("groq_model", "openai/gpt-oss-120b")
        except Exception as e:
            logger.error(f"[LLM Client] Failed to load settings: {e}")

    def _local_chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        model_path = Path(self._local_model) if self._local_model else None
        return _local_chat_completion(messages, model_path, temperature, response_format=response_format)

    def _k2_chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> Optional[str]:
        from core import server as _srv
        model_path = Path(self._local_model) if self._local_model else None
        if model_path is None or not model_path.exists():
            model_path = _srv.resolve_model_path()
        return _k2_chat_completion(messages, model_path, temperature)

    def _ollama_chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        if not _ollama_health_check():
            return _stella_ollama_error()
    def chat(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        history: Optional[list[dict]] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        self.reload_settings()
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        provider = self._provider

        if provider == "Local":
            result = self._local_chat_completion(messages, temperature)
            if result:
                return result
            raise RuntimeError(_stella_local_error(Path(self._local_model) if self._local_model else None))

        elif provider == "K2":
            messages[0]["content"] = messages[0]["content"] + K2_NO_THINK_SUFFIX
            result = self._k2_chat_completion(messages, temperature)
            if result:
                return result
            raise RuntimeError(_stella_local_error(None))

        elif provider == "Ollama":
            result = self._ollama_chat_completion(messages, temperature)
            if result:
                return result
            raise RuntimeError(_stella_ollama_error())

        elif provider == "Groq":
            return groq_client.chat(prompt, system, history, self._groq_model, max_tokens, temperature)

        else:
            return openrouter_client.chat(prompt, system, history, model or self._groq_model, max_tokens, temperature)
    def chat_json(
        self,
        prompt: str,
        system: str = "Return ONLY valid JSON.",
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> dict:
        self.reload_settings()
        messages = [
            {"role": "system", "content": system + " Output valid JSON only, without any markdown formatting."},
            {"role": "user", "content": prompt},
        ]

        if self._provider == "Local":
            raw = self._local_chat_completion(messages, temperature=0.2, response_format={"type": "json_object"})
        elif self._provider == "K2":
            messages[0]["content"] = messages[0]["content"] + K2_NO_THINK_SUFFIX
            raw = self._k2_chat_completion(messages, temperature=0.2)
        elif self._provider == "Ollama":
            raw = self._ollama_chat_completion(messages, temperature=0.2, response_format={"format": "json"})
        elif self._provider == "Groq":
            raw = groq_client.chat_json(prompt, system, self._groq_model, max_tokens)
        else:
            raw = openrouter_client.chat_json(prompt, system, model or self._groq_model, max_tokens)

        if not raw:
            raise RuntimeError("Local AI request failed.")
        clean = raw.strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise
    def chat_with_tools(
        self,
        messages: list[dict],
        declarations: list[dict],
        executor: Callable,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        max_tool_turns: int = 10,
        system_prompt: Optional[str] = None,
    ) -> NativeToolResult:
        provider = provider or self._provider
        self.reload_settings()

        if provider == "Local":
            from core import server as _srv
            model_path = Path(self._local_model) if self._local_model else None
            try:
                _local_port = _srv.port_for_model(model_path)
            except Exception:
                _local_port = 11434
            provider_config = {
                "family": "local",
                "base_url": f"http://127.0.0.1:{_local_port}/v1",
                "model": self._local_model,
            }
            if model_path and not _srv.ensure_running(model_path=model_path):
                return NativeToolResult(
                    "", [], 0, False, _stella_local_error(model_path), provider
                )

        elif provider == "K2":
            from core import server as _srv
            model_path = Path(self._local_model) if self._local_model else None
            if model_path is None or not model_path.exists():
                model_path = _srv.resolve_model_path()
            provider_config = {
                "family": "local",
                "base_url": f"http://127.0.0.1:{_srv.port_for_model(model_path)}/v1",
                "model": model_path.stem if model_path else "k2-horizon",
            }
            if model_path and not _srv.ensure_running(model_path=model_path):
                return NativeToolResult(
                    "", [], 0, False, _stella_local_error(model_path), provider
                )

        elif provider == "Ollama":
            if not _ollama_health_check():
                return NativeToolResult(
                    "", [], 0, False, _stella_ollama_error(), provider
                )
            provider_config = {
                "family": "openai-compatible",
                "base_url": "http://localhost:11434/v1",
                "model": self._ollama_model,
            }

        elif provider == "Groq":
            provider_config = {
                "family": "openai-compatible",
                "base_url": "https://api.groq.com/openai/v1",
                "api_key_resolver": lambda pid: groq_client._load_api_key() if pid == "groq" else "",
                "model": self._groq_model,
            }

        elif provider == "OpenRouter":
            provider_config = {
                "family": "openai-compatible",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_resolver": lambda pid: openrouter_client._load_api_key() if pid == "openrouter" else "",
                "model": model or self._groq_model or "openrouter/auto",
            }

        else:
            return NativeToolResult(
                "", [], 0, True, f"Unknown provider: {provider}", provider
            )

        if system_prompt:
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] = system_prompt + "\n" + messages[0]["content"]
            else:
                messages.insert(0, {"role": "system", "content": system_prompt})

        return run_native_tool_conversation(
            provider_id=provider,
            provider_config=provider_config,
            messages=messages,
            declarations=declarations,
            executor=executor,
            max_tokens=max_tokens,
            temperature=temperature,
            max_tool_turns=max_tool_turns,
            system_prompt=system_prompt,
        )
client = UnifiedAIClient()
LLMClient = UnifiedAIClient
