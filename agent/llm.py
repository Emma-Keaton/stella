"""agent/llm.py - one chat interface over every backend Stella can use.

The agent loop should not care whether the tokens came from the bundled K2
runtime, Groq, or OpenRouter. This adapter normalises them onto one signature
and, importantly, *degrades honestly*: if the local runtime is not up it says
so rather than pretending an answer came from it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

SYSTEM_PREAMBLE = (
    "You are Stella, an autonomous assistant running on the user's own machine.\n"
    "Work the problem rather than describing how you would solve it.\n\n"
    "Operating rules:\n"
    "1. Use tools for anything you can verify. Do not guess file contents, the\n"
    "   current date, or arithmetic - there is a tool for each.\n"
    "2. For multi-step work, set a plan first with the `todo` tool, then update it\n"
    "   as you go so progress is visible.\n"
    "3. After a tool returns an error, read the error and adapt. Do not retry the\n"
    "   identical call more than once.\n"
    "4. If you stored something the user told you, recall it before assuming you\n"
    "   do not know it.\n"
    "5. Stop and report honestly if a step genuinely failed. Never fabricate a\n"
    "   result you did not observe.\n"
    "6. Be concise. No preamble, no restating the request back."
)


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


class LLM:
    """Chat + tool-calling against an OpenAI-compatible endpoint."""

    def __init__(self, base_url: str, model: str = "k2", timeout: float = 300.0,
                 name: str = "local") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.name = name

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/health", timeout=10) as r:
                return r.status == 200
        except Exception:
            # Some servers have no /health; fall back to /models.
            try:
                with urllib.request.urlopen(f"{self.base_url}/v1/models", timeout=10) as r:
                    return r.status == 200
            except Exception:
                return False

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             max_tokens: int = 1024, temperature: float = 0.3) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Read the error body: it often contains the exact reason the request
            # was rejected (e.g. malformed JSON, out-of-range max_tokens, unknown
            # tool name). Without it, failures are unfixable.
            try:
                body_preview = exc.read().decode("utf-8", errors="replace")[:600]
            except Exception:
                body_preview = "<body unavailable>"
            status_line = f"HTTP {exc.code} from {self.name}"
            try:
                reason = exc.reason
            except Exception:
                reason = ""
            if body_preview and body_preview != "<body unavailable>":
                status_line += f": {body_preview}"
            if reason:
                status_line += f" ({reason})"
            return LLMResponse(error=status_line)
        except Exception as exc:
            return LLMResponse(error=f"{self.name} unreachable: {exc}")

        try:
            msg = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            return LLMResponse(error=f"malformed response from {self.name}")

        return LLMResponse(
            text=(msg.get("content") or "").strip(),
            tool_calls=msg.get("tool_calls") or [],
            finish_reason=body["choices"][0].get("finish_reason", ""),
        )


class Backend:
    """Picks the first backend that actually answers.

    Order matters: local K2 first (free, private, offline), then the hosted
    providers. `candidates` is built once at construction.
    """

    def __init__(self, backends: list[LLM]) -> None:
        self.backends = backends
        self.active: LLM | None = None

    def resolve(self) -> LLM | None:
        if self.active is not None and self.active.available():
            return self.active
        for backend in self.backends:
            if backend.available():
                self.active = backend
                return backend
        self.active = None
        return None

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             **kw) -> LLMResponse:
        backend = self.resolve()
        if backend is None:
            return LLMResponse(
                error="no LLM backend is reachable (local K2 is down and no "
                      "hosted provider is configured)"
            )
        return backend.chat(messages, tools, **kw)


def default_backend() -> Backend:
    """Backend chain wired to Stella's existing runtime configuration."""
    from core import k2_runtime

    backends: list[LLM] = []

    # 1. Selected local model (managed via Settings -> Local Models). Takes
    #    priority when the user has chosen a downloaded model.
    try:
        from agent.model_manager import get_selected_model
        selected = get_selected_model()
        if selected and selected.get("endpoint"):
            backends.append(LLM(
                selected["endpoint"],
                model=selected.get("name", "local"),
                name="local-model",
                timeout=600.0,
            ))
    except Exception:
        pass

    # 2. Bundled runtime (present only on the private build; absent on the
    #    public build, in which case this simply contributes nothing).
    try:
        backends.append(LLM(
            f"http://127.0.0.1:{k2_runtime.K2_PORT}",
            model="k2", name="k2-local", timeout=600.0,
        ))
    except Exception:
        pass

    def _cloud(name: str, env: dict, url: str, model: str) -> LLM | None:
        if not env.get("api_key"):
            return None
        # Generous timeouts for cloud APIs; local models set explicitly above.
        return LLM(url, model=model, timeout=120.0, name=name)

    try:
        import os
        env = {k.lower(): v for k, v in os.environ.items()}
    except Exception:
        env = {}

    groq = _cloud("groq", env, "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile")
    if groq:
        backends.append(groq)
    return Backend(backends)