package com.stella.connect.core

import android.content.Context

/**
 * Wake-word listener: arms the microphone for a hot-phrase ("Hey Stella")
 * and invokes [onWakeWord] when it fires.
 *
 * This is a stub wired to the settings toggle and foreground service.
 * Real detection (Porcupine / Snowball / on-device keyword spotting) can be
 * swapped in here without touching callers.
 */
class WakeWordManager private constructor(
    private val context: Context,
    private val onWakeWord: () -> Unit,
) {
    private var listening = false

    fun start() {
        if (listening) return
        listening = true
        // TODO: bind Porcupine/Snowball keyword spotter here; on detection,
        // call onWakeWord() on the main dispatcher.
    }

    fun stop() {
        listening = false
    }

    val isListening: Boolean
        get() = listening

    companion object {
        @Volatile private var instance: WakeWordManager? = null

        fun init(context: Context, onWakeWord: () -> Unit): WakeWordManager {
            return synchronized(this) {
                instance ?: WakeWordManager(context.applicationContext, onWakeWord).also { instance = it }
            }
        }

        fun get(): WakeWordManager? = instance

        fun shutdown() {
            synchronized(this) {
                instance?.stop()
                instance = null
            }
        }
    }
}