#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Stella Termux Backend Stopper
# Stops the Python backend and watcher
# =============================================================================
set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[Stella]${NC} $1"; }
err() { echo -e "${RED}[ERR]${NC} $1"; }

STELLA_DIR=~/stella
PID_FILE="$STELLA_DIR/logs/backend.pid"

# Stop watcher
pkill -f "watcher.sh" 2>/dev/null || true

# Stop backend
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null
        sleep 2
        kill -9 "$PID" 2>/dev/null || true
        log "Backend stopped (PID: $PID)"
    else
        log "Backend not running"
    fi
    rm -f "$PID_FILE"
else
    echo "[Stella] No PID file found"
fi

pkill -f "main.py" 2>/dev/null || true
echo "[Stella] Done"
