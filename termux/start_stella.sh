#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Stella Termux Backend Starter
# Runs the Python backend (WebSocket server) persistently on Android
# Auto-restarts on crash. Started by the Stella app on launch.
# Usage: ./termux/start_stella.sh
# =============================================================================
set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[Stella]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERR]${NC} $1"; }

STELLA_DIR=~/stella
PID_FILE="$STELLA_DIR/logs/backend.pid"
LOG_FILE="$STELLA_DIR/logs/backend.log"
WATCHER_LOG="$STELLA_DIR/logs/watcher.log"

mkdir -p "$STELLA_DIR/logs"

# =============================================================================
# AUTO-COPY BACKEND FILES FROM SHARED STORAGE
# The Stella APK copies main.py + src/ to /sdcard/stella/ on first launch.
# This script ensures they're in ~/stella/backend/ before starting.
# =============================================================================
if [ -d /sdcard/stella/backend ] || [ -f /sdcard/stella/main.py ]; then
    log "Copying Stella backend files from shared storage..."
    mkdir -p ~/stella/backend
    cp -r /sdcard/stella/main.py ~/stella/backend/ 2>/dev/null || true
    cp -r /sdcard/stella/src ~/stella/backend/ 2>/dev/null || true
    log "Backend files synced to ~/stella/backend/"
fi

# Verify backend files exist
if [ ! -f ~/stella/backend/main.py ]; then
    err "main.py not found in ~/stella/backend/"
    err "Please ensure the Stella APK has been launched at least once,"
    err "or manually copy main.py and src/ to ~/stella/backend/"
    exit 1
fi

# Kill any existing Stella backend
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        log "Stopping existing backend (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$OLD_PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi
pkill -f "main.py" 2>/dev/null || true
sleep 1

# Start backend in background with nohup (persistent)
log "Starting Python backend on ws://127.0.0.1:8765..."
cd "$STELLA_DIR/backend"
nohup python main.py --host 0.0.0.0 --port 8765 > "$LOG_FILE" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_FILE"

# Wait for backend to be ready
echo -n "Waiting for backend to start"
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8765/ > /dev/null 2>&1; then
        echo ""
        echo "=================================================="
        echo "  Stella Backend Running!"
        echo "=================================================="
        echo ""
        echo "WebSocket:  ws://127.0.0.1:8765"
        echo "HTTP:       http://127.0.0.1:8765"
        echo "PID:        $BACKEND_PID"
        echo "Log:        $LOG_FILE"
        echo ""
        echo "The Stella app will connect automatically."
        echo ""
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
err "Backend failed to start. Check $LOG_FILE"
cat "$LOG_FILE" 2>/dev/null | tail -20
exit 1
