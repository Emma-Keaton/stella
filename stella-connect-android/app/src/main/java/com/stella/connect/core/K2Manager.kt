package com.stella.connect.core

import com.stella.connect.BuildConfig
import java.io.File
import java.io.RandomAccessFile
import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * K2 Horizon on-device runtime.
 *
 * Owns the ARM64 llama-server binary lifecycle (start/stop/health at
 * 127.0.0.1:11435) and the GGUF weights.
 *
 * Two build shapes share one code path:
 *
 *  - BUNDLED (personal sideload build): BuildConfig.K2_BUNDLED is true and the
 *    APK carries assets/k2/{llama-server, *.gguf}. On first launch we install
 *    that pair into app-private files/k2/ once, then never touch the network.
 *    llama.cpp needs a real path, and APK assets are not one, so the copy is
 *    unavoidable; everything after it is offline.
 *
 *  - DOWNLOAD (default / CI build): no model in the package. Pull the GGUF
 *    once over HTTP with Range resume into the same files/k2/ directory.
 *
 * Either way the runtime sits outside anything an app update swaps out, so an
 * OTA cannot silently replace or delete the weights.
 *
 * Modes: LOCAL (server here) -> DESKTOP (relay to the PC gateway) -> CLOUD.
 * ChatScreen reads [mode] + [statusLine] and never touches sockets itself.
 */
object K2Manager {
    private const val PORT = 11435
    private const val DOWNLOAD_MODEL_FILE = "K2-Horizon-1B-Q4_K_M.gguf"
    private const val MODEL_URL =
        "https://huggingface.co/IFM/K2-Horizon-0.9B-GGUF/resolve/main/" + DOWNLOAD_MODEL_FILE
    private const val MIN_MODEL_BYTES = 100L * 1024 * 1024
    private const val SERVER_ASSET = "k2/llama-server"

    private val _mode = MutableStateFlow("LOCAL")
    val mode: StateFlow<String> = _mode
    private val _statusLine = MutableStateFlow("K2 idle")
    val statusLine: StateFlow<String> = _statusLine
    private val _progress = MutableStateFlow(-1f)
    val downloadProgress: StateFlow<Float> = _progress

    private var serverProc: Process? = null

    /** True when this APK ships the K2 runtime and weights. */
    val bundled: Boolean = BuildConfig.K2_BUNDLED

    /** Filename of the GGUF baked into this APK ("" when not bundled). */
    private val bundledModelName: String =
        if (bundled && BuildConfig.K2_BUNDLED_MODEL.isNotBlank())
            BuildConfig.K2_BUNDLED_MODEL else ""

    fun k2Dir(ctx: Context): File = File(ctx.filesDir, "k2").apply { mkdirs() }

    private fun serverFile(ctx: Context): File = File(k2Dir(ctx), "llama-server")

    private fun downloadedModel(ctx: Context): File = File(k2Dir(ctx), DOWNLOAD_MODEL_FILE)

    private fun usable(f: File): Boolean = f.exists() && f.length() > MIN_MODEL_BYTES

    private fun assetExists(ctx: Context, path: String): Boolean = try {
        ctx.assets.open(path).use { true }
    } catch (_: Exception) {
        false
    }

    /** True when weights are ready on disk, whichever way they got there. */
    fun modelPresent(ctx: Context): Boolean =
        (bundled && usable(File(k2Dir(ctx), bundledModelName))) ||
            usable(downloadedModel(ctx))

    /** Copy the bundled ARM64 server binary out of assets and mark it runnable. */
    fun ensureServer(ctx: Context): Boolean = try {
        val dst = serverFile(ctx)
        if (!usable(dst) && !dst.exists()) {
            ctx.assets.open(SERVER_ASSET).use { inp ->
                val part = File(dst.path + ".part")
                part.outputStream().use { out -> inp.copyTo(out, 1 shl 20) }
                part.renameTo(dst)
            }
        }
        dst.setExecutable(true)
        dst.exists() && dst.canExecute()
    } catch (_: Exception) {
        false
    }

    /**
     * Install the bundled GGUF into files/k2/ once. Reports progress through
     * [downloadProgress] even though nothing is being downloaded, so the UI can
     * reuse one progress path for both build shapes.
     */
    suspend fun installBundledModel(ctx: Context): Boolean = withContext(Dispatchers.IO) {
        if (!bundled || bundledModelName.isBlank()) return@withContext false
        val dst = File(k2Dir(ctx), bundledModelName)
        if (usable(dst)) {
            _progress.value = 1f
            return@withContext true
        }
        val part = File(dst.path + ".part")
        var copied = 0L
        return@withContext try {
            ctx.assets.open("k2/$bundledModelName").use { inp ->
                part.outputStream().use { out ->
                    val buf = ByteArray(1 shl 20)
                    while (true) {
                        val n = inp.read(buf)
                        if (n <= 0) break
                        out.write(buf, 0, n)
                        copied += n
                        _progress.value =
                            (copied.toFloat() / 666_000_000f).coerceIn(0f, 0.99f)
                    }
                }
            }
            val ok = usable(part) && part.renameTo(dst)
            _progress.value = if (ok) 1f else -1f
            ok
        } catch (_: Exception) {
            part.delete()
            _progress.value = -1f
            false
        }
    }

    /** Human-readable name of a SAF content URI, or a stable fallback. */
    private fun displayName(ctx: Context, uri: Uri): String {
        var name = ""
        try {
            ctx.contentResolver.query(uri, null, null, null, null)?.use { c ->
                val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (idx >= 0 && c.moveToFirst()) name = c.getString(idx) ?: ""
            }
        } catch (_: Exception) {}
        if (name.isBlank()) name = uri.lastPathSegment?.substringAfterLast('/') ?: "model.gguf"
        // Force the .gguf extension so resolveModel's suffix scan always sees it.
        if (!name.endsWith(".gguf", ignoreCase = true)) name = "$name.gguf"
        return name
    }

    /**
     * Import a GGUF the user already has on the device (Downloads, a folder,
     * an SD card) into files/k2/ so the on-device runtime can use it - no
     * download, no HuggingFace round-trip.
     *
     * @param uri content:// URI from the system file picker (ACTION_OPEN_DOCUMENT).
     * @return true when the model was copied and passes validation.
     */
    suspend fun importLocalModel(ctx: Context, uri: Uri): Boolean =
        withContext(Dispatchers.IO) {
            // Stop the running server first: on some kernels a mapped mmap file
            // cannot be overwritten in place while llama-server holds it open.
            stop()
            val name = displayName(ctx, uri)
            val dst = File(k2Dir(ctx), name)
            val part = File(dst.path + ".part")
            _progress.value = 0f
            try {
                var total = -1L
                try {
                    ctx.contentResolver.query(uri, null, null, null, null)?.use { c ->
                        val idx = c.getColumnIndex(OpenableColumns.SIZE)
                        if (idx >= 0 && c.moveToFirst() && !c.isNull(idx)) total = c.getLong(idx)
                    }
                } catch (_: Exception) {}
                var copied = 0L
                ctx.contentResolver.openInputStream(uri).use { inp ->
                    requireNotNull(inp) { "Cannot open the selected file." }
                    part.outputStream().use { out ->
                        val buf = ByteArray(1 shl 20)
                        while (true) {
                            val n = inp.read(buf)
                            if (n <= 0) break
                            out.write(buf, 0, n)
                            copied += n
                            if (total > 0) _progress.value = (copied.toFloat() / total).coerceIn(0f, 0.99f)
                        }
                    }
                }
                // Reject non-GGUF early: llama.cpp would just crash with a cryptic
                // error, and a zero-byte pick is always a mistake.
                if (copied < MIN_MODEL_BYTES) {
                    part.delete(); _progress.value = -1f
                    _statusLine.value = "That file is too small to be a model"
                    return@withContext false
                }
                part.inputStream().use { ins ->
                    val magic = ByteArray(4)
                    if (ins.read(magic) != 4 || String(magic) != "GGUF") {
                        part.delete(); _progress.value = -1f
                        _statusLine.value = "That file is not a GGUF model"
                        return@withContext false
                    }
                }
                if (dst.exists()) dst.delete()
                val ok = part.renameTo(dst)
                _progress.value = if (ok) 1f else -1f
                _statusLine.value = if (ok) "Loaded $name" else "Could not save $name"
                if (ok) _mode.value = "LOCAL"
                ok
            } catch (e: Exception) {
                part.delete(); _progress.value = -1f
                _statusLine.value = "Import failed: ${e.message ?: "unknown error"}"
                false
            }
        }

    /** Delete every local weight file (imported or downloaded). */
    fun deleteLocalModel(ctx: Context): Boolean {
        stop()
        return try {
            val dir = k2Dir(ctx)
            var removed = false
            dir.listFiles { f -> f.isFile && f.name.endsWith(".gguf") }?.forEach { f ->
                if (f.delete()) removed = true
            }
            _progress.value = -1f
            _statusLine.value = if (removed) "Local model removed" else "No local model to remove"
            removed
        } catch (_: Exception) {
            false
        }
    }


    /** Weights on disk, or null. Does no I/O beyond a stat. */
    private fun resolveModel(ctx: Context): File? {
        if (bundled && bundledModelName.isNotBlank()) {
            val f = File(k2Dir(ctx), bundledModelName)
            if (usable(f)) return f
        }
        val d = downloadedModel(ctx)
        if (usable(d)) return d
        // An imported model (picked from device storage) may have any name, so
        // fall back to the first usable .gguf in the runtime dir. Covers the
        // "load a model already on my phone" path and survives process restarts.
        val dir = k2Dir(ctx)
        val candidates = dir.listFiles { f -> f.isFile && f.name.endsWith(".gguf") } ?: emptyArray()
        return candidates.firstOrNull { usable(it) }
    }

    /**
     * Get the runtime ready without assuming a network. Bundled builds install
     * from assets; download builds fetch. Returns true when start() can run.
     */
    suspend fun prepare(ctx: Context): Boolean {
        ensureServer(ctx)
        if (modelPresent(ctx)) {
            _progress.value = 1f
            return true
        }
        if (bundled && installBundledModel(ctx)) return true
        return downloadModel(ctx)
    }

    /** Resumable model download (.part + Range). Returns true when complete. */
    suspend fun downloadModel(ctx: Context): Boolean = withContext(Dispatchers.IO) {
        if (modelPresent(ctx)) {
            _progress.value = 1f
            return@withContext true
        }
        val dst = downloadedModel(ctx)
        val part = File(dst.path + ".part")
        var have = if (part.exists()) part.length() else 0L
        var conn: HttpURLConnection? = null
        try {
            repeat(8) { attempt ->
                try {
                    conn = (URL(MODEL_URL).openConnection() as HttpURLConnection).apply {
                        connectTimeout = 30_000; readTimeout = 30_000
                        if (have > 0) setRequestProperty("Range", "bytes=$have-")
                        setRequestProperty("User-Agent", "stella-k2-android/1.0")
                    }
                    val code = conn!!.responseCode
                    if (code == 200 && have > 0) have = 0 // server ignored Range
                    if (code != 200 && code != 206) throw java.io.IOException("HTTP $code")
                    val total = (conn!!.getHeaderField("Content-Length")?.toLongOrNull()
                        ?: -1L) + have
                    RandomAccessFile(part, "rw").use { raf ->
                        raf.seek(have)
                        val buf = ByteArray(262144)
                        var n: Int
                        val inp = conn!!.inputStream
                        while (inp.read(buf).also { n = it } != -1) {
                            raf.write(buf, 0, n)
                            have += n
                            if (total > 0) _progress.value = (have.toFloat() / total).coerceIn(0f, 1f)
                        }
                    }
                    if (total <= 0 || have >= total) {
                        part.renameTo(dst)
                        _progress.value = 1f
                        return@withContext true
                    }
                } catch (e: Exception) {
                    if (attempt == 7) throw e
                    kotlinx.coroutines.delay(minOf(30_000L, 2000L shl attempt))
                } finally {
                    conn?.disconnect(); conn = null
                }
            }
            false
        } catch (_: Exception) {
            _statusLine.value = "Model download paused - retry on Wi-Fi"
            false
        }
    }

    fun start(ctx: Context): Boolean {
        if (isRunning()) return true
        if (!ensureServer(ctx)) {
            _mode.value = "DESKTOP"; return false
        }
        val model = resolveModel(ctx)
        if (model == null) {
            _mode.value = "DESKTOP"; return false
        }
        return try {
            serverProc = ProcessBuilder(
                serverFile(ctx).absolutePath,
                "-m", model.absolutePath,
                "--port", PORT.toString(), "-c", "2048"
            ).redirectErrorStream(true).start()
            Thread.sleep(1500)
            val ok = isRunning()
            _statusLine.value = if (ok) "K2 local ready" else "K2 failed - relaying"
            if (!ok) _mode.value = "DESKTOP"
            ok
        } catch (_: Exception) {
            _mode.value = "DESKTOP"; false
        }
    }

    fun isRunning(): Boolean {
        serverProc?.let { if (it.isAlive) return true }
        return try {
            val c = URL("http://127.0.0.1:$PORT/health").openConnection() as HttpURLConnection
            c.connectTimeout = 2000
            (c.responseCode == 200).also { c.disconnect() }
        } catch (_: Exception) {
            false
        }
    }

    fun stop() {
        try { serverProc?.destroy() } catch (_: Exception) {}
        serverProc = null
        _statusLine.value = "K2 stopped"
    }

    /** POST an OpenAI-style chat body; null when the local server is unusable. */
    suspend fun chat(messagesJson: String, maxTokens: Int = 256): String? =
        withContext(Dispatchers.IO) {
            try {
                val c = (URL("http://127.0.0.1:$PORT/v1/chat/completions").openConnection()
                        as HttpURLConnection).apply {
                    requestMethod = "POST"; connectTimeout = 15_000; readTimeout = 120_000
                    setRequestProperty("Content-Type", "application/json")
                    doOutput = true
                }
                val body = JSONObject()
                    .put("model", "k2")
                    .put("messages", org.json.JSONArray(messagesJson))
                    .put("max_tokens", maxTokens).toString()
                c.outputStream.use { it.write(body.toByteArray()) }
                if (c.responseCode != 200) return@withContext null
                val text = c.inputStream.bufferedReader().readText()
                JSONObject(text).optJSONArray("choices")
                    ?.optJSONObject(0)?.optJSONObject("message")
                    ?.optString("content")
            } catch (_: Exception) {
                null
            }
        }
}