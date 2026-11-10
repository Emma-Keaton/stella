#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Stella Termux Watcher
# Monitors the backend and auto-restarts on crash for persistent uptime.
# Run this in a separate Termux session or background it:
#   nohup ./termux/watcher.sh &
# =============================================================================
set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[Watcher]${NC} $1"; }
warn() { echo -e "${YELLOW}[Watcher]${NC} $1"; }
err() { echo -e "${RED}[Watcher]${NC} $1"; }

STELLA_DIR=~/stella
PID_FILE="$STELLA_DIR/logs/backend.pid"
LOG_FILE="$STELLA_DIR/logs/backend.log"
WATCHER_LOG="$STELLA_DIR/logs/watcher.log"

CHECK_INTERVAL=10  # seconds

mkdir -p "$STELLA_DIR/logs"

log "Watcher started. Checking backend every ${CHECK_INTERVAL}s..."
log "PID file: $PID_FILE"
log "Log file: $LOG_FILE"

while true; do
    BACKEND_ALIVE=false

    # Check if backend process is running
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            # Verify the process is actually main.py
            if ps -p "$PID" -o comm= 2>/dev/null | grep -q python; then
                BACKEND_ALIVE=true
            fi
        fi
    fi

    # Also check by port
    if [ "$BACKEND_ALIVE" = false ]; then
        if curl -s http://127.0.0.1:8765/ > /dev/null 2>&1; then
            BACKEND_ALIVE=true
            # Update PID file with the actual python process
            NEW_PID=$(pgrep -f "main.py" | head -1)
            if [ -n "$NEW_PID" ]; then
                echo "$NEW_PID" > "$PID_FILE"
            fi
        fi
    fi

    if [ "$BACKEND_ALIVE" = true ]; then
        # Backend is healthy, just log occasionally
        echo "$(date '+%Y-%m-%d %H:%M:%S') Backend healthy (PID: $(cat "$PID_FILE" 2>/dev/null))" >> "$WATCHER_LOG"
    else
        err "Backend is down! Attempting restart..."
        echo "$(date '+%Y-%m-%d %H:%M:%S') Backend down, restarting..." >> "$WATCHER_LOG"

        # Clean up stale PID
        rm -f "$PID_FILE"

        # Restart the backend
        cd "$STELLA_DIR"
        nohup python main.py --host 0.0.0.0 --port 8765 > "$LOG_FILE" 2>&1 &
        NEW_PID=$!
        echo "$NEW_PID" > "$PID_FILE"

        # Wait for it to come up
        STARTED=false
        for i in $(seq 1 15); do
            sleep 2
            if curl -s http://127.0.0.1:8765/ > /dev/null 2>&1; then
                log "Backend restarted successfully (PID: $NEW_PID)"
                echo "$(date '+%Y-%m-%d %H:%M:%S') Backend restarted (PID: $NEW_PID)" >> "$WATCHER_LOG"
                STARTED=true
                break
            fi
        done

        if [ "$STARTED" = false ]; then
            err "Failed to restart backend. Will retry in ${CHECK_INTERVAL}s..."
            echo "$(date '+%Y-%m-%d %H:%M:%S') Restart failed, will retry" >> "$WATCHER_LOG"
        fi
    fi

    sleep $CHECK_INTERVAL
done
