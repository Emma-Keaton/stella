"""agent/model_manager.py - Model management settings for the UI.

Provides settings schema for multiple local models (download, switch,
delete, replace) and wires the selected model into the LLM chat path.
"""

from __future__ import annotations

import json
import os
import platform
import re
import urllib.request
from pathlib import Path
from typing import Any, Optional

from core.user_paths import get_user_data_dir


def get_model_dir() -> Path:
    return get_user_data_dir() / "models"


def get_settings_path() -> Path:
    return get_user_data_dir() / "config" / "app_settings.json"


def load_model_settings() -> dict[str, Any]:
    path = get_settings_path()
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f).get("models", {})
    except Exception:
        pass
    return {}


def save_model_settings(data: dict[str, Any]) -> None:
    path = get_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        current: dict[str, Any] = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    current = json.load(f)
            except Exception:
                current = {}
        current["models"] = {**current.get("models", {}), **data}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4)
    except Exception as e:
        print(f"[MODEL MANAGER] Failed to save settings: {e}")


def _quant_of(filename: str) -> str:
    match = re.search(r'(Q[0-9]_[A-Z]+|[A-Z0-9]+|F16|BF16)', filename)
    return match.group(1) if match else ""


def get_model_status(model_path: Path) -> dict[str, Any]:
    if not model_path.exists():
        return {"exists": False, "error": "Model file not found"}
    size = model_path.stat().st_size
    return {
        "exists": True,
        "size_bytes": size,
        # GB alone rounds any sub-10 MB file to 0.0, which hides a truncated
        # or partially-written download. Keep both so the UI can flag it.
        "size_mb": round(size / 1024 ** 2, 2),
        "size_gb": round(size / 1024 ** 3, 2),
        "quant": _quant_of(model_path.name),
        "timestamp": model_path.stat().st_mtime,
    }


def list_downloaded_models() -> list[dict[str, Any]]:
    path = get_model_dir()
    if not path.exists():
        return []
    models = []
    for gguf in path.rglob("*.gguf"):
        status = get_model_status(gguf)
        models.append({
            "name": gguf.name,
            "path": str(gguf),
            "size_mb": status.get("size_mb", 0),
            "size_gb": status.get("size_gb", 0),
            "quant": status.get("quant", ""),
            "timestamp": status.get("timestamp", 0),
            "active": False,
        })
    return models


def get_selected_model() -> Optional[dict[str, Any]]:
    settings = load_model_settings()
    selected = settings.get("selected_model")
    if not selected:
        return None
    model_path = Path(selected.get("path", ""))
    if not model_path.exists():
        return None
    return {
        "name": selected.get("name", model_path.name),
        "path": str(model_path.resolve()),
        "size_gb": selected.get("size_gb", 0),
        "quant": selected.get("quant", ""),
        "endpoint": selected.get("endpoint", ""),
        "active": True,
    }


def get_endpoint_for_model(model_path: Path) -> str:
    for port in [11434, 8080, 8000]:
        try:
            url = f"http://localhost:{port}/v1/models"
            req = urllib.request.Request(url, method="HEAD")
            urllib.request.urlopen(req, timeout=1)
            return f"http://localhost:{port}/v1"
        except Exception:
            continue
    return f"http://localhost:11434/v1"


def set_selected_model(model: dict[str, Any]) -> bool:
    settings = load_model_settings()
    settings["selected_model"] = {
        "name": model["name"],
        "path": model["path"],
        "size_gb": model.get("size_gb", 0),
        "quant": model.get("quant", ""),
        "endpoint": model.get(
            "endpoint", get_endpoint_for_model(Path(model["path"]))
        ),
        "timestamp": model.get("timestamp", 0),
    }
    save_model_settings(settings)
    return True


def delete_model(model: dict[str, Any]) -> dict[str, Any]:
    path = Path(model["path"])
    if not path.exists():
        return {"ok": False, "error": "Model file not found"}
    try:
        size = path.stat().st_size
        path.unlink()
        settings = load_model_settings()
        if settings.get("selected_model", {}).get("path") == str(path):
            del settings["selected_model"]
            save_model_settings(settings)
        return {
            "ok": True,
            "removed": str(path),
            "freed_gb": round(size / 1024 ** 3, 2),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def download_model(demo: dict[str, Any], progress=None) -> dict[str, Any]:
    repo = demo["repo"]
    model_dir = get_model_dir()
    model_dir.mkdir(parents=True, exist_ok=True)
    hf_url = f"https://huggingface.co/api/models/{repo}/tree/main"
    try:
        req = urllib.request.Request(hf_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            tree = json.loads(resp.read().decode())
    except Exception as e:
        return {"ok": False, "error": f"Could not access HuggingFace: {e}"}

    target_file = None
    for item in tree:
        if item.get("type") == "file" and item.get("path", "").endswith(".gguf"):
            candidates = [i.get("path") for i in tree if i.get("path", "").endswith(".gguf")]
            if candidates:
                target_file = candidates[0]
                break

    if not target_file:
        return {"ok": False, "error": f"No GGUF file found in {repo}"}

    file_url = f"https://huggingface.co/{repo}/resolve/main/{target_file}"
    dest = model_dir / target_file
    try:
        req = urllib.request.Request(file_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress and total:
                        progress(downloaded, total)
        return {
            "ok": True,
            "path": str(dest.resolve()),
            "name": dest.name,
            "size_gb": round(dest.stat().st_size / 1024 ** 3, 2),
            "quant": _quant_of(dest.name),
        }
    except Exception as e:
        if dest.exists():
            dest.unlink()
        return {"ok": False, "error": f"Download failed: {e}"}


def replace_model(selected: dict[str, Any], demo: dict[str, Any]) -> dict[str, Any]:
    result = delete_model(selected)
    result.update(download_model(demo))
    return result


def detect_device() -> dict[str, Any]:
    cpu_cores = os.cpu_count() or 2
    machine = platform.machine().lower()
    ram_free_gb = 0
    try:
        import psutil
        ram_free_gb = round(psutil.virtual_memory().available / 1024 ** 3, 2)
    except Exception:
        pass
    return {
        "os": platform.system(),
        "arch": machine,
        "cpu_cores": cpu_cores,
        "ram_free_gb": ram_free_gb,
    }
