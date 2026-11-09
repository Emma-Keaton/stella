"""core/net/http.py - one shared HTTP fetch helper for the observation skills.

Every network-facing skill needs the same three things: a bounded timeout, an
honest User-Agent that names Stella, and a result that carries *which* failure
happened instead of collapsing every error into "failed". This module is that
one place, so no skill hand-rolls its own urllib plumbing (and no skill
retries in a loop against a rate-limited source).

Cache and throttle convention: a caller that hits a quota-ed source passes a
`_Cache` and the helper returns the cached copy with `cached: True` when the
TTL has not expired, so a second question in the same session never spends a
second API credit.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

USER_AGENT = "StellaAI/1.0 (world-watch)"

FAILURE_NETWORK = "network"
FAILURE_HTTP = "http"
FAILURE_PARSE = "parse"
FAILURE_TIMEOUT = "timeout"
FAILURE_RATE = "rate-limited"
FAILURE_REFUSED = "refused"


def get_json(
    url: str,
    timeout: float = 10.0,
    user_agent: str = USER_AGENT,
    cache: Optional["_Cache"] = None,
    ttl: float = 0.0,
    max_bytes: int = 8_000_000,
) -> dict:
    """GET a URL and parse it as JSON, reporting the failure class either way.

    Returns `{"ok": True, "value": <parsed>, "url": url, ...}` or
    `{"ok": False, "failure": <class>, "reason": ...}`. Never raises.
    """
    if cache is not None and ttl > 0:
        cached = cache.get(url, ttl)
        if cached is not None:
            return {"ok": True, "value": cached, "url": url, "cached": True}

    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": user_agent,
    })
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes)
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        failure = FAILURE_RATE if exc.code == 429 else FAILURE_HTTP
        detail = ""
        try:
            detail = exc.read(400).decode("utf-8", errors="ignore")
        except Exception:
            pass
        return {
            "ok": False,
            "failure": failure,
            "status": int(exc.code),
            "reason": f"{url} answered HTTP {exc.code}. {detail}".strip(),
            "url": url,
        }
    except TimeoutError:
        return {"ok": False, "failure": FAILURE_TIMEOUT,
                "reason": f"{url} did not answer within {timeout:g}s.", "url": url}
    except urllib.error.URLError as exc:
        reason = str(exc.reason) if hasattr(exc, "reason") else str(exc)
        if "timed out" in reason.lower():
            return {"ok": False, "failure": FAILURE_TIMEOUT,
                    "reason": f"{url} did not answer within {timeout:g}s.", "url": url}
        return {"ok": False, "failure": FAILURE_NETWORK,
                "reason": f"{url} could not be reached: {reason}", "url": url}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "failure": FAILURE_NETWORK,
                "reason": f"{url} could not be read: {type(exc).__name__}: {exc}", "url": url}

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"ok": False, "failure": FAILURE_PARSE,
                "reason": f"{url} answered {len(raw)} bytes that were not JSON: {exc}", "url": url}

    if cache is not None and ttl > 0:
        cache.put(url, parsed)
    return {
        "ok": True,
        "value": parsed,
        "url": url,
        "cached": False,
        "status": int(status),
        "elapsed_ms": round((time.time() - started) * 1000, 1),
        "bytes": len(raw),
    }


def get_text(
    url: str,
    timeout: float = 10.0,
    user_agent: str = USER_AGENT,
    cache: Optional["_Cache"] = None,
    ttl: float = 0.0,
    max_bytes: int = 8_000_000,
) -> dict:
    """GET a URL as text, reporting the failure class either way."""
    if cache is not None and ttl > 0:
        cached = cache.get(url, ttl)
        if cached is not None:
            return {"ok": True, "value": cached, "url": url, "cached": True}

    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes)
    except urllib.error.HTTPError as exc:
        failure = FAILURE_RATE if exc.code == 429 else FAILURE_HTTP
        return {"ok": False, "failure": failure, "status": int(exc.code),
                "reason": f"{url} answered HTTP {exc.code}", "url": url}
    except TimeoutError:
        return {"ok": False, "failure": FAILURE_TIMEOUT,
                "reason": f"{url} did not answer within {timeout:g}s.", "url": url}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "failure": FAILURE_NETWORK,
                "reason": f"{url} could not be read: {type(exc).__name__}: {exc}", "url": url}

    text = raw.decode("utf-8", errors="replace")
    if cache is not None and ttl > 0:
        cache.put(url, text)
    return {"ok": True, "value": text, "url": url, "cached": False, "bytes": len(raw)}


@dataclass
class _Cache:
    """A tiny on-disk JSON cache, keyed by URL, so repeated questions are free."""

    root: Path
    ttl: float
    entries: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.path = Path(self.root) / "feed-cache.json"
        try:
            self.entries = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self.entries, dict):
                self.entries = {}
        except Exception:
            self.entries = {}

    def _key(self, url: str) -> str:
        safe = "".join(c if c.isalnum() else "-" for c in url)[:120]
        return f"{abs(hash(url)):016x}-{safe}"

    def get(self, url: str, ttl: float | None = None) -> Any:
        entry = self.entries.get(self._key(url))
        if not isinstance(entry, dict):
            return None
        limit = ttl if ttl is not None else self.ttl
        if time.time() - float(entry.get("fetched_at", 0)) > limit:
            return None
        return entry.get("value")

    def put(self, url: str, value: Any) -> None:
        self.entries[self._key(url)] = {
            "fetched_at": round(time.time(), 3),
            "url": url,
            "value": value,
        }
        self.flush()

    def flush(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.entries), encoding="utf-8")
        except Exception:
            pass


def feed_cache(ttl: float = 900.0) -> "_Cache":
    """A cache under Stella's user data dir; offline use then costs nothing."""
    try:
        from core.user_paths import get_user_data_dir

        root = Path(get_user_data_dir()) / "cache" / "world-watch"
    except Exception:
        root = Path(".stella-cache") / "world-watch"
    root.mkdir(parents=True, exist_ok=True)
    return _Cache(root=root, ttl=ttl)
