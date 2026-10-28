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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.stella.connect.core.BridgeSettings
import com.stella.connect.core.CloudKeyStore
import com.stella.connect.core.HudOverlay
import com.stella.connect.core.LocalEngineManager
import com.stella.connect.core.MemoryVaultStore
import com.stella.connect.core.PermissionManager
import com.stella.connect.core.WakeWordManager
import com.stella.connect.ui.theme.StellaTheme
import com.stella.connect.ui.theme.StellaThemeState
import com.stella.connect.ui.theme.StellaThemeStyle
import kotlinx.coroutines.launch

/**
 * Settings screen for the two-screen `chat | settings` navigation.
 *
 * The screen is a section index that opens one focused detail screen per
 * section. The detail screens live in [SettingsSections.kt]; each owns its
 * own state so the index stays cheap to compose.
 *
 * Sections:
 *   - Cloud Providers — hosted model keys + cloud providers ([CloudKeyStore])
 *   - On-device Model — .gguf import / download, runtime selector, remove
 *   - Memory Vault — notes destination folder
 *   - Connections — PC link bridge toggle + pairing entry point
 *   - Permissions — runtime capability grants ([PermissionManager])
 *   - Appearance — theme chips, text size
 *   - System — build info, wake word, unload model, about
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onOpenModels: () -> Unit = {},
    onOpenPairing: () -> Unit = {},
) {
    val context = LocalContext.current
    var section by rememberSaveable { mutableStateOf<SettingsSection?>(null) }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = StellaTheme.colors.bg,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            if (section == null) {
                SettingsSectionIndex(onSelect = { section = it })
            } else {
                SettingsDetailHeader(
                    title = section!!.title,
                    onBack = { section = null },
                )
                when (section) {
                    SettingsSection.AI_SPEED -> AiSpeedDetail(
                        context = context,
                        onOpenModels = onOpenModels,
                    )
                    SettingsSection.CONNECTIONS -> ConnectionsDetail(context) { onOpenPairing() }
                    SettingsSection.APPEARANCE -> AppearanceDetail(context)
                    SettingsSection.WIDGETS -> WidgetsDetail(context)
                    SettingsSection.DATA_BACKUP -> DataBackupDetail(context)
                    null -> Unit
                }
            }
        }
    }
}

/**
 * Detail header: a back affordance plus the section title.
 */
@Composable
private fun SettingsDetailHeader(title: String, onBack: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onBack) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = "Back to settings",
                tint = StellaTheme.colors.textPrimary,
            )
        }
        Text(
            text = title,
            style = MaterialTheme.typography.titleLarge,
            color = StellaTheme.colors.textPrimary,
        )
    }
    HorizontalDivider(color = StellaTheme.colors.surface)
}

/**
 * Download hub: folder gate first, then the catalogued models with
 * per-device suitability (RAM + free storage vs entry minimums).
 * Entries the device cannot run link out to the API (cloud key) section
 * instead of starting a doomed download.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ModelDownloadHub(
    onDismiss: () -> Unit,
    onGoToApi: () -> Unit,
    onDownloaded: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var downloadingId by remember { mutableStateOf<String?>(null) }
    val folderLabel = LocalEngineManager.modelsRootLabel(context)

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Download local model") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                Text(
                    text = "Models download into: $folderLabel",
                    style = MaterialTheme.typography.bodySmall,
                    color = StellaTheme.colors.textSecondary,
                    modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                )
                if (!LocalEngineManager.hasUserFolder(context)) {
                    Text(
                        text = "Pick a models folder first — downloads go there, not the device root.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error.copy(alpha = 0.85f),
                        modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                    )
                }
                LocalEngineManager.ModelCatalog.all.forEach { entry ->
                    val fits = LocalEngineManager.deviceCanRunLocally(context, entry)
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(entry.label, style = MaterialTheme.typography.bodyMedium, color = StellaTheme.colors.textPrimary)
                            Text(
                                text = if (fits) "Fits this device" else "Too heavy for this device",
                                style = MaterialTheme.typography.labelSmall,
                                color = if (fits) MaterialTheme.colorScheme.primary.copy(alpha = 0.8f)
                                else MaterialTheme.colorScheme.error.copy(alpha = 0.8f),
                            )
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        if (fits) {
                            Button(
                                onClick = {
                                    if (downloadingId != null) return@Button
                                    downloadingId = entry.id
                                    scope.launch {
                                        val ok = LocalEngineManager.downloadModel(context, entry)
                                        downloadingId = null
                                        if (ok) {
                                            scope.launch { LocalEngineManager.start(context) }
                                            onDownloaded()
                                        }
                                    }
                                },
                                enabled = downloadingId == null,
                            ) {
                                Text(if (downloadingId == entry.id) "…" else "Get")
                            }
                        } else {
                            OutlinedButton(onClick = onGoToApi) {
                                Text("Use API")
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("Close") }
        },
    )
}

/**
 * A single permission row: name, description, grant status, and a grant button.
 */
@Composable
fun PermissionRow(
    capability: PermissionManager.Capability,
    granted: Boolean,
    onGrant: () -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column {
            Text(
                text = capability.label,
                style = MaterialTheme.typography.bodyMedium,
                color = StellaTheme.colors.textPrimary,
            )
            Text(
                text = capability.why,
                style = MaterialTheme.typography.bodySmall,
                color = StellaTheme.colors.textMuted,
            )
        }
        Spacer(modifier = Modifier.weight(1f))
        Column(
            horizontalAlignment = Alignment.End,
        ) {
            Text(
                text = if (granted) "Granted" else "Not granted",
                style = MaterialTheme.typography.labelSmall,
                color = if (granted) MaterialTheme.colorScheme.primary.copy(alpha = 0.8f)
                else StellaTheme.colors.textMuted,
            )
            if (!granted) {
                OutlinedButton(
                    onClick = onGrant,
                    modifier = Modifier.padding(top = 4.dp),
                ) {
                    Text("Grant")
                }
            }
        }
    }
}

/**
 * A single settings row: title, subtitle, optional click handler.
 */
@Composable
fun SettingRow(
    title: String,
    subtitle: String,
    onClick: (() -> Unit)? = null,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp)
            .clickable { onClick?.invoke() },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                color = StellaTheme.colors.textPrimary,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = StellaTheme.colors.textMuted,
            )
        }
        Spacer(modifier = Modifier.weight(1f))
        if (onClick != null) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = StellaTheme.colors.textMuted,
            )
        }
    }
}

/**
 * A selectable theme chip. Highlights (fills with the theme's primary) when
 * the theme is active; hairline outline otherwise. Tapping applies + persists.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ThemeChip(label: String, style: StellaThemeStyle, context: Context, modifier: Modifier = Modifier) {
    val active = StellaThemeState.style.value == style
    val border = if (active) Color.Transparent else MaterialTheme.colorScheme.outline
    val bg = if (active) MaterialTheme.colorScheme.primary else Color.Transparent
    val fg = if (active) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
    Surface(
        onClick = { StellaThemeState.set(context, style) },
        shape = androidx.compose.foundation.shape.RoundedCornerShape(50),
        color = bg,
        border = androidx.compose.foundation.BorderStroke(1.dp, border),
        modifier = modifier,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelLarge,
            color = fg,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            modifier = Modifier.padding(vertical = 8.dp),
        )
    }
}
