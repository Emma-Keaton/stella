# Omissions from Final Batch — Before Official Launch

This document lists what is intentionally **not** implemented in this batch,
so the team can decide whether to add it before launch or defer to v1.1.

---

## 1. Mobile App UI (Stella Android)

### Deferred visual polish
| Item | Reason | Severity |
|------|--------|----------|
| Dark/light theme toggle | Single void-black theme ships; theming is additive | Low |
| Font-size scaling | Fixed `sp` values throughout | Low |
| Landscape optimization | Portrait-only layout | Low |
| Tablet layout | Phone-only constraints | Low |
| Rich transitions beyond fade/spinner | Basic 500ms fade enter/exit | Low |
| Chat message search / reply / edit | Append-only chat | Medium |
| Settings export/import | No config backup/restore | Low |

### Missing mobile features
| Feature | Reason | Severity |
|---------|--------|----------|
| Biometric unlock (fingerprint/face) for app launch | Not wired into MainActivity | Low |
| App widget / quick settings tile | Not implemented | Low |
| Notification actions (reply from notification) | Notifications permission granted but no action handlers | Medium |
| Background fetch / periodic sync | Foreground service runs but no scheduled work | Low |
| Multi-window / split-screen support | Not tested | Low |

---

## 2. Desktop App (Stella PC)

### Deferred
| Item | Reason | Severity |
|------|--------|----------|
| System tray on Linux/macOS | Tray menu exists on Windows; other platforms TBD | Low |
| Auto-updater UI (progress, changelog) | `updater.py` exists but no user-facing update screen | Low |
| Plugin sandboxing | `PluginManager` loads plugins without isolation | Medium |
| Voice clone training UI | `voice_clone.py` exists but no training screen | Low |
| Daily briefing | Commented out in `main.py` | Low |

### Known issues
| Issue | Impact | Workaround |
|-------|--------|------------|
| `mss` missing caused test collection failures | Desktop pytest couldn't collect until `mss` installed | Install `mss` (done) |
| K2-Horizon returns empty `content` | Reasoning model writes to `reasoning_content` | **Fixed in this batch** |
| K2 chat template may need `reasoning-preserve` tuning | K2 returned empty on first try | May need `--reasoning-preserve` flag tuning |

---

## 3. stella-rea Toolkit

### Not implemented
| Item | Reason | Severity |
|------|--------|----------|
| JADX binary integration (actual APK decompilation) | Adapter written but JADX may not be installed on dev machine | Medium |
| Ghidra headless integration | Adapter written but Ghidra may not be installed | Medium |
| Frida binary integration (actual dynamic tracing) | Adapter written but Frida may not be installed | Medium |
| MCP server transport (stdio/WebSocket) | `mcp.py` written but transport not wired | Low |
| Graph visualization (canvas rendering) | `Graph` serializes to wire shape but no renderer | Low |
| Stella adapter end-to-end test | `stella_adapter.py` imports `agent/` defensively; no live test | Medium |

---

## 4. Automation & Permissions

### Not implemented
| Item | Reason | Severity |
|------|--------|----------|
| Windows desktop permissions (mic, filesystem, accessibility) | Scripts focus on Android ADB; Windows has no formal permission model | Medium |
| Automatic OEM-specific ADB command execution | Scripts print one-liners; user must run them manually | Medium |
| Permission auto-revoke prevention (Android 11+) | Doctor mode warns about it; no auto-remediation | Low |
| Termux script parity with PowerShell | SH script exists but may lag PS1 additions | Medium |

---

## 5. Dual-Architecture Runtime

### Verified working
- K2-Horizon-0.9B loads on MBZUAI fork AND upstream llama.cpp
- Qwen2.5-Coder-1.5B loads on upstream llama.cpp
- Both answer health checks

### Not yet verified end-to-end
| Item | Reason | Severity |
|------|--------|----------|
| K2-Horizon full chat through Stella's `main.py` loop | `reasoning_content` fix applied but not end-to-end tested with Stella UI | Medium |
| Automatic runtime selection per model architecture | `local_runtime.py` resolves binaries; `server.py` picks per architecture | Low |
| Model download from HuggingFace | `LocalEngineManager.ModelCatalog` exists but download flow untested | Medium |

---

## 6. Not Done (Explicitly Deferred)

Per user instruction: **no commit or push** until the complete diff is reviewed and approved.

| Item | Status |
|------|--------|
| `git commit` | Deferred — awaiting user review |
| `git push` | Deferred — awaiting user review |
| ADB device test (phone plugged in) | No device connected during this batch |
| `:app:assembleStaging` rebuild after K2 edits | Build succeeded before edits; APK exists (126 MB) |

---

## Recommended Launch Blockers (must fix before launch)

1. **End-to-end K2 chat test** — Verify Stella's `main.py` local brain path gets a non-empty reply from K2-Horizon through `reasoning_content`
2. **Android APK install on physical device** — Plug in phone, run ADB install + launch, verify chat works
3. **Permission doctor run** — Verify `grant_stella_permissions.ps1 -Doctor` works on a real device
4. **Diff review** — User reviews all 28 changed files before commit

---

## Recommended Post-Launch (v1.1)

1. Theme toggle + font scaling on mobile
2. Chat search/reply/edit
3. JADX/Ghidra/Frida actual binary integration (when tools are installed)
4. Plugin sandboxing
5. Auto-updater UI