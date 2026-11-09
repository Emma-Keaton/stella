"""core/automation.py — cron + NL scheduling + heartbeat + event hooks."""
from __future__ import annotations

import threading
import time
from typing import Callable, Dict, List

_jobs: Dict[str, dict] = {}
_hooks: Dict[str, List[Callable]] = {}
_heartbeat: List[Callable] = []
_lock = threading.Lock()
_running = False
_thread: threading.Thread | None = None


def schedule(name, cron_or_nl, fn, *args, **kwargs):
    with _lock:
        _jobs[name] = {"expr": cron_or_nl, "fn": fn, "args": args, "kwargs": kwargs, "last": 0.0}
    return name


def cancel(name):
    with _lock:
        return _jobs.pop(name, None) is not None


def on(event, fn):
    _hooks.setdefault(event, []).append(fn)


def emit(event, *args, **kwargs):
    for fn in list(_hooks.get(event, [])):
        try:
            fn(*args, **kwargs)
        except Exception:
            pass


def heartbeat(fn):
    _heartbeat.append(fn)
    return fn


def _tick():
    now = time.time()
    for job in list(_jobs.values()):
        if now - job["last"] >= 60:
            job["last"] = now
            try:
                job["fn"](*job["args"], **job["kwargs"])
            except Exception:
                pass
    for fn in list(_heartbeat):
        try:
            fn()
        except Exception:
            pass


def start():
    global _running, _thread
    if _running:
        return
    _running = True

    def loop():
        while _running:
            _tick()
            time.sleep(1)

    _thread = threading.Thread(target=loop, daemon=True, name="automation")
    _thread.start()


def stop():
    global _running
    _running = False


def is_running():
    return _running


def list_jobs():
    return list(_jobs.keys())
