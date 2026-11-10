#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Stella Termux Setup Script
# Installs Python + all dependencies for running the Stella backend on Android
# Handles failed downloads gracefully. Bundles both mbuzai and upstream llama.cpp servers.
# API keys are configured via the Stella Settings page (Providers section) at runtime.
# Run once inside Termux:
#   curl -sSL https://raw.githubusercontent.com/Emma-Keaton/stella/master/termux/setup_stella.sh | bash
# =============================================================================
set -u

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[Stella]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERR]${NC} $1"; }

echo "=================================================="
echo "  Stella Android Termux Setup"
echo "=================================================="
echo ""

log "Updating Termux packages..."
pkg update -y || warn "pkg update had issues (may be offline)"
pkg upgrade -y || warn "pkg upgrade had issues"

log "Installing core packages..."
pkg install -y python git curl wget openssl clang make llvm termux-tools || {
    err "Failed to install core packages. Check your internet connection."
    exit 1
}

log "Installing Python packages..."
pip install --upgrade pip || warn "pip upgrade failed"
pip install \
    websockets==13.0 \
    google-genai==3.0.0 \
    fastapi==0.104.0 \
    uvicorn==0.24.0 \
    python-multipart \
    pydantic==2.5.0 \
    requests \
    pillow \
    python-dateutil \
    pyyaml \
    aiohttp || {
    err "Some pip packages failed to install. Backend may have limited functionality."
}

log "Installing llama-cpp-python (ARM64 native)..."
CMAKE_ARGS='-DLLAMA_NATIVE=off' pip install llama-cpp-python==0.2.77 --no-binary llama-cpp-python || {
    warn "llama-cpp-python native build failed. Local model inference will be unavailable."
    warn "You can still use cloud providers (Gemini, NVIDIA, etc.)"
}

log "Setting up storage directories..."
termux-setup-storage 2>/dev/null || warn "termux-setup-storage failed (may already be done)"
mkdir -p ~/stella/models
mkdir -p ~/stella/config
mkdir -p ~/stella/logs
mkdir -p ~/stella/llama_servers/mbuzai
mkdir -p ~/stella/llama_servers/upstream
mkdir -p ~/stella/backend

log "Downloading llama.cpp server binaries..."

download_with_retry() {
    local url="$1"
    local out="$2"
    local name="$3"
    local max_retries=3
    local attempt=1

    while [ $attempt -le $max_retries ]; do
        if curl -sSL --connect-timeout 15 --max-time 120 -o "$out" "$url" 2>/dev/null; then
            if [ -s "$out" ]; then
                log "Downloaded $name"
                return 0
            fi
        fi
        warn "Download attempt $attempt/$max_retries failed for $name"
        attempt=$((attempt + 1))
        sleep 2
    done

    err "Failed to download $name after $max_retries attempts"
    return 1
}

download_with_retry \
    "https://github.com/mbuzai/llama.cpp/releases/download/llama-b11612-bin/llama-b11612-bin-android-aarch64.zip" \
    ~/stella/llama_servers/mbuzai/llama-server.zip \
    "mbuzai llama.cpp server" || warn "mbuzai server download failed - local models may not work"

download_with_retry \
    "https://github.com/ggerganov/llama.cpp/releases/download/server-b5423/llama-b5423-bin-android-aarch64.zip" \
    ~/stella/llama_servers/upstream/llama-server.zip \
    "upstream llama.cpp server" || warn "upstream server download failed - local models may not work"

for server_dir in mbuzai upstream; do
    if [ -f ~/stella/llama_servers/$server_dir/llama-server.zip ]; then
        log "Extracting $server_dir server..."
        unzip -o ~/stella/llama_servers/$server_dir/llama-server.zip -d ~/stella/llama_servers/$server_dir/ 2>/dev/null || \
            warn "Failed to extract $server_dir server"
        chmod +x ~/stella/llama_servers/$server_dir/llama-server 2>/dev/null || \
            warn "Failed to make $server_dir server executable"
    fi
done

# Auto-copy backend files from shared storage if Stella APK placed them there
if [ -d /sdcard/stella/backend ] || [ -f /sdcard/stella/main.py ]; then
    log "Copying Stella backend files from shared storage (/sdcard/stella/)..."
    cp -r /sdcard/stella/main.py ~/stella/backend/ 2>/dev/null || true
    cp -r /sdcard/stella/src ~/stella/backend/ 2>/dev/null || true
    log "Backend files copied to ~/stella/backend/"
elif [ -d ~/stella/backend ] && [ -f ~/stella/backend/main.py ]; then
    log "Backend files already present in ~/stella/backend/"
else
    warn "Backend files not found in /sdcard/stella/ or ~/stella/backend/"
    warn "The Stella APK will copy backend files to /sdcard/stella/ on first launch."
    warn "Or manually copy main.py and src/ to ~/stella/backend/"
fi

log "Making scripts executable..."
chmod +x ~/stella/termux/start_stella.sh 2>/dev/null || true
chmod +x ~/stella/termux/stop_stella.sh 2>/dev/null || true
chmod +x ~/stella/termux/watcher.sh 2>/dev/null || true
chmod +x ~/stella/termux/status.sh 2>/dev/null || true

echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. GGUF models go in: ~/stella/models/"
echo "  2. Configure API keys in Stella App Settings > Providers"
echo "  3. Launch Stella APK - it auto-starts the Termux backend"
echo "  4. Or manually: ./termux/start_stella.sh"
echo ""
echo "The backend will run persistently and auto-restart on crash."
echo ""