"""
core/k2_runtime.py — tracked K2 runtime contract (desktop + Android).

Why this file exists (and is NOT gitignored, unlike core/k2_server.py)
-----------------------------------------------------------------------
K2 is now a shipping, updatable product surface — not a personal-only local
runtime. This module holds the parts of that contract every platform shares:

- Which K2 *server* binary version we pin, and its SHA-256 per platform
  (Windows x64 for desktop, ARM64 for the Android APK).
- Which GGUF *model* version we pin, its size, and its SHA-256.
- Where each platform keeps the runtime (outside OTA-swapped trees) and the
  HTTP contract both servers speak (OpenAI-compatible, 127.0.0.1:11435).

Desktop keeps using core/k2_server.py untouched for its Windows launch path;
it now reads its pinned model filename from here. Android reads the same
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

# Pinned K2 server (llama.cpp) build.
#
# IMPORTANT: K2 Horizon support does NOT exist in upstream ggml-org/llama.cpp.
# It lives only in the MBZUAI-IFM fork, branch model/K2Horizon, as the model
# card itself documents ("PR to llama.cpp is in progress. MBZUAI-IFM fork of
# llama.cpp is in https://github.com/MBZUAI-IFM/llama.cpp/tree/model/K2Horizon").
# Building from ggml-org produces a llama-server that loads this model as
# "unknown architecture". Pin the SHA so the branch moving fails loudly.
K2_SERVER_VERSION = "mbzuai-ifm-llama.cpp:model/K2Horizon@42adf019"
K2_SERVER_REPO = "https://github.com/MBZUAI-IFM/llama.cpp.git"
K2_SERVER_BRANCH = "model/K2Horizon"
K2_SERVER_COMMIT = "42adf019f76013dac873b5b43950d54d5ab27216"
K2_SERVER_SHA256 = {
    # Windows x64 desktop build (ships beside core/k2_server.py today).
    "windows-x64": "",
    # ARM64 Android build, cross-compiled with NDK r27c at commit 42adf019.
    "android-arm64": "bc417f5f526fb206a36cb2bc5b0835a36677f4917a42754fc057a408dd6ec041",
}

# Pinned GGUF weights.
#
# Upstream calls the family K2-Horizon-0.9B but ships the weight files under
# K2-Horizon-1B-*.gguf; the tensors self-report general.size_label = "1.1B" on
# the same 28-block / 1536-embedding architecture. The two names denote the
# same checkpoint, so keep filename and version in sync with whatever the local
# file is called rather than guessing.
K2_MODEL_FILENAME = "K2-Horizon-0.9B-Q4_K_M.gguf"
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
        "model_filename": K2_MODEL_FILENAME,
        "model_repo": K2_MODEL_REPO,
        "model_version": K2_MODEL_VERSION,
        "model_bytes": K2_MODEL_BYTES,
        "model_sha256": K2_MODEL_SHA256,
        "port": K2_PORT,
    }
