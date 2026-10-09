#!/usr/bin/env bash
# build_linux.sh — build a Stella Linux bundle (PyInstaller onedir).
# Usage:  ./build_linux.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "No .venv found. Create it first:"
    echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pyinstaller"
    exit 1
fi

PYI=".venv/bin/pyinstaller"
if [ ! -x "$PYI" ]; then
    echo "pyinstaller missing in .venv. Install: .venv/bin/pip install pyinstaller"
    exit 1
fi

# Qt6 needs a display/toolkit present even in headless builds on some distros.
echo "==> Pre-flight: free disk"
df -h . | tail -1

echo "==> Building Stella bundle (onedir)"
"$PYI" installer/Stella.spec --noconfirm

echo "==> Done. Bundle at dist/StellaEvo/  (run dist/StellaEvo/StellaEvo)"
echo "    Package as .AppImage / .tar.gz for distribution."
