package com.stella.connect.core

import java.io.File
import java.io.RandomAccessFile
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.OpenableColumns
import android.util.Log
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import org.json.JSONObject

/**
 * Local inference engine: llama-server lifecycle + GGUF weights.
 *
 * It no longer runs one model family - it sniffs each GGUF's
 * `general.architecture` at load and routes it to whichever of the two
 * server builds (upstream llama.cpp, MBZUAI/K2Horizon fork) can run it,
 * preferring the saved runtime choice.
 *
 * Models live in the user's chosen folder (default: shared internal storage
 * Stella/models/); the file-picker imports there and downloads stream there.
 * Nothing is bundled in the APK. The legacy files/k2/ dir is scanned only
 * for migration.
 *
 * Either way the runtime sits outside anything an app update swaps out, so an
 * OTA cannot silently replace or delete the weights.
 *
 * Modes: LOCAL (engine here) -> DESKTOP (relay to the PC gateway) -> CLOUD.
 * ChatScreen reads [mode] + [statusLine] and never touches sockets itself.
 */
object LocalEngineManager {
    private const val PORT = 11435
    private const val MIN_MODEL_BYTES = 100L * 1024 * 1024

    /** This plain build never ships a bundled runtime or model. */
    val bundled: Boolean = false
    private val TAG = "LocalEngineManager"

    /** Shared device directory for GGUF weights: <shared storage>/Stella/models/ */
    fun sharedModelsDir(): File {
        val base = Environment.getExternalStorageDirectory()
        return File(base, "Stella/models").apply { mkdirs() }
    }

    /** Local internal fallback directory */
    fun appInternalModelsDir(ctx: Context): File = File(ctx.filesDir, "models").apply { mkdirs() }

    private const val PREF_MODELS_FOLDER = "stella_models_folder_uri"
    private const val PREF_MODELS_FOLDER_PATH = "stella_models_folder_path"

    /** Persist the user's chosen models library folder (SAF tree URI). */
    fun setModelsFolderUri(ctx: Context, uri: Uri) {
        try {
            ctx.getSharedPreferences("stella_prefs", Context.MODE_PRIVATE)
                .edit().putString(PREF_MODELS_FOLDER, uri.toString()).apply()
            // Try to also persist a real filesystem path when the folder is one:
            // SAF URIs cannot be mmap'd by llama-server, so a real path is needed
            // to actually load a model. For external-storage public dirs the path
            // is derived below; otherwise scan keeps using the default root.
            resolveRealPath(ctx, uri)?.let { setModelsFolderPath(ctx, it) }
        } catch (_: Exception) {}
    }

    /** Persist a real filesystem path for the models folder (File-based I/O). */
    fun setModelsFolderPath(ctx: Context, path: String) {
        try {
            ctx.getSharedPreferences("stella_prefs", Context.MODE_PRIVATE)
                .edit().putString(PREF_MODELS_FOLDER_PATH, path).apply()
        } catch (_: Exception) {}
    }

    /** The user's chosen real models folder path, when it resolves to one. */
    fun getModelsFolderPath(ctx: Context): String? {
        return try {
            ctx.getSharedPreferences("stella_prefs", Context.MODE_PRIVATE)
                .getString(PREF_MODELS_FOLDER_PATH, null)?.takeIf { it.isNotBlank() }
        } catch (_: Exception) { null }
    }

    /**
     * Best-effort mapping of a SAF tree URI to a real filesystem path.
     * Returns a File only when the URI is a document-tree on primary external
     * storage (the only case we can map without Storage Access tricks).
     */
    private fun resolveRealPath(ctx: Context, uri: Uri): String? {
        return try {
            val docId = android.provider.DocumentsContract.getTreeDocumentId(uri) ?: return null
            // Format is usually "primary:Stella/models" for external storage.
            val parts = docId.split(":", limit = 2)
            if (parts.size != 2 || parts[0].lowercase() != "primary") return null
            val base = Environment.getExternalStorageDirectory()
            val f = File(base, parts[1])
            f.apply { mkdirs() }
            if (f.exists() && f.canRead()) f.absolutePath else null
        } catch (_: Exception) { null }
    }

    /** The user's chosen models library folder, if any was picked in Settings. */
    fun getModelsFolderUri(ctx: Context): Uri? {
        return try {
            val s = ctx.getSharedPreferences("stella_prefs", Context.MODE_PRIVATE)
                .getString(PREF_MODELS_FOLDER, null)
            if (s.isNullOrBlank()) null else Uri.parse(s)
        } catch (_: Exception) { null }
    }

    /**
     * The directory Stella scans for runnable GGUF weights.
     * Defaults to shared internal storage (/sdcard/Stella/models) which works
     * for every user via getExternalStorageDirectory(); a user-chosen folder
     * wins when it resolves to a real filesystem path (see resolveRealPath).
     */
    fun modelsRootDir(ctx: Context): File {
        val custom = getModelsFolderPath(ctx)?.let { File(it) }
        if (custom != null) {
            try {
                custom.apply { mkdirs() }
                if (custom.exists() && custom.canRead()) return custom
            } catch (_: Exception) {}
        }
        return sharedModelsDir()
    }

    /** Human-readable label for the current models root (for the UI). */
    fun modelsRootLabel(ctx: Context): String {
        val root = try { modelsRootDir(ctx) } catch (_: Exception) { return "shared storage" }
        val base = try { Environment.getExternalStorageDirectory().absolutePath } catch (_: Exception) { "" }
        return if (base.isNotBlank() && root.absolutePath.startsWith(base)) {
            root.absolutePath.removePrefix(base).trimStart('/').ifBlank { "shared storage" }
        } else root.absolutePath
    }

    /** True when the user has explicitly chosen a models folder (download gate). */
    fun hasUserFolder(ctx: Context): Boolean = getModelsFolderUri(ctx) != null || getModelsFolderPath(ctx) != null

    /** Legacy directory kept for upgrades: older builds staged weights under files/k2/. */
    private const val LEGACY_MODELS_DIR_NAME = "k2"

    /**
     * Descriptor of a GGUF model sitting on the device.
     * @param file  on-disk GGUF path
     * @param name  human-readable name (filename by default)
     * @param arch  GGUF `general.architecture` sniffed from the header, or ""
     * @param sizeBytes file size in bytes
     */
    data class LocalModel(
        val file: File,
        val name: String,
        val arch: String,
        val sizeBytes: Long,
    )

    /** A downloadable model catalogue entry from HuggingFace. */
    data class CatalogEntry(
        val id: String,
        val label: String,
        val repo: String,            // e.g. "bartowski/Llama-3.2-1B-Instruct-GGUF"
        val filename: String,        // exact GGUF file name in the repo
        val url: String,             // https://huggingface.co/.../resolve/main/<filename>
        val minRamMb: Long,          // recommended free RAM (MB) to run comfortably
        val minStorageMb: Long,      // recommended free storage (MB)
    )

    /** Verified HuggingFace GGUF entries. Device specs (RAM/storage) pick the best fit at runtime. */
    object ModelCatalog {
        private const val HF = "https://huggingface.co"

        private fun entry(repo: String, filename: String, label: String, minRamMb: Long, minStorageMb: Long): CatalogEntry =
            CatalogEntry(
                id = repo.replace("/", "-").lowercase(),
                label = label,
                repo = repo,
                filename = filename,
                url = "$HF/$repo/resolve/main/$filename",
                minRamMb = minRamMb,
                minStorageMb = minStorageMb,
            )

        /** K2-0.9B (MBZUAI fork weights, also shipped under the "1B" spelling upstream). */
        val K2_0_9B = entry(
            repo = "IFM/K2-Horizon-0.9B-GGUF",
            filename = "K2-Horizon-1B-Q4_K_M.gguf",
            label = "K2-Horizon 0.9B",
            minRamMb = 2048,
            minStorageMb = 1024,
        )

        /** Llama-3.2-1B Instruct (bartowski quantised GGUF). */
        val LLAMA_3_2_1B = entry(
            repo = "bartowski/Llama-3.2-1B-Instruct-GGUF",
            filename = "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
            label = "Llama-3.2-1B Instruct",
            minRamMb = 2048,
            minStorageMb = 1024,
        )

        /** MobileLLM 1.5B (mradermacher quantised GGUF). */
        val MOBILELLM_1_5B = entry(
            repo = "mradermacher/MobileLLM-1.5B-GGUF",
            filename = "MobileLLM-1.5B.Q4_K_M.gguf",
            label = "MobileLLM 1.5B",
            minRamMb = 3072,
            minStorageMb = 1536,
        )

        val all: List<CatalogEntry> = listOf(K2_0_9B, LLAMA_3_2_1B, MOBILELLM_1_5B)
    }

    /** Which engine build to run. Mirrors core/engine_runtime.py. */
    const val RUNTIME_LLAMACPP = "llama.cpp"
    const val RUNTIME_MBZUAI = "mbuzai"
    const val RUNTIME_DEFAULT = RUNTIME_LLAMACPP
    val RUNTIMES = listOf(RUNTIME_LLAMACPP, RUNTIME_MBZUAI)

    private val _runtime = MutableStateFlow(RUNTIME_DEFAULT)
    val runtime: StateFlow<String> = _runtime

    private val _mode = MutableStateFlow("LOCAL")
    val mode: StateFlow<String> = _mode
    private val _statusLine = MutableStateFlow("Local engine idle")
    val statusLine: StateFlow<String> = _statusLine
    private val _progress = MutableStateFlow(-1f)
    val downloadProgress: StateFlow<Float> = _progress

    private var serverProc: Process? = null



    fun k2Dir(ctx: Context): File = File(ctx.filesDir, LEGACY_MODELS_DIR_NAME).apply { mkdirs() }

    /**
     * Pick the llama.cpp runtime. Both runtimes load K2 and every other GGUF,
     * so this is a preference, not a capability switch.
     *
     * The choice is persisted per-package (both the public and the .k2 build
     * can be installed side by side, and each keeps its own preference), and
     * takes effect the next time the server starts.
     */
    fun setRuntime(ctx: Context, id: String) {
        val chosen = if (id in RUNTIMES) id else RUNTIME_DEFAULT
        _runtime.value = chosen
        try {
            ctx.getSharedPreferences("stella_k2", Context.MODE_PRIVATE)
                .edit().putString("runtime", chosen).apply()
        } catch (_: Exception) {}
    }

    /** Restore the persisted runtime choice. Call once at startup. */
    fun loadRuntime(ctx: Context) {
        try {
            val saved = ctx.getSharedPreferences("stella_k2", Context.MODE_PRIVATE)
                .getString("runtime", RUNTIME_DEFAULT) ?: RUNTIME_DEFAULT
            _runtime.value = if (saved in RUNTIMES) saved else RUNTIME_DEFAULT
        } catch (_: Exception) {}
    }

    /** On-disk GGUF path for a given catalog entry (canonical models root location). */
    fun modelFileFor(ctx: Context, entry: LocalEngineManager.CatalogEntry): File =
        File(modelsRootDir(ctx), entry.filename)

    /**
     * Repurposed from the legacy downloaded-model path: find an interrupted
     * download (a leftover *.part in the models root that matches a catalog
     * entry) so a killed process resumes instead of failing silently.
     * Downloads are resumable via HTTP Range inside [downloadModel].
     */
    private fun findInterruptedDownload(ctx: Context): CatalogEntry? {
        return try {
            val root = modelsRootDir(ctx)
            val parts = root.listFiles { f ->
                f.isFile && f.name.endsWith(".part", ignoreCase = true)
            } ?: return null
            for (part in parts) {
                val wanted = part.name.removeSuffix(".part")
                val entry = ModelCatalog.all.firstOrNull { it.filename == wanted }
                if (entry != null) return entry
            }
            null
        } catch (_: Exception) { null }
    }

    /** Scans for *.gguf across the models root, app-internal files/models/ and legacy files/k2/. */
    fun scanLocalModels(ctx: Context): List<LocalModel> {
        val searchDirs = listOf(
            modelsRootDir(ctx),
            appInternalModelsDir(ctx),
            k2Dir(ctx)
        ).filter { it.exists() && it.canRead() }
        val seen = mutableSetOf<String>()
        val models = mutableListOf<LocalModel>()
        for (dir in searchDirs) {
            dir.listFiles { f -> f.isFile && f.name.endsWith(".gguf", ignoreCase = true) }
                ?.forEach { f ->
                    if (seen.add(f.name)) {
                        models.add(
                            LocalModel(
                                file = f,
                                name = f.nameWithoutExtension,
                                arch = ggufArchitecture(f),
                                sizeBytes = f.length(),
                            )
                        )
                    }
                }
        }
        return models.sortedByDescending { it.sizeBytes }
    }

    /** True when any usable GGUF exists on disk (models/ or legacy k2/). */
    fun modelPresent(ctx: Context): Boolean = scanLocalModels(ctx).any { it.sizeBytes > MIN_MODEL_BYTES }

    /**
     * Pick the best model to run: the first usable scanned GGUF.
     * Returns null when no weights are present.
     */
    fun resolveModel(ctx: Context): LocalModel? =
        scanLocalModels(ctx).firstOrNull { it.sizeBytes > MIN_MODEL_BYTES }

    /**
     * Can this device run [entry] locally? Compares free storage + RAM against the
     * catalogue entry's minimums. When false, the UI should offer a cloud API key instead.
     */
    fun deviceCanRunLocally(ctx: Context, entry: LocalEngineManager.CatalogEntry): Boolean {
        val storageDir = sharedModelsDir()
        val freeStorageMb = storageDir.freeSpace / (1024 * 1024)
        if (freeStorageMb < entry.minStorageMb) return false
        // RAM: rough headroom check using the activity manager.
        val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
        val memInfo = android.app.ActivityManager.MemoryInfo()
        am.getMemoryInfo(memInfo)
        val freeRamMb = memInfo.availMem / (1024 * 1024)
        return freeRamMb >= entry.minRamMb
    }

    /**
     * On-disk binary slots (files/k2/). The bundle that shipped on 2026-10-15
     * carried the MBZUAI/K2Horizon fork as a single file called `llama-server`.
     * ensureServer() rehomes that legacy file into the FORK slot instead of
     * re-downloading anything, and fills whichever slot its staged asset
     * exists for. The slots let start() pick per model architecture.
     */
    private const val SERVER_FILE_FORK = "llama-server-mbuzai"
    private const val SERVER_FILE_UPSTREAM = "llama-server-upstream"
    private const val LEGACY_SERVER_FILE = "llama-server"

    /** jniLib names (gradle -PstellaK2StageJni) - exec'd from nativeLibraryDir. */
    private const val JNI_SERVER_FORK = "libstella-server-mbuzai.so"
    private const val JNI_SERVER_UPSTREAM = "libstella-server-upstream.so"
    private const val JNI_SERVER_LEGACY = "libllama-server.so"

    private const val ARCH_K2 = "k2-horizon"

    /** Assets that can fill an empty slot (staged only in k2 bundle builds). */
    const val ENGINE_ASSET_FORK = "k2/llama-server-mbuzai"
    const val ENGINE_ASSET_UPSTREAM = "k2/llama-server-upstream"

    // GGUF value-type ids, same family as the C++ gguf.h this fork ships
    // (ground truth, verified against real K2 + qwen2 files): the key and
    // string lengths are u64, BOOL=7, STRING=8, ARRAY=9.
    private const val GGUF_V_BOOL = 7
    private const val GGUF_V_STRING = 8
    private const val GGUF_V_ARRAY = 9
    private val GGUF_FIXED = mapOf(0 to 1, 1 to 1, 2 to 2, 3 to 2, 4 to 4,
        5 to 4, 6 to 4, 7 to 1, 10 to 8, 11 to 8, 12 to 8)

    /** `general.architecture` straight from the GGUF header, or "" when it
     * can't be read. Reads a few KB at load time - no mmap, no model load -
     * so start() always knows which server build to run before spawning it.
     */
    fun ggufArchitecture(model: File): String = try {
        RandomAccessFile(model, "r").use { raf ->
            val head = ByteArray(64 * 1024)
            val read = raf.read(head)
            if (read < 16 || String(head, 0, 4) != "GGUF") return ""
            val bb = java.nio.ByteBuffer.wrap(head).order(java.nio.ByteOrder.LITTLE_ENDIAN)
            val version = bb.getInt(4)
            val nKv: Long
            var off: Int
            if (version < 2) {
                nKv = (bb.getInt(12).toLong() and 0xFFFFFFFFL); off = 16
            } else {
                nKv = bb.getLong(16); off = 24
            }
            repeat(minOf(nKv, 64L).toInt()) {
                if (off + 8 > read) return ""
                val klen = bb.getLong(off)
                if (klen < 0 || klen > 512) return ""
                off += 8
                if (off + klen + 4 > read) return ""
                val key = String(head, off, klen.toInt())
                off += klen.toInt()
                val vtype = bb.getInt(off); off += 4
                if (key == "general.architecture") {
                    return readTinyString(head, read, off, vtype)
                }
                off = skipGgufValue(head, read, off, vtype)
                if (off < 0) return ""
            }
            ""
        }
    } catch (_: Exception) { "" }

    /** The architecture value is always a string in practice, so parse it as
     * one whenever the id looks string-ish instead of desyncing. */
    private fun readTinyString(buf: ByteArray, limit: Int, off0: Int, vtype: Int): String {
        if (vtype != GGUF_V_STRING && vtype != GGUF_V_BOOL) return ""
        if (off0 + 8 > limit) return ""
        val bb = java.nio.ByteBuffer.wrap(buf).order(java.nio.ByteOrder.LITTLE_ENDIAN)
        val slen = bb.getLong(off0)
        if (slen < 0 || slen > 64 || off0 + 8 + slen > limit) return ""
        return String(buf, off0 + 8, slen.toInt())
    }

    private fun skipGgufValue(buf: ByteArray, limit: Int, off0: Int, vtype: Int): Int {
        var off = off0
        GGUF_FIXED[vtype]?.let { return off + it }
        val bb = java.nio.ByteBuffer.wrap(buf).order(java.nio.ByteOrder.LITTLE_ENDIAN)
        fun need(n: Int): Boolean = off >= 0 && off + n <= limit
        if (vtype == GGUF_V_STRING) {
            if (!need(8)) return -1
            val n = bb.getLong(off); off += 8
            if (n < 0 || off + n > limit) return -1
            return (off + n).toInt()
        }
        if (vtype == GGUF_V_ARRAY) {
            if (!need(12)) return -1
            val count = bb.getLong(off)
            val etype = bb.getInt(off + 8)
            off += 12
            if (count < 0 || count > 1_000_000) return -1
            val fixed = GGUF_FIXED[etype]
            if (fixed != null && etype != GGUF_V_ARRAY) {
                if (off + count * fixed > limit) return -1
                return (off + count * fixed).toInt()
            }
            repeat(count.toInt()) {
                off = when (etype) {
                    GGUF_V_STRING -> {
                        if (!need(8)) return -1
                        val n = bb.getLong(off); off += 8
                        if (n < 0 || off + n > limit) return -1
                        (off + n).toInt()
                    }
                    GGUF_V_ARRAY -> {
                        val o = skipGgufValue(buf, limit, off, GGUF_V_ARRAY)
                        if (o < 0) return -1
                        o
                    }
                    else -> return -1
                }
            }
            return off
        }
        return -1
    }

    private fun slotFile(ctx: Context, name: String): File = File(k2Dir(ctx), name)

    private fun nativeLibDir(ctx: Context): String = try {
        ctx.applicationInfo.nativeLibraryDir ?: ""
    } catch (_: Exception) { "" }

    private fun jniFile(ctx: Context, name: String): File? {
        val dir = nativeLibDir(ctx)
        if (dir.isBlank()) return null
        return File(dir, name).takeIf { it.exists() && it.length() > 1024 }
    }
    /**
     * Fill empty binary slots from staged assets and rehome the legacy
     * single-binary layout - never touches the network, never deletes a
     * working binary. True when any server is executable-capable (a jniLib
     * counts too). Suspends: asset copies can move 100+ MB on first run.
     */
    suspend fun ensureServer(ctx: Context): Boolean = withContext(Dispatchers.IO) {
        if (jniFile(ctx, JNI_SERVER_FORK) != null) return@withContext true
        if (jniFile(ctx, JNI_SERVER_UPSTREAM) != null) return@withContext true
        if (jniFile(ctx, JNI_SERVER_LEGACY) != null) return@withContext true
        val fork = slotFile(ctx, SERVER_FILE_FORK)
        val upstream = slotFile(ctx, SERVER_FILE_UPSTREAM)
        val legacy = slotFile(ctx, LEGACY_SERVER_FILE)
        if (serverFileUsable(fork) || serverFileUsable(upstream) || serverFileUsable(legacy))
            return@withContext true
        // Rehome the legacy single-file layout: every k2 bundle shipped the
        // MBZUAI cross-compile under the plain name, so without this the fork
        // slot would look empty forever on upgraded installs.
        if (!serverFileUsable(fork) && legacy.exists() && legacy.length() > 1024 * 1024) {
            try {
                if (fork.exists()) fork.delete()
                if (!legacy.renameTo(fork)) legacy.copyTo(fork, overwrite = true)
            } catch (_: Exception) {}
        }
        // Staged assets (bundle builds) fill whichever slot is still empty.
        copySlotAsset(ctx, ENGINE_ASSET_FORK, SERVER_FILE_FORK)
        copySlotAsset(ctx, ENGINE_ASSET_UPSTREAM, SERVER_FILE_UPSTREAM)
        if (serverFileUsable(slotFile(ctx, SERVER_FILE_FORK))) return@withContext true
        if (serverFileUsable(slotFile(ctx, SERVER_FILE_UPSTREAM))) return@withContext true
        return@withContext serverFileUsable(legacy)
    }

    private fun serverFileUsable(f: File): Boolean =
        f.exists() && f.length() > 1024 * 1024

    private fun copySlotAsset(ctx: Context, asset: String, slot: String) {
        val dst = slotFile(ctx, slot)
        if (serverFileUsable(dst) || !assetExists(ctx, asset)) return
        try {
            ctx.assets.open(asset).use { inp ->
                val part = File(dst.path + ".part")
                part.outputStream().use { out -> inp.copyTo(out, 1 shl 20) }
                part.renameTo(dst)
            }
            dst.setExecutable(true)
        } catch (_: Exception) {}
    }

    private fun usable(f: File): Boolean = f.exists() && f.length() > MIN_MODEL_BYTES

    private fun assetExists(ctx: Context, path: String): Boolean = try {
        ctx.assets.open(path).use { true }
    } catch (_: Exception) {
        false
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
     * an SD card) into files/models/ so the on-device runtime can use it -
     * no download, no HuggingFace round-trip.
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
            val dst = File(sharedModelsDir(), name)
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

    /**
     * Unload the active local model from Stella's server.
     * Files stay on device storage — re-load works without re-importing.
     * (Previously this deleted .gguf files from every scanned directory;
     * Remove is unload-only by design.)
     */
    fun deleteLocalModel(ctx: Context): Boolean {
        stop()
        return try {
            _progress.value = -1f
            _statusLine.value = "Local model unloaded"
            true
        } catch (_: Exception) {
            false
        }
    }


    /**
     * Get the runtime ready without assuming a network. Returns true when
     * start() can run (a usable model is already present).
     */
    suspend fun prepare(ctx: Context): Boolean {
        Log.d(TAG, "prepare() called")
        ensureServer(ctx)
        if (modelPresent(ctx)) {
            Log.d(TAG, "prepare(): model already present")
            _progress.value = 1f
            return true
        }
        // Resume an interrupted download instead of failing silently (the .part
        // survives a process kill and downloadModel() continues via Range).
        findInterruptedDownload(ctx)?.let {
            Log.d(TAG, "prepare(): resuming interrupted download ${it.filename}")
            return downloadModel(ctx, it)
        }
        // No forced default download: the user picks a model from the download
        // hub (or imports one). Download stays explicit via downloadModel().
        Log.d(TAG, "prepare(): no model present")
        _statusLine.value = "No model file - pick or download one"
        return false
    }

    /**
     * Download a specific catalogue entry to files/models/. Resumable
     * (.part + Range). Returns true when complete.
     */
    suspend fun downloadModel(ctx: Context, entry: LocalEngineManager.CatalogEntry): Boolean = withContext(Dispatchers.IO) {
        if (modelPresent(ctx)) {
            _progress.value = 1f
            return@withContext true
        }
        val dst = modelFileFor(ctx, entry)
        val part = File(dst.path + ".part")
        var have = if (part.exists()) part.length() else 0L
        var conn: HttpURLConnection? = null
        try {
            repeat(8) { attempt ->
                try {
                    conn = (URL(entry.url).openConnection() as HttpURLConnection).apply {
                        connectTimeout = 30_000; readTimeout = 60_000
                        if (have > 0) setRequestProperty("Range", "bytes=$have-")
                        setRequestProperty("User-Agent", "stella-android/1.0")
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
                        if (dst.exists()) dst.delete()
                        part.renameTo(dst)
                        _progress.value = 1f
                        Log.d(TAG, "downloadModel(): downloaded ${dst.name} to ${dst.parent}")
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

    /**
     * Executable server paths for `model`, best first.
     *
     * On SDK >= 29, Android W^X blocks exec() of writable app-home files, so
     * the only trusted executable is `nativeLibraryDir/libllama-server.so` (a
     * read-only jniLib extracted by AGP). When present it is returned strictly
     * alone; files/k2 and other jniLib slots are fallbacks only for SDK < 29.
     *
     * The model is sniffed at load: k2-horizon orders the fork first (K2
     * pre-tokenizer parity), every other family orders upstream first. The
     * saved runtime preference pulls its binary family to the front inside that
     * order.
     */
    fun serverCandidates(ctx: Context, model: File): List<String> {
        // Android 10+ (targetSdk 29+) enforces W^X: a writable app-home binary
        // cannot be exec()'d. The jniLib is extracted read-only to
        // nativeLibraryDir and stays executable, so it is the sole source.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val nl = nativeLibDir(ctx)
            if (nl.isNotBlank()) {
                val lib = File(nl, JNI_SERVER_LEGACY)
                if (lib.exists() && lib.length() > 1024 * 1024) {
                    return listOf(lib.absolutePath)
                }
            }
            // No nativeLibraryDir server on a W^X device: cannot run locally.
            return emptyList()
        }
        val arch = ggufArchitecture(model)
        val jniFork = jniFile(ctx, JNI_SERVER_FORK)?.absolutePath
        val jniUp = jniFile(ctx, JNI_SERVER_UPSTREAM)?.absolutePath
        val jniLegacy = jniFile(ctx, JNI_SERVER_LEGACY)?.absolutePath
        val fFork = slotFile(ctx, SERVER_FILE_FORK).takeIf { it.exists() }?.absolutePath
        val fUp = slotFile(ctx, SERVER_FILE_UPSTREAM).takeIf { it.exists() }?.absolutePath
        val fLegacy = slotFile(ctx, LEGACY_SERVER_FILE).takeIf { it.exists() }?.absolutePath
        val order = when {
            _runtime.value == RUNTIME_MBZUAI ->
                listOf(jniFork, fFork, jniLegacy, fLegacy, jniUp, fUp)
            _runtime.value == RUNTIME_LLAMACPP ->
                listOf(jniUp, fUp, jniLegacy, fLegacy, jniFork, fFork)
            arch == ARCH_K2 ->
                listOf(jniFork, fFork, jniLegacy, fLegacy, jniUp, fUp)
            else ->
                listOf(jniUp, fUp, jniLegacy, fLegacy, jniFork, fFork)
        }
        return order.filterNotNull().distinct()
    }


    /** Blocking engine start + health poll; suspends on IO.
     * Model mmap takes many seconds on a phone. */
    suspend fun start(ctx: Context): Boolean = withContext(Dispatchers.IO) {
        startBlocking(ctx)
    }

    private suspend fun startBlocking(ctx: Context): Boolean {
        if (isRunning()) return true
        Log.d(TAG, "startBlocking(): ensureServer()")
        if (!ensureServer(ctx)) {
            Log.d(TAG, "startBlocking(): ensureServer() returned false")
            _mode.value = "DESKTOP"
            _statusLine.value = "No local server on this device"
            return false
        }
        Log.d(TAG, "startBlocking(): resolveModel()")
        val model = resolveModel(ctx)
        if (model == null) {
            Log.d(TAG, "startBlocking(): no model found")
            _mode.value = "DESKTOP"
            _statusLine.value = "No model file - pick or download one"
            return false
        }
        Log.d(TAG, "startBlocking(): model=${model.file.absolutePath} size=${model.sizeBytes}")
        // HIT THE MODEL AT LOAD: sniff its GGUF architecture before spawning
        // anything, so the binary that can actually run it goes first.
        val candidates = serverCandidates(ctx, model.file)
        Log.d(TAG, "startBlocking(): server candidates=$candidates")
        if (candidates.isEmpty()) {
            _statusLine.value = "No local server binary - relaying to PC"
            _mode.value = "DESKTOP"
            return false
        }
        var lastErr = "no binary ran"
        for (bin in candidates) {
            val f = File(bin)
            if (!f.exists()) continue
            Log.d(TAG, "startBlocking(): trying binary ${f.absolutePath}")
            try {
                try { f.setExecutable(true) } catch (_: Exception) {}
                serverProc = ProcessBuilder(
                    f.absolutePath,
                    "-m", model.file.absolutePath,
                    "--port", PORT.toString(), "-c", "2048"
                ).redirectErrorStream(true).start()
                // Large models (1GB+) can take many minutes to mmap on a phone;
                // 5 minutes with per-5s progress polling. Never assume early
                // failure - the engine only reports ready when /health answers.
                if (waitHealthy(300_000)) {
                    val arch = ggufArchitecture(model.file)
                    val note = if (arch.isNotBlank()) " ($arch)" else ""
                    _statusLine.value = "Local engine ready via ${f.name}$note"
                    Log.d(TAG, "startBlocking(): engine ready via ${f.name}$note")
                    return true
                }
                val clue = drainExitOutput().ifBlank { "died on startup" }
                lastErr = "${f.name}: $clue"
                Log.d(TAG, "startBlocking(): ${f.name} failed: $clue")
                stop()
            } catch (e: Exception) {
                lastErr = "${f.name}: ${e.message ?: "launch failed"}"
                Log.d(TAG, "startBlocking(): ${f.name} launch exception: ${e.message}")
                stop()
            }
        }
        _mode.value = "DESKTOP"
        _statusLine.value = "Local engine could not start ($lastErr) - relaying to PC"
        return false
    }

    /** Poll /health until the loaded model answers or the timeout lapses.
     * Model load (600MB+ mmap) takes many seconds on a phone; the old code
     * slept 1.5s and gave up, so the engine always read as dead.
     *
     * NOTE: we poll the HTTP health endpoint directly — NOT isRunning() —
     * because isRunning() returns true as soon as the process is alive,
     * which is before the model finishes mmap-ing and the server is ready.
     *
     * Distinguishes:
     *  - still loading (process alive, health not yet 200) — keeps polling + logs
     *  - failed (process died) — returns false and captures exit output
     *  - ready (health 200) — returns true
     *  - timeout — returns false with a "still loading" note */
    private fun waitHealthy(timeoutMs: Long): Boolean {
        val startTime = System.currentTimeMillis()
        val deadline = startTime + timeoutMs
        var lastLog = 0L
        while (System.currentTimeMillis() < deadline) {
            val elapsed = System.currentTimeMillis() - startTime
            try {
                val c = URL("http://127.0.0.1:$PORT/health").openConnection() as HttpURLConnection
                c.connectTimeout = 2000
                c.readTimeout = 2000
                if (c.responseCode == 200) {
                    c.disconnect()
                    Log.d(TAG, "waitHealthy(): health OK after ${elapsed}ms")
                    return true
                }
                c.disconnect()
            } catch (_: Exception) { /* not ready yet */ }
            val p = serverProc
            if (p != null && !p.isAlive) {
                Log.d(TAG, "waitHealthy(): process died after ${elapsed}ms")
                return false
            }
            // Log progress every 5s so we can see it's still loading
            if (elapsed - lastLog >= 5000) {
                Log.d(TAG, "waitHealthy(): still loading (${elapsed / 1000}s / ${timeoutMs / 1000}s)")
                lastLog = elapsed
            }
            Thread.sleep(500)
        }
        Log.d(TAG, "waitHealthy(): timeout after ${timeoutMs}ms — server still not healthy")
        return false
    }

    /** First lines of a dead server's output, for the status line. */
    private fun drainExitOutput(): String = try {
        val p = serverProc ?: return ""
        val out = p.inputStream.bufferedReader()
        val sb = StringBuilder()
        val until = System.currentTimeMillis() + 1500
        while (System.currentTimeMillis() < until && sb.length < 240) {
            if (out.ready()) {
                val line = out.readLine() ?: break
                if (line.isNotBlank()) {
                    if (sb.isNotEmpty()) sb.append(" | ")
                    sb.append(line.trim().take(120))
                }
            } else Thread.sleep(50)
        }
        sb.toString()
    } catch (_: Exception) { "" }
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
        _statusLine.value = "Engine stopped"
    }

    /** POST an OpenAI-style chat body; null when the local server is unusable. */
    suspend fun chat(messagesJson: String, maxTokens: Int = 256): String? =
        withContext(Dispatchers.IO) {
            try {
                val c = (URL("http://127.0.0.1:$PORT/v1/chat/completions").openConnection()
                        as HttpURLConnection).apply {
                    requestMethod = "POST"; connectTimeout = 30_000; readTimeout = 300_000
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
                val msg = JSONObject(text).optJSONArray("choices")
                    ?.optJSONObject(0)?.optJSONObject("message")
                // K2-Horizon (reasoning model) writes to reasoning_content,
                // classic models write to content.  Use whichever is present.
                when {
                    msg != null && !msg.optString("content", "").isBlank() ->
                        msg.optString("content", "")
                    msg != null && !msg.optString("reasoning_content", "").isBlank() ->
                        msg.optString("reasoning_content", "")
                    else -> ""
                }
            } catch (_: Exception) {
                null
            }
        }

    // ---- Phase 1.6: the CLOUD rung of the LOCAL -> DESKTOP -> CLOUD chain ----

    /** Phase 1.6 provider config, or null when unset/unreadable. */
    fun cloudConfig(ctx: Context): CloudProviderConfig? = CloudKeyStore.load(ctx)

    /** True when a provider config with an api key is present. */
    fun cloudAvailable(ctx: Context): Boolean = CloudKeyStore.isConfigured(ctx)

    /**
     * OpenAI-compatible chat against the configured provider. Returns null
     * when no config exists or the call fails, so the chain can fall through.
     * Gemini/Anthropic request shaping lands in Phase 5 - for those, only an
     * explicitly configured base_url (e.g. a local OpenAI-compat proxy) is used.
     */
    suspend fun cloudChat(ctx: Context, messagesJson: String, maxTokens: Int = 256): String? =
        withContext(Dispatchers.IO) {
            val cfg = CloudKeyStore.load(ctx) ?: return@withContext null
            if (cfg.apiKey.isBlank()) return@withContext null
            val endpoint = cloudEndpoint(cfg) ?: return@withContext null
            try {
                val c = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"; connectTimeout = 15_000; readTimeout = 60_000
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Authorization", "Bearer ${cfg.apiKey}")
                    cfg.headers.forEach { (k, v) -> setRequestProperty(k, v) }
                    doOutput = true
                }
                val body = JSONObject()
                    .put("model", cfg.model ?: cfg.provider)
                    .put("messages", org.json.JSONArray(messagesJson))
                    .put("max_tokens", maxTokens)
                cfg.params.forEach { (k, v) -> body.put(k, v) }
                c.outputStream.use { it.write(body.toString().toByteArray()) }
                if (c.responseCode != 200) {
                    Log.w(TAG, "cloudChat(): HTTP ${c.responseCode} from $endpoint")
                    return@withContext null
                }
                val msg = JSONObject(c.inputStream.bufferedReader().readText())
                    .optJSONArray("choices")?.optJSONObject(0)?.optJSONObject("message")
                val out = when {
                    msg != null && msg.optString("content", "").isNotBlank() ->
                        msg.optString("content")
                    msg != null && msg.optString("reasoning_content", "").isNotBlank() ->
                        msg.optString("reasoning_content")
                    else -> ""
                }
                if (out.isBlank()) return@withContext null
                _mode.value = "CLOUD"
                out
            } catch (e: Exception) {
                Log.w(TAG, "cloudChat(): ${e.message}")
                null
            }
        }

    /** Preset OpenAI-compatible endpoints; custom/gemini/anthropic need base_url. */
    private fun cloudEndpoint(cfg: CloudProviderConfig): String? = when (cfg.provider) {
        "groq" -> "https://api.groq.com/openai/v1/chat/completions"
        "openai" -> "https://api.openai.com/v1/chat/completions"
        "openrouter" -> "https://openrouter.ai/api/v1/chat/completions"
        "ollama" -> "http://localhost:11434/v1/chat/completions"
        "lmstudio" -> "http://localhost:1234/v1/chat/completions"
        else -> {
            // Custom / self-hosted: accept either a full .../chat/completions
            // endpoint or an OpenAI-style base URL and complete the path.
            val base = cfg.baseUrl?.trim()?.trimEnd('/') ?: return null
            if (base.isBlank()) null
            else if (base.endsWith("/chat/completions")) base
            else "$base/chat/completions"
        }
    }
}


