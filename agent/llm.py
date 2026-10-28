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

from core.model_ladder import ModelLadder, DEFAULT_LADDER

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
                 name: str = "local", api_key: str = "",
                 auth_header: str = "Authorization",
                 auth_prefix: str = "Bearer ") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.name = name
        self.api_key = api_key
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix

    def _headers(self) -> dict[str, str]:
        """Request headers, including the provider auth header when there is a key."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers[self.auth_header] = f"{self.auth_prefix}{self.api_key}"
        return headers

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
            headers=self._headers(),
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

    The ModelLadder wraps this with per-rung cooldowns: a failed backend is
    locked out for its cooldown period, and the ladder picks the lowest-tier
    available model. Honesty: a model in cooldown is never silently retried.
    """

    def __init__(self, backends: list[LLM]) -> None:
        self._backends: list[LLM] = list(backends)
        self._active: LLM | None = None
        self._ladder = ModelLadder.from_config()

    def resolve(self) -> LLM | None:
        """Pick the best available model via the ModelLadder.

        Falls back to first-available if the ladder has no available rungs.
        """
        pick = self._ladder.pick()
        if pick is not None:
            for b in self._backends:
                if b.name == pick.name and b.available():
                    self._active = b
                    return b
        # Fallback: first available backend (ladder has nothing available)
        for b in self._backends:
            if b.available():
                self._active = b
                return b
        self._active = None
        return None

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             **kw) -> LLMResponse:
        backend = self.resolve()
        if backend is None:
            return LLMResponse(
                error="no LLM backend is reachable (local K2 is down and no "
                      "hosted provider is configured)"
            )
        result = backend.chat(messages, tools, **kw)
        if result.ok:
            self._ladder.report_success(backend.name)
        else:
            self._ladder.report_failure(backend.name)
        return result


class CloudLLM:
    """A cloud provider backend that resolves keys per-request via adapters.chat().

    Unlike the raw `LLM` class, this:
    * resolves the API key on every request (a UI save takes effect immediately),
    * speaks the provider's native wire format (Anthropic / Gemini / OpenAI-compat),
    * never snapshots the key at construction time.
    """

    def __init__(self, provider_id: str, entry: dict) -> None:
        self.provider_id = provider_id
        self.entry = entry
        self.name = f"cloud-{provider_id}"
        self.model = entry.get("model", "")

    def available(self) -> bool:
        """A cloud provider is available if it has a key configured."""
        from core.providers.keys import resolve_key

        return bool(resolve_key(self.provider_id))

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
        **kw,
    ) -> LLMResponse:
        from core.providers.adapters import ProviderError, chat as adapter_chat

        try:
            text = adapter_chat(
                self.provider_id,
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return LLMResponse(text=text, finish_reason="stop")
        except ProviderError as e:
            return LLMResponse(error=f"[{self.provider_id}] {e}")
        except Exception as e:
            return LLMResponse(error=f"[{self.provider_id}] {e}")


def default_backend() -> Backend:
    """Backend chain wired to Stella's existing runtime configuration."""
    from core import engine_runtime

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
            f"http://127.0.0.1:{engine_runtime.K2_PORT}",
            model="k2", name="k2-local", timeout=600.0,
        ))
    except Exception:
        pass

    # 3. Cloud providers, resolved from the shared provider configuration.
    #    The chain comes from the registry + the saved provider store, so a key
    #    saved in Settings > Cloud Providers is actually used here (T1.10).
    #    Uses adapters.chat() so each provider speaks its native wire format
    #    and keys are resolved per-request (no import-time snapshot).
    try:
        from core.providers.router import ProviderRouter
        for entry in ProviderRouter().chain("agent"):
            backends.append(CloudLLM(entry["provider"], entry))
    except Exception:
        pass

    return Backend(backends)