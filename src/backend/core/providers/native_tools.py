"""
src/backend/core/providers/native_tools.py — Native tool calling for ALL providers.

Supports:
  • OpenAI-compatible (groq, openrouter, openai, ollama, lmstudio, custom)
    — `tools` param + `tool_calls` response
  • Anthropic (claude-*) — `tools` param + `tool_use` blocks in response
  • Gemini (gemini-*) — `functionDeclarations` + `functionCall` parts
  • Local llama.cpp / K2 servers — OpenAI-compatible `tools` + `tool_calls`

Returns a NativeToolResult with content + executed tool results.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Optional

import requests

logger = logging.getLogger("stella.providers.native_tools")

# Provider families
OPENAI_COMPATIBLE = {"groq", "openrouter", "openai", "ollama", "lmstudio", "custom"}
ANTHROPIC = {"anthropic"}
GEMINI = {"gemini"}


class NativeToolResult:
    """Result of a native tool call conversation."""

    def __init__(
        self,
        content: str = "",
        tool_calls: Optional[list[dict]] = None,
        turns: int = 0,
        ok: bool = True,
        error: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.turns = turns
        self.ok = ok
        self.error = error
        self.provider = provider

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "tool_calls": self.tool_calls,
            "turns": self.turns,
            "ok": self.ok,
            "error": self.error,
            "provider": self.provider,
        }


# ──────────────────────────────────────────────────────────────────────
# OpenAI-compatible native tool calling
# ──────────────────────────────────────────────────────────────────────

def _openai_compatible_headers(api_key: str, provider_id: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if provider_id == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/stella-ai"
        headers["X-Title"] = "Stella"
    return headers


def _openai_compatible_tools(declarations: list[dict]) -> list[dict]:
    tools = []
    for decl in declarations:
        tools.append({
            "type": "function",
            "function": {
                "name": decl.get("name", ""),
                "description": decl.get("description", ""),
                "parameters": decl.get("parameters", {"type": "object", "properties": {}}),
            },
        })
    return tools


def _openai_compatible_chat_with_tools(
    provider_id: str,
    base_url: str,
    api_key_resolver: Callable[[str], str],
    model: str,
    messages: list[dict],
    declarations: list[dict],
    executor: Any,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    max_tool_turns: int = 10,
) -> NativeToolResult:
    """Native tool calling via OpenAI-compatible chat/completions."""
    tools = _openai_compatible_tools(declarations)
    tool_results: list[dict] = []
    turns = 0
    current_messages = list(messages)

    for turn in range(max_tool_turns):
        turns += 1
        api_key = api_key_resolver(provider_id) if api_key_resolver else ""
        payload = {
            "model": model,
            "messages": current_messages,
            "tools": tools,
            "tool_choice": "required",
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=_openai_compatible_headers(api_key, provider_id),
                json=payload,
                timeout=120,
            )
        except Exception as e:
            logger.error("OpenAI-compatible tool call failed: %s", e)
            return NativeToolResult("", tool_results, turns, False, str(e), provider_id)

        if resp.status_code != 200:
            logger.error("OpenAI-compatible HTTP %d: %s", resp.status_code, resp.text[:200])
            return NativeToolResult("", tool_results, turns, False, f"HTTP {resp.status_code}", provider_id)

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        current_messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            content = message.get("content", "") or ""
            return NativeToolResult(content, tool_results, turns, True, None, provider_id)

        # Execute each tool call locally
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            arguments = fn.get("arguments", "{}")
            call_id = tc.get("id", "")

            try:
                params = json.loads(arguments) if isinstance(arguments, str) else arguments
            except json.JSONDecodeError:
                params = {}

            context = {"source": "native_tool_call", "turn": turns, "provider": provider_id}
            try:
                result = executor.execute(name, params, context)
                tool_results.append({
                    "tool_call_id": call_id,
                    "name": name,
                    "result": result,
                    "error": None,
                })
            except Exception as e:
                logger.error("Tool %s execution failed: %s", name, e)
                tool_results.append({
                    "tool_call_id": call_id,
                    "name": name,
                    "result": "",
                    "error": str(e),
                })

        current_messages.extend(tool_results[-len(tool_calls):])

    return NativeToolResult("", tool_results, turns, False, f"Max tool turns ({max_tool_turns}) reached", provider_id)


# ──────────────────────────────────────────────────────────────────────
# Anthropic native tool calling
# ──────────────────────────────────────────────────────────────────────

def _anthropic_headers(api_key: str) -> dict[str, str]:
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }


def _anthropic_tools(declarations: list[dict]) -> list[dict]:
    tools = []
    for decl in declarations:
        tools.append({
            "name": decl.get("name", ""),
            "description": decl.get("description", ""),
            "input_schema": decl.get("parameters", {"type": "object", "properties": {}}),
        })
    return tools


def _anthropic_chat_with_tools(
    api_key_resolver: Callable[[str], str],
    model: str,
    messages: list[dict],
    declarations: list[dict],
    executor: Any,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    max_tool_turns: int = 10,
    system_prompt: Optional[str] = None,
) -> NativeToolResult:
    """Native tool calling via Anthropic messages API."""
    tools = _anthropic_tools(declarations)
    tool_results: list[dict] = []
    turns = 0

    # Separate system message from conversation
    system = system_prompt or ""
    conv_messages = []
    for m in messages:
        if m.get("role") == "system":
            system = m.get("content", "")
        else:
            conv_messages.append(m)

    current_messages = list(conv_messages)

    for turn in range(max_tool_turns):
        turns += 1
        api_key = api_key_resolver("anthropic") if api_key_resolver else ""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": current_messages,
            "tools": tools,
            "tool_choice": {"type": "any"},
        }

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=_anthropic_headers(api_key),
                json=payload,
                timeout=120,
            )
        except Exception as e:
            logger.error("Anthropic tool call failed: %s", e)
            return NativeToolResult("", tool_results, turns, False, str(e), "anthropic")

        if resp.status_code != 200:
            logger.error("Anthropic HTTP %d: %s", resp.status_code, resp.text[:200])
            return NativeToolResult("", tool_results, turns, False, f"HTTP {resp.status_code}", "anthropic")

        data = resp.json()
        content_blocks = data.get("content", [])

        # Append assistant message
        current_messages.append({"role": "assistant", "content": content_blocks})

        tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
        if not tool_use_blocks:
            # No more tool calls — return text
            text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
            content = "\n".join(text_parts)
            return NativeToolResult(content, tool_results, turns, True, None, "anthropic")

        # Execute each tool call locally
        for block in tool_use_blocks:
            name = block.get("name", "")
            input_data = block.get("input", {})
            tool_use_id = block.get("id", "")

            context = {"source": "native_tool_call", "turn": turns, "provider": "anthropic"}
            try:
                result = executor.execute(name, input_data if isinstance(input_data, dict) else {}, context)
                tool_results.append({
                    "tool_use_id": tool_use_id,
                    "name": name,
                    "result": result,
                    "error": None,
                })
            except Exception as e:
                logger.error("Tool %s execution failed: %s", name, e)
                tool_results.append({
                    "tool_use_id": tool_use_id,
                    "name": name,
                    "result": "",
                    "error": str(e),
                })

        # Append tool results as user messages
        tool_result_blocks = []
        for tr in tool_results[-len(tool_use_blocks):]:
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": tr["tool_use_id"],
                "content": tr["result"] if not tr["error"] else f"Error: {tr['error']}",
            })
        current_messages.append({"role": "user", "content": tool_result_blocks})

    return NativeToolResult("", tool_results, turns, False, f"Max tool turns ({max_tool_turns}) reached", "anthropic")


# ──────────────────────────────────────────────────────────────────────
# Gemini native tool calling
# ──────────────────────────────────────────────────────────────────────

def _gemini_headers(api_key: str) -> dict[str, str]:
    return {
        "x-goog-api-key": api_key,
        "content-type": "application/json",
    }


def _gemini_tools(declarations: list[dict]) -> list[dict]:
    funcs = []
    for decl in declarations:
        funcs.append({
            "name": decl.get("name", ""),
            "description": decl.get("description", ""),
            "parameters": decl.get("parameters", {"type": "object", "properties": {}}),
        })
    return [{"function_declarations": funcs}] if funcs else []


def _gemini_chat_with_tools(
    api_key_resolver: Callable[[str], str],
    model: str,
    messages: list[dict],
    declarations: list[dict],
    executor: Any,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    max_tool_turns: int = 10,
    system_prompt: Optional[str] = None,
) -> NativeToolResult:
    """Native tool calling via Gemini generateContent API."""
    tools = _gemini_tools(declarations)
    tool_results: list[dict] = []
    turns = 0

    # Build Gemini contents from messages
    contents = []
    for m in messages:
        role = m.get("role", "user")
        gemini_role = "model" if role == "assistant" else "user"
        parts = []
        if isinstance(m.get("content"), str):
            parts.append({"text": m["content"]})
        elif isinstance(m.get("content"), list):
            for block in m["content"]:
                if block.get("type") == "text":
                    parts.append({"text": block.get("text", "")})
                elif block.get("type") == "tool_use":
                    parts.append({
                        "functionCall": {
                            "name": block.get("name", ""),
                            "args": block.get("input", {}),
                        },
                    })
                elif block.get("type") == "tool_result":
                    parts.append({
                        "functionResponse": {
                            "name": block.get("name", ""),
                            "response": {"result": block.get("result", ""), "error": block.get("error")},
                        },
                    })
        contents.append({"role": gemini_role, "parts": parts})

    # System prompt as first user message if provided
    if system_prompt:
        contents.insert(0, {"role": "user", "parts": [{"text": system_prompt}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    for turn in range(max_tool_turns):
        turns += 1
        api_key = api_key_resolver("gemini") if api_key_resolver else ""
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if tools:
            payload["tools"] = tools
            payload["toolConfig"] = {"functionCallingConfig": {"mode": "ANY"}}

        try:
            resp = requests.post(url, headers=_gemini_headers(api_key), json=payload, timeout=120)
        except Exception as e:
            logger.error("Gemini tool call failed: %s", e)
            return NativeToolResult("", tool_results, turns, False, str(e), "gemini")

        if resp.status_code != 200:
            logger.error("Gemini HTTP %d: %s", resp.status_code, resp.text[:200])
            return NativeToolResult("", tool_results, turns, False, f"HTTP {resp.status_code}", "gemini")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return NativeToolResult("", tool_results, turns, False, "No candidates", "gemini")

        parts = candidates[0].get("content", {}).get("parts", [])
        # Append model response
        model_parts = []
        for p in parts:
            if "text" in p:
                model_parts.append(p)
            elif "functionCall" in p:
                model_parts.append(p)
        contents.append({"role": "model", "parts": model_parts})

        function_calls = [p for p in parts if "functionCall" in p]
        if not function_calls:
            text_parts = [p.get("text", "") for p in parts if "text" in p]
            content = "\n".join(text_parts)
            return NativeToolResult(content, tool_results, turns, True, None, "gemini")

        # Execute each function call locally
        for fc in function_calls:
            fc_data = fc.get("functionCall", {})
            name = fc_data.get("name", "")
            args = fc_data.get("args", {})

            context = {"source": "native_tool_call", "turn": turns, "provider": "gemini"}
            try:
                result = executor.execute(name, args if isinstance(args, dict) else {}, context)
                tool_results.append({
                    "name": name,
                    "result": result,
                    "error": None,
                })
            except Exception as e:
                logger.error("Tool %s execution failed: %s", name, e)
                tool_results.append({
                    "name": name,
                    "result": "",
                    "error": str(e),
                })

        # Append function responses
        response_parts = []
        for tr in tool_results[-len(function_calls):]:
            response_parts.append({
                "functionResponse": {
                    "name": tr["name"],
                    "response": {"result": tr["result"], "error": tr["error"]},
                },
            })
        contents.append({"role": "function", "parts": response_parts})

    return NativeToolResult("", tool_results, turns, False, f"Max tool turns ({max_tool_turns}) reached", "gemini")


# ──────────────────────────────────────────────────────────────────────
# Local llama.cpp / K2 server native tool calling
# ──────────────────────────────────────────────────────────────────────

def _local_server_chat_with_tools(
    base_url: str,
    model: str,
    messages: list[dict],
    declarations: list[dict],
    executor: Any,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    max_tool_turns: int = 10,
) -> NativeToolResult:
    """Native tool calling via local llama.cpp / K2 OpenAI-compatible server."""
    # Local servers speak OpenAI-compatible chat/completions
    result = _openai_compatible_chat_with_tools(
        provider_id="local",
        base_url=base_url,
        api_key_resolver=lambda _: "",  # no auth for local
        model=model,
        messages=messages,
        declarations=declarations,
        executor=executor,
        max_tokens=max_tokens,
        temperature=temperature,
        max_tool_turns=max_tool_turns,
    )
    return NativeToolResult(
        content=result.content,
        tool_calls=result.tool_calls,
        turns=result.turns,
        ok=result.ok,
        error=result.error,
        provider="local",
    )


# ──────────────────────────────────────────────────────────────────────
# Unified dispatcher
# ──────────────────────────────────────────────────────────────────────

def run_native_tool_conversation(
    provider_id: str,
    provider_config: dict,
    messages: list[dict],
    declarations: list[dict],
    executor: Any,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    max_tool_turns: int = 10,
    system_prompt: Optional[str] = None,
) -> NativeToolResult:
    """
    Dispatch native tool calling to the correct provider backend.

    provider_config keys depend on provider family:
      - openai-compatible: base_url, api_key_resolver, model
      - anthropic: api_key_resolver, model
      - gemini: api_key_resolver, model
      - local: base_url, model
    """
    family = provider_config.get("family", "openai-compatible")

    if family in OPENAI_COMPATIBLE:
        return _openai_compatible_chat_with_tools(
            provider_id=provider_id,
            base_url=provider_config.get("base_url", "http://localhost:11434/v1"),
            api_key_resolver=provider_config.get("api_key_resolver"),
            model=provider_config.get("model", ""),
            messages=messages,
            declarations=declarations,
            executor=executor,
            max_tokens=max_tokens,
            temperature=temperature,
            max_tool_turns=max_tool_turns,
        )

    if family in ANTHROPIC:
        return _anthropic_chat_with_tools(
            api_key_resolver=provider_config.get("api_key_resolver"),
            model=provider_config.get("model", ""),
            messages=messages,
            declarations=declarations,
            executor=executor,
            max_tokens=max_tokens,
            temperature=temperature,
            max_tool_turns=max_tool_turns,
            system_prompt=system_prompt,
        )

    if family in GEMINI:
        return _gemini_chat_with_tools(
            api_key_resolver=provider_config.get("api_key_resolver"),
            model=provider_config.get("model", ""),
            messages=messages,
            declarations=declarations,
            executor=executor,
            max_tokens=max_tokens,
            temperature=temperature,
            max_tool_turns=max_tool_turns,
            system_prompt=system_prompt,
        )

    if family == "local":
        return _local_server_chat_with_tools(
            base_url=provider_config.get("base_url", "http://localhost:11434/v1"),
            model=provider_config.get("model", ""),
            messages=messages,
            declarations=declarations,
            executor=executor,
            max_tokens=max_tokens,
            temperature=temperature,
            max_tool_turns=max_tool_turns,
        )

    # Unknown provider — fall back to plain text (no tools)
    logger.warning("Unknown provider family %s for %s — no native tool calling", family, provider_id)
    return NativeToolResult("", [], 0, True, None, provider_id)
