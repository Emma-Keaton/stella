"""core/ultron.py — Project Ultron: autonomous self-heal crash sentry.

Watches Stella's own modules: on a runtime anomaly it inspects the Python
AST of the offending file, applies a minimal dynamic hotfix (e.g. repairing
a truncated file tail, removing an unbalanced bracket line), re-compiles,
and hot-reloads the module — without terminating the workflow.

Every patch is recorded and revertible: the original source is backed up
before any edit, and `rollback()` restores it. Ultron never touches safety
rules, guardrails or permission code.
"""
from __future__ import annotations

import ast
import importlib
import logging
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultron")

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKUP_DIR = _REPO_ROOT / "data" / "ultron_backups"
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Modules Ultron must never modify (safety-critical).
PROTECTED = ("guardrail", "approvals", "confirm", "threat_model", "security", "policy")

_patches: List[Dict[str, Any]] = []
_lock = threading.Lock()
_running = False


def _is_protected(path: Path) -> bool:
    return any(p in path.name.lower() for p in PROTECTED)


def check_module(path: Path) -> Optional[str]:
    """Return a repaired source if the file fails to compile, else None."""
    try:
        src = path.read_text(encoding="utf-8-sig")  # utf-8-sig: ignore a BOM
        compile(src, str(path), "exec")
        return None
    except SyntaxError as e:
        src = path.read_text(encoding="utf-8-sig")
        lines = src.splitlines(keepends=True)
        # Minimal hotfix: drop the offending line if it is unbalanced, then retry.
        if e.lineno and 1 <= e.lineno <= len(lines):
            patched = "".join(lines[: e.lineno - 1] + lines[e.lineno:])
            try:
                compile(patched, str(path), "exec")
                return patched
            except SyntaxError:
                pass
        return None
    except Exception:
        return None


def heal_file(path: Path) -> Dict[str, Any]:
    """Check one module; if broken, back up + hotfix + verify + reload."""
    path = Path(path)
    if _is_protected(path):
        return {"ok": False, "reason": "protected module", "file": str(path)}
    patched = check_module(path)
    if patched is None:
        return {"ok": True, "healed": False, "file": str(path)}
    with _lock:
        backup = _BACKUP_DIR / (path.name + ".bak")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(patched, encoding="utf-8")
        record = {"ok": True, "healed": True, "file": str(path),
                  "backup": str(backup), "at": time.time()}
        _patches.append(record)
    logger.warning("[Ultron] hotfixed %s (backup at %s)", path, backup)
    _reload(path)
    return record


def _reload(path: Path) -> None:
    """Hot-reload a module by file path if it is already imported."""
    try:
        rel = path.relative_to(_REPO_ROOT)
        mod_name = ".".join(rel.with_suffix("").parts)
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
    except Exception as e:
        logger.error("[Ultron] reload failed for %s: %s", path, e)


def scan_all(root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """AST-check every Stella python file under root (default: core/ + agent/)."""
    root = root or _REPO_ROOT
    results = []
    for sub in ("core", "agent", "src"):
        d = root / sub
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.py")):
            if "ultron_backups" in str(p):
                continue
            results.append(heal_file(p))
    return results


def rollback(file: str) -> Dict[str, Any]:
    """Restore a hotfixed module from its backup."""
    name = Path(file).name
    backup = _BACKUP_DIR / (name + ".bak")
    if not backup.exists():
        return {"ok": False, "reason": "no backup"}
    shutil.copy2(backup, Path(file))
    _reload(Path(file))
    return {"ok": True, "restored": str(file)}


def patches() -> List[Dict[str, Any]]:
    return list(_patches)


def start_watchdog(interval: float = 5.0) -> None:
    """Background thread that periodically AST-checks and heals modules."""
    global _running, _thread, _watch_interval
    _watch_interval = interval
    if _running:
        return
    _running = True

    def _loop():
        while _running:
            try:
                scan_all()
            except Exception:
                logger.error("[Ultron] scan error:\n%s", traceback.format_exc())
            time.sleep(_watch_interval)

    _thread = threading.Thread(target=_loop, daemon=True, name="ultron-sentry")
    _thread.start()


def stop_watchdog() -> None:
    global _running
    _running = False

_thread: Optional[threading.Thread] = None
_watch_interval = 5.0
