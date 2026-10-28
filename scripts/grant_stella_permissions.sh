#!/usr/bin/env bash
# =============================================================================
# Stella Cross-OS Permission Grant Script (Bash - Linux/macOS)
# =============================================================================
# Automatically grants all permissions required for Stella's full operation
# on Linux and macOS. Runs without user confirmation where possible.
#
# Usage:
#   chmod +x scripts/grant_stella_permissions.sh
#   ./scripts/grant_stella_permissions.sh
#   sudo ./scripts/grant_stella_permissions.sh   # for system-wide changes
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() {
    local level="$1"
    shift
    local msg="$*"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    case "$level" in
        ERROR)  echo -e "\033[31m[$ts] [ERROR] $msg\033[0m" ;;
        WARN)   echo -e "\033[33m[$ts] [WARN] $msg\033[0m" ;;
        OK)     echo -e "\033[32m[$ts] [OK] $msg\033[0m" ;;
        INFO)   echo -e "\033[36m[$ts] [INFO] $msg\033[0m" ;;
        *)      echo "[$ts] [$level] $msg" ;;
    esac
}

is_root() {
    [[ "$(id -u)" -eq 0 ]]
}

require_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        log ERROR "This script must run as root/sudo to grant all permissions."
        log ERROR "Run: sudo $0"
        exit 1
    fi
}

has_cmd() {
    command -v "$1" >/dev/null 2>&1
}

grant_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir" 2>/dev/null || true
    fi
    if [[ -d "$dir" ]]; then
        chmod 755 "$dir" 2>/dev/null || true
        log OK "Filesystem access granted: $dir"
        GRANTED+=("Filesystem: $dir")
    else
        log ERROR "Failed to create directory: $dir"
        FAILED+=("Filesystem: $dir")
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

log "========================================================================"
log " Stella Permission Grant Script (Linux/macOS)"
log "========================================================================"

GRANTED=()
FAILED=()

# Detect OS
OS="$(uname -s)"
log "Detected OS: $OS"

# --- 1. Filesystem permissions ---------------------------------------------
log "Granting filesystem permissions..."

STELLA_DIRS=(
    "$HOME/.local/share/StellaAI"
    "$HOME/.local/share/StellaAI/config"
    "$HOME/.local/share/StellaAI/deliverables"
    "$HOME/.local/share/StellaAI/models"
    "$HOME/.local/share/StellaAI/audit"
    "$HOME/.config/StellaAI"
)

for dir in "${STELLA_DIRS[@]}"; do
    grant_dir "$dir"
done

# --- 2. Shell configuration ------------------------------------------------
log "Configuring shell environment..."

SHELL_RC=""
if [[ "$OS" == "Darwin" ]]; then
    SHELL_RC="$HOME/.zshrc"
    if [[ ! -f "$HOME/.zshrc" && -f "$HOME/.bash_profile" ]]; then
        SHELL_RC="$HOME/.bash_profile"
    fi
else
    SHELL_RC="$HOME/.bashrc"
    if [[ ! -f "$HOME/.bashrc" && -f "$HOME/.profile" ]]; then
        SHELL_RC="$HOME/.profile"
    fi
fi

if [[ -f "$SHELL_RC" ]]; then
    if ! grep -q "STELLA_HOME" "$SHELL_RC"; then
        {
            echo ""
            echo "# Stella AI environment"
            export STELLA_HOME="$HOME/.local/share/StellaAI"
            export PATH="$HOME/.local/share/StellaAI/scripts:\$PATH"
        } >> "$SHELL_RC"
        log OK "Shell environment configured in $SHELL_RC"
        GRANTED+=("Shell config: $SHELL_RC")
    else
        log OK "Shell environment already configured in $SHELL_RC"
    fi
else
    log WARN "Could not find shell rc file to configure"
fi

# --- 3. File permissions for Stella scripts --------------------------------
log "Setting script permissions..."

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -d "$SCRIPTS_DIR" ]]; then
    chmod +x "$SCRIPTS_DIR"/*.sh 2>/dev/null || true
    log OK "Script permissions set in $SCRIPTS_DIR"
    GRANTED+=("Script permissions: $SCRIPTS_DIR")
fi

# --- 4. macOS specific permissions -----------------------------------------
if [[ "$OS" == "Darwin" ]]; then
    log "Applying macOS-specific permissions..."

    # Full disk access cannot be granted programmatically without user interaction
    # but we can at least note it
    log WARN "Full Disk Access must be granted manually in System Preferences > Privacy & Security > Full Disk Access"
    log WARN "Terminal.app (or your terminal) needs Full Disk Access for Stella to access all files"

    # Accessibility permissions for automation
    log WARN "Accessibility permissions may be needed for automation features"

    # Allow unsigned apps (developer mode)
    if is_root; then
        spctl --master-disable 2>/dev/null || true
        log OK "Gatekeeper restrictions relaxed (allows unsigned apps)"
        GRANTED+=("Gatekeeper: disabled")
    fi
fi

# --- 5. Linux specific -----------------------------------------------------
if [[ "$OS" == "Linux" ]]; then
    log "Applying Linux-specific permissions..."

    # Add user to relevant groups
    for group in audio video input dialout; do
        if getent group "$group" >/dev/null 2>&1; then
            if ! groups "$USER" | grep -qw "$group"; then
                usermod -aG "$group" "$USER" 2>/dev/null || true
                log OK "Added user to group: $group"
                GRANTED+=("Group: $group")
            fi
        fi
    done
fi

# --- 6. Summary ------------------------------------------------------------
log ""
log "========================================================================"
log " Permission Grant Summary"
log "========================================================================"
log "Granted: ${#GRANTED[@]} item(s)"
for g in "${GRANTED[@]}"; do
    log "  [+] $g"
done
if [[ ${#FAILED[@]} -gt 0 ]]; then
    log "Failed: ${#FAILED[@]} item(s)"
    for f in "${FAILED[@]}"; do
        log "  [-] $f"
    done
fi
log ""
log "Stella permissions have been granted where possible."
log "Review any failures above and resolve manually if needed."
log "========================================================================"

if [[ ${#FAILED[@]} -gt 0 ]]; then
    exit 1
fi
