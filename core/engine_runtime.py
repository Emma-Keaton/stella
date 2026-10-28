"""
core/k2_runtime.py — tracked K2 runtime contract (desktop + Android).

Why this file exists (and is NOT gitignored, unlike core/server.py's
predecessor core/k2_server.py, which now remains only as a shim)
-----------------------------------------------------------------------
K2 is now a shipping, updatable product surface — not a personal-only local
runtime. This module holds the parts of that contract every platform shares:

- Which K2 *server* binary version we pin, and its SHA-256 per platform
  (Windows x64 for desktop, ARM64 for the Android APK).
- Which GGUF *model* version we pin, its size, and its SHA-256.
- Where each platform keeps the runtime (outside OTA-swapped trees) and the
  HTTP contract both servers speak (OpenAI-compatible, 127.0.0.1:11435).

Desktop keeps using core/server.py (renamed from core/k2_server.py when the
server became architecture-sensitive) for its launch path; it now reads its
pinned model filename from here. Android reads the same
constants through the bundled k2/ asset + the versioned manifest entry.

K2 release gating
-----------------
The release manifest carries a `k2:` block (see scripts/stella_build.py).
`core/updater.py` compares `k2.server_version` / `k2.model_version`
separately from the app version and skips the k2/ tree entirely unless the
release sets `k2_release: true`. App updates therefore never touch the
server binary or the 600MB+ model download unless K2 itself changed.
"""

from __future__ import annotations

K2_PORT = 11435
K2_CTX = 2048
# The server is architecture-sensitive now (any GGUF, not just K2), so its
# public name dropped the k2 prefix. The old constants stay as aliases: the
# port/ctx values are part of the persisted settings contract and the desktop
# + Android code both import them.
SERVER_PORT = K2_PORT
SERVER_CTX = K2_CTX
SERVER_MODEL_FILENAME = "K2-Horizon-0.9B-Q4_K_M.gguf"

# ---------------------------------------------------------------------------
# Which llama.cpp runtime carries K2, and which carries everything else.
#
# CORRECTION (was wrong here until 2026-10-14): this file used to claim K2
# Horizon "does NOT exist in upstream ggml-org/llama.cpp" and pinned only the
# MBZUAI-IFM fork. That is no longer true. Verified against upstream master:
#
#   src/llama-arch.h    -> LLM_ARCH_K2_HORIZON
#   src/llama-arch.cpp  -> { LLM_ARCH_K2_HORIZON, "k2-horizon" }
#   src/models/k2-horizon.cpp -> full loader + graph (MoVA, MoE, grouped norm)
#
# The fork (MBZUAI-IFM/llama.cpp @ model/K2Horizon) still exists and is kept as
# a first-class, user-selectable option - it adds the K2 pre-tokenizer splitter
# and predates the upstream merge - but it publishes no prebuilt binaries, so
# it can only be used from a locally compiled server. Upstream publishes signed
# release archives for every desktop OS, which is why it is the default.
#
# Consequence for both runtimes: EITHER one loads K2, and both load every other
# GGUF architecture. "Fork" is therefore a preference (pre-tokenizer parity,
# reproducibility from source), never a requirement. See local_runtime.py for
# the resolver that turns RUNTIMES into an actual binary on a given OS.
# ---------------------------------------------------------------------------

RUNTIME_UPSTREAM = "llama.cpp"
RUNTIME_MBZUAI = "mbuzai"
RUNTIME_DEFAULT = RUNTIME_UPSTREAM

#: Every runtime id Stella offers. The UI must be able to show all of these.
RUNTIMES = (RUNTIME_UPSTREAM, RUNTIME_MBZUAI)

# Pinned upstream release. b11612 is the current prebuilt train and already
# contains K2-Horizon; SHA-256 per platform so a swapped or truncated archive
# fails loudly instead of producing a llama-server that segfaults on load.
UPSTREAM_VERSION = "b11612"
UPSTREAM_RELEASE_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b11612"

# Pinned K2 fork build (no prebuilt binaries are published for it).
K2_SERVER_VERSION = "mbuzai-llama.cpp:model/K2Horizon@42adf019"
K2_SERVER_REPO = "https://github.com/MBZUAI-IFM/llama.cpp.git"
K2_SERVER_BRANCH = "model/K2Horizon"
K2_SERVER_COMMIT = "42adf019f76013dac873b5b43950d54d5ab27216"

# Release archive per (runtime, platform) -> the file we download and verify.
#
# Platform keys are the ones Stella actually ships or runs on:
#   windows-x64   desktop Windows  (x64 binary; runs on arm64 Windows too)
#   linux-x64     desktop Linux
#   macos-arm64   Apple silicon
#   macos-x64     Intel Macs
#   android-arm64 the APK (cross-compiled from source, not downloaded)
#
# The MBZUAI fork publishes no archives, so its entries are empty by design and
# are satisfied by a locally built server (see local_runtime.find_server).
RUNTIME_ARCHIVES: dict[str, dict[str, dict[str, str]]] = {
    RUNTIME_UPSTREAM: {
        "windows-x64": {
            "url": f"{UPSTREAM_RELEASE_URL}/llama-b11612-bin-win-cpu-x64.zip",
            "sha256": "b8456ccb1be98365a5a2227efa5c495508a6a3ebce881c6189a1dbeaaa170b69",
            "bytes": "19553433",
        },
        "linux-x64": {
            "url": f"{UPSTREAM_RELEASE_URL}/llama-b11612-bin-ubuntu-x64.tar.gz",
            "sha256": "06fbaabe471aab27727882cd8f1b5c231d2eaa346fce1a3171041e2868f08c2a",
            "bytes": "17774766",
        },
        "macos-arm64": {
            "url": f"{UPSTREAM_RELEASE_URL}/llama-b11612-bin-macos-arm64.tar.gz",
            "sha256": "f54afc174f3b0fd01d520179aaf21caa37e4f11396015f304407a95feb5042ae",
            "bytes": "12157573",
        },
        # Intel Macs need their own build: the arm64 archive is the wrong ISA
        # and would not launch at all under Rosetta.
        "macos-x64": {
            "url": f"{UPSTREAM_RELEASE_URL}/llama-b11612-bin-macos-x64.tar.gz",
            "sha256": "1649b0ba742b15afd68f70d1294bad34593965010a9cfb0e85792e7f11057a58",
            "bytes": "11650386",
        },
    },
    RUNTIME_MBZUAI: {},
}

# Server binary name inside each archive / build output, per platform.
SERVER_BASENAME = {
    "windows-x64": "llama-server.exe",
    "linux-x64": "llama-server",
    "macos-arm64": "llama-server",
    "macos-x64": "llama-server",
    "android-arm64": "llama-server",
}

# Legacy alias kept so existing imports of K2_SERVER_SHA256 keep working; it now
# points at the upstream Windows archive, which is what ships beside this file.
K2_SERVER_SHA256 = {
    "windows-x64": RUNTIME_ARCHIVES[RUNTIME_UPSTREAM]["windows-x64"]["sha256"],
    # ARM64 Android build, cross-compiled with NDK r27c at fork commit 42adf019.
    "android-arm64": "bc417f5f526fb206a36cb2bc5b0835a36677f4917a42754fc057a408dd6ec041",
}

# Pinned GGUF weights.
#
# Upstream calls the family K2-Horizon-0.9B but ships the weight files under
# K2-Horizon-1B-*.gguf; the tensors self-report general.size_label = "1.1B" on
# the same 28-block / 1536-embedding architecture. The two names denote the
# same checkpoint, so every accepted spelling is listed here and the resolver
# matches on any of them instead of one guessed name. (The Android download
# path historically used the 1B spelling while desktop used 0.9B; both are the
# same 666,184,352-byte file, so both must be recognised or a user who already
# has the weights gets offered a pointless second download.)
K2_MODEL_FILENAME = "K2-Horizon-0.9B-Q4_K_M.gguf"
K2_MODEL_ALIASES = (
    K2_MODEL_FILENAME,
    "K2-Horizon-1B-Q4_K_M.gguf",
)
# Architecture-neutral names (the model resolver is no longer K2-only: any
# GGUF on disk goes through the same list). core/server.py reads these.
SERVER_MODEL_ALIASES = K2_MODEL_ALIASES
K2_MODEL_VERSION = "2026-10-01"
K2_MODEL_BYTES = 666_184_352
K2_MODEL_SHA256 = (
    "08c4baf06554edee1846d0490ace73d73e70f6cb02c02143c8283a98a1ea43ea"
)
K2_MODEL_REPO = "IFM/K2-Horizon-0.9B-GGUF"
K2_MODEL_URL = (
    f"https://huggingface.co/{K2_MODEL_REPO}/resolve/main/K2-Horizon-1B-Q4_K_M.gguf"
)

# Where each platform stages the runtime. None of these live inside an
# OTA-swapped install tree, by design (see module docstring).
K2_DESKTOP_MODEL_DIRNAME = "models"          # <install>/models (desktop)
K2_ANDROID_SUBDIR = "k2"                     # app-private files/k2/ (APK)
K2_CONFIG_KEYS = ("k2_port", "k2_threads", "k2_ctx", "k2_autostart")
# Settings keys, renamed from k2_* to server_* now that the server is
# architecture-sensitive (not K2-specific). Persisted settings files written
# before the rename still carry the k2_* keys, so core/server.py reads the
# new name first and falls back to the legacy twin.
SERVER_RUNTIME_KEY = "server_runtime"
SERVER_CONFIG_KEYS = ("server_port", "server_threads", "server_ctx",
                      "server_autostart")
K2_RUNTIME_KEY = "k2_runtime"  # legacy setting name, read as fallback
K2_CONFIG_KEYS = ("k2_port", "k2_threads", "k2_ctx", "k2_autostart")
LEGACY_K2_RUNTIME_KEY = "k2_runtime"


# ---------------------------------------------------------------------------
# GGUF architecture sniffing — the one piece of "which server do I need?" both
# platforms agree on.
#
# Two llama-server builds ship with Stella and they are NOT interchangeable at
# the edges: the MBZUAI fork build carries the K2-Horizon loader + the K2
# pre-tokenizer, while a plain upstream build is the safer binary for every
# other GGUF family. The model file itself says which one it needs: the first
# metadata KV of every GGUF is `general.architecture` (e.g. "k2-horizon",
# "llama", "qwen2"). Reading it costs a 4 KB read instead of a 600 MB mmap,
# so the server resolver can pick per-model instead of per-app.
#
# The header layout (little-endian throughout):
#   u32 magic "GGUF" | u32 version | u64 n_tensors | u64 n_kv
#   then n_kv metadata pairs: u32 key_len, key bytes, u32 value_type, value
# String values are u64 length + bytes; array values are u64 count + u32
# element type + elements. We stop at the first `general.architecture` and
# give up cleanly (returning "") on anything malformed — an unreadable arch
# must never block a start, it only loses the optimisation.
# ---------------------------------------------------------------------------
K2_ARCH = "k2-horizon"

# Value-type ids exactly as this llama.cpp family serializes them (ground
# truth: ggml/include/gguf.h in the MBZUAI fork - BOOL=7, STRING=8, ARRAY=9 -
# and both models in models/ agree byte-for-byte). The pre-2026-10-15 reader
# used a third, invented enum (string as 6 in the skip path, 8 in the match
# path) plus u32 key lengths and header offsets from a different layout, so it
# returned "" for every real file and architecture routing never engaged.
GGUF_TYPE_UINT8 = 0
GGUF_TYPE_INT8 = 1
GGUF_TYPE_UINT16 = 2
GGUF_TYPE_INT16 = 3
GGUF_TYPE_UINT32 = 4
GGUF_TYPE_INT32 = 5
GGUF_TYPE_FLOAT32 = 6
GGUF_TYPE_BOOL = 7
GGUF_TYPE_STRING = 8
GGUF_TYPE_ARRAY = 9
GGUF_TYPE_UINT64 = 10
GGUF_TYPE_INT64 = 11
GGUF_TYPE_FLOAT64 = 12

_GGUF_FIXED_SIZE = {
    GGUF_TYPE_UINT8: 1, GGUF_TYPE_INT8: 1,
    GGUF_TYPE_UINT16: 2, GGUF_TYPE_INT16: 2,
    GGUF_TYPE_UINT32: 4, GGUF_TYPE_INT32: 4, GGUF_TYPE_FLOAT32: 4,
    GGUF_TYPE_BOOL: 1,
    GGUF_TYPE_UINT64: 8, GGUF_TYPE_INT64: 8, GGUF_TYPE_FLOAT64: 8,
}


def gguf_architecture(model) -> str:
    """`general.architecture` for a GGUF file, or "" when unreadable.

    Reads at most the first few metadata pairs; never loads tensor data
    (a few KB instead of a 600MB mmap).

    Header layout, little-endian throughout::

        v1 : u32 magic | u32 version | u32 n_tensors | u32 n_kv  (kv @16)
        v2+: u32 magic | u32 version | u64 n_tensors | u64 n_kv  (kv @24)

    Each metadata pair is: u64 key length | key bytes | u32 value type |
    value (string values are u64 length + bytes).

    The architecture value is always a string, so that one key accepts both
    observed encodings instead of desyncing on exotic writers.
    """
    import struct
    try:
        with open(str(model), "rb") as f:
            head = f.read(65536)
    except OSError:
        return ""
    if len(head) < 16 or head[:4] != b"GGUF":
        return ""
    try:
        (version,) = struct.unpack_from("<I", head, 4)
        if version < 2:
            (n_kv,) = struct.unpack_from("<I", head, 12)
            off = 16
        else:
            (n_kv,) = struct.unpack_from("<Q", head, 16)
            off = 24
        for _ in range(min(n_kv, 64)):
            if off + 8 > len(head):
                break
            (klen,) = struct.unpack_from("<Q", head, off)
            off += 8
            if off + klen + 4 > len(head):
                break
            key = head[off:off + klen].decode("utf-8", "replace")
            off += klen
            (vtype,) = struct.unpack_from("<I", head, off)
            off += 4
            if key == "general.architecture":
                if vtype in (GGUF_TYPE_STRING, GGUF_TYPE_BOOL):
                    # STRING here; BOOL tolerated because a handful of foreign
                    # writers use the alternate enum where 7 means string.
                    if off + 8 > len(head):
                        return ""
                    (slen,) = struct.unpack_from("<Q", head, off)
                    if slen > 64:
                        return ""
                    off += 8
                    return head[off:off + slen].decode("utf-8", "replace")
                return ""
            # Skip the value so the scan lands on the next pair.
            off = _skip_gguf_value(head, off, vtype)
            if off < 0:
                break
        return ""
    except Exception:
        return ""


def _skip_gguf_value(buf: bytes, off: int, vtype: int) -> int:
    """Byte offset just past one GGUF metadata value; -1 when it runs out."""
    import struct
    fixed = _GGUF_FIXED_SIZE
    if vtype in fixed:
        return off + fixed[vtype]
    if vtype == GGUF_TYPE_STRING:
        if off + 8 > len(buf):
            return -1
        (n,) = struct.unpack_from("<Q", buf, off)
        return off + 8 + n
    if vtype == GGUF_TYPE_ARRAY:
        if off + 12 > len(buf):
            return -1
        (count,) = struct.unpack_from("<Q", buf, off)
        (etype,) = struct.unpack_from("<I", buf, off + 8)
        off += 12
        if count > 1_000_000:
            return -1
        if etype == GGUF_TYPE_STRING:
            for _ in range(count):
                if off + 8 > len(buf):
                    return -1
                (n,) = struct.unpack_from("<Q", buf, off)
                off += 8 + n
            return off
        if etype == GGUF_TYPE_ARRAY:
            for _ in range(count):
                off = _skip_gguf_value(buf, off, etype)
                if off < 0:
                    return -1
            return off
        elen = fixed.get(etype)
        if elen is None:
            return -1
        return off + count * elen
    return -1


def host_platform() -> str:
    """Platform key for the machine we are running on.

    Used to pick the right release archive in RUNTIME_ARCHIVES. Returns the
    canonical key, or "" when the host is one Stella cannot fetch a prebuilt
    server for (which is a real answer: the caller must then fall back to a
    locally built binary rather than downloading the wrong architecture).
    """
    import platform as _pf
    import sys

    system = _pf.system().lower()
    machine = _pf.machine().lower()
    is_arm = machine in ("arm64", "aarch64")

    # Android: sys.getandroidapilevel exists only on the CPython Android port.
    if hasattr(sys, "getandroidapilevel"):
        return "android-arm64" if is_arm else ""
    if system == "windows":
        # Upstream ships one x64 build; Windows-on-ARM runs it via emulation.
        return "windows-x64"
    if system == "darwin":
        return "macos-arm64" if is_arm else "macos-x64"
    if system == "linux":
        return "linux-arm64" if is_arm else "linux-x64"
    return ""


def runtimes_available(platform: str = "") -> tuple:
    """Runtime ids that can actually be provisioned on `platform`.

    The MBZUAI fork publishes no binaries, so it is only offered where a
    locally compiled server can supply it - i.e. everywhere on desktop, where
    the user can build it, but never auto-downloaded. Upstream is offered
    wherever a verified release archive exists for the platform.
    """
    plat = platform or host_platform()
    available = []
    if plat in RUNTIME_ARCHIVES.get(RUNTIME_UPSTREAM, {}):
        available.append(RUNTIME_UPSTREAM)
    if plat:
        available.append(RUNTIME_MBZUAI)
    return tuple(available)


def k2_manifest_block(server_sha_android: str = "") -> dict:
    """The `k2:` block scripts/stella_build.py stamps into manifest.json."""
    sha = dict(K2_SERVER_SHA256)
    if server_sha_android:
        sha["android-arm64"] = server_sha_android
    return {
        "server_version": K2_SERVER_VERSION,
        "server_repo": K2_SERVER_REPO,
        "server_branch": K2_SERVER_BRANCH,
        "server_commit": K2_SERVER_COMMIT,
        "server_sha256": sha,
        # Both runtimes are user-selectable; upstream is the default and the
        # only one with downloadable prebuilt archives.
        "upstream_version": UPSTREAM_VERSION,
        "runtimes": list(RUNTIMES),
        "default_runtime": RUNTIME_DEFAULT,
        "runtime_archives": RUNTIME_ARCHIVES,
        "model_filename": K2_MODEL_FILENAME,
        "model_aliases": list(K2_MODEL_ALIASES),
        "model_repo": K2_MODEL_REPO,
        "model_version": K2_MODEL_VERSION,
        "model_bytes": K2_MODEL_BYTES,
        "model_sha256": K2_MODEL_SHA256,
        "port": K2_PORT,
    }

