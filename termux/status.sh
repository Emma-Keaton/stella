#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Stella Termux Status
# Checks if the backend is running and shows connection info
# =============================================================================
set -u

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

STELLA_DIR=~/stella
PID_FILE="$STELLA_DIR/logs/backend.pid"
LOG_FILE="$STELLA_DIR/logs/backend.log"

echo "=================================================="
echo "  Stella Backend Status"
echo "=================================================="
echo ""

# Check PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo -e "Backend: ${GREEN}RUNNING${NC} (PID: $PID)"
    else
        echo -e "Backend: ${RED}STOPPED${NC} (stale PID file)"
        rm -f "$PID_FILE"
    fi
else
    echo -e "Backend: ${RED}STOPPED${NC} (no PID file)"
fi

# Check WebSocket port
echo -n "WebSocket (ws://127.0.0.1:8765): "
if curl -s http://127.0.0.1:8765/ > /dev/null 2>&1; then
    echo -e "${GREEN}RESPONDING${NC}"
else
    echo -e "${RED}NOT RESPONDING${NC}"
fi

# Check HTTP port
echo -n "HTTP (http://127.0.0.1:8765): "
if curl -s http://127.0.0.1:8765 > /dev/null 2>&1; then
    echo -e "${GREEN}RESPONDING${NC}"
else
    echo -e "${RED}NOT RESPONDING${NC}"
fi

# Show recent log
echo ""
echo "Recent log (last 10 lines):"
if [ -f "$LOG_FILE" ]; then
    tail -10 "$LOG_FILE"
else
    echo "  (no log file yet)"
fi

echo ""
echo "=================================================="
