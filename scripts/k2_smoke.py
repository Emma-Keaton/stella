"""One-shot K2 smoke test: resolve the runtime, start it, ask it a question.

Run: .venv/Scripts/python.exe scripts/k2_smoke.py
Exists because starting K2 needs several seconds and a real prompt round-trip
proves the server not just the HTTP port.
"""
import sys
import json
import urllib.request

sys.path.insert(0, r"E:\Projects\stella")

from core import k2_server as k


def main() -> int:
    print("runtime :", k.runtime())
    print("server  :", k.server_binary())
    print("model   :", k.resolve_model_path())
    print("port    :", k.port())

    ok = k.start(wait=True)
    print("start   :", ok)
    print("running :", k.is_running())
    print("url     :", k.base_url())
    if not ok or not k.is_running():
        print("K2 DID NOT START")
        return 1

    body = json.dumps({
        "model": "k2-horizon-0.9b",
        "messages": [{"role": "user", "content": "Say hello in exactly three words."}],
        "max_tokens": 256,
        "temperature": 0.2,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{k.base_url()}/v1/chat/completions",
        data=body, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print("chat    : FAILED", exc)
        return 1

    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    print("chat    :", text.strip()[:200])
    print("K2 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
