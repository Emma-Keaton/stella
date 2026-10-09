#!/usr/bin/env bash
# build.sh — one command to build Stella on any host (macOS/Linux).
# Thin wrapper over scripts/stella_build.py; identical to build.ps1.
#
#   ./build.sh --plan
#   ./build.sh --edition lite --os linux --release
#   ./build.sh --edition full --os android
set -euo pipefail
cd "$(dirname "$0")"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
    echo "No .venv. Create it first:" >&2
    echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pyinstaller" >&2
    exit 1
fi

exec "$PY" scripts/stella_build.py "$@"
