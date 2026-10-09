#!/usr/bin/env python3
"""Stella model manager — device-aware GGUF model lifecycle tool.

Detects live device specs, searches HuggingFace for fitting public GGUF
models IN REAL TIME (no cached lists), and downloads / removes / replaces
models. Works as a CLI and as an importable API for the Stella GUI/app.

Usage:
    python scripts/stella_model_manager.py detect
    python scripts/stella_model_manager.py search qwen --limit 10
    python scripts/stella_model_manager.py download <repo_id> <filename>
    python scripts/stella_model_manager.py remove <path-or-name>
    python scripts/stella_model_manager.py replace <old> <repo_id> <filename>
    python scripts/stella_model_manager.py list

Only stdlib + psutil (optional; falls back to os/sys primitives).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import urllib.request
import urllib.parse
from pathlib import Path

HF_API = "https://huggingface.co/api/models"
HF_RESOLVE = "https://huggingface.co"

QUANT_RANK = ["Q2_K", "Q3_K_S", "Q3_K_M", "Q3_K_L", "Q4_0", "Q4_K_S",
              "Q4_K_M", "Q5_0", "Q5_K_S", "Q5_K_M", "Q6_K", "Q8_0", "F16", "BF16"]


def _http_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "stella-model-manager/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------- specs ---
def detect_specs() -> dict:
    """Live device spec detection (no caching)."""
    cpu_cores = os.cpu_count() or 2
    machine = platform.machine().lower()
    is_arm = machine in ("arm64", "aarch64", "armv7l", "armv8l")
    ram_free_gb = ram_total_gb = 0.0
    try:
        import psutil
        vm = psutil.virtual_memory()
        ram_free_gb = round(vm.available / 1024 ** 3, 2)
        ram_total_gb = round(vm.total / 1024 ** 3, 2)
        disk_free_gb = round(psutil.disk_usage(str(Path.home())).free / 1024 ** 3, 2)
    except Exception:
        disk_free_gb = round(shutil.disk_usage(str(Path.home())).free / 1024 ** 3, 2)

    gpu = "none"
    try:
        import subprocess
        out = subprocess.run(["nvidia-smi", "-L"], capture_output=True,
                             text=True, timeout=5).stdout.strip()
        if out and "GPU" in out:
            gpu = "nvidia-discrete"
    except Exception:
        pass

    if ram_free_gb and ram_free_gb <= 2.5 or cpu_cores <= 2:
        bucket = "low_end"
    elif ram_free_gb and ram_free_gb <= 5.5 or cpu_cores <= 4:
        bucket = "mid_end"
    else:
        bucket = "high_end"
    if is_arm and bucket == "high_end":
        bucket = "arm_high"

    return {
        "os": platform.system(), "os_release": platform.release(),
        "arch": machine, "is_arm": is_arm,
        "cpu_cores": cpu_cores, "ram_free_gb": ram_free_gb,
        "ram_total_gb": ram_total_gb, "disk_free_gb": disk_free_gb,
        "gpu": gpu, "bucket": bucket,
        "max_model_gb": round(max(0.5, (ram_free_gb or 4) * 0.4), 2),
    }


def preferred_quants(specs: dict) -> list:
    if specs["gpu"] == "nvidia-discrete":
        return ["Q4_0", "Q4_K_M", "Q5_K_M", "Q8_0"]
    return ["Q4_K_M", "Q4_K_S", "Q4_0", "Q5_K_M", "Q3_K_M"]


# ------------------------------------------------------------- HF live ---
def _quant_of(filename: str) -> str:
    m = re.search(r"(Q\d(?:_\w+)+|F16|BF16|Q\d_\d)", filename, re.IGNORECASE)
    return m.group(1).upper() if m else "?"


def search_models(query: str = "", limit: int = 15, specs: dict | None = None) -> list:
    """Real-time HuggingFace search for public GGUF models fitting the device."""
    specs = specs or detect_specs()
    params = {"search": query or "gguf", "filter": "gguf",
              "sort": "likes", "direction": "-1", "limit": str(limit * 2)}
    url = HF_API + "?" + urllib.parse.urlencode(params)
    try:
        results = _http_json(url)
    except Exception as e:
        return [{"error": f"HF search failed (offline?): {e}"}]

    quants = preferred_quants(specs)
    out = []
    for m in results:
        repo = m.get("id", "")
        siblings = [s.get("rfilename", "") for s in (m.get("siblings") or [])]
        if not siblings:
            # search API omits file lists — fetch the repo record live
            try:
                detail = _http_json(HF_API + "/" + repo, timeout=20)
                siblings = [s.get("rfilename", "") for s in (detail.get("siblings") or [])]
            except Exception:
                continue
        ggufs = [s for s in siblings if s.lower().endswith(".gguf")]
        if not ggufs:
            continue
        # pick best-fitting quant file
        ranked = sorted(ggufs, key=lambda f: (quants.index(_quant_of(f))
                        if _quant_of(f) in quants else 99, len(f)))
        fname = ranked[0]
        out.append({
            "repo": repo, "file": fname, "quant": _quant_of(fname),
            "likes": m.get("likes", 0), "downloads": m.get("downloads", 0),
            "fits_bucket": specs["bucket"],
            "url": f"{HF_RESOLVE}/{repo}/resolve/main/{fname}",
        })
        if len(out) >= limit:
            break
    return out


def _remote_size(url: str) -> int:
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "stella-model-manager/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return int(resp.headers.get("Content-Length", 0))
    except Exception:
        return 0


def download_file(url: str, dest: Path, progress=None, timeout: int = 3600) -> Path:
    """Resumable download with progress callback(progress_bytes, total_bytes)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = _remote_size(url)
    have = dest.stat().st_size if dest.exists() else 0
    if total and have >= total > 0:
        return dest
    headers = {"User-Agent": "stella-model-manager/1.0"}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    mode = "ab" if have else "wb"
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, mode) as f:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
            have += len(chunk)
            if progress:
                progress(have, total)
    return dest


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- local ---
def default_model_dir() -> Path:
    base = Path(__file__).resolve().parent.parent
    return base / "models"


def legacy_runtimes_allowed() -> bool:
    """LM Studio / Ollama internal dirs are referenced ONLY on dev machines
    that opt in. Every other device uses direct runtime files/folders only."""
    if os.environ.get("STELLA_INCLUDE_LEGACY_RUNTIMES", "") == "1":
        return True
    cands = [Path.home() / ".stella" / "config" / "app_settings.json",
             Path(__file__).resolve().parent.parent / "config" / "app_settings.json"]
    try:
        lad = os.environ.get("LOCALAPPDATA")
        if lad:
            cands.insert(0, Path(lad) / "BrahmaAI" / "config" / "app_settings.json")
    except Exception:
        pass
    for cand in cands:
        try:
            if json.loads(cand.read_text(encoding="utf-8-sig")).get(
                    "include_legacy_runtimes", False):
                return True
        except Exception:
            continue
    return False


LEGACY_DIRS = [Path.home() / ".lmstudio" / "models",
               Path.home() / ".cache" / "lm-studio" / "models",
               Path.home() / ".cache" / "huggingface"]


def list_local(dirs: list | None = None) -> list:
    # Direct runtime files/folders first — the only sources on normal devices.
    roots = [Path(d) for d in (dirs or [default_model_dir(), Path.home() / "models"])]
    if legacy_runtimes_allowed():
        roots += LEGACY_DIRS
    found = []
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob("*.gguf"):
            try:
                found.append({"name": f.name, "path": str(f),
                              "gb": round(f.stat().st_size / 1024 ** 3, 2),
                              "quant": _quant_of(f.name)})
            except OSError:
                pass
    return found


def remove_model(target: str) -> dict:
    """Delete a model by path or filename (searches known dirs)."""
    p = Path(target)
    if not p.exists():
        for m in list_local():
            if m["name"] == target or m["path"] == target:
                p = Path(m["path"])
                break
    if not p.exists():
        return {"ok": False, "error": f"model not found: {target}"}
    size = p.stat().st_size
    p.unlink()
    return {"ok": True, "removed": str(p), "freed_gb": round(size / 1024 ** 3, 2)}


def replace_model(old: str, repo: str, filename: str,
                  dest_dir: Path | None = None, progress=None) -> dict:
    """Remove old model, download new one, return new path."""
    info = remove_model(old)
    url = f"{HF_RESOLVE}/{repo}/resolve/main/{filename}"
    dest = (Path(dest_dir) if dest_dir else default_model_dir()) / filename
    print(f"[stella] downloading {repo}/{filename} ...")
    download_file(url, dest, progress=progress)
    return {"ok": True, "removed": info.get("removed"),
            "freed_gb": info.get("freed_gb", 0),
            "new": str(dest),
            "new_gb": round(dest.stat().st_size / 1024 ** 3, 2)}


# ------------------------------------------------------------------- CLI ---
def _pct(done: int, total: int):
    if total:
        print(f"\r  {done/1024/1024:.1f}/{total/1024/1024:.1f} MB "
              f"({100*done/total:.1f}%)", end="", flush=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="stella-model-manager",
                                 description="Device-aware GGUF model manager")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect", help="print live device profile as JSON")
    s = sub.add_parser("search", help="live HF search for fitting models")
    s.add_argument("query", nargs="?", default="")
    s.add_argument("--limit", type=int, default=15)
    d = sub.add_parser("download", help="download a model file")
    d.add_argument("repo"); d.add_argument("file")
    d.add_argument("--dir", default=None)
    r = sub.add_parser("remove", help="delete a local model")
    r.add_argument("target")
    rp = sub.add_parser("replace", help="remove old + download new")
    rp.add_argument("old"); rp.add_argument("repo"); rp.add_argument("file")
    rp.add_argument("--dir", default=None)
    sub.add_parser("list", help="list local .gguf models")
    args = ap.parse_args(argv)

    if args.cmd == "detect":
        print(json.dumps(detect_specs(), indent=2))
    elif args.cmd == "search":
        specs = detect_specs()
        print(f"# device: {specs['bucket']} | {specs['cpu_cores']} cores | "
              f"{specs['ram_free_gb']}GB free RAM | max model ~{specs['max_model_gb']}GB")
        for m in search_models(args.query, args.limit, specs):
            if "error" in m:
                print("ERROR:", m["error"]); return 1
            print(f"- {m['repo']} :: {m['file']} [{m['quant']}] "
                  f"likes={m['likes']} dl={m['downloads']}")
    elif args.cmd == "download":
        url = f"{HF_RESOLVE}/{args.repo}/resolve/main/{args.file}"
        dest = (Path(args.dir) if args.dir else default_model_dir()) / args.file
        download_file(url, dest, progress=_pct)
        print(f"\nOK → {dest}")
    elif args.cmd == "remove":
        print(json.dumps(remove_model(args.target), indent=2))
    elif args.cmd == "replace":
        print(json.dumps(replace_model(args.old, args.repo, args.file,
                                       Path(args.dir) if args.dir else None,
                                       progress=_pct), indent=2))
        print("\nOK")
    elif args.cmd == "list":
        for m in list_local():
            print(f"- {m['name']} [{m['quant']}] {m['gb']}GB :: {m['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
