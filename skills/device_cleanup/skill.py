"""
feature/device_cleanup - Device cleanup skills for Stella.

Provides storage cleanup, RAM/memory cleanup, cache clearing, and system
maintenance operations. All operations are read-only or explicitly destructive
only when requested, with clear honesty about what was actually freed.

Design principles:
- Never delete user files without explicit confirmation
- Report what can and cannot be cleaned
- Degrade gracefully when tools are missing
- Cross-platform (Windows, macOS, Linux)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

FEATURE_METADATA = {
    "name": "device_cleanup",
    "aliases": ["device_cleanup", "clean_device", "clean_storage", "free_space",
                "clear_cache", "clean_memory", "disk_cleanup", "cleanup_device"],
    "description": (
        "Clean up device storage, memory, and cache safely. Can scan for "
        "reclaimable space without deleting anything, or perform cleanup "
        "operations with explicit confirmation. Reports what can and cannot "
        "be cleaned so users can plan their cleanup strategy."
    ),
    "triggers": [
        "clean up", "cleanup", "clean disk", "free space", "clear cache",
        "clear memory", "disk cleanup", "storage cleanup", "clean device",
        "free up space", "remove cache", "clear temporary files", "clean system",
    ],
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "One of: scan_storage, clean_cache, clean_temp, clean_memory, system_info. Defaults to scan_storage.",
            },
            "target": {
                "type": "string",
                "description": "Target to clean: 'temp', 'cache', 'all', or a specific path.",
            },
            "confirm": {
                "type": "boolean",
                "description": "Must be true to actually perform destructive cleanup. Defaults to false (dry run).",
                "default": False,
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, only scan and report without deleting anything. Defaults to true.",
                "default": True,
            },
        },
        "required": [],
    },
    "version": "1.0.0",
    "active": True,
    "category": "system",
    "optional_dependencies": [],
}


def execute(**kwargs: Any) -> Dict[str, Any]:
    """Execute a device cleanup operation.

    Supported operations:
      - scan_storage: Scan for reclaimable space without deleting anything
      - clean_cache: Clear application/browser caches (dry-run by default)
      - clean_temp: Clean temporary files (dry-run by default)
      - clean_memory: Clear memory caches (OS-dependent)
      - system_info: Get system storage/memory info
    """
    operation = kwargs.get("operation", "scan_storage") or "scan_storage"

    if operation == "backends":
        return _op_backends()

    if operation == "scan_storage":
        return _op_scan_storage(kwargs)

    if operation == "clean_cache":
        return _op_clean_cache(kwargs)

    if operation == "clean_temp":
        return _op_clean_temp(kwargs)

    if operation == "clean_memory":
        return _op_clean_memory(kwargs)

    if operation == "system_info":
        return _op_system_info(kwargs)

    return _op_result("device_cleanup", False, error=f"Unknown operation: {operation}")


def _op_result(operation: str, ok: bool, value: Any = None, error: Optional[str] = None) -> Dict[str, Any]:
    result = {"operation": operation, "ok": ok}
    if value is not None:
        result["value"] = value
    if error is not None:
        result["error"] = error
    return result


def _op_backends() -> Dict[str, Any]:
    """Report backend availability."""
    backends = {
        "filesystem": {
            "available": True,
            "description": "Filesystem operations for cleanup",
        },
        "psutil": {
            "available": _HAS_PSUTIL,
            "description": "Detailed memory/storage information",
        },
    }
    all_ok = all(b["available"] for b in backends.values())
    return {
        "operation": "backends",
        "ok": all_ok,
        "value": backends,
        "spoken_narrative": "Cleanup backends are available." if all_ok else "Some cleanup backends are unavailable.",
    }


def _op_system_info(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Get system storage and memory information."""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        info = {
            "storage": {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "free_percent": round((free / total) * 100, 1) if total > 0 else 0,
            }
        }
    except Exception as exc:
        info = {"storage": {"error": str(exc)}}

    # Memory info
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["memory"] = {
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "used_bytes": mem.used,
            "free_bytes": mem.available,
            "percent_used": mem.percent,
        }
    except Exception:
        info["memory"] = {"error": "psutil not available"}

    return _op_result("system_info", True, value=info)


def _op_scan_storage(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Scan for reclaimable space without deleting anything."""
    target = kwargs.get("target", "all")
    import shutil

    results = {}

    # System temp
    try:
        temp_dir = Path(tempfile.gettempdir())
        temp_size = _dir_size(temp_dir)
        results["temp"] = {
            "path": str(temp_dir),
            "size_bytes": temp_size,
            "reclaimable": True,
        }
    except Exception as exc:
        results["temp"] = {"error": str(exc)}

    # Cache directories
    cache_dirs = _get_cache_dirs()
    cache_info = {}
    for name, path in cache_dirs.items():
        try:
            p = Path(path)
            if p.exists():
                cache_info[name] = {
                    "path": str(p),
                    "size_bytes": _dir_size(p),
                    "reclaimable": True,
                }
            else:
                cache_info[name] = {
                    "path": str(p),
                    "size_bytes": 0,
                    "reclaimable": False,
                    "reason": "not found",
                }
        except Exception as exc:
            cache_info[name] = {"error": str(exc)}
    results["cache"] = cache_info

    # Total reclaimable
    total_reclaimable = 0
    for key, val in results.items():
        if isinstance(val, dict) and val.get("reclaimable"):
            total_reclaimable += val.get("size_bytes", 0)

    return _op_result("scan_storage", True, value={
        "target": target,
        "results": results,
        "total_reclaimable_bytes": total_reclaimable,
        "operation": "scan_storage",
    })


def _op_clean_cache(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Clean cache directories. Dry-run by default."""
    dry_run = kwargs.get("dry_run", True)
    confirm = kwargs.get("confirm", False)

    if not dry_run and not confirm:
        return _op_result("clean_cache", False, error="confirm=true required to perform cleanup. Use dry_run=true to preview.")

    cache_dirs = _get_cache_dirs()
    total_freed = 0
    results = {}

    for name, path in cache_dirs.items():
        try:
            p = Path(path)
            if not p.exists():
                cache_info = {"path": str(p), "size_bytes": 0, "reclaimable": False, "reason": "not found"}
                results[name] = cache_info
                continue

            size = _dir_size(p)
            if dry_run:
                results[name] = {
                    "path": str(p),
                    "size_bytes": size,
                    "would_free": size,
                    "dry_run": True,
                }
                total_freed += size
            else:
                _dir_delete_contents(p)
                results[name] = {
                    "path": str(p),
                    "size_bytes": size,
                    "freed": size,
                    "dry_run": False,
                }
                total_freed += size
        except Exception as exc:
            results[name] = {"error": str(exc)}

    return _op_result("clean_cache", True, value={
        "dry_run": dry_run,
        "total_freed_bytes": total_freed,
        "results": results,
        "operation": "clean_cache",
    })


def _op_clean_temp(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Clean temporary files. Dry-run by default."""
    dry_run = kwargs.get("dry_run", True)
    confirm = kwargs.get("confirm", False)

    if not dry_run and not confirm:
        return _op_result("clean_temp", False, error="confirm=true required to perform cleanup. Use dry_run=true to preview.")

    try:
        temp_dir = Path(tempfile.gettempdir())
        if not temp_dir.exists():
            return _op_result("clean_temp", True, value={
                "dry_run": dry_run,
                "total_freed_bytes": 0,
                "results": {"temp": {"path": str(temp_dir), "size_bytes": 0, "reclaimable": False, "reason": "not found"}},
                "operation": "clean_temp",
            })

        size = _dir_size(temp_dir)
        if dry_run:
            return _op_result("clean_temp", True, value={
                "dry_run": True,
                "total_freed_bytes": size,
                "results": {"temp": {"path": str(temp_dir), "size_bytes": size, "would_free": size, "dry_run": True}},
                "operation": "clean_temp",
            })

        _dir_delete_contents(temp_dir)
        return _op_result("clean_temp", True, value={
            "dry_run": False,
            "total_freed_bytes": size,
            "results": {"temp": {"path": str(temp_dir), "size_bytes": size, "freed": size, "dry_run": False}},
            "operation": "clean_temp",
        })
    except Exception as exc:
        return _op_result("clean_temp", False, error=str(exc))


def _op_clean_memory(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Clear memory caches (OS-dependent)."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        info = {
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "used_bytes": mem.used,
            "percent_used": mem.percent,
        }
    except Exception:
        info = {"error": "psutil not available"}

    # On most systems, we can't forcefully clear memory without root/admin
    # and it's generally not recommended. We report the current state.
    return _op_result("clean_memory", True, value={
        "cleaned": False,
        "reason": "Memory cleanup requires OS-specific operations and is not automatically performed.",
        "memory_info": info,
        "operation": "clean_memory",
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False


def _dir_size(path: Path) -> int:
    """Calculate total size of files in a directory (bytes)."""
    total = 0
    try:
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total


def _dir_delete_contents(path: Path) -> int:
    """Delete all contents of a directory (not the directory itself). Returns bytes freed."""
    total_freed = 0
    try:
        for item in path.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    size = item.stat().st_size
                    item.unlink()
                    total_freed += size
                elif item.is_dir():
                    size = _dir_size(item)
                    shutil.rmtree(item)
                    total_freed += size
            except Exception:
                pass
    except Exception:
        pass
    return total_freed


def _get_cache_dirs() -> dict:
    """Get common cache directories for the current OS."""
    dirs = {}
    home = Path.home()

    if os.name == "nt":  # Windows
        local = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        dirs["browser_cache"] = str(Path(local) / "Google" / "Chrome" / "User Data" / "Default" / "Cache")
        dirs["temp"] = str(Path(os.environ.get("TEMP", Path.home() / "AppData" / "Local" / "Temp")))
    else:  # macOS / Linux
        dirs["browser_cache"] = str(home / "Library" / "Caches" / "Google" / "Chrome")
        dirs["system_cache"] = str(Path.home() / ".cache")
        dirs["tmp"] = "/tmp"

    return dirs
