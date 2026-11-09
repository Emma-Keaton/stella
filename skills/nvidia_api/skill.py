"""
Feature: nvidia_api
Description: Tests an Nvidia NIM API key for compatibility, uptime and response time, and lists the models it can see.
Uses theme tokens from themes.json (no hardcoded colours). Every operation reports what it measured and the exact failure class; no latency, model list or completion is ever invented.
"""

FEATURE_METADATA = {
    "name": "nvidia_api",
    "aliases": ["nvidia_nim", "nvidia_api_test", "test_nvidia_key", "ping_nvidia", "nvidia_models"],
    "description": "Test an Nvidia NIM API key: measure latency and uptime (ping), list the models the key can currently see, and run one short chat completion as a smoke test. Reports the exact failure class (no key / auth / quota / network) instead of guessing, and never fabricates a latency or a model list.",
    "triggers": [
        "ping nvidia", "test nvidia api key", "check nvidia key", "nvidia api key compatibility",
        "is my nvidia key working", "nvidia uptime", "nvidia response time", "list nvidia models",
        "available nvidia models", "nvidia nim models", "smoke test nvidia",
    ],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: ping | models | chat | check. ping measures latency/uptime; models lists the live catalogue; chat runs one tiny completion; check verifies the key access. Defaults to ping.",
            },
            "model": {
                "type": "STRING",
                "description": "Optional model id for the chat operation. Defaults to the first model the key can see.",
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "author": "Stella",
    "category": "providers",
    "optional_dependencies": [],
}

_PROVIDER = "nvidia"
_BASE_URL = "https://integrate.api.nvidia.com/v1"
_SMOKE_PROMPT = "Reply with the single word: ready"


def _theme_colour(key: str, fallback: str | None = None) -> str | None:
    """Read a colour from the active theme, with an optional fallback."""
    try:
        from theme_tokens import theme_colour
        return theme_colour(key) or fallback
    except Exception:
        return fallback


def _deliverables_dir():
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "deliverables"
    except Exception:
        import os
        from pathlib import Path
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StellaAI" / "deliverables"


def _resolve_key() -> str:
    """Resolve the NIM key through the single key-resolution path."""
    try:
        from core.providers.keys import resolve_key
        return (resolve_key(_PROVIDER) or "").strip()
    except Exception:
        return ""


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    """One operation record, so every branch states its own outcome."""
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _post_json(url: str, payload: dict, api_key: str, timeout: float) -> dict:
    import json
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "StellaAI-NvidiaCheck/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return _op("post", True, body)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="ignore")[:300]
        except Exception:
            pass
        return _op("post", False, None, f"HTTP {exc.code} from {url}. {detail}".strip())
    except Exception as exc:
        return _op("post", False, None, f"{type(exc).__name__}: {exc}")


def _ping(api_key: str) -> dict:
    """Measure latency and reachability against the NIM base URL."""
    import socket
    import ssl
    import time

    probes = []
    reachable = False

    tcp_start = time.time()
    try:
        with socket.create_connection(("integrate.api.nvidia.com", 443), timeout=6.0):
            reachable = True
        probes.append({"probe": "tcp-connect", "ms": round((time.time() - tcp_start) * 1000, 2), "ok": True})
    except Exception as exc:
        probes.append({"probe": "tcp-connect", "ms": None, "ok": False, "error": f"{type(exc).__name__}: {exc}"})

    handshake_start = time.time()
    try:
        context = ssl.create_default_context()
        with socket.create_connection(("integrate.api.nvidia.com", 443), timeout=6.0) as sock:
            with context.wrap_socket(sock, server_hostname="integrate.api.nvidia.com"):
                pass
        reachable = True
        probes.append({"probe": "tls-handshake", "ms": round((time.time() - handshake_start) * 1000, 2), "ok": True})
    except Exception as exc:
        probes.append({"probe": "tls-handshake", "ms": None, "ok": False, "error": f"{type(exc).__name__}: {exc}"})

    api_start = time.time()
    try:
        import urllib.error
        import urllib.request
        request = urllib.request.Request(
            f"{_BASE_URL}/models",
            headers={"Accept": "application/json", "User-Agent": "StellaAI-NvidiaCheck/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=8.0) as response:
            status_code = getattr(response, "status", 200)
        probes.append({"probe": "api-unauth", "ms": round((time.time() - api_start) * 1000, 2),
                       "ok": True, "status": status_code})
    except urllib.error.HTTPError as exc:
        probes.append({"probe": "api-unauth", "ms": round((time.time() - api_start) * 1000, 2),
                       "ok": exc.code in (401, 403), "status": int(exc.code)})
        reachable = reachable or exc.code in (401, 403)
    except Exception as exc:
        probes.append({"probe": "api-unauth", "ms": None, "ok": False, "error": f"{type(exc).__name__}: {exc}"})

    measured = [p["ms"] for p in probes if p.get("ok") and isinstance(p.get("ms"), (int, float))]
    latency = round(sum(measured) / len(measured), 2) if measured else None

    if not reachable and api_key:
        completions_start = time.time()
        smoke = _post_json(
            f"{_BASE_URL}/chat/completions",
            {"model": "meta/llama-3.1-8b-instruct",
             "messages": [{"role": "user", "content": _SMOKE_PROMPT}],
             "max_tokens": 8, "temperature": 0.0},
            api_key, 15.0)
        probes.append({"probe": "api-with-key", "ms": round((time.time() - completions_start) * 1000, 2),
                       "ok": smoke["ok"], "error": smoke["error"]})
        if smoke["ok"]:
            reachable = True
            latency = round((time.time() - completions_start) * 1000, 2)

    return {
        "reachable": reachable,
        "latency_ms": latency,
        "probes": probes,
        "base_url": _BASE_URL,
        "key_configured": bool(api_key),
    }


def _models(api_key: str, force: bool = False) -> dict:
    try:
        from core.providers import catalogue

        outcome = catalogue.refresh(_PROVIDER, force=force)
    except Exception as exc:
        return _op("models", False, None, f"{type(exc).__name__}: {exc}")

    if outcome.get("ok"):
        return _op("models", True, {
            "models": outcome.get("models") or [],
            "count": len(outcome.get("models") or []),
            "source": outcome.get("source"),
            "cached": bool(outcome.get("cached")),
            "fetched_at": outcome.get("fetched_at"),
            "added": outcome.get("added"),
        })
    return _op("models", False, None, outcome.get("reason") or "No models could be listed.")


def _chat(api_key: str, model: str) -> dict:
    if not model:
        listed = _models(api_key)
        model = (listed.get("value") or {}).get("models", [""])[0] if listed["ok"] else ""
    if not model:
        return _op("chat", False, None, "No model is available for this key, so no completion can be run.")
    if not api_key:
        return _op("chat", False, None, "No API key is configured for Nvidia, so no completion can be run.")

    import time

    started = time.time()
    posted = _post_json(
        f"{_BASE_URL}/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": _SMOKE_PROMPT}],
         "max_tokens": 16, "temperature": 0.0},
        api_key, 20.0)
    elapsed = round((time.time() - started) * 1000, 2)
    if not posted["ok"]:
        return _op("chat", False, None, f"{posted['error']} (after {elapsed} ms)")
    body = posted.get("value") if isinstance(posted.get("value"), dict) else {}
    choices = body.get("choices") or []
    text = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
    usage = body.get("usage") or {}
    return _op("chat", True, {
        "model": model,
        "reply": text or None,
        "latency_ms": elapsed,
        "usage": usage,
    })


def execute(**kwargs) -> dict:
    """Test the Nvidia NIM key: ping, models, chat or check."""
    operation = str(kwargs.get("operation") or "ping").strip().lower()
    api_key = _resolve_key()
    records: list[dict] = []

    if not api_key:
        records.append(_op("key", False, None,
                           "No API key is configured for Nvidia. Add one in Settings > Cloud Providers, "
                           "or set NVIDIA_API_KEY. Without a key, model lists and completions cannot be read."))

    if operation == "ping":
        measured = _ping(api_key)
        result = {"operation": "ping", "ok": measured["reachable"], "value": measured, "error": ""}
    elif operation == "models":
        result = _models(api_key)
    elif operation == "chat":
        result = _chat(api_key, str(kwargs.get("model") or "").strip())
    elif operation == "check":
        result = _models(api_key)
    else:
        result = _op(operation, False, None, f"Unknown operation '{operation}'. Use ping, models, chat or check.")

    records.append(result)

    value = result.get("value") or {}
    if operation == "ping":
        probes = value.get("probes") or []
        failures = [p.get("error") for p in probes if not p.get("ok") and p.get("error")]
        if value.get("latency_ms") is None:
            summary = (
                "Nvidia NIM ping could not be measured. "
                + ("Failures: " + "; ".join(failures) if failures else "No probe returned a measurement.")
                + " This usually means the endpoint is unreachable from this network or a firewall is blocking it."
            )
        else:
            summary = (
                f"Nvidia NIM ping: reachable, average {value['latency_ms']} ms across {len(probes)} probes."
            )
            if not api_key:
                summary += " No key is configured, so authenticated latency was not measured."
        title = "Nvidia NIM Ping"
    elif operation == "chat":
        value = result.get("value") or {}
        summary = (
            f"Nvidia NIM chat smoke test on {value.get('model')}: replied in {value.get('latency_ms')} ms "
            f"with '{value.get('reply')}'"
            if result["ok"] else f"Nvidia NIM chat smoke test did not complete: {result['error']}"
        )
        title = "Nvidia NIM Chat Smoke Test"
    elif operation in ("models", "check"):
        value = result.get("value") or {}
        summary = (
            f"Nvidia NIM exposes {value.get('count')} models for this key. Changes against the shipped list: "
            f"+{len(value.get('added') or [])} new, -{len(value.get('retired') or [])} not returned."
            if result["ok"] else f"Nvidia NIM model list unavailable: {result['error']}"
        )
        title = "Nvidia NIM Models"
    else:
        summary = f"Nvidia NIM check did not run: {result.get('error') or 'unknown operation'}."
        title = "Nvidia NIM Unknown Operation"

    return {
        "title": title,
        "summary": summary,
        "spoken_narrative": summary,
        "operation": operation,
        "ok": bool(result.get("ok")),
        "records": records,
        "key_configured": bool(api_key),
        "models": (result.get("value") or {}).get("models") if operation == "models" else None,
    }
