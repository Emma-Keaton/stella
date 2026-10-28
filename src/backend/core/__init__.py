# src/backend/core — Core backend engine services (index)
# engine.py          — Stella engine main loop (replaces PyQt6 coupling)
# action_loader.py   — Auto-discovers actions/ TOOL dicts
# plugin_loader.py   — Auto-discovers plugins/ PLUGIN dicts
# server.py          — llama.cpp server manager
# llm_router.py      — LLM provider routing
# memory_manager.py  — Core memory manager
# stt.py / tts.py    — Speech-to-text / Text-to-speech
# wake_word.py       — Wake word detection
# confirm.py         — User confirmation dialogs
# echo.py            — Echo guard
# hotkey.py          — Push-to-talk hotkey
# identity.py        — User/assistant identity
# sensorium.py       — Situational awareness telemetry
# session.py         — Session management
# workspace_service.py — Workspace service
# providers/         — LLM provider abstraction (base, registry, schema, adapters, keys, catalogue)
# mcp/               — MCP server/client/marketplace
# net/               — Networking (http, pcap, apk)
# media/             — Media (player, volume, radiobrowser, iptv)
# astro/             — Astronomy (sgp4, passes)
# radio/             — Radio (adsb)
# security/          — Security tools (handshake, hashcat, wireless, tools)
