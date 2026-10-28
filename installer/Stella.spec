ï»¿# -*- mode: python ; coding: utf-8 -*-
# Stella desktop bundle (PyInstaller onedir).
#
# Two variants come out of this one spec:
#
#   PUBLIC  (default) Ã¢â¬â no K2 runtime, no weights. The app detects the absence
#           and suggests the user download the K2 package. This is what CI and
#           the GitHub release ship.
#
#   PERSONAL SERVER Ã¢â¬â set STELLA_SERVER_BUNDLE=1 before invoking PyInstaller, with
#           STELLA_SERVER_MODEL / STELLA_SERVER pointing at the local files:
#             $env:STELLA_SERVER_BUNDLE   = "1"
#             $env:STELLA_SERVER_MODEL    = "E:\...\K2-Horizon-0.9B-Q4_K_M.gguf"
#             $env:STELLA_SERVER          = "E:\...\llama-server.exe"
#             (STELLA_K2_SERVER still works as the legacy name for the binary.)
#             pyinstaller installer\Stella.spec --noconfirm
#           The weights land in k2/ next to the exe, where core/k2_runtime.py
#           resolves them without touching the network.
#
# The GGUF is never committed: installer/Stella.spec reads it from an absolute
# path outside the repo and .gitignore covers the staged copy.
import os
import sys

cwd = os.path.abspath(os.getcwd())

# ---------------------------------------------------------------------------
# Personal K2 payload (opt-in; see header).
# ---------------------------------------------------------------------------
K2_ON = os.environ.get("STELLA_SERVER_BUNDLE", "").strip().lower() in ("1", "true", "yes", "on")
K2_DIRNAME = "k2"
k2_datas = []

if K2_ON:
    _model = os.environ.get("STELLA_SERVER_MODEL", "").strip()
    _server = (os.environ.get("STELLA_SERVER", "").strip()
               or os.environ.get("STELLA_K2_SERVER", "").strip())
    _missing = [p for p in (_model, _server) if not p or not os.path.isfile(p)]
    if _missing:
        raise SystemExit(
            "STELLA_SERVER_BUNDLE=1 but these are missing/not files: "
            + ", ".join(repr(m) for m in _missing)
            + "\nSet STELLA_SERVER_MODEL and STELLA_SERVER to absolute paths."
        )

    # llama-server ships as `llama-server` on Linux and `llama-server.exe`
    # on Windows; keep the native suffix so Popen finds it.
    #
    # NOTE the dest of each datas tuple is the DIRECTORY to unpack into, not a
    # target filename. Passing "k2/llama-server.exe" produced a nested
    # k2/llama-server.exe/llama-server.exe and the launcher could not find the
    # binary. Dest must be just K2_DIRNAME.
    k2_datas = [
        (_model, K2_DIRNAME),
        (_server, K2_DIRNAME),
    ]

a = Analysis(
    [os.path.join(cwd, 'main.py')],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(cwd, 'assets'), 'assets'),
        (os.path.join(cwd, 'config'), 'config'),
        (os.path.join(cwd, 'core'), 'core'),
        (os.path.join(cwd, 'agent'), 'agent'),
        (os.path.join(cwd, 'stella_connect'), 'stella_connect'),
        (os.path.join(cwd, 'actions'), 'actions'),
        (os.path.join(cwd, 'dashboard/static'), 'dashboard/static'),
        (os.path.join(cwd, 'smart_home'), 'smart_home'),
        (os.path.join(cwd, 'memory'), 'memory'),
        (os.path.join(cwd, 'plugins'), 'plugins'),
        (os.path.join(cwd, 'features'), 'features'),
        (os.path.join(cwd, 'workspace_store.py'), '.'),
        (os.path.join(cwd, 'README.md'), '.'),
        (os.path.join(cwd, 'requirements.txt'), '.'),
        (os.path.join(cwd, 'version.txt'), '.')
    ] + k2_datas,
    hiddenimports=[
        'mediapipe', 'cv2', 'instagrapi', 'google.genai', 'PyQt6', 'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebChannel', 'pyautogui', 'sounddevice',
        'keyboard', 'docx', 'pptx', 'multipart', 'passlib', 'bcrypt', 'aiohttp', 'websockets',
        'uvicorn', 'fastapi', 'plyer', 'pydantic', 'typing_extensions', 'requests', 'beautifulsoup4',
        'numpy', 'pyperclip', 'matplotlib', 'edge_tts', 'qrcode', 'psutil', 'speedtest',
        'pycparser', 'cffi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# STRICT EXCLUSIONS FOR PERSONAL DATA
excluded_files = [
    'ig_browser_profile',
    'patch_backups',
    'patch_history.json',
    'api_keys.json',
    'ig_session.json',
    'email_credentials.json',
    'identity.json',
    'device_location_cache.json',
    'learned_rules.json',
    'organizer_history.json',
    'calendar_events.json',
    'long_term.json',
    'nutrition_log.json',
    'stella_connect.json',
    'devices.json'
]

_repo_norm = cwd.replace('\\', '/') + '/'
a.datas = [
    x for x in a.datas
    # Personal K2 payloads live outside the repo; never let the personal-data
    # filter match them by accident.
    if not x[0].replace('\\', '/').startswith(_repo_norm)
    or not any(excl in x[0].replace('\\', '/')
               for excl in excluded_files)
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Stella',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(cwd, 'assets/stella_logo.ico') if os.path.exists(os.path.join(cwd, 'assets/stella_logo.ico')) else None,
    version=os.path.join(cwd, 'version.txt') if os.path.exists(os.path.join(cwd, 'version.txt')) else None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Stella'
)

