package com.stella.connect.core

import android.content.Context
import android.content.Intent
import android.net.Uri

/**
 * Memory Vault settings: the user's opt-in notes destination.
 *
 * Activation + a SAF tree URI (picked with [androidx.activity.result.contract
 * .ActivityResultContracts.OpenDocumentTree] and a persistable read/write
 * grant) live in app-private preferences. The tree URI is the default
 * destination for every note_* device command; when the vault is off (or no
 * folder was chosen) notes fall back to app-scoped storage - never the raw
 * external root.
 */
object MemoryVaultStore {
    private const val PREFS = "stella_memory_vault"
    private const val KEY_ENABLED = "vault_enabled"
    private const val KEY_TREE_URI = "vault_tree_uri"

    private fun prefs(ctx: Context) =
        ctx.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun isEnabled(ctx: Context): Boolean = prefs(ctx).getBoolean(KEY_ENABLED, false)

    fun setEnabled(ctx: Context, enabled: Boolean) {
        prefs(ctx).edit().putBoolean(KEY_ENABLED, enabled).apply()
    }

    /** Raw persisted tree URI, independent of the activation toggle. */
    fun treeUri(ctx: Context): Uri? =
        prefs(ctx).getString(KEY_TREE_URI, null)?.let { runCatching { Uri.parse(it) }.getOrNull() }

    fun setTreeUri(ctx: Context, uri: Uri?) {
        prefs(ctx).edit().putString(KEY_TREE_URI, uri?.toString()).apply()
    }

    /**
     * The destination the note commands should actually write to: the chosen
     * tree only when the vault is switched on *and* a folder is stored.
     */
    fun activeTreeUri(ctx: Context): Uri? = if (isEnabled(ctx)) treeUri(ctx) else null

    /** Persist the read+write grant for [uri]; call right after picking. */
    fun takePersistableGrant(ctx: Context, uri: Uri): Boolean = try {
        ctx.contentResolver.takePersistableUriPermission(
            uri,
            Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION,
        )
        true
    } catch (_: Exception) {
        false
    }

    /** Drop the vault entirely: toggle off, URI + grants released. */
    fun clear(ctx: Context) {
        treeUri(ctx)?.let { uri ->
            try {
                ctx.contentResolver.releasePersistableUriPermission(
                    uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION,
                )
            } catch (_: Exception) {}
        }
        prefs(ctx).edit().remove(KEY_ENABLED).remove(KEY_TREE_URI).apply()
    }
}
