# Stella Mobile — Simplified Redesign

This redesign strips away the cockpit clutter and technical jargon. It models the calm, effortless minimalism of **Gemini, ChatGPT, and Siri**, while preserving Stella’s futuristic sci-fi identity through **Orbitron**, **Exo 2**, soft neon glows, and the holographic background.

---

## 1. Visual Language: Calm Sci-Fi

Instead of dense telemetry dials and developer jargon, the interface uses **breathing room, soft frosted glass, and clear, human language**.

```
┌──────────────────────────────────────────────────────────────┐
│  FONTS                                                       │
│  • Headlines & Brand:  Orbitron (Bold / Medium)              │
│  • Conversation & UI:  Exo 2 (Regular / Medium / SemiBold)   │
│                                                              │
│  PALETTE                                                     │
│  • Background: Deep Void (`#0C0D14`) + Holographic WebView   │
│  • Cards: Soft Smoked Glass (`Color.Black.copy(alpha = 0.5)`)│
│  • Glow / Accent: Soft Cyan (`#00F0FF`) & Warm White         │
│  • Border: Subtle hairline outline (`Cyan.copy(alpha = 0.15)`)│
└──────────────────────────────────────────────────────────────┘
```

### Friendly Vocabulary (No Developer Jargon)

| Old / Overcomplicated Copy | New Friendly Copy |
|---|---|
| `34.2 tok/s • Vulkan Backend • Q4_K_M` | **Fast • Running on this phone** |
| `Synapse PC Bridge • Host: 192.168.1.5` | **Connected to your PC** |
| `Capability Radar Matrix (AppOps)` | **Permissions & Setup** |
| `Context window 1840/4096 tokens` | *(Hidden — managed automatically)* |
| `Duplex Voice Engine Active` | **Listening...** |
| `Export Encrypted JSON Config` | **Backup & Restore** |

---

## 2. Navigation Architecture: 3 Core Screens (Zero Bottom Nav)

```
[ First Open ] ──► Screen 1: Welcome & Setup
                         │
                         ▼
                   Screen 2: Home (Chat + Voice) ◄──► Left Drawer (Past Chats)
                         │
                         ▼
                   Screen 3: Settings
```

All other tools (PC pairing scanner, voice mode, model selector, widgets) appear as **clean slide-up sheets or overlays** within these three screens.

---

## 3. Screen-by-Screen Walkthrough

### Screen 1: Welcome & Quick Setup (`/onboarding`)

A 3-step setup flow that takes under 30 seconds.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                         S T E L L A                          │
│                      Your AI Companion                       │
│                                                              │
│             [ Soft Holographic Core Animation ]              │
│                                                              │
│   How would you like to use Stella?                          │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │  ● On this phone                                     │   │
│   │    Private, fast, and works without internet.        │   │
│   └──────────────────────────────────────────────────────┘   │
│   ┌──────────────────────────────────────────────────────┐   │
│   │  ○ Link to my computer                               │   │
│   │    Share power and files with your desktop Stella.   │   │
│   └──────────────────────────────────────────────────────┘   │
│                                                              │
│   [ Allow Mic & Camera ] ── "So Stella can hear and see"    │
│                                                              │
│                     [ Get Started  → ]                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

1. **Step 1: Introduction:** Clean Orbitron title with the floating holographic background.
2. **Step 2: Choose Mode:** Two simple cards: **On this phone** or **Link to my computer**.
3. **Step 3: Enable Permissions:** A single friendly toggle with plain English explanations ("Allow Mic & Camera so Stella can hear your voice and read QR codes").

---

### Screen 2: Home & Chat (`/home`)

The main screen is clean and open, just like ChatGPT or Gemini.

```
┌──────────────────────────────────────────────────────────────┐
│ [≡]                    ● On this phone                   [⚙] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                                                              │
│                         S T E L L A                          │
│                    "What's on your mind?"                    │
│                                                              │
│                                                              │
│   [ Explain this photo ]          [ Help me write something ]│
│                                                              │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │ Stella                                               │   │
│   │ I've summarized your notes from today. Ready when    │   │
│   │ you are!                                             │   │
│   └──────────────────────────────────────────────────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐  │
│  │  [ + ]   Ask Stella anything...              [ 🎙 ]   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### What’s on the Screen:
* **Top Bar (Minimal):**
  * `[≡]` **History button** (opens past chats).
  * **Status pill (Center):** Shows `● On this phone` (Cyan) or `● Connected to PC` (Green). Tapping it shows a simple card: *"Everything is running smoothly."*
  * `[⚙]` **Settings button**.
* **Chat Area:**
  * Clean messages. User bubbles on the right (soft cyan glow), Stella’s replies on the left (smoked glass).
  * Long-press any message for: **Copy**, **Read Aloud**, **Edit**, or **Try Again**.
* **Bottom Floating Input Pill:**
  * `[ + ]`: Attach photo, document, or scan PC pairing code.
  * Text box: *"Ask Stella anything..."*
  * `[ 🎙 ]`: Large, soft-glowing voice button.

---

### The Left Sidebar: Chat History

Tapping `[≡]` or swiping from the left slides open a clean history panel. On tablets or foldables, this panel stays pinned on the left side with a button to hide it whenever you want full screen.

```
┌─────────────────────────────┬────────────────────────────────┐
│  CHATS                  [✕] │                                │
│                             │                                │
│  [ +  New Chat ]            │                                │
│                             │                                │
│  🔍 Search your chats...    │                                │
│                             │                                │
│  Today                      │                                │
│  • Planning the road trip   │          (Main Chat Area)      │
│  • Python script fix        │                                │
│                             │                                │
│  Yesterday                  │                                │
│  • Book recommendations     │                                │
│  • Meeting summary          │                                │
│                             │                                │
│  ─────────────────────────  │                                │
│  Model: Mistral 7B  [Change]│                                │
└─────────────────────────────┴────────────────────────────────┘
```

* **Search Bar:** Quickly find past conversations.
* **Groups:** Organized simply by *Today*, *Yesterday*, and *Previous 7 Days*.
* **Bottom Note:** Shows which model is active with a simple `[Change]` link.

---

### Screen 3: Settings (`/settings`)

Organized into clear, everyday categories instead of technical walls of text.

```
┌──────────────────────────────────────────────────────────────┐
│ ◄ Back                     Settings                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   AI & SPEED                                                 │
│   • On-device AI Model              Mistral 7B (Default)  ›  │
│   • Download New Model              Browse library        ›  │
│                                                              │
│   CONNECTIONS                                                │
│   • Link to Computer                Connected (Home PC)   ›  │
│   • Cloud Backup API                Optional key          ›  │
│                                                              │
│   APPEARANCE                                                 │
│   • Theme                           Dark Void / OLED / Light │
│   • Text Size                       Normal / Large        ›  │
│                                                              │
│   HOME SCREEN WIDGETS                                        │
│   • Customize Widgets               Choose look & buttons ›  │
│                                                              │
│   DATA & BACKUP                                              │
│   • Save Backup File                Export chats & setup  ›  │
│   • Restore Backup                  Import file           ›  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. The Out-of-App Floating HUD (When App is Closed)

When you summon Stella while using other apps (via gesture, side-button, or notification tile), a compact, non-intrusive card floats at the bottom of your screen, just like **Siri or Gemini**.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│   (Your normal phone screen: Instagram, Browser, Home, etc.) │
│                                                              │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │  ✦ Stella                         [ ☊ Voice ]  [ ✕ ] │   │
│   │                                                      │   │
│   │  "Here is what's on your screen..."                  │   │
│   │                                                      │   │
│   │  [ Summarize screen ]   [ Read aloud ]               │   │
│   ├──────────────────────────────────────────────────────┤   │
│   │  Ask a follow up...                            [ ▲ ] │   │
│   └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

* **No Clutter:** Only appears when called; easily swiped away.
* **Screen Aware:** One-tap button to *"Summarize screen"* or *"Explain this photo"*.
* **Voice or Type:** Tap the mic to talk, or type in the small bar.

---

## 5. Live Duplex Voice Mode (Like Gemini Live / ChatGPT Voice)

Tapping the mic `[ 🎙 ]` transitions into an uncluttered voice interface.

```
┌──────────────────────────────────────────────────────────────┐
│                                                        [ ✕ ] │
│                                                              │
│                                                              │
│                                                              │
│                         ░░▒▒▓▓██▓▓▒▒░░                       │
│                       ▒▓██████████████▓▒                     │
│                      ▓██████████████████▓                    │
│                       ▒▓██████████████▓▒                     │
│                         ░░▒▒▓▓██▓▓▒▒░░                       │
│                                                              │
│                                                              │
│                      "Listening to you..."                   │
│                                                              │
│                                                              │
│                                                              │
│                                                              │
│         [ 🔇 Mute ]        [ 📷 Share Camera ]               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

* **The Glowing Orb:** A smooth particle orb centered on screen. It gently pulses when listening, ripples when talking, and pauses instantly when you interrupt it.
* **Friendly Status:** Simple text under the orb: *"Listening..."*, *"Thinking..."*, or *"Speaking..."*.
* **Two Controls:** **Mute** and **Share Camera** (if you want Stella to look at something with you).

---

## 6. Simple Home Screen Widgets

Configured inside **Settings > Customize Widgets** without complex metrics.

```
┌──────────────────┐    ┌───────────────────────────────────────┐
│ ✦ Stella         │    │ ✦ Stella              ● Ready         │
│                  │    ├───────────────────────────────────────┤
│ [ 🎙 Talk ]      │    │ "Tap the mic to talk or type a prompt"│
│                  │    │ [ Ask anything...               ] [🎙]│
└──────────────────┘    └───────────────────────────────────────┘
  1x1 Quick Voice         4x2 Compact Prompt & Voice Bar
```

* **1x1 Button Widget:** Tap anywhere on your home screen to instantly talk to Stella.
* **4x2 Assistant Widget:** A clean search bar with a status dot and mic button.
* **Customization in Settings:** Simple checkboxes for what you want on the widget: *Status dot*, *Voice button*, *Camera button*.

---

## 7. Jetpack Compose UI Implementation (Clean & Modern)

Here is how the streamlined **Home Screen** is constructed using **Orbitron**, **Exo 2**, and clean Material 3 components:

```kotlin
@Composable
fun SimpleHomeScreen(
    onOpenDrawer: () -> Unit,
    onOpenSettings: () -> Unit,
    onStartVoice: () -> Unit,
    viewModel: HomeViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        containerColor = Color(0xFF0C0D14), // Deep Void
        topBar = {
            // MINIMAL TOP BAR
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .statusBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                IconButton(onClick = onOpenDrawer) {
                    Icon(
                        imageVector = Icons.Default.Menu,
                        contentDescription = "Chat History",
                        tint = Color.White
                    )
                }

                // FRIENDLY STATUS PILL
                Surface(
                    color = Color.White.copy(alpha = 0.08f),
                    shape = RoundedCornerShape(20.dp),
                    border = BorderStroke(0.5.dp, Color(0xFF00F0FF).copy(alpha = 0.3f))
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(7.dp)
                                .background(Color(0xFF00F0FF), CircleShape)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = if (uiState.isPcConnected) "Connected to PC" else "On this phone",
                            fontFamily = Exo2FontFamily,
                            fontSize = 12.sp,
                            color = Color.White
                        )
                    }
                }

                IconButton(onClick = onOpenSettings) {
                    Icon(
                        imageVector = Icons.Default.Settings,
                        contentDescription = "Settings",
                        tint = Color.White
                    )
                }
            }
        },
        bottomBar = {
            // CLEAN INPUT PILL
            Surface(
                color = Color(0xFF13151F),
                shape = RoundedCornerShape(28.dp),
                border = BorderStroke(0.5.dp, Color.White.copy(alpha = 0.12f)),
                modifier = Modifier
                    .fillMaxWidth()
                    .navigationBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { viewModel.onAttach() }) {
                        Icon(
                            imageVector = Icons.Default.Add,
                            contentDescription = "Attach",
                            tint = Color.White.copy(alpha = 0.7f)
                        )
                    }

                    TextField(
                        value = uiState.inputText,
                        onValueChange = { viewModel.onInputChanged(it) },
                        placeholder = {
                            Text(
                                "Ask Stella anything...",
                                fontFamily = Exo2FontFamily,
                                color = Color.White.copy(alpha = 0.4f)
                            )
                        },
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = Color.Transparent,
                            unfocusedContainerColor = Color.Transparent,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent,
                            focusedTextColor = Color.White
                        ),
                        modifier = Modifier.weight(1f)
                    )

                    // VOICE BUTTON
                    IconButton(
                        onClick = onStartVoice,
                        modifier = Modifier
                            .size(42.dp)
                            .background(Color(0xFF00F0FF).copy(alpha = 0.15f), CircleShape)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Mic,
                            contentDescription = "Voice Mode",
                            tint = Color(0xFF00F0FF)
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // HOLOGRAPHIC WEBVIEW BACKGROUND
            HolographicBackground(modifier = Modifier.fillMaxSize())

            // EMPTY STATE OR CONVERSATION LIST
            if (uiState.messages.isEmpty()) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Text(
                        text = "STELLA",
                        fontFamily = OrbitronFontFamily,
                        fontWeight = FontWeight.Bold,
                        fontSize = 28.sp,
                        letterSpacing = 4.sp,
                        color = Color.White
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "What would you like to explore today?",
                        fontFamily = Exo2FontFamily,
                        fontSize = 15.sp,
                        color = Color.White.copy(alpha = 0.6f)
                    )
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(uiState.messages) { message ->
                        ChatMessageItem(message = message)
                    }
                }
            }
        }
    }
}
```

---

## 8. Summary of Solved Gaps

1. **Simple, Non-Techie Aesthetic:** Replaced raw telemetry and developer jargon with clear, conversational copy and calm breathing room modeled on Gemini, ChatGPT, and Siri.
2. **Brand Typography Intact:** Headlines use **Orbitron**; body text and conversations use **Exo 2**.
3. **Zero Bottom Navigation:** Eliminated the bottom tab bar completely.
4. **Chat History Drawer:** Instant access to past sessions via top-left icon or edge swipe; permanently pinnable with a collapse button on tablets and foldables.
5. **3 Core Screens:** All workflows consolidated into **Welcome & Setup**, **Home (Chat & Voice)**, and **Settings**.
6. **Everyday HUD & Overlays:** Includes the out-of-app floating assistant overlay, full-screen live duplex voice mode with kinetic orb, and customizable homescreen widgets.