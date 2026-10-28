package com.stella.connect.ui

import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.stella.connect.core.CloudKeyStore
import com.stella.connect.ui.theme.StellaTheme

@Composable
fun ProviderSelector(
    context: Context,
    modifier: Modifier = Modifier,
) {
    val aiProviders = listOf("groq", "gemini", "openai", "anthropic", "openrouter", "ollama", "lmstudio", "nvidia", "custom")
    val cloudProviders = listOf("google_drive", "onedrive", "dropbox")

    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("AI Providers", style = MaterialTheme.typography.titleMedium, color = StellaTheme.colors.textPrimary)
        Text("Add an API key to enable a model provider.", style = MaterialTheme.typography.bodySmall, color = StellaTheme.colors.textMuted)
        aiProviders.forEach { name ->
            ProviderCard(name = name, isCloud = false, context = context)
        }
        Spacer(Modifier.height(8.dp))
        Text("Cloud Providers", style = MaterialTheme.typography.titleMedium, color = StellaTheme.colors.textPrimary)
        Text("Connect a cloud account for backup and sync.", style = MaterialTheme.typography.bodySmall, color = StellaTheme.colors.textMuted)
        cloudProviders.forEach { name ->
            ProviderCard(name = name, isCloud = true, context = context)
        }
    }
}

@Composable
private fun ProviderCard(name: String, isCloud: Boolean, context: Context) {
    var cfg by remember { mutableStateOf(CloudKeyStore.load(context)) }
    val connected = if (isCloud) false else (cfg?.provider == name && !cfg?.apiKey.isNullOrBlank())
    var showDialog by remember { mutableStateOf(false) }
    var keyInput by remember { mutableStateOf("") }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(name.replaceFirstChar { it.uppercase() }, style = MaterialTheme.typography.bodyLarge, color = StellaTheme.colors.textPrimary)
                    Text(if (connected) "Connected" else "Not connected", style = MaterialTheme.typography.bodySmall, color = StellaTheme.colors.textMuted)
                }
                if (!isCloud) {
                    OutlinedButton(onClick = { keyInput = cfg?.apiKey ?: ""; showDialog = true }) {
                        Text(if (connected) "Update key" else "Add key")
                    }
                } else {
                    OutlinedButton(onClick = { /* launch OAuth */ }) {
                        Text("Connect")
                    }
                }
            }
        }
    }

    if (showDialog) {
        AlertDialog(
            onDismissRequest = { showDialog = false },
            title = { Text("API key for ${name.replaceFirstChar { it.uppercase() }}") },
            text = {
                OutlinedTextField(
                    value = keyInput,
                    onValueChange = { keyInput = it },
                    label = { Text("API key") },
                    singleLine = true,
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    val current = CloudKeyStore.load(context)
                    CloudKeyStore.save(context, (current ?: com.stella.connect.core.CloudProviderConfig(provider = name, apiKey = "")).copy(provider = name, apiKey = keyInput.trim()))
                    cfg = CloudKeyStore.load(context)
                    showDialog = false
                }) { Text("Save") }
            },
            dismissButton = { TextButton(onClick = { showDialog = false }) { Text("Cancel") } },
        )
    }
}
