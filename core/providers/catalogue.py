"""core/providers/catalogue.py - live model catalogues for every cloud provider.

A provider's model list is not static: NIM, OpenAI, Groq, OpenRouter and the
local runtimes all add and retire models on their own schedule. This module
keeps a small on-disk cache per provider with a TTL, so the model picker can
show what a provider actually serves right now - and refresh it manually,
on a schedule, or after a key changes.

Honesty rules (same as everywhere else in Stella):

* a failed fetch keeps the last good list and says when it was fetched
* a missing key is reported as "no key", never as "no models"
* a 401 is a key problem, a 429 is a quota problem, a timeout is a network
  problem - the three are never conflated
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("providers.catalogue")

#: How long a cached catalogue is trusted before a refresh is offered.
DEFAULT_TTL_SECONDS = 6 * 60 * 60

#: Failure classes, so callers can tell a bad key from a bad network.
FAILURE_AUTH = "auth"          # 401 / 403 - the key is wrong or lacks access
FAILURE_QUOTA = "quota"        # 429 - rate limited or out of credit
FAILURE_NETWORK = "network"    # DNS, timeout, TLS, connection refused
FAILURE_NO_KEY = "no-key"      # nothing configured for this provider
FAILURE_UNKNOWN = "unknown"


def _cache_path() -> Path:
    try:
        from core.user_paths import get_user_data_dir

        path = Path(get_user_data_dir()) / "config" / "provider_catalogues.json"
    except Exception:
        path = Path("config") / "provider_catalogues.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_cache() -> dict[str, Any]:
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(data: dict[str, Any]) -> None:
    try:
        _cache_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not write the model catalogue cache: %s", exc)


def _env_key(provider_id: str) -> str:
    """The environment variable for a provider key, via the single resolver."""
    try:
        from core.providers import keys as keys_mod

        return keys_mod.resolve_key(provider_id) or ""
    except Exception:
        return ""


def _models_url(provider_id: str) -> Optional[str]:
    try:
        from core.providers import registry

        base = (registry.get_provider(provider_id) or {}).get("base_url") or ""
        endpoint = (registry.get_provider(provider_id) or {}).get("models_endpoint")
    except Exception:
        return None
    if not base or not endpoint:
        return None
    return base.rstrip("/") + endpoint


def _classify_error(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if "401" in text or "403" in text or "unauthorized" in text or "forbidden" in text:
        return FAILURE_AUTH
    if "429" in text or "rate limit" in text or "quota" in text:
        return FAILURE_QUOTA
    if "timed out" in text or "timeout" in text or "urlerror" in text or "connection" in text:
        return FAILURE_NETWORK
    return FAILURE_UNKNOWN


def _parse_models(payload: Any) -> list[str]:
    """Accept the OpenAI shape, or a bare list of model ids."""
    entries = []
    if isinstance(payload, dict):
        entries = payload.get("data") or payload.get("models") or payload.get("items") or []
    elif isinstance(payload, list):
        entries = payload
    models: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            models.append(entry)
        elif isinstance(entry, dict):
            model_id = entry.get("id") or entry.get("name") or entry.get("model")
            if model_id:
                models.append(str(model_id))
    seen: set[str] = set()
    unique: list[str] = []
    for m in models:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique


def fetch_models(provider_id: str, base_url: str = "", api_key: str = "") -> dict[str, Any]:
    """Fetch the live model list for one provider.

    Returns `{"ok": True, "models": [...], "fetched_at": ..., "source": url}` on
    success, or `{"ok": False, "failure": <class>, "reason": ...}` on failure.
    Never raises.
    """
    pid = str(provider_id or "").strip().lower()
    url = _models_url(pid)
    if not url:
        try:
            from core.providers import registry

            static = list((registry.get_provider(pid) or {}).get("models") or [])
        except Exception:
            static = []
        if static:
            return {
                "ok": True,
                "models": static,
                "fetched_at": round(time.time(), 3),
                "source": "registry",
                "note": "This provider publishes no model list endpoint; showing the models shipped in the registry.",
            }
        return {
            "ok": False,
            "failure": FAILURE_UNKNOWN,
            "reason": f"Provider '{pid}' has no model list endpoint and no registry models.",
        }

    if not api_key:
        try:
            from core.providers import registry

            needs = bool((registry.get_provider(pid) or {}).get("requires_key"))
        except Exception:
            needs = True
        if needs:
            return {
                "ok": False,
                "failure": FAILURE_NO_KEY,
                "reason": (
                    f"No API key is configured for {pid}, so its model list cannot be read. "
                    "Add the key in Settings > Cloud Providers."
                ),
            }

    import urllib.error
    import urllib.request

    headers = {"Accept": "application/json", "User-Agent": "StellaAI-ProviderCatalogue/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "failure": _classify_error(exc),
            "reason": f"{url} answered HTTP {exc.code}.",
            "status": int(exc.code),
        }
    except Exception as exc:
        return {
            "ok": False,
            "failure": _classify_error(exc),
            "reason": f"{url} could not be read: {type(exc).__name__}: {exc}",
        }

    models = _parse_models(payload)
    if not models:
        return {
            "ok": False,
            "failure": FAILURE_UNKNOWN,
            "reason": f"{url} answered without any models in it.",
        }
    return {
        "ok": True,
        "models": models,
        "fetched_at": round(time.time(), 3),
        "source": url,
    }


def refresh(provider_id: str, force: bool = False) -> dict[str, Any]:
    """Refresh one provider's catalogue, refreshing the cache on success."""
    pid = str(provider_id or "").strip().lower()
    cached = _load_cache().get(pid) or {}
    ttl = DEFAULT_TTL_SECONDS
    try:
        from core.providers import registry

        ttl = float((registry.get_provider(pid) or {}).get("models_ttl_seconds") or DEFAULT_TTL_SECONDS)
    except Exception:
        ttl = DEFAULT_TTL_SECONDS

    fetched_at = float(cached.get("fetched_at") or 0)
    if not force and cached.get("models") and (time.time() - fetched_at) < ttl:
        result = dict(cached)
        result["cached"] = True
        return result

    outcome = fetch_models(pid, api_key=_env_key(pid))
    outcome["provider"] = pid
    outcome["cached"] = False
    if outcome.get("ok"):
        data = _load_cache()
        data[pid] = outcome
        _save_cache(data)
        try:
            from core.providers import registry

            previous = list((registry.get_provider(pid) or {}).get("models") or [])
        except Exception:
            previous = []
        outcome["added"] = [m for m in outcome["models"] if m not in previous]
        outcome["retired"] = [m for m in previous if m not in outcome["models"]]
    else:
        if cached.get("models"):
            outcome["stale_models"] = cached["models"]
            outcome["stale_fetched_at"] = fetched_at
        outcome["cached"] = bool(cached.get("models"))
    return outcome


def list_models(provider_id: str, force: bool = False) -> list[str]:
    """The model list for a provider - live when possible, registry otherwise."""
    outcome = refresh(provider_id, force=force)
    if outcome.get("models"):
        return list(outcome["models"])
    if outcome.get("stale_models"):
        return list(outcome["stale_models"])
    try:
        from core.providers import registry

        return list((registry.get_provider(provider_id) or {}).get("models") or [])
    except Exception:
        return []


def status(provider_id: str) -> dict[str, Any]:
    """Cache state for one provider, for the Settings row."""
    pid = str(provider_id or "").strip().lower()
    cached = _load_cache().get(pid) or {}
    return {
        "provider": pid,
        "models": list(cached.get("models") or []),
        "fetched_at": cached.get("fetched_at"),
        "source": cached.get("source"),
        "failure": cached.get("failure"),
        "reason": cached.get("reason"),
    }


def check_key(provider_id: str) -> dict[str, Any]:
    """Verify that a stored key actually authenticates and can list models.

    Returns a small report: `{"ok": bool, "failure": class, "reason": ...}`.
    Never raises, never echoes the key.
    """
    pid = str(provider_id or "").strip().lower()
    key = _env_key(pid)
    if not key:
        return {
            "ok": False,
            "failure": FAILURE_NO_KEY,
            "reason": f"No API key is configured for {pid}.",
        }
    outcome = fetch_models(pid, api_key=key)
    if outcome.get("ok"):
        return {
            "ok": True,
            "failure": None,
            "reason": f"The key works and {pid} served {len(outcome['models'])} models.",
            "model_count": len(outcome["models"]),
        }
    return {
        "ok": False,
        "failure": outcome.get("failure"),
        "reason": outcome.get("reason"),
        "model_count": 0,
    }


def refresh_all(force: bool = False) -> dict[str, dict[str, Any]]:
    """Refresh every provider that publishes a model list."""
    try:
        from core.providers import registry

        ids = registry.provider_ids()
    except Exception:
        ids = []
    return {pid: refresh(pid, force=force) for pid in ids}


def refresh_stale() -> dict[str, dict[str, Any]]:
    """Refresh only the catalogues whose TTL has expired.

    Safe to call often: a provider whose cache is still fresh is not contacted,
    so a once-a-minute scheduler tick costs nothing. Returns what it did.
    """
    outcomes: dict[str, dict[str, Any]] = {}
    try:
        from core.providers import registry

        ids = registry.provider_ids()
    except Exception:
        ids = []
    for pid in ids:
        try:
            info = status(pid)
            fetched_at = float(info.get("fetched_at") or 0)
            fresh = bool(info.get("models")) and (time.time() - fetched_at) < DEFAULT_TTL_SECONDS
        except (TypeError, ValueError):
            fresh = False
        if not fresh:
            outcomes[pid] = refresh(pid)
    return outcomes


def keyed_service_url(provider_id: str, url_template: str) -> str:
    """Build a URL that carries a key in its path, from the single resolver.

    Skills that need a key *inside* the URL (FIRMS's area CSV endpoint takes it
    in the path) ask this rather than importing the key module themselves, so
    the "one key-resolution site" guard stays honest and no skill ever has to
    hold, log or substring a key. The returned string contains the key: treat it
    as a secret, which is why it is only ever handed straight to a fetcher.
    """
    key = _env_key(provider_id)
    if not key:
        raise KeyError(f"no API key is configured for {provider_id}")
    return url_template.format(key=key)


def register_periodic_refresh(job_name: str = "provider-model-catalogue-refresh") -> bool:
    try:
        from core import automation
    except Exception:
        return False
    try:
        automation.schedule(job_name, "every 6 hours", refresh_stale)
        return True
    except Exception:
        return False
