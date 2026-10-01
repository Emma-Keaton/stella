"""
Brahma Local Brain Engine (v2)
Provides full offline local LLM execution using an OpenAI-compatible local runtime
(Ollama, LM Studio, vLLM, or LocalAI) with automatic tool-calling and hardware acceleration.
"""

import json
import urllib.request
import urllib.error
import threading
from typing import Dict, Any, List, Optional, Generator

DEFAULT_ENDPOINT = "http://localhost:11434/v1"
OLLAMA_BASE = "http://localhost:11434"


class LocalBrain:
    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, default_model: str = "qwen2.5:3b"):
        self.endpoint = endpoint.rstrip("/")
        self.default_model = default_model
        self.enabled = False
        self._cached_models: List[str] = []

    def is_available(self) -> bool:
        """Checks if the local LLM server is up and responding."""
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    self._cached_models = [m.get("name") for m in data.get("models", [])]
                    return True
        except Exception:
            pass
        return False

    def list_installed_models(self) -> List[str]:
        """Returns all downloaded models on the local runtime."""
        self.is_available()
        return self._cached_models

    def pull_model_async(self, model_name: str, progress_callback=None):
        """Pulls a model from the local runtime library in the background."""
        def _pull():
            try:
                url = f"{OLLAMA_BASE}/api/pull"
                payload = json.dumps({"name": model_name}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=1200) as resp:
                    for line in resp:
                        if line:
                            try:
                                chunk = json.loads(line.decode("utf-8"))
                                if progress_callback:
                                    progress_callback(chunk)
                            except Exception:
                                pass
            except Exception as e:
                if progress_callback:
                    progress_callback({"error": str(e)})

        threading.Thread(target=_pull, daemon=True).start()

    def generate_chat_stream(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Streams completions from the local runtime.
        Yields parsed stream delta chunks or tool calls.
        """
        active_model = model or self.default_model
        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        # Convert tool declarations if provided
        if tools:
            formatted_tools = []
            for t in tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {}),
                    }
                })
            payload["tools"] = formatted_tools

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=60.0) as resp:
            for line in resp:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    content = line_str[6:].strip()
                    if content == "[DONE]":
                        break
                    try:
                        chunk = json.loads(content)
                        yield chunk
                    except Exception:
                        pass

    def chat_complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Non-streaming completion for fast single-turn tool calls and structured responses."""
        active_model = model or self.default_model
        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            formatted_tools = []
            for t in tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {}),
                    }
                })
            payload["tools"] = formatted_tools

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90.0) as resp:
            return json.loads(resp.read().decode("utf-8"))


# Global singleton instance
local_brain = LocalBrain()
