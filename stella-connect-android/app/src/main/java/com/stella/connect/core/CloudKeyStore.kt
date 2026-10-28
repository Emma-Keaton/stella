package com.stella.connect.core

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import org.json.JSONArray
import org.json.JSONObject
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Phase 1.6 cloud provider configuration: one JSON document
 * `{provider, api_key, base_url, model, headers{}, params{}, fallback[]}`
 * sealed with an explicit Android Keystore AES-256-GCM key.
 *
 * Only `Base64(iv || ciphertext)` is ever written to disk - no plaintext key
 * material in prefs, and the wrapping key never leaves the Keystore.
 */
data class CloudProviderConfig(
    val provider: String,
    val apiKey: String,
    val baseUrl: String? = null,
    val model: String? = null,
    val headers: Map<String, String> = emptyMap(),
    val params: Map<String, String> = emptyMap(),
    val fallback: List<String> = emptyList(),
) {
    fun toJson(): String = JSONObject().apply {
        put("provider", provider)
        put("api_key", apiKey)
        if (!baseUrl.isNullOrBlank()) put("base_url", baseUrl)
        if (!model.isNullOrBlank()) put("model", model)
        put("headers", JSONObject(headers as Map<*, *>))
        put("params", JSONObject(params as Map<*, *>))
        put("fallback", JSONArray(fallback))
    }.toString()

    companion object {
        /** Preset providers from the Phase 1.6 contract; `custom` uses base_url. */
        val KNOWN_PROVIDERS = listOf(
            "groq", "gemini", "openai", "anthropic",
            "openrouter", "ollama", "lmstudio", "custom",
        )

        fun fromJson(json: String): CloudProviderConfig? {
            return try {
                val o = JSONObject(json)
                val provider = o.optString("provider", "").trim().lowercase()
                if (provider.isEmpty()) return null
                CloudProviderConfig(
                    provider = provider,
                    apiKey = o.optString("api_key", ""),
                    baseUrl = o.optString("base_url", "").ifBlank { null },
                    model = o.optString("model", "").ifBlank { null },
                    headers = o.optJSONObject("headers")?.let { j ->
                        j.keys().asSequence().associateWith { j.optString(it, "") }
                    } ?: emptyMap(),
                    params = o.optJSONObject("params")?.let { j ->
                        j.keys().asSequence().associateWith { j.optString(it, "") }
                    } ?: emptyMap(),
                    fallback = o.optJSONArray("fallback")?.let { a ->
                        (0 until a.length()).map { a.optString(it, "") }.filter { it.isNotBlank() }
                    } ?: emptyList(),
                )
            } catch (_: Exception) {
                null
            }
        }
    }
}

object CloudKeyStore {
    private const val PREFS_NAME = "stella_cloud_config"
    private const val KEY_BLOB = "config_blob"
    private const val KEY_ALIAS = "stella_cloud_cfg_key"
    private const val TRANSFORMATION = "AES/GCM/NoPadding"
    private const val GCM_TAG_BITS = 128
    private const val GCM_IV_BYTES = 12

    private fun prefs(ctx: Context): SharedPreferences =
        ctx.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    /** Keystore-held AES-256 key; created lazily, never exported. */
    private fun keystoreKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        gen.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return gen.generateKey()
    }

    fun save(ctx: Context, config: CloudProviderConfig) {
        val iv = ByteArray(GCM_IV_BYTES).also { SecureRandom().nextBytes(it) }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, keystoreKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
        val ciphertext = cipher.doFinal(config.toJson().toByteArray(Charsets.UTF_8))
        val payload = Base64.encodeToString(iv + ciphertext, Base64.NO_WRAP)
        prefs(ctx).edit().putString(KEY_BLOB, payload).apply()
    }

    fun load(ctx: Context): CloudProviderConfig? {
        var payload = prefs(ctx).getString(KEY_BLOB, null)
        if (payload == null) {
            migrateLegacyApiKey(ctx)
            payload = prefs(ctx).getString(KEY_BLOB, null) ?: return null
        }
        return try {
            val all = Base64.decode(payload, Base64.NO_WRAP)
            if (all.size <= GCM_IV_BYTES) return null
            val iv = all.copyOfRange(0, GCM_IV_BYTES)
            val ciphertext = all.copyOfRange(GCM_IV_BYTES, all.size)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, keystoreKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
            CloudProviderConfig.fromJson(String(cipher.doFinal(ciphertext), Charsets.UTF_8))
        } catch (_: Exception) {
            null
        }
    }

    fun clear(ctx: Context) {
        prefs(ctx).edit().remove(KEY_BLOB).apply()
    }

    fun isConfigured(ctx: Context): Boolean = load(ctx)?.apiKey?.isNotBlank() == true

    // ---- Legacy Settings API: folded onto the single provider config. ----

    fun setApiKey(ctx: Context, key: String?) {
        if (key.isNullOrBlank()) {
            clearApiKey(ctx)
            return
        }
        val current = load(ctx)
        save(
            ctx,
            (current ?: CloudProviderConfig(provider = "custom", apiKey = "")).copy(apiKey = key),
        )
    }

    fun getApiKey(ctx: Context): String? = load(ctx)?.apiKey?.takeIf { it.isNotBlank() }

    fun clearApiKey(ctx: Context) = clear(ctx)

    /** One-shot import of the pre-1.6 EncryptedSharedPreferences api key. */
    private fun migrateLegacyApiKey(ctx: Context) {
        try {
            val app = ctx.applicationContext
            val master = MasterKey.Builder(app).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
            val old = EncryptedSharedPreferences.create(
                app, "stella_cloud", master,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
            )
            val key = old.getString("cloud_api_key", null)
            if (!key.isNullOrBlank()) {
                save(ctx, CloudProviderConfig(provider = "custom", apiKey = key))
            }
        } catch (_: Exception) {
            // Legacy store absent or unreadable - nothing to migrate.
        }
    }
}
