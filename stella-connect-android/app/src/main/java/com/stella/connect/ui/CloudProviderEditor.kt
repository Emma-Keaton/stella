package com.stella.connect.ui

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.stella.connect.core.CloudKeyStore
import com.stella.connect.core.CloudProviderConfig
import com.stella.connect.ui.theme.StellaTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Preset OpenAI-compatible base URLs; mirrors desktop `core/cloud_config.py`. */
private val PROVIDER_PRESETS: Map<String, String> = mapOf(
    "groq" to "https://api.groq.com/openai/v1",
    "gemini" to "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai" to "https://api.openai.com/v1",
    "anthropic" to "https://api.anthropic.com/v1",
    "openrouter" to "https://openrouter.ai/api/v1",
    "ollama" to "http://localhost:11434/v1",
    "lmstudio" to "http://localhost:1234/v1",
    "custom" to "",
)

private val PROVIDER_LABELS = mapOf(
    "groq" to "Groq",
    "gemini" to "Google Gemini",
    "openai" to "OpenAI",
    "anthropic" to "Anthropic",
    "openrouter" to "OpenRouter",
    "ollama" to "Ollama (Local)",
    "lmstudio" to "LM Studio (Local)",
    "custom" to "Custom (OpenAI-compatible)",
)

/**
 * Cloud Providers editor: the single Phase 1.6 provider slot.
 *
 * Every field of the `{provider, api_key, base_url, model, headers{},
 * params{}, fallback[]}` contract is editable, the model list can be fetched
 * live from `/models`, the connection can be tested, and the config is sealed
 * with an Android Keystore key by [CloudKeyStore] on save.
 */
@Composable
fun CloudProviderEditor(context: Context, modifier: Modifier = Modifier) {
    val scope = rememberCoroutineScope()
    val saved = remember { CloudKeyStore.load(context) }

    var provider by remember { mutableStateOf(saved?.provider ?: "groq") }
    var apiKey by remember { mutableStateOf("") }
    var keyVisible by remember { mutableStateOf(false) }
    var model by remember { mutableStateOf(saved?.model ?: "") }
    var baseUrl by remember {
        mutableStateOf(saved?.baseUrl ?: PROVIDER_PRESETS[saved?.provider ?: "groq"].orEmpty())
    }
    var headers by remember { mutableStateOf(JSONObject(saved?.headers ?: emptyMap<String, String>()).toString()) }
    var params by remember { mutableStateOf(JSONObject(saved?.params ?: emptyMap<String, String>()).toString()) }
    var status by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var providerMenu by remember { mutableStateOf(false) }

    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Provider", style = MaterialTheme.typography.labelSmall, color = StellaTheme.colors.textMuted)
        Box {
            OutlinedButton(
                onClick = { providerMenu = true },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(PROVIDER_LABELS[provider] ?: provider)
                Spacer(Modifier.width(8.dp))
                Icon(Icons.Default.ArrowDropDown, contentDescription = "Change provider")
            }
            DropdownMenu(expanded = providerMenu, onDismissRequest = { providerMenu = false }) {
                PROVIDER_LABELS.forEach { (id, label) ->
                    DropdownMenuItem(
                        text = { Text(label) },
                        onClick = {
                            provider = id
                            providerMenu = false
                            if (baseUrl.isBlank() || PROVIDER_PRESETS.values.contains(baseUrl)) {
                                baseUrl = PROVIDER_PRESETS[id].orEmpty()
                            }
                        },
                    )
                }
            }
        }

        OutlinedTextField(
            value = apiKey,
            onValueChange = { apiKey = it },
            label = { Text(if (saved?.apiKey?.isNotBlank() == true) "API key (saved - hidden)" else "API key") },
            singleLine = true,
            visualTransformation = if (keyVisible) VisualTransformation.None else PasswordVisualTransformation(),
            trailingIcon = {
                TextButton(onClick = { keyVisible = !keyVisible }) {
                    Text(if (keyVisible) "Hide" else "Show")
                }
            },
            modifier = Modifier.fillMaxWidth(),
        )

        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            OutlinedTextField(
                value = model,
                onValueChange = { model = it },
                label = { Text("Model") },
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
            Spacer(Modifier.width(8.dp))
            OutlinedButton(
                enabled = !busy,
                onClick = {
                    busy = true
                    status = "Fetching models..."
                    scope.launch {
                        val result = withContext(Dispatchers.IO) {
                            fetchModels(
                                baseUrl.trim().ifBlank { PROVIDER_PRESETS[provider].orEmpty() },
                                apiKey.ifBlank { saved?.apiKey.orEmpty() },
                            )
                        }
                        busy = false
                        result.onSuccess { ids ->
                            model = ids.firstOrNull() ?: model
                            status = if (ids.isEmpty()) "No models found for this key. Check the key and provider." else "${ids.size} models available. Selected ${ids.firstOrNull() ?: "none"}"
                        }
                        result.onFailure { status = "Couldn’t fetch models. Please check your API key, internet connection, and base URL." }
                    }
                },
            ) { Text("Fetch") }
        }

        OutlinedTextField(
            value = baseUrl,
            onValueChange = { baseUrl = it },
            label = { Text("Base URL") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        OutlinedTextField(
            value = headers,
            onValueChange = { headers = it },
            label = { Text("Headers (JSON)") },
            modifier = Modifier.fillMaxWidth(),
        )

        OutlinedTextField(
            value = params,
            onValueChange = { params = it },
            label = { Text("Params (JSON)") },
            modifier = Modifier.fillMaxWidth(),
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(
                enabled = !busy,
                onClick = {
                    val parsedHeaders = parseJsonObject(headers)
                    val parsedParams = parseJsonObject(params)
                    if (parsedHeaders == null || parsedParams == null) {
                        status = "Headers and params need valid JSON. Check brackets and commas."
                        return@Button
                    }
                    val key = apiKey.ifBlank { saved?.apiKey.orEmpty() }
                    if (key.isBlank() && provider != "ollama" && provider != "lmstudio") {
                        status = "Please add an API key for this provider."
                        return@Button
                    }
                    CloudKeyStore.save(
                        context,
                        CloudProviderConfig(
                            provider = provider,
                            apiKey = key,
                            baseUrl = baseUrl.trim().ifBlank { null },
                            model = model.trim().ifBlank { null },
                            headers = parsedHeaders,
                            params = parsedParams,
                        ),
                    )
                    apiKey = ""
                    status = "Saved securely. Your key is sealed on this device."
                },
            ) { Text("Save") }
            OutlinedButton(
                enabled = !busy,
                onClick = {
                    busy = true
                    status = "Testing..."
                    scope.launch {
                        val result = withContext(Dispatchers.IO) {
                            testConnection(
                                baseUrl.trim().ifBlank { PROVIDER_PRESETS[provider].orEmpty() },
                                apiKey.ifBlank { saved?.apiKey.orEmpty() },
                                model.trim().ifBlank { saved?.model.orEmpty() },
                            )
                        }
                        busy = false
                        status = result.fold(
                            onSuccess = { "Connection OK. This key can talk to the model." },
                            onFailure = { "Connection failed. Please check your API key and model name. If the key is correct, the model may be overloaded or unavailable." },
                        )
                    }
                },
            ) { Text("Test") }
            OutlinedButton(
                enabled = !busy,
                onClick = {
                    CloudKeyStore.clear(context)
                    apiKey = ""
                    model = ""
                    baseUrl = PROVIDER_PRESETS[provider].orEmpty()
                    status = "Configuration forgotten"
                },
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.error,
                ),
            ) { Text("Forget") }
        }

        if (status.isNotBlank()) {
            Text(
                status,
                style = MaterialTheme.typography.labelSmall,
                color = if (status.startsWith("Saved") || status.contains("OK")) {
                    StellaTheme.colors.primary
                } else {
                    StellaTheme.colors.textSecondary
                },
            )
        }

        Text(
            text = buildString {
                append("Keys are sealed with this device's keystore and never shown again after saving. ")
                append("Custom needs a Base URL; Stella completes the /chat/completions path.")
            },
            style = MaterialTheme.typography.labelSmall,
            color = StellaTheme.colors.textMuted,
        )
    }
}

private fun parseJsonObject(raw: String): Map<String, String>? {
    val text = raw.trim()
    if (text.isEmpty()) return emptyMap()
    return try {
        val obj = JSONObject(text)
        obj.keys().asSequence().associateWith { obj.optString(it, "") }
    } catch (_: Exception) {
        null
    }
}

/** GET `{base}/models`; returns provider model ids. */
private fun fetchModels(baseUrl: String, apiKey: String): Result<List<String>> = try {
    val url = URL(baseUrl.trimEnd('/') + "/models")
    val c = (url.openConnection() as HttpURLConnection).apply {
        requestMethod = "GET"
        connectTimeout = 10_000
        readTimeout = 15_000
        setRequestProperty("Authorization", "Bearer $apiKey")
    }
    when (c.responseCode) {
        200 -> {
            val body = c.inputStream.bufferedReader().readText()
            val data = JSONObject(body).optJSONArray("data")
            val ids = (0 until (data?.length() ?: 0))
                .mapNotNull { data?.optJSONObject(it)?.optString("id") }
                .filter { it.isNotBlank() }
            c.disconnect()
            Result.success(ids)
        }
        else -> {
            c.disconnect()
            Result.failure(RuntimeException("HTTP ${c.responseCode}"))
        }
    }
} catch (e: Exception) {
    Result.failure(e)
}

/** Minimal 1-token POST to `{base}/chat/completions` with tool schema check. */
private fun testConnection(baseUrl: String, apiKey: String, model: String): Result<Unit> = try {
    val url = URL(baseUrl.trimEnd('/') + "/chat/completions")
    val c = (url.openConnection() as HttpURLConnection).apply {
        requestMethod = "POST"
        connectTimeout = 10_000
        readTimeout = 30_000
        setRequestProperty("Content-Type", "application/json")
        setRequestProperty("Authorization", "Bearer $apiKey")
        doOutput = true
    }
    val payload = JSONObject()
        .put("model", model.ifBlank { "gpt-3.5-turbo" })
        .put("messages", org.json.JSONArray().put(JSONObject().put("role", "user").put("content", "ping")))
        .put("max_tokens", 1)
        .put("tools", org.json.JSONArray().put(JSONObject().put("type", "function").put("function", JSONObject().put("name", "test_tool").put("description", "test").put("parameters", JSONObject().put("type", "object")))))
        .toString()
    c.outputStream.use { it.write(payload.toByteArray()) }
    val code = c.responseCode
    c.disconnect()
    if (code in 200..299) Result.success(Unit)
    else Result.failure(RuntimeException("HTTP $code"))
} catch (e: Exception) {
    Result.failure(e)
}
