package com.stella.connect.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.result.contract.ActivityResultContracts.OpenDocumentTree
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.stella.connect.core.*
import com.stella.connect.ui.theme.StellaTheme
import com.stella.connect.ui.theme.StellaThemeState
import com.stella.connect.ui.theme.StellaThemeStyle
import kotlinx.coroutines.launch

/**
 * The structured settings information architecture.
 *
 * The settings screen is a section index ([SettingsSectionIndex]) that opens
 * one focused detail screen per section. Each detail composable owns its own
 * state so the index stays cheap to compose and every section can evolve
 * independently.
 */
enum class SettingsSection(val title: String, val subtitle: String) {
    AI_SPEED("AI & SPEED", "On-device model, cloud models, download"),
    CONNECTIONS("CONNECTIONS", "Link to computer, cloud backup"),
    APPEARANCE("APPEARANCE", "Theme, text size"),
    WIDGETS("HOME SCREEN WIDGETS", "Customize widgets"),
    DATA_BACKUP("DATA & BACKUP", "Save, restore, export"),
}

@Composable
fun SettingsSectionIndex(onSelect: (SettingsSection) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            text = "Settings",
            style = MaterialTheme.typography.headlineSmall,
            color = StellaTheme.colors.textPrimary,
        )
        SettingsSection.values().forEach { section ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onSelect(section) }
                    .padding(vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(section.title, style = MaterialTheme.typography.bodyLarge, color = StellaTheme.colors.textPrimary)
                    Text(section.subtitle, style = MaterialTheme.typography.bodySmall, color = StellaTheme.colors.textMuted)
                }
                Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, contentDescription = null, tint = StellaTheme.colors.textMuted)
            }
            HorizontalDivider(color = StellaTheme.colors.surface)
        }
    }
}


/**
 * Cloud providers: API keys for hosted AI models plus OAuth-style cloud
 * providers. Backed by [CloudKeyStore]; keys are encrypted at rest.
 */
@Composable
fun CloudProvidersDetail(context: Context) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Cloud Providers", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        Text(
            "Add a key for a hosted model provider, or point Stella at your own endpoint. " +
                "Keys are sealed with this device's keystore.",
            style = MaterialTheme.typography.bodySmall,
            color = StellaTheme.colors.textSecondary,
        )
        CloudProviderEditor(context = context, modifier = Modifier.fillMaxWidth())
        
        HorizontalDivider(color = StellaTheme.colors.surface)
        
        // Routing
        Text("Routing", style = MaterialTheme.typography.titleMedium, color = StellaTheme.colors.textPrimary)
        Text(
            "Route chat, agent, and voice to different providers.",
            style = MaterialTheme.typography.bodySmall,
            color = StellaTheme.colors.textSecondary,
        )
        var chatProvider by remember { mutableStateOf("Auto") }
        var agentProvider by remember { mutableStateOf("Auto") }
        var voiceProvider by remember { mutableStateOf("Auto") }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text("Chat:", style = MaterialTheme.typography.labelSmall, color = StellaTheme.colors.textMuted, modifier = Modifier.weight(0.3f))
            OutlinedButton(onClick = { /* open provider selector */ }, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.outlinedButtonColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Text(chatProvider)
            }
        }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text("Agent:", style = MaterialTheme.typography.labelSmall, color = StellaTheme.colors.textMuted, modifier = Modifier.weight(0.3f))
            OutlinedButton(onClick = { /* open provider selector */ }, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.outlinedButtonColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Text(agentProvider)
            }
        }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text("Voice:", style = MaterialTheme.typography.labelSmall, color = StellaTheme.colors.textMuted, modifier = Modifier.weight(0.3f))
            OutlinedButton(onClick = { /* open provider selector */ }, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.outlinedButtonColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Text(voiceProvider)
            }
        }
    }
}

/**
 * On-device model: import a .gguf, pick the models folder, choose the runtime
 * engine, and open the download catalogue. The catalogue flags models that are
 * too heavy for this device instead of starting a doomed download.
 */
@Composable
fun OnDeviceModelDetail(
    context: Context,
    onOpenModels: () -> Unit = {},
    onGoToApi: () -> Unit = {},
) {
    val scope = rememberCoroutineScope()
    val runtimeFlow = LocalEngineManager.runtime
    val currentRuntime by runtimeFlow.collectAsState()
    var runtimeMenuOpen by remember { mutableStateOf(false) }
    var modelPresent by remember { mutableStateOf(LocalEngineManager.modelPresent(context)) }
    var showDownloadHub by remember { mutableStateOf(false) }

    val importLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: Exception) {}
            scope.launch {
                LocalEngineManager.importLocalModel(context, uri)
                modelPresent = LocalEngineManager.modelPresent(context)
                if (modelPresent) scope.launch { LocalEngineManager.start(context) }
            }
        }
    }

    val folderLauncher = rememberLauncherForActivityResult(OpenDocumentTree()) { uri: Uri? ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
            } catch (_: Exception) {}
            LocalEngineManager.setModelsFolderUri(context, uri)
            modelPresent = LocalEngineManager.modelPresent(context)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("On-device Model", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        Text(
            "On-device models live in your chosen models folder. Import a .gguf file already on this phone, or open the download hub.",
            style = MaterialTheme.typography.bodySmall,
            color = StellaTheme.colors.textSecondary,
        )
        Text(
            text = if (modelPresent) "Model ready - on-device" else "No model installed",
            style = MaterialTheme.typography.bodyMedium,
            color = if (modelPresent) StellaTheme.colors.primary else StellaTheme.colors.textSecondary,
        )
        Button(
            onClick = { importLauncher.launch(arrayOf("*/*")) },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Import .gguf")
        }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(
                "Models folder",
                style = MaterialTheme.typography.labelSmall,
                color = StellaTheme.colors.textMuted,
                modifier = Modifier.weight(1f),
            )
            Text(
                LocalEngineManager.modelsRootLabel(context),
                style = MaterialTheme.typography.bodySmall,
                color = StellaTheme.colors.textSecondary,
                modifier = Modifier.weight(1f),
            )
            Button(onClick = { folderLauncher.launch(null) }) { Text("Choose") }
            TextButton(onClick = onOpenModels) { Text("Manage") }
        }
        Text(
            "Runtime engine",
            style = MaterialTheme.typography.labelSmall,
            color = StellaTheme.colors.textMuted,
        )
        Box {
            OutlinedButton(
                onClick = { runtimeMenuOpen = true },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(currentRuntime.uppercase())
                Spacer(Modifier.width(8.dp))
                Icon(
                    imageVector = Icons.Default.ArrowDropDown,
                    contentDescription = "Change runtime",
                )
            }
            DropdownMenu(
                expanded = runtimeMenuOpen,
                onDismissRequest = { runtimeMenuOpen = false },
            ) {
                LocalEngineManager.RUNTIMES.forEach { id ->
                    DropdownMenuItem(
                        text = { Text(id.uppercase()) },
                        onClick = {
                            runtimeMenuOpen = false
                            LocalEngineManager.setRuntime(context, id)
                        },
                    )
                }
            }
        }
        if (modelPresent) {
            Button(
                onClick = {
                    LocalEngineManager.deleteLocalModel(context)
                    modelPresent = LocalEngineManager.modelPresent(context)
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = androidx.compose.ui.graphics.Color.Transparent,
                    contentColor = MaterialTheme.colorScheme.error,
                ),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Remove local model")
            }
        }
        Button(
            onClick = { showDownloadHub = true },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = StellaTheme.colors.primary,
                contentColor = StellaTheme.colors.buttonContent,
            ),
        ) {
            Text("Download local model")
        }
    }

    if (showDownloadHub) {
        ModelDownloadHub(
            onDismiss = {
                showDownloadHub = false
                modelPresent = LocalEngineManager.modelPresent(context)
            },
            onGoToApi = {
                showDownloadHub = false
                onGoToApi()
            },
            onDownloaded = {
                modelPresent = LocalEngineManager.modelPresent(context)
                scope.launch { LocalEngineManager.start(context) }
            },
        )
    }
}

/**
 * Memory Vault: activation plus the notes destination folder.
 */
@Composable
fun MemoryVaultDetail(context: Context) {
    var vaultOn by remember { mutableStateOf(MemoryVaultStore.isEnabled(context)) }
    var vaultTree by remember { mutableStateOf<Uri?>(MemoryVaultStore.treeUri(context)) }
    val vaultLabel = vaultTree?.let {
        it.lastPathSegment?.substringAfterLast('/') ?: it.toString()
    } ?: "App-private storage (default)"
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { uri ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
            } catch (_: Exception) {}
            MemoryVaultStore.takePersistableGrant(context, uri)
            MemoryVaultStore.setTreeUri(context, uri)
            vaultTree = uri
        }
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Memory Vault", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        Text(
            "Memory Vault stores Stella's notes. Choose a folder you control; off keeps notes in app-private storage.",
            style = MaterialTheme.typography.bodySmall,
            color = StellaTheme.colors.textSecondary,
        )
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Memory Vault", style = MaterialTheme.typography.bodyMedium, color = StellaTheme.colors.textPrimary)
            Switch(
                checked = vaultOn,
                onCheckedChange = { value ->
                    vaultOn = value
                    MemoryVaultStore.setEnabled(context, value)
                    if (value && vaultTree == null) launcher.launch(null)
                },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = StellaTheme.colors.primary,
                    uncheckedThumbColor = StellaTheme.colors.textMuted,
                    checkedTrackColor = StellaTheme.colors.primary.copy(alpha = 0.3f),
                    uncheckedTrackColor = StellaTheme.colors.glassBorder,
                ),
            )
        }
        if (vaultOn) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text("Destination", style = MaterialTheme.typography.labelSmall, color = StellaTheme.colors.textMuted, modifier = Modifier.weight(1f))
                Text(
                    vaultLabel,
                    style = MaterialTheme.typography.bodySmall,
                    color = if (vaultTree != null) StellaTheme.colors.textSecondary else StellaTheme.colors.warning,
                    modifier = Modifier.weight(1f),
                )
                Button(onClick = { launcher.launch(null) }) { Text("Choose") }
            }
            if (vaultTree == null) {
                Text(
                    "No folder chosen yet - notes stay in app-private storage until you pick one.",
                    style = MaterialTheme.typography.labelSmall,
                    color = StellaTheme.colors.warning,
                )
            }
        }
        HorizontalDivider(color = StellaTheme.colors.surface)
        // Inspector
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Memory Inspector", style = MaterialTheme.typography.bodyMedium, color = StellaTheme.colors.textPrimary)
            Spacer(modifier = Modifier.weight(1f))
            Text("View inspector", style = MaterialTheme.typography.bodySmall, color = StellaTheme.colors.textSecondary)
        }
        Spacer(Modifier.height(12.dp))
        // Backup & Restore
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Backup & Restore", style = MaterialTheme.typography.bodyMedium, color = StellaTheme.colors.textPrimary)
            Spacer(modifier = Modifier.weight(1f))
            Button(onClick = { /* export backup */ }, colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.surface)) { Text("Export") }
            OutlinedButton(onClick = { /* import backup */ }, modifier = Modifier.width(80.dp)) { Text("Import") }
        }
        Spacer(Modifier.height(12.dp))
        // Audit Log
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Audit Log", style = MaterialTheme.typography.bodyMedium, color = StellaTheme.colors.textPrimary)
            Spacer(modifier = Modifier.weight(1f))
            TextButton(onClick = { /* open audit */ }) { Text("View audit log") }
        }
    }
}

/**
 * Connections: PC link bridge toggle plus the pairing sheet entry point.
 */
@Composable
fun ConnectionsDetail(context: Context, onOpenPairing: () -> Unit = {}) {
    var bridgeOn by remember { mutableStateOf(BridgeSettings.isEnabled(context)) }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Connections", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        Text(
            "Relay chat to a paired desktop gateway. Optional; on-device chat works without it.",
            style = MaterialTheme.typography.bodySmall,
            color = StellaTheme.colors.textSecondary,
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Switch(
                checked = bridgeOn,
                onCheckedChange = { value ->
                    bridgeOn = value
                    BridgeSettings.setEnabled(context, value)
                },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = if (bridgeOn) StellaTheme.colors.primary else StellaTheme.colors.textMuted,
                    uncheckedThumbColor = StellaTheme.colors.textMuted,
                    checkedTrackColor = StellaTheme.colors.primary.copy(alpha = 0.3f),
                    uncheckedTrackColor = StellaTheme.colors.glassBorder,
                ),
            )
            Text(
                text = if (bridgeOn) "Bridge enabled" else "Bridge disabled",
                style = MaterialTheme.typography.bodyMedium,
                color = StellaTheme.colors.textPrimary,
                modifier = Modifier.padding(start = 12.dp),
            )
        }
        if (!BridgeSettings.isAvailable()) {
            Text(
                "Bridge not available in this build.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.error.copy(alpha = 0.8f),
            )
        }
        SettingRow(
            title = "PC pairing & Devices",
            subtitle = "Manage paired computers and scan QR",
            onClick = onOpenPairing,
        )
    }
}

/**
 * Permissions: runtime capability grants.
 *
 * Rows come from the single [PermissionManager.capabilities] list, so the UI
 * can never drift from what the core actually supports. Dialog-path rows show
 * a Grant button wired to the runtime permission launcher; Settings-path rows
 * deep-link to the OS grant page.
 */
@Composable
fun PermissionsDetail(context: Context) {
    var tick by remember { mutableStateOf(0) }
    val lifecycleOwner = androidx.lifecycle.compose.LocalLifecycleOwner.current
    androidx.compose.runtime.DisposableEffect(lifecycleOwner) {
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME) tick++
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    // Single source of truth: only capabilities this OS actually has.
    val caps = remember(tick) {
        PermissionManager.capabilities.filter { Build.VERSION.SDK_INT >= it.minSdk }
    }

    val runtimeLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { _ -> tick++ }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Permissions", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        Text(
            "Runtime capabilities. Grant each to enable the corresponding feature.",
            style = MaterialTheme.typography.bodySmall,
            color = StellaTheme.colors.textSecondary,
        )
        caps.forEach { cap ->
            val needsPrereqs = !PermissionManager.prerequisitesMet(context, cap)
            val isGranted = PermissionManager.granted(context, cap)
            val perUse = cap.path == PermissionManager.GrantPath.PER_USE
            PermissionRow(
                capability = cap,
                granted = isGranted,
                onGrant = {
                    if (needsPrereqs) return@PermissionRow
                    when {
                        perUse -> { /* consent is asked at capture time */ }
                        cap.runtime.isNotEmpty() ->
                            runtimeLauncher.launch(cap.runtime.toTypedArray())
                        else -> {
                            val intent = PermissionManager.settingsIntent(context, cap)
                            if (intent != null) {
                                try {
                                    context.startActivity(intent)
                                } catch (_: Exception) {
                                    tick++
                                }
                            } else {
                                val adb = PermissionManager.adbCommand(context, cap)
                                if (adb.isNotBlank()) {
                                    android.widget.Toast.makeText(
                                        context,
                                        "Run from your PC: $adb",
                                        android.widget.Toast.LENGTH_LONG,
                                    ).show()
                                }
                                tick++
                            }
                        }
                    }
                },
            )
            if (needsPrereqs) {
                Text(
                    "Grant the earlier rows first.",
                    style = MaterialTheme.typography.labelSmall,
                    color = StellaTheme.colors.warning,
                    modifier = Modifier.padding(start = 4.dp, bottom = 8.dp),
                )
            }
        }
    }
}

/**
 * Appearance: the four themes plus a text-size step.
 */
@Composable
fun AppearanceDetail(context: Context) {
    var largeText by remember { mutableStateOf(StellaThemeState.largeText.value) }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Appearance", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        Text(
            "Theme applies instantly and is remembered.",
            style = MaterialTheme.typography.bodySmall,
            color = StellaTheme.colors.textSecondary,
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            ThemeChip("Void", StellaThemeStyle.VOID, context, Modifier.weight(1f))
            ThemeChip("OLED", StellaThemeStyle.OLED, context, Modifier.weight(1f))
            ThemeChip("Aurora", StellaThemeStyle.AURORA, context, Modifier.weight(1f))
            ThemeChip("Light", StellaThemeStyle.LIGHT, context, Modifier.weight(1f))
        }
        HorizontalDivider(color = StellaTheme.colors.surface)
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text("Text size", style = MaterialTheme.typography.bodyMedium, color = StellaTheme.colors.textPrimary)
                Text(
                    if (largeText) "Large" else "Normal",
                    style = MaterialTheme.typography.bodySmall,
                    color = StellaTheme.colors.textMuted,
                )
            }
            Switch(
                checked = largeText,
                onCheckedChange = { value ->
                    largeText = value
                    StellaThemeState.setLargeText(context, value)
                },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = StellaTheme.colors.primary,
                    uncheckedThumbColor = StellaTheme.colors.textMuted,
                    checkedTrackColor = StellaTheme.colors.primary.copy(alpha = 0.3f),
                    uncheckedTrackColor = StellaTheme.colors.glassBorder,
                ),
            )
        }
    }
}

/**
 * System: build info, the wake word, model unload and about.
 *
 * The HUD overlay is always on - it is invoked by the wake word, so it has no
 * settings toggle. Only the wake word itself is configurable here.
 */
@Composable
fun SystemDetail(context: Context) {
    var voiceWakeOn by remember { mutableStateOf(VoiceHudSettings.isHudEnabled(context)) }
    var modelPresent by remember { mutableStateOf(LocalEngineManager.modelPresent(context)) }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("System", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        SettingRow(
            title = "Build",
            subtitle = Build.VERSION.RELEASE + " (API ${Build.VERSION.SDK_INT})",
        )
        SettingRow(
            title = "Package",
            subtitle = context.packageName,
        )
        SettingRow(
            title = "Runtime bundled",
            subtitle = "No",
        )
        SettingRow(
            title = "Wake word",
            subtitle = if (voiceWakeOn) "Listening" else "Off",
            onClick = {
                voiceWakeOn = !voiceWakeOn
                VoiceHudSettings.setHudEnabled(context, voiceWakeOn)
                WakeWordManager.get()?.let {
                    if (voiceWakeOn) it.start() else it.stop()
                }
            },
        )
        Text(
            "The HUD overlay follows the wake word and is always on.",
            style = MaterialTheme.typography.labelSmall,
            color = StellaTheme.colors.textMuted,
        )
        SettingRow(
            title = "Unload local model",
            subtitle = if (LocalEngineManager.isRunning()) {
                "Stop the engine now - the file stays on the device"
            } else {
                "Engine idle - file stays on the device"
            },
            onClick = {
                LocalEngineManager.stop()
                modelPresent = LocalEngineManager.modelPresent(context)
            },
        )
        SettingRow(
            title = "Feedback channel",
            subtitle = "Stable",
            onClick = { },
        )
        SettingRow(
            title = "Check updates on startup",
            subtitle = "Enabled",
            onClick = { },
        )
        SettingRow(
            title = "About",
            subtitle = "Stella Connect - on-device AI",
            onClick = { },
        )
    }
}

@Composable
fun AiSpeedDetail(context: Context, onOpenModels: () -> Unit = {}) {
    var selectedSub by remember { mutableStateOf("overview") }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("AI & SPEED", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        if (selectedSub == "overview") {
            SettingRow(
                title = "On-device AI Model",
                subtitle = if (LocalEngineManager.modelPresent(context)) "Mistral 7B (Default)" else "No model installed",
                onClick = { selectedSub = "model" }
            )
            SettingRow(
                title = "Cloud Models",
                subtitle = "API keys, models, endpoints",
                onClick = { selectedSub = "cloud" }
            )
            SettingRow(
                title = "Download New Model",
                subtitle = "Browse library",
                onClick = { selectedSub = "download" }
            )
        } else {
            when (selectedSub) {
                "model" -> {
                    OnDeviceModelDetail(context = context, onOpenModels = onOpenModels, onGoToApi = {})
                    SettingRow(title = "Back", subtitle = "", onClick = { selectedSub = "overview" })
                }
                "cloud" -> {
                    CloudProvidersDetail(context)
                    SettingRow(title = "Back", subtitle = "", onClick = { selectedSub = "overview" })
                }
                "download" -> {
                    var showHub by remember { mutableStateOf(true) }
                    if (showHub) {
                        ModelDownloadHub(onDismiss = { showHub = false }, onGoToApi = {}, onDownloaded = {})
                    }
                    SettingRow(title = "Back", subtitle = "", onClick = { selectedSub = "overview" })
                }
            }
        }
    }
}

@Composable
fun WidgetsDetail(context: Context) {
    var selectedSize by remember { mutableStateOf("4x2") }
    var selectedTheme by remember { mutableStateOf(StellaThemeStyle.VOID) }
    var micEnabled by remember { mutableStateOf(true) }
    var statusEnabled by remember { mutableStateOf(true) }
    var quickLogEnabled by remember { mutableStateOf(true) }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("HOME SCREEN WIDGETS", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        Text("Customize appearance and content for mobile and desktop widgets", style = MaterialTheme.typography.bodySmall, color = StellaTheme.colors.textMuted)
        
        // Size / Ratio
        Text("Widget Size", style = MaterialTheme.typography.titleMedium, color = StellaTheme.colors.textPrimary)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("1x1", "2x2", "4x2").forEach { size ->
                val selected = selectedSize == size
                Button(
                    onClick = { selectedSize = size },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = if (selected) StellaTheme.colors.primary else StellaTheme.colors.surface)
                ) { Text(size) }
            }
        }

        // Theme
        Text("Theme", style = MaterialTheme.typography.titleMedium, color = StellaTheme.colors.textPrimary)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StellaThemeStyle.values().forEach { style ->
                val selected = selectedTheme == style
                Button(
                    onClick = { selectedTheme = style },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.buttonColors(containerColor = if (selected) StellaTheme.colors.primary else StellaTheme.colors.surface)
                ) { Text(style.name) }
            }
        }

        // Elements
        Text("Widget Elements", style = MaterialTheme.typography.titleMedium, color = StellaTheme.colors.textPrimary)
        SettingRow(
            title = "Microphone Input",
            subtitle = if (micEnabled) "Enabled" else "Disabled",
            onClick = { micEnabled = !micEnabled }
        )
        SettingRow(
            title = "Status Indicator",
            subtitle = if (statusEnabled) "Enabled" else "Disabled",
            onClick = { statusEnabled = !statusEnabled }
        )
        SettingRow(
            title = "Quick Log Shortcuts",
            subtitle = if (quickLogEnabled) "Enabled" else "Disabled",
            onClick = { quickLogEnabled = !quickLogEnabled }
        )

        Button(onClick = { /* add to home screen */ }, modifier = Modifier.fillMaxWidth()) {
            Text("Add Widget to Home Screen")
        }
    }
}

@Composable
fun DataBackupDetail(context: Context) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("DATA & BACKUP", style = MaterialTheme.typography.titleLarge, color = StellaTheme.colors.textPrimary)
        SettingRow(title = "Save Backup File", subtitle = "Export chats & setup", onClick = {})
        SettingRow(title = "Restore Backup", subtitle = "Import file", onClick = {})
    }
}
