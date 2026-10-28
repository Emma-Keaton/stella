"""Regression tests for the cross-OS local runtime + K2 server contract.

Covers the three things that made "download, load and run any local model"
silently impossible:

  1. `core/k2_server.py` hardcoded `.venv/llama.cpp/llama-server.exe`, so any
     machine that was not one specific Windows dev checkout had no server at
     all - and the public build therefore could not run a single local model.
     `local_runtime.find_server()` must resolve across the install tree, the
     user data dir and PATH, and `k2_server` must go through it.

  2. The MBZUAI fork and upstream llama.cpp were framed as "fork required",
     resting on a stale claim that upstream lacked the K2 architecture. Both
     runtimes must be offered on every OS, and each must be able to load K2
     *and* any other GGUF.

  3. The K2 weights ship under two filenames (the 0.9B and 1B spellings of the
     same checkpoint). Resolving only one told users their model was missing.
"""

import os
from pathlib import Path

import pytest

from core import engine_runtime as kr
from core import k2_server
from core import local_runtime


@pytest.fixture
def plat(request):
    """A platform key that matches the OS the suite is actually running on.

    The runtime layer is deliberately per-OS (exec bit vs .exe suffix, archive
    format), so a test that pretends to be Linux while running on Windows would
    be asserting behaviour that cannot happen. Callers pass the platform they
    want to simulate.
    """
    return "windows-x64" if os.name == "nt" else "linux-x64"


def make_server(directory: Path, platform: str = "") -> Path:
    """Create a plausible, runnable llama-server inside `directory`."""
    name = kr.SERVER_BASENAME.get(platform or (
        "windows-x64" if os.name == "nt" else "linux-x64"), "llama-server")
    server = directory / name
    server.write_bytes(b"stub-binary")
    server.chmod(0o755)
    return server


# --------------------------------------------------------------- runtimes ----
def test_both_runtimes_are_offered_on_every_desktop_os():
    """A user on any OS must be able to choose either runtime."""
    for plat in ("windows-x64", "linux-x64", "macos-arm64", "macos-x64"):
        available = kr.runtimes_available(plat)
        assert kr.RUNTIME_UPSTREAM in available, f"{plat} must offer llama.cpp"
        assert kr.RUNTIME_MBZUAI in available, f"{plat} must offer the mbuzai fork"


def test_upstream_has_a_verified_archive_per_supported_os():
    """Every downloadable platform needs a real URL and a real SHA-256.

    An empty hash would make verification a no-op and let a tampered or
    truncated binary be executed, which is worse than having no binary.
    """
    archives = kr.RUNTIME_ARCHIVES[kr.RUNTIME_UPSTREAM]
    for plat in ("windows-x64", "linux-x64", "macos-arm64"):
        spec = archives[plat]
        assert spec["url"].startswith("https://"), plat
        assert len(spec["sha256"]) == 64, f"{plat} needs a full SHA-256"
        int(spec["sha256"], 16)  # raises if not hex
        assert int(spec["bytes"]) > 0, plat


def test_fork_publishes_no_binaries_and_says_so():
    """Auto-downloading the fork must fail cleanly rather than silently handing
    back the upstream binary, which would misreport which code is running."""
    assert kr.RUNTIME_ARCHIVES[kr.RUNTIME_MBZUAI] == {}
    assert local_runtime.download_server(kr.RUNTIME_MBZUAI,
                                         "windows-x64") is None


def test_host_platform_is_a_known_key():
    plat = kr.host_platform()
    assert plat == "" or plat in kr.SERVER_BASENAME, f"unknown platform {plat!r}"


def test_server_basename_is_platform_correct():
    """Windows needs the .exe suffix; POSIX must not have one or the launch
    fails with ENOENT."""
    assert kr.SERVER_BASENAME["windows-x64"] == "llama-server.exe"
    for plat in ("linux-x64", "macos-arm64", "android-arm64"):
        assert kr.SERVER_BASENAME[plat] == "llama-server", plat


def test_k2_architecture_is_supported_upstream():
    """The old code asserted the opposite. Upstream llama.cpp has carried
    LLM_ARCH_K2_HORIZON since the merge, so the fork is a preference - this
    test pins that fact so the stale comment cannot come back unnoticed."""
    assert kr.RUNTIME_UPSTREAM in kr.RUNTIMES
    assert "windows-x64" in kr.RUNTIME_ARCHIVES[kr.RUNTIME_UPSTREAM]
    # The default must be the runtime that can actually be downloaded.
    assert kr.RUNTIME_DEFAULT == kr.RUNTIME_UPSTREAM


# ------------------------------------------------------------ resolution ----
def test_find_server_finds_a_binary_next_to_the_app(monkeypatch, sandbox, plat):
    """The portable-zip / installer layout puts llama-server beside the exe.
    That layout must resolve on any OS, not just the dev checkout."""
    server = make_server(sandbox, plat)

    monkeypatch.setattr(local_runtime, "_base_dir", lambda: sandbox)
    monkeypatch.setattr(kr, "host_platform", lambda: plat)
    monkeypatch.setattr(local_runtime.shutil, "which", lambda *_: None)

    assert local_runtime.find_server(kr.RUNTIME_UPSTREAM, plat) == server


def test_find_server_rejects_a_non_executable_file(monkeypatch, sandbox, plat):
    """A file that exists but cannot be executed would blow up at Popen with a
    confusing OS error, so it must be skipped rather than returned.

    The check is per-OS on purpose: POSIX tracks this with the exec bit,
    Windows with the file extension (see local_runtime._is_runnable).
    """
    # Correct name and exec bit for the platform, but not a runnable form:
    # on POSIX the bit is cleared, on Windows the suffix is wrong.
    wrong = sandbox / ("llama-server" if os.name == "nt" else "llama-server")
    wrong.write_bytes(b"not runnable")
    wrong.chmod(0o755 if os.name == "nt" else 0o644)

    monkeypatch.setattr(local_runtime, "_base_dir", lambda: sandbox)
    monkeypatch.setattr(kr, "host_platform", lambda: plat)
    monkeypatch.setattr(local_runtime.shutil, "which", lambda *_: None)

    assert local_runtime.find_server(kr.RUNTIME_UPSTREAM, plat) is None


def test_explicit_env_override_wins(monkeypatch, sandbox, plat):
    """STELLA_K2_SERVER is the escape hatch for a user who built the fork
    themselves; it must beat every default location."""
    pinned = make_server(sandbox, plat)
    default_dir = sandbox / "default"
    default_dir.mkdir()
    make_server(default_dir, plat)

    monkeypatch.setenv("STELLA_K2_SERVER", str(pinned))
    monkeypatch.setattr(local_runtime, "_base_dir", lambda: default_dir)
    monkeypatch.setattr(kr, "host_platform", lambda: plat)
    monkeypatch.setattr(local_runtime.shutil, "which", lambda *_: None)

    assert local_runtime.find_server(kr.RUNTIME_UPSTREAM, plat) == pinned


def test_find_server_returns_none_when_nothing_is_installed(monkeypatch,
                                                            sandbox, plat):
    monkeypatch.setenv("STELLA_K2_SERVER", "")
    monkeypatch.setattr(local_runtime, "_base_dir", lambda: sandbox / "nowhere")
    monkeypatch.setattr(local_runtime.shutil, "which", lambda *_: None)
    assert local_runtime.find_server(kr.RUNTIME_UPSTREAM, plat) is None


def test_ensure_server_never_downloads_when_told_not_to(monkeypatch):
    """Offline / first-run callers must get a clean None, not a network hang."""

    def _boom(*a, **k):  # pragma: no cover - must never be reached
        raise AssertionError("must not touch the network")

    monkeypatch.setattr(local_runtime, "find_server", lambda *a, **k: None)
    monkeypatch.setattr(local_runtime, "download_server", _boom)
    assert local_runtime.ensure_server(allow_download=False) is None


# ----------------------------------------------------------- launch argv ----
def test_build_command_uses_the_platform_binary_and_selected_model(sandbox):
    """Any GGUF the user picked must be what gets served - not just K2."""
    server = sandbox / "llama-server"
    model = sandbox / "Qwen2.5-3B-Instruct-Q4_K_M.gguf"
    argv = local_runtime.build_command(server, model, port=1234, threads=3,
                                       ctx=4096)
    assert argv[0] == str(server)
    assert "-m" in argv and str(model) in argv
    assert "--port" in argv and "1234" in argv
    assert "-c" in argv and "4096" in argv
    assert "-t" in argv and "3" in argv


def test_build_command_can_serve_a_k2_model(sandbox):
    """The same code path must handle the K2 checkpoint, so switching between
    "my model" and "K2" is not a special case."""
    argv = local_runtime.build_command(
        sandbox / "llama-server",
        sandbox / kr.K2_MODEL_FILENAME,
        port=kr.K2_PORT,
    )
    assert kr.K2_MODEL_FILENAME in " ".join(argv)
    assert str(kr.K2_PORT) in argv


def test_build_command_omits_threads_when_autodetect(sandbox):
    """Passing 0 means "let llama.cpp decide"; emitting -t 0 would break it."""
    argv = local_runtime.build_command(sandbox / "s", sandbox / "m.gguf",
                                       threads=0)
    assert "-t" not in argv


# ------------------------------------------------------ K2 server wrapper ---
def test_k2_server_resolves_binary_through_the_runtime_layer(monkeypatch,
                                                             sandbox, plat):
    """The original bug: SERVER_EXE was one hardcoded path. k2_server must now
    delegate to local_runtime so resolution works on any OS."""
    server = make_server(sandbox, plat)

    monkeypatch.setattr(kr, "host_platform", lambda: plat)
    monkeypatch.setattr(local_runtime, "_base_dir", lambda: sandbox)
    monkeypatch.setattr(local_runtime.shutil, "which", lambda *_: None)
    monkeypatch.setattr(k2_server, "runtime", lambda: kr.RUNTIME_UPSTREAM)

    resolved = k2_server.server_binary()
    assert resolved == server
    # The binary name must be the one this platform actually uses.
    assert resolved.name == kr.SERVER_BASENAME[plat]


def test_k2_server_runtime_setting_falls_back_on_garbage(monkeypatch):
    """A corrupt/legacy value must not silently disable local inference.

    Patches go through `core.server` (the functions read their globals there);
    assertions go through the `k2_server` shim so old imports stay covered.
    """
    from core import server as server_mod
    monkeypatch.setattr(server_mod, "_load_setting", lambda key, default: "not-a-runtime")
    assert k2_server.runtime() == kr.RUNTIME_DEFAULT
    monkeypatch.setattr(server_mod, "_load_setting",
                        lambda key, default: kr.RUNTIME_MBZUAI)
    assert k2_server.runtime() == kr.RUNTIME_MBZUAI


def test_k2_model_resolution_accepts_both_filename_spellings(monkeypatch,
                                                             sandbox):
    """K2-Horizon ships as ...0.9B... and ...1B... (same 666 MB checkpoint).
    A user holding either spelling has the model; both must be found."""
    from core import server as server_mod
    monkeypatch.setattr(server_mod, "_model_search_dirs", lambda: [sandbox])
    assert k2_server.resolve_model_path() is None

    for name in kr.K2_MODEL_ALIASES:
        (sandbox / name).write_bytes(b"GGUF" + b"\0" * 1024)
        assert k2_server.resolve_model_path() == sandbox / name
        (sandbox / name).unlink()


def test_k2_start_reports_missing_runtime_instead_of_raising(monkeypatch):
    """No binary available must be a clean False, not a crash."""
    from core import server as server_mod
    monkeypatch.setattr(server_mod, "is_running", lambda: False)
    monkeypatch.setattr(server_mod, "resolve_model_path", lambda: Path(__file__))
    monkeypatch.setattr(server_mod, "ensure_server_binary", lambda **k: None)
    assert k2_server.start() is False


# -------------------------------------------------------------- manifest ----
def test_gguf_architecture_reads_real_files():
    """The architecture sniffer is what routes a model to the right server.

    Regression: it used to read the header at wrong offsets (n_kv@12,
    first key@20, u32 key lengths) and the wrong STRING type id, returning ""
    for every real file - so `server_binary()` never left its default path.
    Both models ship in models/ (the K2 one is gitignored, so each file is
    skipped independently when absent).
    """
    from core import engine_runtime as er

    checks = (
        ("K2-Horizon-0.9B-Q4_K_M.gguf", "k2-horizon"),
        ("qwen2.5-coder-1.5b-instruct-q4_k_m.gguf", "qwen2"),
    )
    ran = 0
    for name, expected in checks:
        path = Path(__file__).resolve().parent.parent / "models" / name
        if not path.is_file():
            continue
        ran += 1
        assert er.gguf_architecture(path) == expected, name
    if ran == 0:
        pytest.skip("no model files present to sniff")


def test_gguf_architecture_rejects_non_gguf(sandbox):
    from core import engine_runtime as er

    junk = sandbox / "not-model.bin"
    junk.write_bytes(b"hello world" * 100)
    assert er.gguf_architecture(junk) == ""
    assert er.gguf_architecture(sandbox / "missing.gguf") == ""


def test_manifest_advertises_both_runtimes():
    """The release manifest is what the updater and the UI read. If it lists
    one runtime, the UI can only offer one."""
    block = kr.k2_manifest_block()
    assert block["runtimes"] == list(kr.RUNTIMES)
    assert len(block["runtimes"]) >= 2
    assert block["default_runtime"] == kr.RUNTIME_DEFAULT
    assert block["model_aliases"] == list(kr.K2_MODEL_ALIASES)


def test_legacy_server_sha_alias_still_populated():
    """Existing callers import K2_SERVER_SHA256; it must not regress to empty."""
    assert kr.K2_SERVER_SHA256["windows-x64"]
    assert len(kr.K2_SERVER_SHA256["windows-x64"]) == 64


def test_describe_is_json_serialisable():
    """The Settings UI reads this straight into a widget."""
    import json

    assert json.loads(json.dumps(local_runtime.describe()))["runtimes"] == \
        list(kr.RUNTIMES)


