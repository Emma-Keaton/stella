"""core/providers/adapters.py - per-provider wire formats.

Two wire formats are supported:

* `openai`    - POST {base}/chat/completions, `Authorization: Bearer <key>`,
                body `{model, messages, max_tokens, temperature}`.
* `anthropic` - POST {base}/v1/messages, `x-api-key: <key>` plus
                `anthropic-version: 2023-06-01`, body
                `{model, max_tokens, messages, system}` where `system` is a
                top-level field rather than a message.

Anthropic is NOT OpenAI-compatible. Sending it `Authorization: Bearer` to
`/chat/completions` 404s silently - this adapter is the fix (T1.4).

Every adapter resolves its key through `core.providers.keys.resolve_key()` on
each request, so a key saved in the UI takes effect without a restart (T1.9).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

logger = logging.getLogger("providers.adapters")

DEFAULT_TIMEOUT = 120
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7


class ProviderError(RuntimeError):
    """A provider request failed. Carries a safe, truncated message."""

    def __init__(self, provider_id: str, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.provider_id = provider_id
        self.status = status


def _truncate(text: str, limit: int = 200) -> str:
    """Truncate a provider error body so a key can never be echoed at length."""
    text = (text or "").strip()
    return text[:limit]


def _error_message(provider_id: str, resp: Any) -> str:
    """Build a safe error message from a response."""
    status = getattr(resp, "status_code", None)
    body = ""
    try:
        body = resp.text or ""
    except Exception:
        body = ""
    detail = _truncate(body)
    return f"[{provider_id}] HTTP {status}: {detail}" if detail else f"[{provider_id}] HTTP {status}"


def _auth_headers(provider_id: str, cfg: dict[str, Any]) -> dict[str, str]:
    """Build the auth headers for a provider, per its registry auth_style."""
    key = cfg.get("api_key") or ""
    style = cfg.get("auth_style") or "bearer"
    headers: dict[str, str] = {"Content-Type": "application/json"}

    if style == "none":
        pass
    elif style == "x-api-key":
        if key:
            headers["x-api-key"] = key
    else:  # bearer / custom
        if key:
            headers["Authorization"] = f"Bearer {key}"

    # User-supplied headers win over the derived ones.
    headers.update({str(k): str(v) for k, v in (cfg.get("headers") or {}).items()})
    return headers


def _build_openai_body(cfg: dict[str, Any], messages: list[dict], **kw) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": cfg.get("model") or "",
        "messages": messages,
        "max_tokens": int(kw.get("max_tokens") or DEFAULT_MAX_TOKENS),
        "temperature": float(kw.get("temperature", DEFAULT_TEMPERATURE)),
    }
    if kw.get("response_format"):
        body["response_format"] = kw["response_format"]
    body.update(cfg.get("params") or {})
    return body


def _build_anthropic_body(cfg: dict[str, Any], messages: list[dict], **kw) -> dict[str, Any]:
    """Anthropic Messages API body.

    `system` is a top-level string, not a message in the list. Anthropic
    rejects a `system`-role message in `messages`.
    """
    system = None
    chat: list[dict] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            system = content if isinstance(content, str) else json.dumps(content)
            continue
        if role not in ("user", "assistant"):
            continue
        # Anthropic requires strictly alternating user/assistant turns and
        # does not accept an empty content list.
        if not content:
            continue
        chat.append({"role": role, "content": content})

    body: dict[str, Any] = {
        "model": cfg.get("model") or "",
        "max_tokens": int(kw.get("max_tokens") or DEFAULT_MAX_TOKENS),
        "temperature": float(kw.get("temperature", DEFAULT_TEMPERATURE)),
        "messages": chat,
    }
    if system:
        body["system"] = system
    return body


def _extract_openai_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return (message.get("content") or "").strip()


def _extract_anthropic_text(payload: dict[str, Any]) -> str:
    """Anthropic returns a list of content blocks, each with `text`."""
    blocks = payload.get("content") or []
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "".join(parts).strip()


def chat(provider_id: str, messages: list[dict], **kw) -> str:
    """Send a chat request to a provider and return the assistant text.

    Raises ProviderError on failure. The caller decides whether to fall back.
    """
    import requests

    from core.providers.keys import resolve_provider_config

    cfg = resolve_provider_config(provider_id)
    pid = cfg["provider"]
    base = cfg.get("base_url") or ""
    if not base:
        raise ProviderError(pid, f"[{pid}] No base URL configured.")

    if cfg.get("requires_key") and not cfg.get("api_key"):
        raise ProviderError(
            pid,
            f"[{pid}] API key is missing. Add one in Settings > Cloud Providers.",
        )

    wire = cfg.get("wire_format") or "openai"
    headers = _auth_headers(pid, cfg)

    if wire == "anthropic":
        url = base.rstrip("/") + "/v1/messages"
        body = _build_anthropic_body(cfg, messages, **kw)
        headers["anthropic-version"] = "2023-06-01"
        extract = _extract_anthropic_text
    else:
        url = base.rstrip("/") + "/chat/completions"
        body = _build_openai_body(cfg, messages, **kw)
        extract = _extract_openai_text

    timeout = float(kw.get("timeout") or DEFAULT_TIMEOUT)
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    except Exception as e:
        raise ProviderError(pid, f"[{pid}] Request failed: {e}") from e

    if resp.status_code == 401 or resp.status_code == 403:
        raise ProviderError(
            pid,
            f"[{pid}] Authentication failed. Check the API key for {pid}.",
            status=resp.status_code,
        )
    if resp.status_code >= 400:
        raise ProviderError(pid, _error_message(pid, resp), status=resp.status_code)

    try:
        payload = resp.json()
    except Exception as e:
        raise ProviderError(pid, f"[{pid}] Malformed response: {e}") from e

    text = extract(payload)
    if not text:
        raise ProviderError(pid, f"[{pid}] Empty response from provider.")
    return text


def list_models(provider_id: str, api_key: Optional[str] = None) -> list[str]:
    """Fetch the model list for a provider.

    Anthropic has no /models endpoint, so its static registry list is returned.
    """
    from core.providers.keys import resolve_key
    from core.providers.registry import models_endpoint, static_models

    pid = str(provider_id or "").strip().lower()
    endpoint = models_endpoint(pid)
    if not endpoint:
        return static_models(pid)
    if not api_key:
        api_key = resolve_key(pid)

    import requests

    from core.providers.registry import base_url_for

    base = base_url_for(pid)
    if not base:
        return static_models(pid)

    headers = {"Content-Type": "application/json"}
    if api_key:
        if pid == "anthropic":
            headers["x-api-key"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(base.rstrip("/") + endpoint, headers=headers, timeout=10)
        if resp.status_code >= 400:
            return static_models(pid)
        payload = resp.json()
    except Exception as e:
        logger.warning("[%s] Could not fetch models: %s", pid, e)
        return static_models(pid)

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        data = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return static_models(pid)

    models: list[str] = []
    for entry in data:
        if isinstance(entry, str):
            models.append(entry)
        elif isinstance(entry, dict):
            name = entry.get("id") or entry.get("name") or entry.get("model")
            if name:
                models.append(str(name))
    return models or static_models(pid)
