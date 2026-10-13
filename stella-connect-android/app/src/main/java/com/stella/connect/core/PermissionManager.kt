package com.stella.connect.core

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.ContextCompat

/**
 * Every permission Stella can use, and how to ask for it.
 *
 * Android splits permissions into three families that need three different
 * mechanisms, and getting this wrong is why apps end up permanently denied:
 *
 *  1. DANGEROUS runtime permissions - request with a dialog (camera, mic,
 *     contacts, location, nearby devices).
 *  2. SPECIAL permissions - no dialog exists; the user must toggle them in
 *     Settings. Only a settings Intent can route them.
 *     (overlay, all-files access, install-unknown-apps)
 *  3. ONE-TIME consent - MediaProjection screen capture is neither of the
 *     above: each capture needs its own system consent dialog, and the grant
 *     dies with the process.
 *
 * All of them are OPTIONAL. Stella is designed to run with none of them: the
 * user picks how much the assistant can reach. [granted] reports what is
 * actually held so the UI can show honest status instead of blocking.
 */
object PermissionManager {

    /** One entry per thing Stella may ask for. */
    data class Capability(
        val id: String,
        val label: String,
        val why: String,
        /** Manifest permissions to request together; empty = settings-only. */
        val runtime: List<String> = emptyList(),
        val special: Special? = null,
        /** API level below which this capability does not exist. */
        val minSdk: Int = Build.VERSION_CODES.O,
    )

    enum class Special { OVERLAY, ALL_FILES, INSTALL_PACKAGES }

    val capabilities: List<Capability> = listOf(
        Capability(
            "camera", "Camera",
            "Scan QR codes to pair, and let Stella see what you point it at.",
            runtime = listOf(Manifest.permission.CAMERA),
        ),
        Capability(
            "microphone", "Microphone",
            "Voice wake word and hands-free chat.",
            runtime = listOf(Manifest.permission.RECORD_AUDIO),
        ),
        Capability(
            "notifications", "Notifications",
            "Shows the persistent connection status and replies.",
            runtime = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
                listOf(Manifest.permission.POST_NOTIFICATIONS) else emptyList(),
            minSdk = Build.VERSION_CODES.TIRAMISU,
        ),
        Capability(
            "photos", "Photos & media",
            "Read images and video you want Stella to work with.",
            runtime = buildList {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    add(Manifest.permission.READ_MEDIA_IMAGES)
                    add(Manifest.permission.READ_MEDIA_VIDEO)
                    add(Manifest.permission.READ_MEDIA_AUDIO)
                } else {
                    add(Manifest.permission.READ_EXTERNAL_STORAGE)
                }
            },
        ),
        Capability(
            "files", "All files",
            "Read, create and edit files anywhere on shared storage so Stella " +
                "can automate real file work. Requires a one-time Settings toggle.",
            runtime = if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU)
                listOf(
                    Manifest.permission.READ_EXTERNAL_STORAGE,
                    Manifest.permission.WRITE_EXTERNAL_STORAGE,
                )
            else emptyList(),
            special = Special.ALL_FILES,
        ),
        Capability(
            "screen", "Screen control",
            "See the screen and tap, swipe and type for you. Android asks " +
                "you to confirm every time.",
            special = null, // handled by MediaProjection consent, see startProjection()
        ),
        Capability(
            "overlay", "Display over other apps",
            "Draw the Stella control bar on top of whatever is open.",
            special = Special.OVERLAY,
        ),
        Capability(
            "location", "Location",
            "Context-aware automation, e.g. home vs away.",
            runtime = listOf(
                Manifest.permission.ACCESS_COARSE_LOCATION,
                Manifest.permission.ACCESS_FINE_LOCATION,
            ),
        ),
        Capability(
            "bluetooth", "Nearby devices",
            "Talk to local accessories over Bluetooth.",
            runtime = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S)
                listOf(Manifest.permission.BLUETOOTH_CONNECT) else emptyList(),
            minSdk = Build.VERSION_CODES.S,
        ),
        Capability(
            "install", "Install packages",
            "Let Stella install updates you ask it to.",
            special = Special.INSTALL_PACKAGES,
        ),
        Capability(
            "autopilot", "Autopilot (accessibility)",
            "Read the screen and perform taps, swipes and gestures. Enable the " +
                "Stella Autopilot service in Settings > Accessibility.",
            runtime = emptyList(),
            minSdk = Build.VERSION_CODES.P,
        ),
    )

    fun granted(ctx: Context, cap: Capability): Boolean = when (cap.id) {
        // Screen capture is never "held" - it is granted per capture.
        "screen" -> false
        "autopilot" -> accessibilityEnabled(ctx)
        else -> {
            val runtimeOk = cap.runtime.all {
                ContextCompat.checkSelfPermission(ctx, it) == PackageManager.PERMISSION_GRANTED
            }
            val specialOk = when (cap.special) {
                Special.OVERLAY -> Settings.canDrawOverlays(ctx)
                Special.ALL_FILES -> canManageFiles(ctx)
                Special.INSTALL_PACKAGES -> canRequestInstall(ctx)
                null -> true
            }
            runtimeOk && specialOk
        }
    }

    fun grantedIds(ctx: Context): Set<String> =
        capabilities.filter { granted(ctx, it) }.map { it.id }.toSet()

    /** Runtime permissions to batch-request, minus ones already held. */
    fun missingRuntime(ctx: Context): List<String> =
        capabilities.flatMap { it.runtime }
            .distinct()
            .filter {
                ContextCompat.checkSelfPermission(ctx, it) != PackageManager.PERMISSION_GRANTED
            }

    /**
     * Intent that opens the Settings page for a special permission.
     * Returns null when the capability needs no Settings trip.
     */
    fun settingsIntent(ctx: Context, cap: Capability): Intent? {
        val action = when (cap.special) {
            Special.OVERLAY -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M)
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION else return null
            Special.ALL_FILES -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R)
                Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION else null
            Special.INSTALL_PACKAGES -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES else return null
            null -> return null
        }
        return Intent(action).apply {
            if (cap.special == Special.ALL_FILES && Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                data = Uri.parse("package:${ctx.packageName}")
            }
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
    }

    /** Deep link to the app's own detail page, used as a fallback route. */
    fun appDetailsIntent(ctx: Context): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            .setData(Uri.parse("package:${ctx.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    // ---- individual probes -------------------------------------------------

    fun canDrawOverlays(ctx: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(ctx)

    fun canManageFiles(ctx: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R)
            android.os.Environment.isExternalStorageManager()
        else ContextCompat.checkSelfPermission(
            ctx, Manifest.permission.READ_EXTERNAL_STORAGE
        ) == PackageManager.PERMISSION_GRANTED

    fun canRequestInstall(ctx: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            ctx.packageManager.canRequestPackageInstalls()
        else true

    fun accessibilityEnabled(ctx: Context): Boolean = try {
        val expected = "${ctx.packageName}/${com.stella.connect.accessibility.StellaAccessibilityService::class.java.name}"
        val enabled = Settings.Secure.getString(
            ctx.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ).orEmpty()
        enabled.split(':').any { it.equals(expected, ignoreCase = true) }
    } catch (_: Exception) {
        false
    }
}