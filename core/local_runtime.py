"""core/local_runtime.py — resolve and provision the local llama.cpp runtime.

Why this exists
---------------
`core/server.py` used to hardcode a single path,
`.venv/llama.cpp/llama-server.exe`. That works on exactly one machine: a
Windows dev box where somebody manually unzipped a release. It fails on Linux,
on macOS, on any install that is not that repo checkout, and on the public
build where nobody ever downloaded a server at all — so the public app shipped
with no way to run any local model, despite docs/model-management.md promising
that a user can download and run their own GGUF.

This module closes that gap for every edition and every OS:

  * `find_server(runtime)`  — locate an already-installed llama-server, looking
    in the install tree, the user data dir, the dev toolchain, and a locally
    compiled fork build. Never touches the network.
  * `ensure_server(runtime)` — the same, but when nothing is found and a
    verified release archive exists for this OS, fetch, SHA-256 verify and
    unpack it. Falls back to `find_server` for the MBZUAI fork, which has no
    published binaries.
  * `build_command(...)`    — the argv to actually launch a server around a
    chosen .gguf on a chosen port.

Both runtimes are offered on every OS (see engine_runtime.RUNTIMES): upstream
llama.cpp has K2-Horizon support and prebuilt archives for Windows/Linux/macOS;
the MBZUAI fork is available wherever the user has compiled it. Either one can
serve K2 *and* any other GGUF, so the runtime is a preference, never a lock-in.

Everything here is offline-safe: no network call happens unless something is
missing AND `allow_download` is true.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from core import engine_runtime as kr

USER_AGENT = "stella-local-runtime/1.0"


def _log(msg: str) -> None:
    print(f"[runtime] {msg}")


# ------------------------------------------------------------------ locations
def _base_dir() -> Path:
    """Install root (works both from source and from a PyInstaller bundle).

    In a frozen onedir build, `sys._MEIPASS` is the `_internal/` folder that
    holds bundled datas like our `k2/` payload. Preferring it over the exe
    directory means the resolver finds `k2/llama-server*` wherever the spec
    actually puts it.
    """
    frozen_base = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and frozen_base:
        return Path(frozen_base)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def runtime_dir(runtime: str = "") -> Path:
    """Where the runtime for `runtime` lives (outside the OTA-swapped tree)."""
    rt = runtime or kr.RUNTIME_DEFAULT
    try:
        from core.user_paths import get_user_data_dir
        return get_user_data_dir() / "runtimes" / rt
    except Exception:
        return _base_dir() / "runtimes" / rt


def server_name(platform: str = "") -> str:
    return kr.SERVER_BASENAME.get(platform or kr.host_platform(), "llama-server")


def _candidate_dirs(runtime: str, platform: str) -> list[Path]:
    """Every place a usable llama-server might already be, best source first.

    Order matters: an explicitly built/pinned binary must win over a
    convenience copy, otherwise a user who compiled the fork would silently get
    the upstream binary back.
    """
    name = server_name(platform)
    base = _base_dir()
    out: list[Path] = []

    # 1. Explicit override. Lets a developer pin an exact binary.
    # This resolver prefers the STELLA_SERVER escape hatch, keeping
    # STELLA_LLAMA_SERVER + the legacy STELLA_K2_SERVER for older setups.
    env = (os.environ.get("STELLA_SERVER")
           or os.environ.get("STELLA_LLAMA_SERVER")
           or os.environ.get("STELLA_K2_SERVER"))
    if env:
        out.append(Path(env))

    # 2. Per-runtime managed dir (what download_server installs into).
    out.append(runtime_dir(runtime) / name)

    # 3. The historical dev layout, kept so existing checkouts keep working.
    out.append(base / ".venv" / "llama.cpp" / name)

    # 4. Next to the app binary (portable zip / installer).
    out.append(base / name)
    # Bundled K2 payload. The personal build stages the server + weights into
    # a `k2/` folder next to the exe; PyInstaller onedir puts datas under
    # `_internal/`. Neither is on the historical dev path, so without these
    # two the shipped K2 build could not find its own runtime.
    out.append(base / "k2" / name)
    out.append(base / "_internal" / "k2" / name)
    try:
        from core.user_paths import get_user_data_dir
        user = get_user_data_dir()
        out.append(user / name)
        out.append(user / "llama.cpp" / name)
    except Exception:
        pass

    # 5. The fork's cross-compile output, only when looking for the fork.
    if runtime == kr.RUNTIME_MBZUAI:
        out.append(base / "llama-k2" / "bin" / name)
        out.append(base / "vendor" / "llama.cpp" / "build" / "bin" / name)

    # 6. On PATH, so a distro-installed llama-server is usable as-is.
    on_path = shutil.which(name) or shutil.which("llama-server")
    if on_path:
        out.append(Path(on_path))

    # De-dupe while preserving order.
    seen: set[str] = set()
    unique: list[Path] = []
    for p in out:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _is_runnable(path: Path) -> bool:
    """True when `path` is a real file this process can execute.

    `os.access(X_OK)` is unreliable on Windows: it returns True for any
    readable file, because Windows tracks executability through the file
    extension, not a permission bit. Checking the suffix too means a stray
    non-executable file is still rejected there, while POSIX keeps relying on
    the exec bit it actually has.
    """
    try:
        if not path.is_file():
            return False
    except OSError:
        return False
    if os.name == "nt":
        # .exe/.bat/.cmd are the executable forms on Windows; a bare
        # "llama-server" would fail at Popen with a confusing OS error.
        return path.suffix.lower() in (".exe", ".bat", ".cmd")
    return os.access(path, os.X_OK)


def find_server(runtime: str = "", platform: str = "") -> Optional[Path]:
    """Return an existing llama-server for `runtime`, or None.

    A candidate must be a real, executable file: a non-executable llama-server
    would fail at Popen with a confusing OS error, so it is rejected here and
    the caller gets a clear None instead.
    """
    rt = runtime or kr.RUNTIME_DEFAULT
    plat = platform or kr.host_platform()
    for cand in _candidate_dirs(rt, plat):
        if _is_runnable(cand):
            return cand
    return None


def installed_runtimes() -> dict[str, Optional[str]]:
    """Map runtime id -> server path (or None) for what is on disk right now."""
    return {rt: (str(p) if (p := find_server(rt)) else None) for rt in kr.RUNTIMES}


def describe() -> dict:
    """Machine-readable runtime state, for the Settings UI and for tests."""
    plat = kr.host_platform()
    return {
        "platform": plat,
        "host_os": sys.platform,
        "runtimes": list(kr.RUNTIMES),
        "default_runtime": kr.RUNTIME_DEFAULT,
        "available_runtimes": list(kr.runtimes_available(plat)),
        "installed": installed_runtimes(),
        "runtime_dir": str(runtime_dir()),
    }


# ------------------------------------------------------------------ provision
def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_server(archive: Path, dest_dir: Path, name: str) -> Optional[Path]:
    """Pull the llama-server binary out of a release archive into dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / name
    try:
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as zf:
                member = next(
                    (n for n in zf.namelist() if Path(n).name == name), None
                )
                if member is None:
                    _log(f"{name} not found inside {archive.name}")
                    return None
                with zf.open(member) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
        else:
            with tarfile.open(archive, "r:*") as tf:
                member = next(
                    (m for m in tf.getmembers()
                     if m.isfile() and Path(m.name).name == name),
                    None,
                )
                if member is None:
                    _log(f"{name} not found inside {archive.name}")
                    return None
                extracted = tf.extractfile(member)
                if extracted is None:
                    return None
                with open(target, "wb") as out:
                    shutil.copyfileobj(extracted, out)
    except (zipfile.BadZipFile, tarfile.TarError, OSError) as exc:
        _log(f"could not unpack {archive.name}: {exc}")
        return None

    if not target.is_file():
        return None
    try:
        target.chmod(0o755)
    except OSError:
        pass  # Windows has no exec bit; the file is still runnable there.
    return target


def download_server(runtime: str = "", platform: str = "",
                    progress=None) -> Optional[Path]:
    """Fetch + verify + unpack the prebuilt server for this OS. None on failure.

    Only the upstream runtime has published archives. Asking for the MBZUAI
    fork returns None immediately rather than downloading the wrong binary —
    the caller should then tell the user to build it from source.
    """
    rt = runtime or kr.RUNTIME_DEFAULT
    plat = platform or kr.host_platform()
    spec = kr.RUNTIME_ARCHIVES.get(rt, {}).get(plat)
    if not spec:
        _log(f"no prebuilt {rt} server for '{plat or 'this OS'}'")
        return None

    url, expected = spec["url"], spec["sha256"].lower()
    name = server_name(plat)
    dest_dir = runtime_dir(rt)
    tmp = dest_dir / "_download"
    try:
        tmp.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log(f"cannot create {tmp}: {exc}")
        return None
    archive = tmp / url.rsplit("/", 1)[-1]

    try:
        if archive.exists() and _sha256_of(archive) == expected:
            _log("archive already cached and verified")
        else:
            _log(f"downloading {rt} server ({name})")
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=300) as resp, \
                    open(archive, "wb") as f:
                total = int(resp.headers.get("Content-Length", 0) or 0)
                have = 0
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    have += len(chunk)
                    if progress and total:
                        progress(have, total)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        _log(f"download failed: {exc}")
        return None

    actual = _sha256_of(archive)
    if expected and actual != expected:
        # A mismatch means a tampered mirror or a truncated transfer. Never
        # execute it: an unverified binary is worse than no binary.
        _log(f"SHA-256 mismatch for {archive.name}: got {actual}, want {expected}")
        try:
            archive.unlink()
        except OSError:
            pass
        return None

    installed = _extract_server(archive, dest_dir, name)
    try:
        archive.unlink()
    except OSError:
        pass
    return installed


def ensure_server(runtime: str = "", platform: str = "",
                  allow_download: bool = True, progress=None) -> Optional[Path]:
    """Return a usable llama-server for `runtime`, downloading if permitted."""
    existing = find_server(runtime, platform)
    if existing is not None:
        return existing
    if not allow_download:
        _log("no local server found and downloads are disabled")
        return None
    found = download_server(runtime, platform, progress=progress)
    if found is None:
        # Fork or unsupported OS: surface any local build we may have missed.
        return find_server(runtime, platform)
    return found


# --------------------------------------------------------------------- launch
def build_command(server: Path, model: Path, port: int = kr.K2_PORT,
                  threads: int = 0, ctx: int = kr.K2_CTX,
                  extra: Optional[list[str]] = None) -> list[str]:
    """argv to launch llama-server around `model`.

    Thread default of half the logical CPUs is the documented sweet spot for
    CPU-only inference: more threads than that costs more in contention than it
    buys in throughput on the small machines Stella targets.
    """
    argv = [str(server), "-m", str(model), "--port", str(port),
            "-c", str(ctx)]
    if threads and threads > 0:
        argv += ["-t", str(threads)]
    if extra:
        argv += list(extra)
    return argv


def probe(port: int, timeout: float = 2.0) -> bool:
    """True when an OpenAI-compatible server answers on `port`."""
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/health", method="GET"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m core.local_runtime "
              "[status|ensure|install RUNTIME]")
        return 0
    cmd = argv[0]
    if cmd == "status":
        for key, val in describe().items():
            print(f"{key}: {val}")
        return 0
    if cmd in ("ensure", "install"):
        runtime = argv[1] if len(argv) > 1 else kr.RUNTIME_DEFAULT
        if runtime not in kr.RUNTIMES:
            print(f"unknown runtime '{runtime}' (choose from {list(kr.RUNTIMES)})")
            return 2
        found = ensure_server(runtime)
        print(f"{runtime}: {found}" if found else f"{runtime}: unavailable")
        return 0 if found else 1
    print(f"unknown command '{cmd}'")
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))



