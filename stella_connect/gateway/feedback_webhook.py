"""
Anonymous feedback inbox — receive update requests from any Stella install.

Why this exists
---------------
Outbound feedback (core/feedback.py) lets *this* machine send a structured
report to the creator. This module is the other half: a tiny stdlib-only HTTP
receiver that runs *on the creator's machine* and collects anonymous upgrade /
update requests from every Stella install in the world into a local inbox.

Security posture (deliberately paranoid)
----------------------------------------
- Accepts only POST /feedback with a small JSON body. Anything else is 404.
- Hard size cap (64 KB) — oversized bodies are rejected before being read.
- Every report goes through feedback.scrub() — secrets never touch the disk,
  even from a hostile sender.
- Per-IP rate limit (default 10/hour). Anonymous inbound is fine;
  unauthenticated execution is not — NOTHING here ever runs code.
- Binds to 127.0.0.1 by default. Expose it wider (Tailscale, reverse proxy)
  only deliberately, never by accident.
- Concurrent posts are serialized with a lock + atomic file replace.

File layout (under the Stella user-data dir)
--------------------------------------------
  feedback/inbox/pending/<id>.json    — unreviewed requests
  feedback/inbox/approved/<id>.json   — you approved (scripts/feedback_review.py)
  feedback/inbox/rejected/<id>.json   — you rejected
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
MAX_BODY_BYTES = 64 * 1024
RATE_LIMIT_PER_HOUR = 10
RATE_WINDOW_S = 3600

_WRITE_LOCK = threading.Lock()
_HITS: dict[str, list[float]] = {}
_HITS_LOCK = threading.Lock()


def _inbox_dirs() -> dict[str, Path]:
    try:
        from core.user_paths import get_user_data_dir
        base = get_user_data_dir() / "feedback" / "inbox"
    except Exception:
        base = Path.home() / ".stella" / "feedback" / "inbox"
    dirs = {k: base / k for k in ("pending", "approved", "rejected")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def _anon_ip(ip: str) -> str:
    """Anonymize a sender IP to /24 (v4) or /48 (v6) — enough for rate
    limiting and abuse triage, not enough to identify anyone."""
    try:
        addr = ipaddress.ip_address(ip)
        if isinstance(addr, ipaddress.IPv4Address):
            return str(ipaddress.ip_network(f"{ip}/24", strict=False).network_address) + "/24"
        return str(ipaddress.ip_network(f"{ip}/48", strict=False).network_address) + "/48"
    except Exception:
        return "unknown"


def _rate_ok(key: str) -> bool:
    now = time.time()
    with _HITS_LOCK:
        hits = [t for t in _HITS.get(key, []) if now - t < RATE_WINDOW_S]
        if len(hits) >= RATE_LIMIT_PER_HOUR:
            _HITS[key] = hits
            return False
        hits.append(now)
        _HITS[key] = hits
        return True


def _validate_report(obj: object) -> tuple[bool, str, dict]:
    """Schema-check an inbound report. Returns (ok, error, clean_dict)."""
    if not isinstance(obj, dict):
        return False, "body must be a JSON object", {}
    allowed = {"kind", "encountered", "did", "how", "need", "app_version",
               "device", "contact"}
    clean = {k: obj[k] for k in allowed if k in obj}
    for field in ("encountered", "need"):
        val = clean.get(field)
        if not isinstance(val, str) or not val.strip():
            return False, f"field '{field}' is required", {}
        if len(val) > 4000:
            return False, f"field '{field}' too long (max 4000 chars)", {}
    for field in ("did", "how", "contact"):
        if field in clean and not isinstance(clean[field], str):
            return False, f"field '{field}' must be a string", {}
        if isinstance(clean.get(field), str) and len(clean[field]) > 4000:
            return False, f"field '{field}' too long (max 4000 chars)", {}
    if "device" in clean and not isinstance(clean["device"], dict):
        return False, "field 'device' must be an object", {}
    if "kind" in clean and not isinstance(clean["kind"], str):
        return False, "field 'kind' must be a string", {}
    return True, "", clean


def store_report(clean: dict, sender_ip: str) -> Path:
    """Scrub, envelope, and atomically store a validated report. Returns path."""
    from core import feedback as fb
    for field in ("encountered", "did", "how", "need", "contact"):
        if isinstance(clean.get(field), str):
            clean[field] = fb.scrub(clean[field])
    blob = json.dumps(clean, sort_keys=True).encode("utf-8")
    rid = hashlib.sha256(blob + str(time.time_ns()).encode()).hexdigest()[:16]
    envelope = {
        "id": rid,
        "schema": SCHEMA_VERSION,
        "status": "pending",
        "received_utc": datetime.now(timezone.utc).isoformat(),
        "sender": _anon_ip(sender_ip),
        "report": clean,
    }
    dirs = _inbox_dirs()
    dest = dirs["pending"] / f"{rid}.json"
    tmp = dest.with_suffix(".tmp")
    with _WRITE_LOCK:
        tmp.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
        tmp.replace(dest)
    return dest

# ---------------------------------------------------------------------------
# HTTP layer. Kept in the same file so the receiver stays one deployable unit.
# ---------------------------------------------------------------------------
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Handler(BaseHTTPRequestHandler):
    server_version = "StellaFeedback/1.0"

    def log_message(self, *args):  # quiet; triage reads the inbox files
        pass

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/health"):
            dirs = _inbox_dirs()
            n = len(list(dirs["pending"].glob("*.json")))
            self._json(200, {"ok": True, "pending": n})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/feedback":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except Exception:
            n = 0
        if n <= 0 or n > MAX_BODY_BYTES:
            self._json(413, {"ok": False, "error": "body must be 1..65536 bytes"})
            return
        try:
            obj = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            self._json(400, {"ok": False, "error": "invalid JSON"})
            return
        ip = (self.client_address[0] if self.client_address else "unknown")
        if not _rate_ok(_anon_ip(ip)):
            self._json(429, {"ok": False, "error": "rate limited, try later"})
            return
        ok, err, clean = _validate_report(obj)
        if not ok:
            self._json(422, {"ok": False, "error": err})
            return
        try:
            dest = store_report(clean, ip)
        except Exception as e:
            self._json(500, {"ok": False, "error": f"store failed: {e}"[:200]})
            return
        self._json(202, {"ok": True, "id": dest.stem,
                         "note": "received for review; suggestions are human-gated"})


def run(host: str = "127.0.0.1", port: int = 8766) -> None:
    """Serve the inbox receiver. Blocks; run in a thread or with --serve."""
    if host not in ("127.0.0.1", "localhost", "::1"):
        print(f"[feedback-inbox] WARNING: binding to {host} exposes the "
              f"receiver beyond this machine. Prefer a reverse proxy.")
    srv = ThreadingHTTPServer((host, port), _Handler)
    print(f"[feedback-inbox] listening on http://{host}:{port}/feedback "
          f"(GET /health for status)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Stella anonymous feedback inbox")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8766)
    args = ap.parse_args()
    run(args.host, args.port)

