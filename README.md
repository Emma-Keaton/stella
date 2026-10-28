# ⚡ Stella AI — Personal AI Assistant

<div align="center">

<img src="assets/stella_logo.png" alt="Stella AI Logo" width="220" />

### *Modular, Self-Evolving AI Assistant with Electron Desktop + Android Companion*

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white)](https://python.org)
[![Electron](https://img.shields.io/badge/GUI-Electron%20%2B%20SolidJS-black?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![WebSocket](https://img.shields.io/badge/IPC-WebSocket%20IPC-blue?logo=websockets&logoColor=white)](https://websockets.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://python.org)
[![Android](https://img.shields.io/badge/Android-Kotlin%20%2B%20Compose-72C534?logo=android&logoColor=white)](https://developer.android.com/)

</div>

---

## 🌌 Overview

**Stella AI** is a modular, self-evolving personal AI assistant. It runs a Python backend with an Electron + SolidJS desktop frontend and a Kotlin/Compose Android companion. Users choose their LLM provider during onboarding (Gemini Live, OpenAI-compatible, Anthropic, OpenRouter, Groq, Ollama, LM Studio, or custom). Stella includes built-in actions, drop-in plugins, packaged skills, and a Dr. Zero-inspired self-evolution system that trains and improves without training data dumps.

---

## 🏗️ Architecture

```
Stella/
├── main.py                     # Python backend entry point (WebSocket IPC server)
├── requirements.txt            # Python dependencies
├── bootstrap.py                # Cross-platform tiered installer (moved to scripts/)
├── setup.py                    # Dependency installer (moved to scripts/)
├── stella_redesign.md          # Full redesign plan
├── LICENSE
├── README.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── SECURITY.md
├── TRADEMARK.md
│
├── apps/                       # Deployable applications
│   ├── desktop/                # Electron + SolidJS desktop app
│   │   ├── src/main/           # Electron main process (lifecycle, IPC)
│   │   ├── src/preload/        # Typed bridge: window.stella API
│   │   └── src/renderer/       # SolidJS UI components
│   ├── dashboard/              # FastAPI web dashboard
│   └── stella-connect/         # Device pairing gateway service
│
├── packages/                   # Shared libraries
│   ├── contracts/              # IPC/wire protocol types (TS + Python)
│   ├── ui/                     # Shared design tokens, theme
│   ├── logging/                # Audit logging
│   └── brand/                  # Logos, avatars
│
├── src/                        # Python backend core
│   ├── backend/
│   │   ├── agent/              # Agentic runtime (loop, planner, executor, tools)
│   │   │   ├── loop.py         # Think→act→observe→verify loop
│   │   │   ├── planner.py      # Task planner (JSON tool steps)
│   │   │   ├── executor.py     # AgentExecutor (all layers dispatch)
│   │   │   ├── tools.py        # Tool dataclass, Registry, built-in tools
│   │   │   ├── skill_loader.py # Loads skills from skills/
│   │   │   ├── integration.py  # Bridge UI/voice → agent loop
│   │   │   └── evolution/      # Dr. Zero self-evolution (NEW)
│   │   │       ├── proposer.py     # Generates diverse questions
│   │   │       ├── solver.py       # Attempts questions using agent tools
│   │   │       ├── curriculum.py   # Automated difficulty curriculum
│   │   │       ├── hrpo.py         # Hop-grouped relative policy optimization
│   │   │       └── engine.py       # Evolution loop orchestrator
│   │   ├── core/               # Core engine services
│   │   │   ├── engine.py       # Stella engine main loop (single emit() touchpoint)
│   │   │   ├── action_loader.py   # Auto-discovers actions/ TOOL dicts
│   │   │   ├── plugin_loader.py   # Auto-discovers plugins/ PLUGIN dicts
│   │   │   ├── server.py          # llama.cpp server manager
│   │   │   ├── llm_router.py      # LLM provider routing
│   │   │   ├── memory_manager.py  # Core memory manager
│   │   │   ├── providers/         # LLM provider abstraction
│   │   │   │   ├── base.py        # Provider contracts
│   │   │   │   ├── registry.py    # Provider discovery + build cache
│   │   │   │   ├── schema.py      # Tool declaration translation + budget
│   │   │   │   ├── adapters.py    # Wire format adapters
│   │   │   │   ├── keys.py        # API key resolution
│   │   │   │   ├── catalogue.py   # Service credential catalogue
│   │   │   │   ├── llm_client.py  # Legacy LLM client (moved)
│   │   │   │   ├── groq_client.py # Legacy Groq client (moved)
│   │   │   │   └── or_client.py   # Legacy OpenRouter client (moved)
│   │   │   ├── mcp/, net/, media/, astro/, radio/, security/
│   │   └── memory/             # Memory layer
│   │       ├── config_manager.py  # api_keys.json single source of truth
│   │       └── memory_manager.py  # Long-term memory store
│   │       └── workspace_store.py # Workspace/conversation store (moved)
│   ├── main/                   # Python app lifecycle
│   └── preload/                # Python-side bridge
│
├── actions/                    # Built-in core skills (TOOL dict pattern)
│   ├── weather_report.py       # Each file: module-level TOOL dict + handler
│   ├── web_search.py
│   ├── file_controller.py
│   ├── computer_control.py
│   ├── ... (~50 actions preserved)
│   └── spotify_mcp_server/     # TypeScript MCP server
│
├── plugins/                    # Drop-in user plugins (PLUGIN dict pattern)
│   ├── __init__.py
│   └── _template.py            # Drop-in plugin template
│
├── skills/                     # Packaged shareable skills (SKILL.md + skill.py)
│   ├── <skill-slug>/           # One folder per skill
│   │   ├── SKILL.md            # YAML frontmatter: name, description, category, source
│   │   ├── skill.py            # execute(**kwargs)
│   │   └── assets/             # Skill-specific assets
│   ├── skills-lock.json        # Lockfile: skill file hashes + versions
│   └── skills-disabled/        # Disabled skills staging area
│
├── features/                   # Existing feature skills preserved (skill.py + manifest.json)
│   └── <feature-slug>/
│       ├── skill.py
│       ├── manifest.json
│       └── test_cases.json (optional)
│
├── config/                     # Configuration (api_keys.json single source of truth)
│   ├── api_keys.json           # ALL config: provider keys, plugin enablement, voice, etc.
│   ├── identity.json
│   ├── providers.json          # Provider capability definitions (shared with Android)
│   ├── tool_policy.json
│   └── certs/
│
├── memory/                     # Memory storage (JSON/JSONL)
├── models/                     # GGUF model files (user-managed, NOT bundled)
│   └── .gitkeep                # Download via download hub, not committed
│
├── assets/                     # Static assets (images, sounds, fonts, web_background)
├── stella-connect-android/     # Kotlin/Compose Android companion (unchanged)
├── tests/                      # Test suite
├── scripts/                    # Build, update, model manager, dependency sync
├── docs/                       # Documentation
├── build/, dist/, installer/, evals/, vendor/
```

---

## 🎯 Skill Layers (Three Tiers)

Stella organizes capabilities into three layers, inspired by Mark-LVI and OpenBot:

| Layer | Location | Pattern | Purpose |
|---|---|---|---|
| **Actions** | `actions/` | Module-level `TOOL` dict | Built-in core capabilities (~50 preserved) |
| **Plugins** | `plugins/` | Module-level `PLUGIN` dict + `run()` | Drop-in user extensions (opt-out enablement) |
| **Skills** | `skills/` | `SKILL.md` + `skill.py` + `skills-lock.json` | Packaged, versioned, shareable skills |

**Writing skill** (`skills/writing/`) — Comprehensive writing assistant with operations:
- `document` — Structured documents (title, sections, conclusion)
- `email` — Professional/casual emails
- `report` — Findings reports with recommendations
- `letter` — Formal/personal letters
- `note` — Short notes/memos with tags and priority
- `summary` — Extractive text summarization
- `rewrite` — Tone/style rewriting
- `proofread` — Grammar, spelling, clarity checking

Example: `{"operation": "email", "to": "team@example.com", "subject": "Deadline", "body": "...", "tone": "professional"}`

---

## 🧠 Self-Evolution (Dr. Zero)

Stella includes a Dr. Zero-inspired self-evolution system that trains and improves without training data:

- **Proposer** — Generates diverse, challenging-yet-solvable questions from domain templates
- **Solver** — Stella's own agent attempts each question using available tools
- **Curriculum** — Automated difficulty adjustment based on solver success rate
- **HRPO** — Hop-Grouped Relative Policy Optimization for efficient evaluation

The engine runs in the background: `propose → solve → evaluate → adjust difficulty → repeat`. Zero training data required.

---

## 🔌 Provider Selection

Users choose their LLM provider during onboarding. The choice is stored in `config/api_keys.json`:

- **Gemini Live** (default) — Native audio conversation
- **OpenAI-compatible** — Any `/v1/chat/completions` endpoint
- **Anthropic** — Claude models
- **OpenRouter** — Multiple models via one key
- **Groq** — Fast inference
- **Ollama / LM Studio** — Local models
- **Custom** — User-defined endpoint

K2 models are **not bundled**. If you want K2 Horizon or other K2 models, download them yourself via the download hub in Settings.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ 
- Node.js 18+ (for Electron desktop)
- A Google Gemini API key (or another provider key)

### Backend (Python)

```powershell
# Clone the repository
git clone https://github.com/Emma-Keaton/stella.git
cd stella

# Create and activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the backend
python main.py
```

The backend starts a WebSocket IPC server on `ws://127.0.0.1:8765`.

### Desktop (Electron + SolidJS)

```powershell
cd apps/desktop
npm install
npm run dev
```

The Electron app connects to the Python backend via WebSocket.

### Android (Kotlin/Compose)

Open `stella-connect-android/` in Android Studio and build. The app connects to the same WebSocket backend using the StellaProtocol wire format.

---

## 📱 Android Companion (Stella Connect)

The Android app at `stella-connect-android/` is built with Kotlin + Jetpack Compose. It connects to the Python backend via WebSocket using `StellaProtocol` envelopes (`type`, `request_id`, `timestamp`, `payload`). Features:

- Chat with Stella from your phone
- Provider configuration synced from `config/providers.json`
- Encrypted API key storage (Android Keystore)
- Device pairing and command execution
- HUD overlay and widgets

---

## 📄 License

**Personal & Private Local Use Only — No Distribution.**

This project is licensed under the **Stella AI Source-Available Personal Use License**.

- ✅ **Allowed:** Download, clone, inspect, build, and run locally on your own device for personal, educational, and research use.
- 🚫 **No Distribution:** Do not distribute, redistribute, re-upload, mirror, share, transmit, sublicense, or publish this software anywhere.
- 🚫 **No Commercial Use:** Do not sell, rent, monetize, bundle, or host as a paid SaaS/cloud service.

See [LICENSE](LICENSE) for full terms.

---

<div align="center">
<b>Stella AI</b> • Modular • Self-Evolving • Private
</div>
