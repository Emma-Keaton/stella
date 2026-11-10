"""
Stella — Modal Deployment

Deploys the full Stella stack on Modal:
  1. Python backend (main.py) — WebSocket IPC on port 8765
  2. Next.js frontend — served as static files on port 3000 (or via Modal web server)

Usage:
    modal deploy modal.py          # Deploy to Modal cloud
    modal run modal.py::stella.run_locally  # Test locally with Modal

Environment variables (set via `modal secret create`):
  - GEMINI_API_KEY, NVIDIA_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY, etc.
  - APP_URL (public Modal URL, set after first deploy)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import modal

# ── Paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = REPO_ROOT / "frontend"
OUT_DIR = FRONTEND_DIR / "out"  # Next.js static export output

# ── Modal image ────────────────────────────────────────────────────────────
# Python backend dependencies
stella_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "curl", "build-essential")
    .run_commands(
        "pip install --upgrade pip",
    )
    .pip_install(
        "websockets>=12.0",
        "google-genai>=3.0.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "python-multipart",
        "pydantic>=2.0",
        "requests",
        "pillow",
        "python-dateutil",
        "pyyaml",
        "aiohttp",
    )
    # Copy the whole repo so main.py and src/ are available
    .add_local_dir(REPO_ROOT, remote="/root/stella")
    .workdir("/root/stella")
)

# ── Modal App ──────────────────────────────────────────────────────────────
app = modal.App("stella-backend")


@app.function(
    image=stella_image,
    ports=[8765, 3000],
    secrets=[modal.Secret.from_name("stella-api-keys")],  # create via modal CLI
    timeout=3600,
    keep_warm=1,
)
@modal.web_server(8765, startup_timeout=120)
def backend():
    """
    Runs the Stella Python backend WebSocket server on port 8765.
    Modal's @web_server exposes this port as a public HTTPS WebSocket endpoint.
    """
    os.chdir("/root/stella")
    os.environ["PYTHONPATH"] = "/root/stella"
    # Allow connections from any origin (Modal URL + localhost)
    os.environ.setdefault("STELLA_HOST", "0.0.0.0")
    os.environ.setdefault("STELLA_PORT", "8765")

    # Launch main.py as a subprocess; Modal web_server keeps it alive
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        env=os.environ,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Stream logs to Modal console
    assert proc.stdout
    for line in proc.stdout:
        print(line, end="")


@app.function(
    image=stella_image,
    ports=[3000],
    timeout=3600,
    keep_warm=1,
)
@modal.web_server(3000, startup_timeout=120)
def frontend():
    """
    Serves the pre-built Next.js frontend static files on port 3000.
    Requires `npm run export` to have been run locally (produces frontend/out/).
    """
    os.chdir("/root/stella/frontend")
    os.environ["NODE_ENV"] = "production"

    # Serve static files with a simple Python HTTP server (no Node needed on Modal)
    # The out/ directory must be present in the image (copied via add_local_dir).
    if not OUT_DIR.exists():
        print(
            "ERROR: frontend/out/ not found. Run `npm run export` locally before deploying.",
            file=sys.stderr,
        )
        sys.exit(1)

    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", "3000", "--directory", str(OUT_DIR)],
        env=os.environ,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    assert proc.stdout
    for line in proc.stdout:
        print(line, end="")


@app.local_entrypoint()
def run_locally():
    """Convenience entrypoint for `modal run modal.py` — prints info only."""
    print("Stella Modal deployment ready.")
    print("Run: modal deploy modal.py")
    print("Then set APP_URL to your Modal app URL and reconnect clients.")


# ── Local model (free tier GPU) ────────────────────────────────────────────
# If you want to run a local GGUF model on Modal's free GPU tier, uncomment
# and configure the GPU-backed function below. Requires llama.cpp Python bindings.
#
# @app.function(
#     image=modal.Image.debian_slim().pip_install("llama-cpp-python"),
#     gpu="t4",  # free tier: 1 T4 GPU
#     timeout=3600,
# )
# def run_local_model(prompt: str) -> str:
#     from llama_cpp import Llama
#     llm = Llama(model_path="/root/stella/models/model.gguf", n_gpu_layers=1)
#     return llm(prompt)["choices"][0]["text"]
