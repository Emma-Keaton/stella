# Stella Zero-Friction AI Assistant Widget – Cross-Platform Design

## 1. Component Hierarchy

### Desktop Dock / Floating Overlay
```
DockRoot
├─ TopBar
│  ├─ AgentStateIndicator [Idle|Listening|Processing|Muted]
│  ├─ ThemeBadge
│  └─ SettingsGear
├─ InputHub
│  ├─ VoiceStreamingMic
│  ├─ QuickTextField [persistent focus]
│  ├─ VisionCapture
│  │  ├─ ScreenMarquee
│  │  └─ DragDropZone
│  └─ VoiceMemoRecorder
├─ GlanceablePanel
│  ├─ ProgressTracker [task + %]
│  ├─ ContextEventCard [next event + prep notes]
│  └─ MicroBadges [insights, actions]
├─ AutomationStrip
│  ├─ ClipboardSummarize
│  ├─ AtomicLoggers [$ ✓ 💡 💧]
│  ├─ ReadAloud
│  └─ RoutineMacro
└─ SystemControls
   ├─ PrivacyMuteKillSwitch
   └─ RecentThreadsSwitcher [3-5]
```

### Mobile Widget 2x2
```
Widget2x2Root
├─ HeaderRow
│  ├─ AgentStateDot
│  └─ PrivacyToggle
├─ PrimaryInput
│  ├─ MicButton 44pt
│  └─ TextChip [tap to keyboard]
├─ GlanceRow
│  ├─ ProgressDot
│  └─ BadgeCount
└─ QuickActions [4 icons]
```

### Mobile Widget 4x2
```
Widget4x2Root
├─ TopBar [State + Settings]
├─ InputHubRow
│  ├─ Mic
│  ├─ Text
│  ├─ CameraLens
│  └─ Memo
├─ GlancePanel
│  ├─ ProgressBar
│  └─ ContextCard
├─ AutomationGrid [2x2]
│  ├─ Clipboard
│  ├─ $ Logger
│  ├─ ✓ Logger
│  ├─ 💡 Logger
└─ SystemRow
   ├─ MuteKill
   └─ RecentThreads
```

## 2. State Machine & Visual Treatment

**Idle**
- Orb static, soft glow Cyan 20%
- Background Void #0C0D14, surface glass #12141F
- Mic icon outline, text muted

**Listening**
- Orb pulse ring, Cyan #00F0FF 100% opacity, 120bpm
- Mic icon filled, “Listening…” label
- Haptic light feedback mobile

**Processing**
- Orb rotating, accent Primary #00E5A3
- Progress bar visible, “Processing… 65%”
- Disables input hub, shows cancel

**Privacy-Muted**
- Orb grayscale, red strike
- All mic/camera inputs disabled
- Banner “Privacy on – no audio/camera”

Transitions use 180ms ease-out, no jank.

## 3. Micro-Interaction Flows

### Clipboard Summarization
1. Tap Clipboard icon
2. Widget reads clipboard via platform API
3. Show inline preview “Summarizing 342 chars…”
4. Agent returns summary, widget shows 2-line preview + “Open in chat”
5. Success haptic + micro-badge increment

No app open. Failure shows friendly toast “Couldn’t read clipboard. Check app permissions”.

### Quick Logging
1. Tap $ / ✓ / 💡 / 💧
2. Quick inline field slides up with template
3. Type 1-3 words, auto-submit on Enter/Dismiss
4. Log saved, badge updates, widget returns to idle
5. Error: “Log saved locally. Will sync when online.”

## 4. Platform Adaptations

**Desktop**
- Pinned overlay / tray dock, persistent keyboard
- Hover micro-interactions, tooltips
- Screen marquee via native snip API, drag-drop file ingestion

**Mobile**
- 44pt+ tap targets
- Text chip launches native keyboard
- Camera lens integration, sensor context
- Grid sizes 2x2 minimal, 4x2 full

## 5. Cloud Provider Key Validation

During AI & SPEED → Cloud Models configuration:
1. User enters API key
2. On blur, run `TestKey()` → ping `/models` endpoint
3. Pull active model list, filter by `can_run` + not overloaded
4. UI shows ✅ Valid key, model dropdown populated with verified models
5. Invalid key → friendly error: “This key isn’t working. Check your provider dashboard and paste again.”
6. Model unavailable → “This model is overloaded right now. Try another from the list.”

Validation prevents runtime errors in chat.

## 6. Friendly Error Translation & Issue Routing

All device logs pass through `UserFriendlyErrorMapper`:
- Technical → Human: “Engine crashed with OOM” → “Stella ran out of memory loading the model. Try a smaller model or free up RAM.”
- Each error surfaces “Report to Stella” button
- Report bundles: app version, OS, theme, last action, sanitized log
- Routes to Stella repo issue template with tags `user-reported`

Goal: catch failure at config time, explain in plain language, feed back to creators for global fix.

## 7. Implementation Notes

- Widget config persisted in DataStore: size, theme, enabled elements
- Desktop overlay via Electron composable window with always-on-top flag
- Mobile widgets via GlanceAppWidget with config activity
- Shared state via `AgentStateStore` + `VoiceBridge`
- Theme system: Void, OLED, Aurora, Light – applied to widget and main app
