package com.stella.connect.core

import android.content.Context
import org.json.JSONObject

/**
 * Phase 4.5 provider registry - the Kotlin half of the shared registry.
 *
 * Reads `assets/providers.json`, which is a byte-for-byte copy of
 * `config/providers.json` in the repository root. The two files MUST stay
 * identical; `ProviderRegistryTest.kt` and `tests/test_provider_registry.py`
 * both fail CI if they diverge.
 *
 * Never hard-code a provider id, base URL or wire format here - read it from
 * the registry so desktop and Android cannot drift apart.
 */
data class ProviderDefinition(
    val id: String,
    val label: String,
    val authStyle: String,
    val wireFormat: String,
    val baseUrl: String,
    val requiresKey: Boolean,
    val chatEndpoint: String,
    val modelsEndpoint: String?,
    val staticModels: List<String>,
) {
    val isAnthropic: Boolean get() = wireFormat == "anthropic"
    val isLocal: Boolean get() = !requiresKey
}

object ProviderRegistry {

    private const val ASSET_NAME = "providers.json"

    /** Display-label aliases, mirroring `core/providers/registry.py`. */
    private val LABEL_ALIASES = mapOf(
        "gemini" to "gemini",
        "google gemini" to "gemini",
        "google" to "gemini",
        "groq" to "groq",
        "openai" to "openai",
        "open ai" to "openai",
        "anthropic" to "anthropic",
        "claude" to "anthropic",
        "openrouter" to "openrouter",
        "open router" to "openrouter",
        "ollama" to "ollama",
        "lmstudio" to "lmstudio",
        "lm studio" to "lmstudio",
        "custom" to "custom",
        "local" to "local",
    )

    @Volatile
    private var cached: Map<String, ProviderDefinition>? = null

    /** All providers, keyed by id, in registry order. */
    fun all(context: Context): Map<String, ProviderDefinition> {
        cached?.let { return it }
        val loaded = load(context)
        cached = loaded
        return loaded
    }

    /** Provider ids, in registry order. */
    fun ids(context: Context): List<String> = all(context).keys.toList()

    /** One provider definition, or null when the id is unknown. */
    fun get(context: Context, providerId: String): ProviderDefinition? =
        all(context)[providerId.trim().lowercase()]

    /** Human label for a provider id. */
    fun labelFor(context: Context, providerId: String): String =
        get(context, providerId)?.label ?: providerId

    /** Map a display label (or an id) to a canonical provider id. */
    fun idFor(context: Context, label: String): String {
        val key = label.trim().lowercase()
        if (key.isEmpty()) return "custom"
        if (all(context).containsKey(key)) return key
        return LABEL_ALIASES[key] ?: "custom"
    }

    /** Drop the cache - used by tests. */
    fun invalidate() {
        cached = null
    }

    private fun load(context: Context): Map<String, ProviderDefinition> {
        val out = LinkedHashMap<String, ProviderDefinition>()
        val json = try {
            context.assets.open(ASSET_NAME).bufferedReader().use { it.readText() }
        } catch (e: Exception) {
            return out
        }
        val array = try {
            JSONObject(json).optJSONArray("providers")
        } catch (e: Exception) {
            null
        } ?: return out

        for (i in 0 until array.length()) {
            val o = array.optJSONObject(i) ?: continue
            val id = o.optString("id", "").trim().lowercase()
            if (id.isEmpty()) continue
            val models = mutableListOf<String>()
            o.optJSONArray("models")?.let { arr ->
                for (j in 0 until arr.length()) models.add(arr.optString(j, ""))
            }
            out[id] = ProviderDefinition(
                id = id,
                label = o.optString("label", id),
                authStyle = o.optString("auth_style", "bearer"),
                wireFormat = o.optString("wire_format", "openai"),
                baseUrl = o.optString("base_url", "").trimEnd('/'),
                requiresKey = o.optBoolean("requires_key", false),
                chatEndpoint = o.optString("chat_endpoint", "/chat/completions"),
                modelsEndpoint = if (o.isNull("models_endpoint")) null
                                 else o.optString("models_endpoint", ""),
                staticModels = models.filter { it.isNotEmpty() },
            )
        }
        return out
    }
}
