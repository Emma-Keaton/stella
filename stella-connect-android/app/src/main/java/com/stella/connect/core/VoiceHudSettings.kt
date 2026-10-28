package com.stella.connect.core

import android.content.Context

/**
 * Voice & HUD settings (wake word + HUD overlay), persisted via SharedPreferences.
 * Mirrors BridgeSettings for parity.
 */
object VoiceHudSettings {

    private const val PREFS = "stella_voice_hud"
    private const val KEY_WAKE_WORD = "wake_word"
    private const val KEY_HUD_ENABLED = "hud_enabled"

    fun wakeWord(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getString(KEY_WAKE_WORD, "stella") ?: "stella"
    }

    fun setWakeWord(context: Context, value: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_WAKE_WORD, value).apply()
    }

    fun isHudEnabled(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getBoolean(KEY_HUD_ENABLED, true)
    }

    fun setHudEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(KEY_HUD_ENABLED, enabled).apply()
    }
}
