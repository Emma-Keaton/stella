package com.stella.connect.core

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import androidx.core.content.ContextCompat

/**
 * Every permission Stella can use, and how to ask for it.
 *
 * Android splits permissions into four families that need four
 * different mechanisms, and getting this wrong is why apps end up
 * permanently denied:
 *
 *  1. DANGEROUS runtime permissions - request with a dialog
 *     (camera, mic, contacts, location, nearby devices).
 *  2. SPECIAL permissions - no dialog exists; the user must toggle
 *     them in Settings. Only a settings Intent can route them
 *     (overlay, all-files access, install-unknown-apps).
 *  3. ADB-ONLY permissions - no Settings toggle is exposed on many
 *     OEM builds (doze exemption), so the shell user is the only
 *     way. The app shows the exact one-liner to run from a PC.
 *  4. ONE-TIME consent - MediaProjection screen capture is neither
 *     of the above: each capture needs its own system consent
 *     dialog, and the grant dies with the process.
 *
 * All of them are OPTIONAL. Stella is designed to run with none of
 * them: the user picks how much the assistant can reach. [granted]
 * reports what is actually held so the UI can show honest status
 * instead of blocking.
 */
object PermissionManager {

    /** How a capability is granted. */
    enum class GrantPath {
        /** Dangerous permission - one system dialog. */
        DIALOG,
        /** Special permission - try the Settings page, then the ADB card. */
        SETTINGS,
        /** Only the shell user can grant it - show the PC one-liner. */
        ADB,
        /** Per-use consent (MediaProjection). Nothing to pre-grant. */
        PER_USE,
    }

    /** One entry per thing Stella may ask for. */
    data class Capability(
        val id: String,
        val label: String,
        val why: String,
        /** Manifest permissions to request together; empty = not dialog-based. */
        val runtime: List<String> = emptyList(),
        val special: Special? = null,
        /** API level below which this capability does not exist. */
        val minSdk: Int = Build.VERSION_CODES.O,
        /** Primary grant mechanism. */
        val path: GrantPath = GrantPath.DIALOG,
        /** ADB one-liner template; `{pkg}` is replaced at display time. */
        val adbCommand: String = "",
        /** Capability ids that must be granted before this one. */
        val requires: List<String> = emptyList(),
    )

    enum class Special { OVERLAY, ALL_FILES, INSTALL_PACKAGES }

    /** The accessibility component, in the `pkg/component` form ADB uses. */
    fun accessibilityComponent(pkg: String) =
        "$pkg/com.stella.connect.accessibility.StellaAccessibilityService"

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
                    // API 34 lets the user grant "only some photos". That partial
                    // grant arrives as READ_MEDIA_VISUAL_USER_SELECTED, and it is
                    // declared in the manifest - so request it alongside the full
                    // set. Without it a "Select photos" grant looks like nothing
                    // was granted and the card stays broken forever.
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                        add(Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED)
                    }
                } else {
                    add(Manifest.permission.READ_EXTERNAL_STORAGE)
                }
            },
        ),
        Capability(
            "files", "All files",
            "Read, create and edit files anywhere on shared storage so Stella " +
                "can automate real file work. The Settings toggle is hidden on " +
                "many builds, so the ADB line is the reliable path.",
            runtime = if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU)
                listOf(
                    Manifest.permission.READ_EXTERNAL_STORAGE,
                    Manifest.permission.WRITE_EXTERNAL_STORAGE,
                )
            else emptyList(),
            special = Special.ALL_FILES,
            path = GrantPath.SETTINGS,
            adbCommand = "adb shell appops set {pkg} MANAGE_EXTERNAL_STORAGE allow",
        ),
        Capability(
            "overlay", "Display over other apps",
            "Draw the Stella control bar on top of whatever is open.",
            special = Special.OVERLAY,
            path = GrantPath.SETTINGS,
            adbCommand = "adb shell appops set {pkg} SYSTEM_ALERT_WINDOW allow",
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
            "location_background", "Location (background)",
            "Home vs away even when the app is closed. Needs foreground " +
                "location first; ADB grants both in one shot.",
            runtime = listOf(Manifest.permission.ACCESS_BACKGROUND_LOCATION),
            minSdk = Build.VERSION_CODES.Q,
            requires = listOf("location"),
        ),
        Capability(
            "bluetooth", "Nearby devices",
            "Talk to local accessories over Bluetooth.",
            // CONNECT is for connecting, SCAN is for discovery - they are two
            // separate dangerous permissions on API 31+ and the manifest
            // declares both. Requesting only CONNECT left discovery dead on
            // every supported OS version.
            runtime = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S)
                listOf(
                    Manifest.permission.BLUETOOTH_CONNECT,
                    Manifest.permission.BLUETOOTH_SCAN,
                ) else emptyList(),
            minSdk = Build.VERSION_CODES.S,
        ),
        Capability(
            "install", "Install packages",
            "Let Stella install updates you ask it to.",
            special = Special.INSTALL_PACKAGES,
            path = GrantPath.SETTINGS,
            adbCommand = "adb shell appops set {pkg} REQUEST_INSTALL_PACKAGES allow",
        ),
        Capability(
            "autopilot", "Autopilot (accessibility)",
            "Read the screen and perform taps, swipes and gestures. Enable the " +
                "Stella Autopilot service in Settings > Accessibility.",
            runtime = emptyList(),
            minSdk = Build.VERSION_CODES.P,
            path = GrantPath.SETTINGS,
            adbCommand = "adb shell settings put secure enabled_accessibility_services " +
                "{pkg}/com.stella.connect.accessibility.StellaAccessibilityService\n" +
                "adb shell settings put secure accessibility_enabled 1",
        ),
        Capability(
            "doze", "Doze exemption",
            "Keep the connection alive in deep standby. No Settings toggle " +
                "is exposed on most builds - grant it from a PC over ADB.",
            runtime = emptyList(),
            minSdk = Build.VERSION_CODES.M,
            path = GrantPath.ADB,
            adbCommand = "adb shell dumpsys deviceidle whitelist +{pkg}",
        ),
        Capability(
            "screen", "Screen control",
            "See the screen and tap, swipe and type for you. Android asks " +
                "you to confirm every time.",
            special = null, // handled by MediaProjection consent, see startProjection()
            path = GrantPath.PER_USE,
        ),
    )

    fun granted(ctx: Context, cap: Capability): Boolean = when (cap.id) {
        // Screen capture is never "held" - it is granted per capture.
        "screen" -> false
        "autopilot" -> accessibilityEnabled(ctx)
        "doze" -> dozeExempt(ctx)
        else -> {
            val runtimeOk = cap.runtime.all {
                ContextCompat.checkSelfPermission(ctx, it) == PackageManager.PERMISSION_GRANTED
            }
            val specialOk = when (cap.special) {
                Special.OVERLAY -> canDrawOverlays(ctx)
                Special.ALL_FILES -> canManageFiles(ctx)
                Special.INSTALL_PACKAGES -> canRequestInstall(ctx)
                null -> true
            }
            runtimeOk && specialOk
        }
    }

    fun grantedIds(ctx: Context): Set<String> =
        capabilities.filter { granted(ctx, it) }.map { it.id }.toSet()

    /** Runtime permissions to batch-request, minus ones already held.
     *  Background location is withheld until foreground location is
     *  granted: requesting it first always fails. */
    fun missingRuntime(ctx: Context): List<String> {
        val foregroundLocation = listOf(
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.ACCESS_FINE_LOCATION,
        ).all {
            ContextCompat.checkSelfPermission(ctx, it) == PackageManager.PERMISSION_GRANTED
        }
        return capabilities.flatMap { it.runtime }
            .distinct()
            .filter {
                ContextCompat.checkSelfPermission(ctx, it) != PackageManager.PERMISSION_GRANTED
            }
            .filterNot {
                it == Manifest.permission.ACCESS_BACKGROUND_LOCATION && !foregroundLocation
            }
    }

    /** True when every capability in [requires] is granted. */
    fun prerequisitesMet(ctx: Context, cap: Capability): Boolean =
        cap.requires.all { req ->
            val required = capabilities.firstOrNull { it.id == req } ?: return@all true
            granted(ctx, required)
        }

    /**
     * Ordered Settings routes for a capability: OEM-specific first,
     * then the stock action, then an alternative stock route, then the
     * app-details page (which always resolves). The caller tries each
     * in turn so a missing OEM page degrades instead of crashing.
     */
    fun settingsIntents(ctx: Context, cap: Capability): List<Intent> {
        val out = mutableListOf<Intent>()
        out += oemIntents(ctx, cap)
        settingsIntent(ctx, cap)?.let { out += it }
        alternativeSettingsIntent(ctx, cap)?.let { out += it }
        out += appDetailsIntent(ctx)
        return out
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
            null -> when (cap.id) {
                "autopilot" -> Settings.ACTION_ACCESSIBILITY_SETTINGS
                "doze" -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M)
                    Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS else null
                else -> null
            }
        }
        return action?.let { a ->
            Intent(a).apply {
                if (cap.special != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    // Special pages are per-app: point them at us.
                    data = Uri.parse("package:${ctx.packageName}")
                }
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        }
    }

    /** A second, different stock route (used when the first is filtered). */
    private fun alternativeSettingsIntent(ctx: Context, cap: Capability): Intent? {
        if (cap.special == Special.ALL_FILES && Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            // The all-apps list sometimes shows apps the per-app page filters out.
            return Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return null
    }

    /** OEM-specific routes where a reliable one exists. */
    private fun oemIntents(ctx: Context, cap: Capability): List<Intent> {
        val manufacturer = Build.MANUFACTURER.orEmpty().lowercase()
        val pkg = ctx.packageName
        val out = mutableListOf<Intent>()
        if (manufacturer.contains("xiaomi") || manufacturer.contains("redmi") ||
            manufacturer.contains("poco")
        ) {
            // MIUI's permission editor covers runtime + special toggles.
            runCatching {
                Intent("miui.intent.action.APP_PERM_EDITOR")
                    .setClassName(
                        "com.miui.securitycenter",
                        "com.miui.permcenter.permissions.PermissionsEditorActivity",
                    )
                    .putExtra("extra_pkgname", pkg)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }.onSuccess { out += it }
        }
        return out
    }

    /** Deep link to the app's own detail page, used as a fallback route. */
    fun appDetailsIntent(ctx: Context): Intent =
        Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
            .setData(Uri.parse("package:${ctx.packageName}"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    /** The ADB one-liner for a capability, with the real package id. */
    fun adbCommand(ctx: Context, cap: Capability): String =
        cap.adbCommand.replace("{pkg}", ctx.packageName)

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

    fun dozeExempt(ctx: Context): Boolean = try {
        val pm = ctx.getSystemService(Context.POWER_SERVICE) as? PowerManager ?: return false
        pm.isIgnoringBatteryOptimizations(ctx.packageName)
    } catch (_: Exception) {
        false
    }
}
