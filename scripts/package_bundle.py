#!/usr/bin/env python3
"""
scripts/package_bundle.py — build, estimate, and stage a Stella bundle.

Three jobs, deliberately kept together because they answer the same question:
"what will it actually cost me to run Stella on this machine?"

    plan      Read the device, work out how much disk and RAM each choice
              (API-only / cloud, small local model, large local model) needs,
              and PRINT THE TOTAL before anything is downloaded. Nothing is
              installed here — this is the number you read first so you do not
              burn a metered connection on a 4 GB model you did not want.

    check     Free-disk and free-RAM pre-flight. Fails loudly with a clear
              message rather than letting pip or a download die halfway.

    download  Fetch a package (model GGUF, wheel, archive) with a downloader
              that survives slow networks: HTTP Range resume, chunked writes,
              retry with backoff on a dropped connection, and a `.part` file so
              an interrupted run picks up exactly where it stopped.

Usage:
    python scripts/package_bundle.py plan
    python scripts/package_bundle.py check
    python scripts/package_bundle.py download <url> [--dest PATH] [--min-free-gb N]

Only stdlib is required.
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GIB = 1024 ** 3

# Rough on-disk footprint of the pieces that ship regardless of choice.
# The Python deps + PyQt6 + browser engines dominate; the app code is small.
BASE_APP_GB = 1.2          # PyInstaller COLLECT output, unpacked
PYTHON_DEPS_GB = 1.6       # site-packages the runtime pulls in
PLAYWRIGHT_GB = 0.5        # headless browser (installed by bootstrap)
OVERHEAD_GB = 0.4          # logs, caches, temp extraction

# Local model options offered at install time. Sizes are approximate GGUF
# file sizes on disk; RAM guidance is the model + working KV cache.
MODEL_TIERS = [
    {"id": "api_only", "label": "Cloud API only (Gemini / Groq)",
     "download_gb": 0.0, "disk_gb": 0.0, "ram_gb": 0.5},
    {"id": "qwen_1_5b_q4", "label": "Local 1.5B (Q4) - light chat / offline",
     "download_gb": 1.0, "disk_gb": 1.0, "ram_gb": 2.0},
    {"id": "qwen_3b_q4", "label": "Local 3B (Q4) - balanced offline",
     "download_gb": 2.0, "disk_gb": 2.0, "ram_gb": 4.0},
    {"id": "qwen_7b_q4", "label": "Local 7B (Q4) - strong offline, needs a GPU to be quick",
     "download_gb": 4.4, "disk_gb": 4.4, "ram_gb": 8.0},
    {"id": "qwen_14b_q4", "label": "Local 14B (Q4) - heavy offline, workstation only",
     "download_gb": 9.0, "disk_gb": 9.0, "ram_gb": 16.0},
]


# ------------------------------------------------------------------ device ---
def _disk_free_gb(path) -> float:
    return round(shutil.disk_usage(str(path)).free / GIB, 2)


def _ram_gb():
    """Return (total_gb, available_gb). Falls back to /proc on non-psutil."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        return round(vm.total / GIB, 2), round(vm.available / GIB, 2)
    except Exception:
        pass
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/meminfo", encoding="utf-8") as f:
                total_kb = avail_kb = 0
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_kb = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        avail_kb = int(line.split()[1])
                return round(total_kb / 1024 / 1024, 2), round(avail_kb / 1024 / 1024, 2)
    except Exception:
        pass
    try:
        if sys.platform.startswith("win"):
            import ctypes

            class _MS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            ms = _MS()
            ms.dwLength = ctypes.sizeof(_MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return (round(ms.ullTotalPhys / GIB, 2),
                    round(ms.ullAvailPhys / GIB, 2))
    except Exception:
        pass
    return 0.0, 0.0


def _net_up() -> bool:
    try:
        socket.create_connection(("huggingface.co", 443), timeout=4).close()
        return True
    except Exception:
        return False


# -------------------------------------------------------------------- plan ---
def estimate(choice_id: str) -> dict:
    base = BASE_APP_GB + PYTHON_DEPS_GB + PLAYWRIGHT_GB + OVERHEAD_GB
    tier = next((t for t in MODEL_TIERS if t["id"] == choice_id), MODEL_TIERS[0])
    return {
        "choice": choice_id,
        "label": tier["label"],
        "base_disk_gb": round(base, 2),
        "model_disk_gb": tier["disk_gb"],
        "total_disk_gb": round(base + tier["disk_gb"], 2),
        "download_gb": round(tier["download_gb"], 2),
        "peak_ram_gb": round(base * 0.4 + tier["ram_gb"], 2),
    }


def cmd_plan() -> int:
    disk_free = _disk_free_gb(Path.home())
    ram_total, ram_avail = _ram_gb()
    online = _net_up()

    print("=" * 66)
    print("  STELLA BUNDLE PLAN  -  read this before you download")
    print("=" * 66)
    print(f"  Disk free        : {disk_free} GB")
    print(f"  RAM total/avail  : {ram_total} / {ram_avail} GB")
    print(f"  Network          : {'online' if online else 'OFFLINE (resume later)'}")
    print("-" * 66)
    print(f"  Fixed app cost   : ~{round(BASE_APP_GB + PYTHON_DEPS_GB + PLAYWRIGHT_GB + OVERHEAD_GB, 2)} GB on disk")
    print()
    print("  Choose a runtime - the TOTAL is what lands on your disk:")
    print()

    fits_any = False
    for tier in MODEL_TIERS:
        est = estimate(tier["id"])
        disk_ok = disk_free >= est["total_disk_gb"] + 1.0  # +1 GB headroom
        ram_ok = ram_total == 0 or ram_total >= est["peak_ram_gb"]
        ok = disk_ok and ram_ok
        fits_any = fits_any or ok
        flag = "OK " if ok else "NO "
        print(f"   [{flag}] {tier['label']}")
        print(f"          disk total : {est['total_disk_gb']} GB   "
              f"download : {est['download_gb']} GB   "
              f"peak RAM : {est['peak_ram_gb']} GB")
        if not disk_ok:
            print("          -> not enough free disk (need ~1 GB headroom on top)")
        if not ram_ok:
            print("          -> not enough RAM for this tier")
        print()

    print("-" * 66)
    print("  The app + deps (~3.7 GB) install regardless of model choice.")
    print("  'api_only' keeps your disk use to that fixed cost and needs no")
    print("  model download - best on metered/slow connections.")
    if not fits_any:
        print("  !! Nothing fits on this machine right now. Free up disk or pick")
        print("     the API-only option.")
    print("=" * 66)
    return 0


# ------------------------------------------------------------------- check ---
def cmd_check(min_free_gb: float = 5.0, path=None) -> int:
    target = Path(path) if path else Path.home()
    disk_free = _disk_free_gb(target)
    ram_total, ram_avail = _ram_gb()
    print(f"Disk free ({target}) : {disk_free} GB (need >= {min_free_gb} GB)")
    print(f"RAM total / available: {ram_total} / {ram_avail} GB")
    if disk_free < min_free_gb:
        print(f"FAIL: only {disk_free} GB free. Free up at least "
              f"{round(min_free_gb - disk_free, 2)} GB and retry.")
        return 1
    if ram_total and ram_avail < 1.0:
        print("WARN: very little free RAM; close other apps before launching.")
    print("OK: enough space to proceed.")
    return 0

# ---------------------------------------------------------------- download ---
def resumable_download(url: str, dest: Path, *,
                       timeout: int = 30,
                       max_retries: int = 8,
                       chunk: int = 1024 * 256,
                       min_free_gb: float = 0.0) -> Path:
    """Download `url` to `dest`, surviving slow/flaky networks.

    - Writes to a `.part` file so an interrupted run never leaves a half-file
      masquerading as the real thing.
    - Sends a Range header for whatever `.part` bytes already exist, so the
      server resumes instead of restarting.
    - Retries on socket/HTTP errors with exponential backoff. A server that
      ignores Range (returns 200) simply restarts that chunk cleanly.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    have = part.stat().st_size if part.exists() else 0

    if min_free_gb and _disk_free_gb(dest.parent) < min_free_gb:
        raise RuntimeError(
            f"Not enough free disk in {dest.parent} (need >= {min_free_gb} GB)."
        )

    headers = {"User-Agent": "stella-bundle/1.0"}
    if have:
        headers["Range"] = f"bytes={have}-"

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        mode = "ab" if have else "wb"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp, \
                    open(part, mode) as f:
                if have and resp.status == 200:
                    f.seek(0)          # server ignored Range; start over
                    have = 0
                total = int(resp.headers.get("Content-Length", 0)) + have
                t0 = time.time()
                while True:
                    block = resp.read(chunk)
                    if not block:
                        break
                    f.write(block)
                    have += len(block)
                    if total:
                        pct = have * 100 // total
                        rate = have / GIB / max(time.time() - t0, 0.001)
                        sys.stdout.write(
                            f"\r  {have / GIB:5.2f} / {total / GIB:5.2f} GB  "
                            f"({pct:3d}%)  {rate:4.2f} GB/s"
                        )
                        sys.stdout.flush()
            sys.stdout.write("\n")
            os.replace(part, dest)
            return dest
        except (urllib.error.URLError, urllib.error.HTTPError,
                socket.timeout, ConnectionError, TimeoutError, OSError) as e:
            wait = min(2 ** attempt, 30)
            print(f"\n  network hiccup ({e.__class__.__name__}). "
                  f"Retry {attempt}/{max_retries} in {wait}s "
                  f"(resuming from {have / GIB:.2f} GB)...")
            time.sleep(wait)
    raise RuntimeError(f"Gave up downloading {url} after {max_retries} retries. "
                       f"Partial file kept at {part}; re-run to resume.")


def cmd_download(url: str, dest=None, min_free_gb: float = 1.0) -> int:
    if not dest:
        name = url.split("?")[0].rstrip("/").split("/")[-1] or "download.bin"
        dest = str(Path.home() / "models" / name)
    dest_path = Path(dest)
    try:
        out = resumable_download(url, dest_path, min_free_gb=min_free_gb)
        print(f"Downloaded -> {out}")
        return 0
    except Exception as e:
        print(f"FAIL: {e}")
        return 1


# -------------------------------------------------------------------- main ---
def main() -> int:
    ap = argparse.ArgumentParser(description="Stella bundle planner / downloader")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("plan", help="show disk/RAM/download cost per choice")

    p_check = sub.add_parser("check", help="free-disk / free-RAM pre-flight")
    p_check.add_argument("--min-free-gb", type=float, default=5.0)
    p_check.add_argument("--path", default=None)

    p_dl = sub.add_parser("download", help="resumable download (models, archives)")
    p_dl.add_argument("url")
    p_dl.add_argument("--dest", default=None)
    p_dl.add_argument("--min-free-gb", type=float, default=1.0)

    args = ap.parse_args()
    if args.cmd == "plan":
        return cmd_plan()
    if args.cmd == "check":
        return cmd_check(args.min_free_gb, args.path)
    if args.cmd == "download":
        return cmd_download(args.url, args.dest, args.min_free_gb)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


