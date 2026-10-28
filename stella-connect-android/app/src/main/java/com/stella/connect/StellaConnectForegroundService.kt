package com.stella.connect

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.stella.connect.commands.DeviceCommandHandler
import com.stella.connect.core.AgentStateStore
import com.stella.connect.core.ConnectionState
import com.stella.connect.core.HudOverlay
import com.stella.connect.core.LocalEngineManager
import com.stella.connect.core.WakeWordManager
import com.stella.connect.network.StellaWebSocketClient
import com.stella.connect.pairing.PairingStorage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.collect

class StellaConnectForegroundService : Service() {
    private val scope = CoroutineScope(Job() + Dispatchers.IO)
    private lateinit var storage: PairingStorage
    private lateinit var client: StellaWebSocketClient
    private var started = false
    private var wakeLock: PowerManager.WakeLock? = null
    private var keepAliveJob: Job? = null

    /** Crash-loop guard for engine restarts (bad model must not spin forever). */
    private var engineFailStreak = 0

    override fun onCreate() {
        super.onCreate()
        storage = PairingStorage(this)
        client = StellaWebSocketClient(this, storage, DeviceCommandHandler(this))
        createNotificationChannel()
        acquireWakeLock()
        // Wire wake word → HUD → chat: when the wake word fires, show the HUD
        // bubble and post a nudge so the user knows Stella is listening.
        WakeWordManager.init(this) {
            scope.launch {
                HudOverlay.init(this@StellaConnectForegroundService).show()
                AgentStateStore.addChatMessage(
                    com.stella.connect.core.ChatMessage(
                        id = java.util.UUID.randomUUID().toString(),
                        role = "user",
                        text = "(wake word)",
                        timestamp = System.currentTimeMillis(),
                        status = "Received",
                    )
                )
            }
        }
        try {
            val notification = buildNotification("Stella", "Starting connection")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
        } catch (security: SecurityException) {
            stopSelf()
            return
        } catch (t: Throwable) {
            stopSelf()
            return
        }
        scope.launch {
            AgentStateStore.connectionState.collect {
                updateNotification()
            }
        }
        startKeepAlive()
    }

    /** Keep the CPU awake while the service (and engine) should be alive. */
    private fun acquireWakeLock() {
        try {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "stella:engine").apply {
                setReferenceCounted(false)
                acquire()
            }
        } catch (_: Exception) {}
    }

    /**
     * Watchdog loop: the local engine must survive backgrounding and silent
     * crashes. If a model is present but llama-server is not running, restart
     * it (with a crash-loop backoff so a bad model cannot spin forever).
     * Also keeps the notification truthful (never "Disconnected" on-device).
     */
    private fun startKeepAlive() {
        keepAliveJob?.cancel()
        keepAliveJob = scope.launch {
            while (true) {
                delay(15_000)
                try {
                    val ctx = applicationContext
                    if (LocalEngineManager.modelPresent(ctx) && !LocalEngineManager.isRunning()) {
                        if (engineFailStreak >= 3) {
                            AgentStateStore.setStatus("Engine restart paused - will retry in 5 min")
                            delay(300_000)
                            engineFailStreak = 0
                        }
                        AgentStateStore.addLog("Keep-alive: engine not running - restarting")
                        val ok = LocalEngineManager.prepare(ctx) && LocalEngineManager.start(ctx)
                        if (ok) {
                            engineFailStreak = 0
                            AgentStateStore.addLog("Keep-alive: engine restarted")
                        } else {
                            engineFailStreak += 1
                        }
                    } else if (LocalEngineManager.isRunning()) {
                        engineFailStreak = 0
                    }
                    // Refresh notification wording (on-device vs paired states).
                    updateNotification()
                } catch (e: Exception) {
                    AgentStateStore.addLog("Keep-alive error: ${e.message ?: "unknown"}")
                }
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                client.disconnect()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_SEND_CHAT -> {
                val text = intent.getStringExtra(EXTRA_CHAT_TEXT)
                if (!text.isNullOrBlank()) {
                    handleChatText(text)
                }
                return START_STICKY
            }
        }
        connectIfPossible()
        return START_STICKY
    }

    /**
     * Chat entry point shared by the paired-PC path (relay a frame over the
     * socket) and the standalone path (answer locally with the K2 runtime).
     *
     * A message is always echoed into the thread first so the composer never
     * looks dead; only the transport differs.
     */
    private fun handleChatText(text: String) {
        AgentStateStore.addChatMessage(
            com.stella.connect.core.ChatMessage(
                id = java.util.UUID.randomUUID().toString(),
                role = "user",
                text = text,
                timestamp = System.currentTimeMillis(),
                status = "Sent",
            )
        )
        if (AgentStateStore.gateway.value != null) {
            client.sendChatMessage(text)
            return
        }
        AgentStateStore.setStatus(
            when {
                com.stella.connect.core.LocalEngineManager.modelPresent(applicationContext) ->
                    "Thinking on-device..."
                com.stella.connect.core.LocalEngineManager.cloudAvailable(applicationContext) ->
                    "Relaying to cloud..."
                else -> "Thinking..."
            },
        )
        scope.launch {
            val reply = answerLocally(text)
            AgentStateStore.addChatMessage(
                com.stella.connect.core.ChatMessage(
                    id = java.util.UUID.randomUUID().toString(),
                    role = "assistant",
                    text = reply,
                    timestamp = System.currentTimeMillis(),
                    status = "Sent",
                )
            )
            AgentStateStore.setStatus(
                if (com.stella.connect.core.LocalEngineManager.mode.value == "CLOUD")
                    "Answered via cloud - link your PC any time"
                else
                    "Running on-device - connect to your PC any time",
            )
        }
    }

    /**
     * Standalone answer: K2 local model if it is alive, otherwise an honest
     * fallback that names the device's live state (bridge off, model state,
     * pairing invitation) instead of inventing an answer.
     *
     * Never throws: worst case the user gets a stateful pointer card.
     */
    private suspend fun answerLocally(text: String): String {
        val low = text.lowercase()
        if (low.contains("pair") || low.contains("link") || low.contains("connect") || low.contains("pc")) {
            return "Linking to your PC is optional. Tap \"Link to my PC\" on the home screen " +
                "to scan the QR code, or keep chatting with me here on this phone."
        }
        if (low.contains("model") || low.contains("download") || low.contains("k2")) {
            return k2StateLine()
        }
        return try {
            val messages = org.json.JSONArray()
                .put(org.json.JSONObject().put("role", "system").put("content",
                    "You are Stella, a concise on-device assistant. No PC is linked. " +
                    "Answer briefly. If you cannot answer on-device, say what is possible here."))
                .put(org.json.JSONObject().put("role", "user").put("content", text))
                .toString()
            val started = com.stella.connect.core.LocalEngineManager.start(applicationContext)
            if (started) {
                val out = com.stella.connect.core.LocalEngineManager.chat(messages, 256)?.trim()
                if (!out.isNullOrBlank()) return out
            }
            // LOCAL rung unavailable -> CLOUD rung (Phase 1.6 chain).
            val cloud = com.stella.connect.core.LocalEngineManager
                .cloudChat(applicationContext, messages, 256)?.trim()
            if (!cloud.isNullOrBlank()) cloud else k2StateLine()
        } catch (_: Exception) {
            k2StateLine()
        }
    }

    private fun k2StateLine(): String {
        val ctx = applicationContext
        return when {
            com.stella.connect.core.LocalEngineManager.isRunning() ->
                "Stella is running on this phone. Ask me anything."
            com.stella.connect.core.LocalEngineManager.modelPresent(ctx) ->
                "The on-device model is ready - I'm starting the local engine now. Ask again in a moment."
            else ->
                "No model downloaded yet and no PC linked. I can still help with device " +
                "info and pairing - say \"pair\" and I'll walk you through linking, or download " +
                "a model for full offline chat."
        }
    }

    private fun connectIfPossible() {
        val endpoint = AgentStateStore.gateway.value ?: return
        val credential = storage.loadCredential()
        val offer = AgentStateStore.pairingOffer.value ?: storage.loadGatewayHint()
        if (!started) {
            started = true
        }
        client.connect(endpoint, credential, offer)
        AgentStateStore.setConnectionState(ConnectionState.CONNECTING)
    }

    private fun updateNotification() {
        val state = AgentStateStore.connectionState.value
        val gateway = AgentStateStore.gateway.value
        val text = when {
            state == ConnectionState.CONNECTED -> "Connected to Stella"
            state == ConnectionState.CONNECTING -> "Connecting to Stella"
            state == ConnectionState.RECONNECTING -> "Reconnecting"
            // On-device mode: there is nothing to be "disconnected" from.
            gateway == null ->
                if (LocalEngineManager.isRunning()) "On-device - local engine running"
                else "On-device - local only"
            else -> "Disconnected - retrying"
        }
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.notify(NOTIFICATION_ID, buildNotification("Stella", text))
    }

    private fun buildNotification(title: String, text: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stella_launcher)
            .setContentTitle(title)
            .setContentText(text)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(CHANNEL_ID, "Stella", NotificationManager.IMPORTANCE_LOW)
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(channel)
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        keepAliveJob?.cancel()
        try { wakeLock?.release() } catch (_: Exception) {}
        wakeLock = null
        client.disconnect()
        WakeWordManager.shutdown()
        HudOverlay.shutdown()
        super.onDestroy()
    }

    companion object {
        const val ACTION_STOP = "com.stella.connect.action.STOP"
        const val ACTION_SEND_CHAT = "com.stella.connect.action.SEND_CHAT"
        const val EXTRA_CHAT_TEXT = "com.stella.connect.extra.CHAT_TEXT"
        private const val CHANNEL_ID = "stella_connect"
        private const val NOTIFICATION_ID = 4201
    }
}

