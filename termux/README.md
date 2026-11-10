# Stella Android Termux Integration

Run the full Stella backend (Python + WebSocket + llama.cpp servers) directly on your Android device via Termux. The Stella app's WebView connects to ws://127.0.0.1:8765 locally — no external server, no Modal, no cloud required.

## What This Provides

| Component | Purpose |
|-----------|---------|
| setup_stella.sh | One-time install of Python + all dependencies on Termux |
| start_stella.sh | Starts the backend persistently (WebSocket on port 8765) |
| stop_stella.sh | Stops backend and watcher |
| status.sh | Check if backend is running |
| watcher.sh | Auto-restarts backend on crash (persistent uptime) |

## Installation

### Step 1: Install Termux

Install Termux from F-Droid (recommended) or Google Play.

### Step 2: Run Setup

Open Termux and run:

`ash
curl -sSL https://raw.githubusercontent.com/Emma-Keaton/stella/master/termux/setup_stella.sh | bash
`

This installs Python 3, pip, all backend dependencies, llama-cpp-python (ARM64), and both mbuzai + upstream llama.cpp server binaries. Storage directories are created at ~/stella/models/, ~/stella/config/, ~/stella/logs/.

### Step 3: Copy Backend Files

Copy main.py and src/ from the repo to your device, then in Termux:

`ash
cp /sdcard/stella/main.py ~/stella/
cp -r /sdcard/stella/src ~/stella/
`

### Step 4: Copy GGUF Models (Optional)

`ash
cp /sdcard/stella/models/*.gguf ~/stella/models/
`

### Step 5: Start the Backend

`ash
cd ~/stella
chmod +x termux/start_stella.sh
./termux/start_stella.sh
`

### Step 6: Launch the Stella App

Open the Stella Android app. It auto-launches the Termux backend and connects to ws://127.0.0.1:8765.

## Managing the Backend

`ash
./termux/status.sh      # Check status
./termux/start_stella.sh # Start backend
./termux/stop_stella.sh  # Stop backend
nohup ./termux/watcher.sh &  # Auto-restart on crash
`

## API Keys

Configure in Stella App Settings > Providers. Keys stored in ~/stella/config/api_keys.json.

## Local Models

Place GGUF models in ~/stella/models/. Supports K2-Horizon-0.9B, Qwen2.5-Coder-1.5B, and other GGUF models via llama-cpp-python (ARM64).

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend wont start | Check ~/stella/logs/backend.log |
| WebSocket not responding | Run ./termux/status.sh |
| llama-cpp-python build fails | Use cloud providers instead |
| Termux intent not launching | Start backend manually via start_stella.sh |

## Requirements

- Android 5.0+ (API 24+)
- Termux app installed
- ~200MB free storage for Python + packages
- ~500MB+ for GGUF models (optional)
- Internet for initial setup
