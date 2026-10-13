package com.stella.connect.core

import android.content.Context
import com.stella.connect.BuildConfig

/**
 * The PC bridge, as a user-controlled setting.
 *
 * Why it exists: most phones cannot run frontier models, so the phone's agent
 * is often strongest when it delegates large work to a desktop that hosts the
 * model. That makes "connect to your PC" a core capability rather than a
 * power-user extra - so it ships in the public build too, and is simply off
 * until the user turns it on.
 *
 * Why it is opt-in: it means the device can talk to a machine on your network.
 * That should be a decision the user makes deliberately, not a default they
 * have to think about. Personal (K2) builds default it on because that build
 * exists precisely to talk to your PC.
 */
object BridgeSettings {

    private const val PREFS = "stella_bridge"
    private const val KEY_ENABLED = "bridge_enabled"

    fun isEnabled(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        // Personal builds start on; public builds start off and stay off
        // until the user enables it.
        return prefs.getBoolean(KEY_ENABLED, BuildConfig.BRIDGE_DEFAULT_ON)
    }

    fun setEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_ENABLED, enabled).apply()
    }

    /** False only if a build ever ships without bridge support compiled in. */
    fun isAvailable(): Boolean = BuildConfig.BRIDGE_AVAILABLE

    fun statusLine(context: Context): String = when {
        !isAvailable() -> "PC bridge: not available in this build"
        isEnabled(context) -> "PC bridge: on"
        else -> "PC bridge: off"
    }
}