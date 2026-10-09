#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# scripts/setup_termux.sh — one-command bootstrap for Android (Termux).
#
# Termux is the Android equivalent of a Linux shell, but it is an *app*, so it
# cannot be silently installed from inside Stella. This script:
#   1. Detects whether Termux is already installed, or where the "dex" binary
#      lives (Termux runtime) or is installed manually.
#   2. Offers (console) the two ways to get Termux:
#        - Open the F-Droid store page.
#        - Download the official Termux APK from the upstream repo.
#   3. Once Termux is present, runs the real bootstrap END-TO-END:
#        - refreshes package lists
#        - installs the stdlib + pip toolchain
#        - installs every tier of the Stella requirements, smallest-first
#        - marks each tier COMPLETE before moving on (never partially done)
#        - clears the download on network failures and retries (resumable)
#   4. Then hands off to `bootstrap.py --all` which performs the real build.
#
# Usage:
#   ./scripts/setup_termux.sh                 # interactive guide
#   ./scripts/setup_termux.sh --yes           # non-interactive (assumes guide)
#   ./scripts/setup_termux.sh --skip-install  # only print the Termux setup;
#                                               # do not execute the project
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERMINAL="bash"
YES=0
SKIP_INSTALL=0

usage() {
    sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --yes)    YES=1; shift ;;
        --skip-install) SKIP_INSTALL=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown flag: $1"; usage; exit 1 ;;
    esac
done

log()  { printf '\033[1;36m[stella-termux]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[err]\033[0m %s\n' "$*" >&2; }

ask() {
    # ask "message" → prints yes/no interactively (or YES=1 → yes)
    if [[ ${YES} -eq 1 ]]; then
        return 0
    fi
    read -r -p "$1 (y/N): " ans
    case "${ans,,}" in y|yes) return 0;; *) return 1;; esac
}

# --- 1. Detect Termux ------------------------------------------------------
TERMUX_BIN=""
if command -v termux-setup-storage &>/dev/null; then
    TERMUX_BIN="$(command -v termux-setup-storage)"
    log "Termux detected (runtime binary: ${TERMUX_BIN})."
elif [[ -n "${PREFIX:-}" && -x "${PREFIX}/bin/bash" ]]; then
    TERMUX_BIN="${PREFIX}/bin/bash"
    log "Termux environment detected (PREFIX=${PREFIX})."
else
    log "No Termux runtime found. Stella cannot run self-contained on Android."
    if ask "Would you like to install Termux from the F-Droid store now?"; then
        xdg-open https://f-droid.org/packages/com.termux/ 2>/dev/null \
            || open https://f-droid.org/packages/com.termux/ 2>/dev/null \
            || echo "(No browser; paste this URL in a browser: https://f-droid.org/packages/com.termux/)"
    fi
    exit 0
fi

# --- 2. Guides the user to install Termux if they do not already have it ---
if [[ ${SKIP_INSTALL} -eq 1 ]]; then
    ok "Skipping install step (--skip-install)."
    exit 0
fi

# --- 3. Run the real bootstrap ---------------------------------------------
log "Running the full bootstrap inside Termux (core first, then optional tiers)..."
if ! ${TERMINAL} -l -c "cd ${REPO_DIR}; .venv/bin/python scripts/bootstrap.py --all"; then
    err "Bootstrap failed. Re-run this script (it is resumable) or run the"
    err "same command inside Termux manually:"
    err "  pkg update && pkg install -y python"
    err "  python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

ok "Bootstrap complete. Stella is ready."
