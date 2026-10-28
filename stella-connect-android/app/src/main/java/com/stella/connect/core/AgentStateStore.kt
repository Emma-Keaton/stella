package com.stella.connect.core

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object AgentStateStore {
    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _gateway = MutableStateFlow<GatewayEndpoint?>(null)
    val gateway: StateFlow<GatewayEndpoint?> = _gateway.asStateFlow()

    private val _pairingOffer = MutableStateFlow<PairingOffer?>(null)
    val pairingOffer: StateFlow<PairingOffer?> = _pairingOffer.asStateFlow()

    private val _credential = MutableStateFlow<DeviceCredential?>(null)
    val credential: StateFlow<DeviceCredential?> = _credential.asStateFlow()

    private val _statusText = MutableStateFlow("Ready")
    val statusText: StateFlow<String> = _statusText.asStateFlow()

    private val _lastError = MutableStateFlow<String?>(null)
    val lastError: StateFlow<String?> = _lastError.asStateFlow()

    private val _logs = MutableStateFlow<List<String>>(emptyList())
    val logs: StateFlow<List<String>> = _logs.asStateFlow()

    private val _chatHistory = MutableStateFlow<List<ChatMessage>>(emptyList())
    val chatHistory: StateFlow<List<ChatMessage>> = _chatHistory.asStateFlow()

    /** Active workspace id. When null, defaults to "personal". */
    private val _activeWorkspaceId = MutableStateFlow<String?>(null)
    val activeWorkspaceId: StateFlow<String?> = _activeWorkspaceId.asStateFlow()

    /** Active thread id within the active workspace. */
    private val _activeThreadId = MutableStateFlow<String?>(null)
    val activeThreadId: StateFlow<String?> = _activeThreadId.asStateFlow()

    fun setActiveWorkspace(workspaceId: String?) {
        _activeWorkspaceId.value = workspaceId
    }

    fun setActiveThread(threadId: String?) {
        _activeThreadId.value = threadId
    }

    /**
     * Ids of the capabilities the user has actually granted, refreshed from
     * MainActivity.onResume() (special permissions are toggled in Settings).
     */
    private val _grantedPermissions = MutableStateFlow<Set<String>>(emptySet())
    val grantedPermissions: StateFlow<Set<String>> = _grantedPermissions.asStateFlow()

    fun setConnectionState(state: ConnectionState) {
        _connectionState.value = state
    }

    fun setGateway(endpoint: GatewayEndpoint?) {
        _gateway.value = endpoint
    }

    fun setPairingOffer(offer: PairingOffer?) {
        _pairingOffer.value = offer
    }

    fun setCredential(credential: DeviceCredential?) {
        _credential.value = credential
    }

    fun setStatus(text: String) {
        _statusText.value = text
    }

    fun setError(text: String?) {
        _lastError.value = text
    }

    fun addLog(message: String) {
        _logs.value = (_logs.value + message).takeLast(50)
    }

    fun addChatMessage(msg: ChatMessage) {
        val current = _chatHistory.value.toMutableList()
        current.removeAll { it.id == msg.id }
        current.add(msg)
        _chatHistory.value = current
    }

    fun setChatHistory(messages: List<ChatMessage>) {
        _chatHistory.value = messages
    }

    fun setGrantedPermissions(ids: Set<String>) {
        _grantedPermissions.value = ids
    }

    /**
     * Live-voice pause flag. True when the user tapped the VoiceOrb to pause
     * inference + speech (orb shows "Paused — tap to resume"). The foreground
     * service reads this to gate TTS dispatch.
     */
    private val _voicePaused = MutableStateFlow(false)
    val voicePaused: StateFlow<Boolean> = _voicePaused.asStateFlow()

    fun setVoicePaused(paused: Boolean) {
        _voicePaused.value = paused
    }
}

/**
 * The guided "grant everything" walk.
 *
 * [queue] is the ordered list of capability ids still to hand
 * to the user, [index] is the current step, and [adbHint] is
 * the ADB one-liner for the step that just failed to flip in
 * Settings - shown instead of looping back to the dead page.
 */
data class PermissionWalkState(
    val queue: List<String> = emptyList(),
    val index: Int = 0,
    val adbHint: String? = null,
    val finished: Boolean = false,
)

object PermissionWalkStore {
    private val _walk = MutableStateFlow(PermissionWalkState())
    val walk: StateFlow<PermissionWalkState> = _walk.asStateFlow()

    fun start(queue: List<String>) {
        _walk.value = PermissionWalkState(queue = queue, index = 0)
    }

    fun advance() {
        val cur = _walk.value
        val next = cur.index + 1
        _walk.value = if (next >= cur.queue.size) {
            cur.copy(finished = true, adbHint = null)
        } else {
            cur.copy(index = next, adbHint = null)
        }
    }

    /** Keep the current step but surface the ADB fallback. */
    fun stuck(adbLine: String?) {
        _walk.value = _walk.value.copy(adbHint = adbLine)
    }

    fun skip() {
        advance()
    }

    fun clear() {
        _walk.value = PermissionWalkState()
    }
}

object StellaConnectCapabilities {
    val INITIAL = listOf(
        "device_info",
        "battery",
        "flashlight",
        "volume",
        "media",
        "launch_app",
        "apps",
        "open_url",
        "wifi_state",
    )
}
