#!/usr/bin/env bash
# build_macos.sh — build a Stella macOS bundle (.app via PyInstaller onedir).
# Usage:  ./build_macos.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "No .venv found. Create it first:"
    echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pyinstaller"
    exit 1
fi

PYI=()
if [ -x ".venv/bin/pyinstaller" ]; then
    PYI=(".venv/bin/pyinstaller")
else
    PYI=(".venv/bin/python" "-m" "PyInstaller")
fi
if ! "${PYI[@]}" --version >/dev/null 2>&1; then
    echo "pyinstaller missing in .venv. Install: .venv/bin/pip install pyinstaller" >&2
    exit 1
fi

echo "==> Pre-flight: free disk"
"$PYI" --version >/dev/null 2>&1 || true
df -h . | tail -1

echo "==> Building Stella.app (onedir)"
"$PYI" installer/Stella.spec --noconfirm

echo "==> Done. Bundle at dist/StellaEvo/  (run dist/StellaEvo/StellaEvo)"
echo "    Tip: use a .spec windowed build + create-dmg for distribution."
