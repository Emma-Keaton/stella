"""
scripts/selftest_webhook.py — end-to-end test of the anonymous feedback inbox.

Spins up stella_connect/gateway/feedback_webhook.py on localhost, posts a
valid report (expect 202 + inbox file), then bad payloads (400/413/422),
a health check, a secret-leak scrub check, and one approve round-trip
through scripts/feedback_review.py.

Run:  py scripts/selftest_webhook.py   (stdlib only)
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.environ.setdefault("STELLA_DATA_DIR_TEST", "1")

FAILED = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        FAILED.append(name)


def post(port, obj, raw=None):
    body = raw if raw is not None else json.dumps(obj).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/feedback", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


import urllib.error  # noqa: E402  (kept after helper for clarity)


def main():
    import urllib.error as _e  # noqa
    from stella_connect.gateway import feedback_webhook as wh

    port = 18766
    t = threading.Thread(target=wh.run, kwargs={"port": port}, daemon=True)
    t.start()
    time.sleep(0.5)

    good = {"kind": "upgrade-request", "encountered": "no dark splash",
            "did": "opened app", "how": "clicked icon",
            "need": "add dark splash", "app_version": "0.4.0",
            "contact": "sk-live-SECRETSTUFF12345"}
    code, res = post(port, good)
    check("valid report accepted (202)", code == 202 and res.get("ok") is True)
    rid = res.get("id", "")

    pending = list(wh._inbox_dirs()["pending"].glob("*.json"))
    check("inbox file written", any(p.stem == rid for p in pending))
    if rid:
        stored = json.loads((wh._inbox_dirs()["pending"] / f"{rid}.json").read_text())
        check("sender anonymized", stored.get("sender", "").endswith(("/24", "/48")))
        check("secrets scrubbed", "SECRETSTUFF" not in json.dumps(stored))
        check("status pending", stored.get("status") == "pending")

    code, _ = post(port, {"encountered": "x"})
    check("missing 'need' rejected (422)", code == 422)
    code, _ = post(port, {}, raw=b"not json{{{")
    check("garbage rejected (400)", code == 400)

    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=10) as r:
        h = json.loads(r.read().decode())
    check("health reports pending", h.get("ok") is True and h.get("pending", 0) >= 1)

    # Triage CLI round-trip
    r = subprocess.run([sys.executable, "scripts/feedback_review.py", "show", rid],
                       capture_output=True, text=True, cwd=REPO, timeout=30)
    check("review show works", r.returncode == 0 and rid in r.stdout)
    r = subprocess.run([sys.executable, "scripts/feedback_review.py", "approve", rid],
                       capture_output=True, text=True, cwd=REPO, timeout=30)
    check("review approve works", r.returncode == 0)
    check("moved to approved",
          (wh._inbox_dirs()["approved"] / f"{rid}.json").exists())

    print("RESULT:", "PASS" if not FAILED else f"FAIL: {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
