package com.stella.connect.core

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.speech.tts.TextToSpeech
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/** Broadcast receiver for `am broadcast -a com.stella.connect.CHAT_PROMPT --es prompt "..."`.
 *
 * Starts the local engine (prepare -> start) and, once healthy, sends the prompt
 * through [LocalEngineManager.chat] and logs Stella's reply. Manifest-registered so
 * adb can trigger it even when the app process is not running.
 *
 * When a chat prompt is received: loads model, starts engine, streams response
 * to HUD overlay, then speaks it via TTS.
 */
class ChatPromptReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "ChatPromptReceiver"
        private const val ACTION_CHAT_PROMPT = "com.stella.connect.CHAT_PROMPT"
        private const val EXTRA_PROMPT = "prompt"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_CHAT_PROMPT) return
        val prompt = intent.getStringExtra(EXTRA_PROMPT) ?: "Introduce yourself, Stella."
        Log.d(TAG, "CHAT_PROMPT received: $prompt")

        // Keep the process alive while the engine loads (model mmap takes seconds).
        val pending = goAsync()

        CoroutineScope(Dispatchers.IO).launch {
            try {
                AgentStateStore.addLog("CHAT_PROMPT received: $prompt")
                Log.d(TAG, "calling prepare()")
                val ready = LocalEngineManager.prepare(context)
                Log.d(TAG, "prepare() returned $ready")
                if (!ready) {
                    AgentStateStore.addLog("No model present - pick or download one")
                    return@launch
                }
                Log.d(TAG, "calling start()")
                val started = LocalEngineManager.start(context)
                Log.d(TAG, "start() returned $started")
                if (!started) {
                    AgentStateStore.addLog("Local engine failed to start")
                    return@launch
                }

                // Show HUD overlay with streaming text
                val hud = HudOverlay.init(context)
                hud.showText("Stella is thinking...\n\n")

                Log.d(TAG, "calling chat() with HUD + TTS")
                val arr = JSONArray().put(JSONObject().put("role", "user").put("content", prompt))
                val reply = LocalEngineManager.chat(arr.toString())

                if (reply != null) {
                    Log.d(TAG, "chat() returned: $reply")
                    AgentStateStore.addLog("Stella: $reply")

                    // Update HUD with full response
                    hud.showText("Stella:\n$reply")

                    // Speak the response via TTS
                    speak(context, reply)
                } else {
                    Log.d(TAG, "chat() returned null")
                    hud.showText("Stella: (no response)")
                }
            } catch (e: Exception) {
                Log.e(TAG, "CHAT_PROMPT error", e)
                AgentStateStore.addLog("CHAT_PROMPT error: ${e.message ?: "unknown"}")
                HudOverlay.init(context).showText("Error: ${e.message}")
            } finally {
                pending.finish()
            }
        }
    }

    private fun speak(context: Context, text: String) {
        lateinit var tts: TextToSpeech
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts.language = java.util.Locale.getDefault()
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "stella_intro")
            }
        }
    }
}
