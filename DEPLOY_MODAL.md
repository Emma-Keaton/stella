# Stella — Deployment on Modal

Run the full Stella stack (Python backend WebSocket + Next.js frontend) on Modal's cloud, expose a public HTTPS URL, and access it from any device (web, Android, desktop). Uses Modal's free monthly GPU allowance for local model inference while still allowing cloud provider API keys (Gemini, NVIDIA, OpenRouter, etc.).

## Prerequisites

1. **GitHub account** — repo at `https://github.com/Emma-Keaton/stella.git`
2. **Modal account** — sign up at https://modal.com (free tier included)
3. **Modal CLI** — `npm install -g modal` or `pip install modal`
4. **Node.js** — for building the frontend locally before deploy
5. Provider API keys (Gemini, NVIDIA, OpenRouter, OpenAI, Groq, Anthropic, etc.)

## 1. Push Local Changes to GitHub

The local `master` branch already has all commits (startup scripts, PWA, WebSocket manager, connection status pill, theme fixes). Push them:

```bash
cd /path/to/stella
git push origin master
```

If `git push` hangs, Git's credential manager may need interactive auth. Log in to GitHub in your browser or run:
```bash
git config --global credential.helper manager
git push origin master
```

## 2. Build the Frontend Static Export (for Modal)

Modal serves the frontend as static files. Build it locally so `out/` is included in the container image:

```bash
cd frontend
npm install
npm run export
```

This creates `frontend/out/index.html` and `_next/` static assets. The Next.js API routes under `frontend/app/api/` are intentionally excluded from the static export because the Modal deployment connects the frontend directly to the Python backend WebSocket at `wss://<your-modal-url>`.

## 3. Authenticate with Modal

```bash
modal token new
```

This opens a browser window to authenticate. Credentials are stored at `~/.modal.toml`.

## 4. Create Modal Secrets for API Keys

Store provider API keys as a Modal secret (never in code):

```bash
modal secret create stella-api-keys \
  GEMINI_API_KEY="AIzaSy..." \
  NVIDIA_API_KEY="nvapi-..." \
  OPENROUTER_API_KEY="sk-or-..." \
  OPENAI_API_KEY="sk-..." \
  GROQ_API_KEY="gsk_..." \
  ANTHROPIC_API_KEY="sk-ant-..." \
  GOOGLE_MAPS_API_KEY="..."
```

Add more keys later:
```bash
modal secret create stella-extra-keys \
  NEW_KEY="value"
```

Reference multiple secrets in `modal.py` via `secrets=[...]` on each `@app.function`.

## 5. Deploy to Modal

```bash
modal deploy modal.py
```

Modal builds the container image, starts the Python backend on port 8765 (WebSocket) and the frontend static server on port 3000, and assigns public HTTPS URLs like:
- `https://stella-backend-xxxx.modal.host` (WebSocket + API)
- `https://stella-frontend-xxxx.modal.host` (frontend UI)

Copy these URLs — you need them next.

## 6. Configure APP_URL and WS_URL

Update `.env` (local) or the Modal secret with your public URLs:

```bash
modal secret create stella-api-keys \
  GEMINI_API_KEY="..." \
  ... \
  APP_URL="https://stella-frontend-xxxx.modal.host" \
  NEXT_PUBLIC_WS_URL="wss://stella-backend-xxxx.modal.host"

modal deploy modal.py
```

## 7. Access from Any Device

### Web Browser
Open `https://stella-frontend-xxxx.modal.host`. The browser connects to the backend WebSocket at `wss://stella-backend-xxxx.modal.host`.

### Android (Capacitor wrapper)
Edit `android/app/src/main/java/com/stella/android/MainActivity.java`:
```java
private static final String DEFAULT_HTTP_URL = "https://stella-frontend-xxxx.modal.host";
private static final String DEFAULT_WS_URL = "wss://stella-backend-xxxx.modal.host";
```
Rebuild: `cd android && ./gradlew assembleRelease` (requires Android SDK).

### Desktop (Tauri)
Update `frontend/src-tauri/tauri.conf.json`:
```json
"devUrl": "https://stella-frontend-xxxx.modal.host"
```
Then: `cd frontend && npx @tauri-apps/cli build`.

## 8. Free Tier — Local Model + Cloud Providers

### Local Model on Modal GPU (Free Tier)
Modal's free tier includes GPU time (typically 1 T4 GPU-hour/day). Uncomment the `run_local_model` function in `modal.py`:

```python
@app.function(
    image=modal.Image.debian_slim().pip_install("llama-cpp-python"),
    gpu="t4",
    timeout=3600,
)
def run_local_model(prompt: str) -> str:
    from llama_cpp import Llama
    llm = Llama(model_path="/root/stella/models/model.gguf", n_gpu_layers=1)
    return llm(prompt)["choices"][0]["text"]
```

Upload your GGUF model:
```bash
modal volume put stella-models ./models/your-model.gguf /your-model.gguf
```
Update `model_path` in `modal.py` and redeploy.

### Cloud Providers (Simultaneous)
Use cloud providers at the same time as the local model. The frontend's `SettingsModal` lets you select any provider:

| Provider | Env Var | Free Tier? |
|----------|---------|------------|
| Gemini | `GEMINI_API_KEY` | Yes |
| NVIDIA NIM | `NVIDIA_API_KEY` | Yes (free credits) |
| OpenRouter | `OPENROUTER_API_KEY` | Yes (some free models) |
| OpenAI | `OPENAI_API_KEY` | Trial |
| Groq | `GROQ_API_KEY` | Yes |
| Anthropic | `ANTHROPIC_API_KEY` | Trial |

Add all keys to the `stella-api-keys` Modal secret. The frontend Settings UI lets users switch providers per-conversation.

## 9. Managing the Deployment

```bash
modal app logs stella-backend     # View logs
modal shell stella-backend        # Shell into container
modal secret list                 # List secrets
modal deploy modal.py             # Redeploy after changes
modal app delete stella-backend   # Delete the app
```

## 10. Architecture

```
Modal Cloud
├─ Frontend (3000)  → Next.js static → https://stella-frontend-xxxx.modal.host
└─ Backend (8765)   → Python main.py  → wss://stella-backend-xxxx.modal.host
                        │
              ┌─────────┼─────────┐
            Web     Android   Desktop
          Browser   (Capacitor) (Tauri)
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `frontend/out/` not found | Run `npm run export` in `frontend/` before deploy |
| WebSocket connection refused | Use `wss://` in `NEXT_PUBLIC_WS_URL` matching backend URL |
| CORS errors | Backend CSP in `modal.py` allows `*` — adjust if needed |
| Modal GPU out of memory | Use smaller GGUF model or reduce `n_gpu_layers` |
| API key not working | Verify key is in `stella-api-keys` secret and redeploy |
