package com.stella.connect

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.stella.connect.core.AgentStateStore
import com.stella.connect.core.LocalEngineManager
import com.stella.connect.core.PermissionManager
import com.stella.connect.core.PermissionWalkStore
import com.stella.connect.pairing.PairingStorage
import com.stella.connect.ui.StellaConnectApp
import com.stella.connect.ui.theme.StellaConnectTheme

class MainActivity : ComponentActivity() {
    private lateinit var storage: PairingStorage
    private var pendingServiceStart = false

    /**
     * Screen control needs its own consent dialog per capture - Android offers
     * no persistent grant. We hold the result token so a running service can
     * keep the projection alive.
     */
    private var projectionToken: Intent? = null

    /** Set while a batch runtime dialog is up and a walk should follow. */
    private var pendingWalk = false

    /** Set while we are waiting for a Settings trip to flip a capability. */
    private var walkAwaitingResult = false

    private val cameraPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()) { }

    private val notificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()) { granted ->
        if (granted || Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            if (pendingServiceStart) {
                pendingServiceStart = false
                startGatewayService()
            }
        } else {
            pendingServiceStart = false
            AgentStateStore.setError("Notifications are off, so connection status will not show.")
        }
    }

    /** One batch request for every remaining dangerous permission. */
    private val bulkPermissions = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        val denied = granted.filterValues { !it }.keys
        if (denied.isNotEmpty()) {
            AgentStateStore.setStatus("${denied.size} permission(s) declined - Stella will run without them")
        }
        if (pendingServiceStart) {
            pendingServiceStart = false
            startGatewayService()
        }
        if (pendingWalk) {
            pendingWalk = false
            startPermissionWalk()
        }
    }

    /** The system "start capturing?" dialog. */
    private val screenCapture = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK && result.data != null) {
            projectionToken = result.data
            AgentStateStore.setStatus("Screen control active")
            startGatewayService()
        } else {
            AgentStateStore.setStatus("Screen control declined")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        // Must run before super.onCreate so the system splash is never
        // replaced by a flash of the app theme.
        installSplashScreen()
        super.onCreate(savedInstanceState)

        // Restore the user's llama.cpp runtime choice (llama.cpp or the MBZUAI
        // fork) before anything tries to start the server, so the first launch
        // after a process death uses the same runtime as the last one.
        LocalEngineManager.loadRuntime(this)

        // Restore the selected theme (Dark/Light/Aurora) before setContent so
        // the first frame paints with the right scheme.
        com.stella.connect.ui.theme.StellaThemeState.init(this)

        storage = PairingStorage(this)
        AgentStateStore.setCredential(storage.loadCredential())
        storage.loadGatewayHint()?.let {
            AgentStateStore.setPairingOffer(it)
            AgentStateStore.setGateway(
                com.stella.connect.core.GatewayEndpoint(
                    name = "Stella PC",
                    host = it.host,
                    port = it.port,
                )
            )
        }

        maybeStartService()
        setContent {
            StellaConnectTheme {
                StellaConnectApp(
                    onRequestCameraPermission = {
                        cameraPermission.launch(Manifest.permission.CAMERA)
                    },
                    onRequestNotificationPermission = {
                        notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                    },
                    onRequestAllPermissions = { requestAllPermissions() },
                    onOpenSettings = { capId -> openSettings(capId) },
                    onRequestScreenControl = { requestScreenControl() },
                    onStartService = { maybeStartService() },
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Special permissions are toggled in Settings, so refresh on return,
        // then let the guided walk verify whether the trip flipped anything.
        AgentStateStore.setGrantedPermissions(PermissionManager.grantedIds(this))
        resumeWalkIfActive()
    }

    /**
     * Ask for every dangerous permission still missing, in one system
     * dialog. Declined ones are simply skipped later - nothing here is
     * required. When the dialog is done we walk the remaining special
     * permissions, one Settings page at a time.
     */
    private fun requestAllPermissions() {
        val missing = PermissionManager.missingRuntime(this)
        if (missing.isEmpty()) {
            startPermissionWalk()
            return
        }
        pendingWalk = true
        bulkPermissions.launch(missing.toTypedArray())
    }

    // ---- guided permission walk ----------------------------------------

    /**
     * The walk covers everything the batch dialog cannot: the special
     * permissions that live in Settings and the ADB-only ones. Screen
     * control is excluded - it is asked for per use, by design.
     */
    private fun startPermissionWalk() {
        val queue = PermissionManager.capabilities
            .filter { it.id != "screen" }
            .filter { it.path != PermissionManager.GrantPath.DIALOG }
            .filterNot { PermissionManager.granted(this, it) }
            .map { it.id }
        if (queue.isEmpty()) {
            PermissionWalkStore.clear()
            AgentStateStore.setStatus("All permissions granted")
            return
        }
        PermissionWalkStore.start(queue)
        openWalkStep()
    }

    /** Open the correct page for the current walk step. */
    private fun openWalkStep() {
        val walk = PermissionWalkStore.walk.value
        if (walk.queue.isEmpty() || walk.finished) return
        if (walk.adbHint != null) return   // stuck: show the ADB card, don't loop
        val cap = PermissionManager.capabilities.firstOrNull { it.id == walk.queue[walk.index] }
            ?: return

        // ADB-only capabilities have no Settings page worth opening - go
        // straight to the PC one-liner.
        if (cap.path == PermissionManager.GrantPath.ADB) {
            PermissionWalkStore.stuck(PermissionManager.adbCommand(this, cap))
            return
        }
        // Background location cannot be granted before foreground location.
        // ADB handles both in one shot, so hand over the line instead.
        if (!PermissionManager.prerequisitesMet(this, cap)) {
            PermissionWalkStore.stuck(PermissionManager.adbCommand(this, cap))
            return
        }
        walkAwaitingResult = true
        launchFirstResolvable(PermissionManager.settingsIntents(this, cap))
    }

    /**
     * Called on every resume. If the step we just opened got granted we
     * advance and open the next page; if the user came back without
     * flipping it we reroute to the ADB card instead of re-opening the
     * same dead page.
     */
    private fun resumeWalkIfActive() {
        val walk = PermissionWalkStore.walk.value
        if (walk.queue.isEmpty() || walk.finished) return
        val cap = PermissionManager.capabilities.firstOrNull { it.id == walk.queue[walk.index] }
            ?: return

        if (PermissionManager.granted(this, cap)) {
            PermissionWalkStore.advance()
            if (!PermissionWalkStore.walk.value.finished) openWalkStep()
            walkAwaitingResult = false
        } else if (walkAwaitingResult) {
            PermissionWalkStore.stuck(PermissionManager.adbCommand(this, cap))
            walkAwaitingResult = false
        }
    }

    /** The user tapped "Next" on a stuck (ADB) card. */
    private fun skipWalkStep() {
        PermissionWalkStore.advance()
        if (!PermissionWalkStore.walk.value.finished) openWalkStep()
    }

    private fun stopPermissionWalk() {
        walkAwaitingResult = false
        PermissionWalkStore.clear()
    }

    /** Try each route in order; the last (app-details) always resolves. */
    private fun launchFirstResolvable(intents: List<Intent>) {
        for (intent in intents) {
            if (intent.resolveActivity(packageManager) == null) continue
            try {
                startActivity(intent)
                return
            } catch (_: Exception) {
                // Next route.
            }
        }
        try {
            startActivity(PermissionManager.appDetailsIntent(this))
        } catch (_: Exception) {
            AgentStateStore.setError("Could not open Settings.")
        }
    }

    private fun openSettings(capId: String) {
        val cap = PermissionManager.capabilities.firstOrNull { it.id == capId }
        if (cap == null) {
            openAppDetails()
            return
        }
        launchFirstResolvable(PermissionManager.settingsIntents(this, cap))
    }

    private fun openAppDetails() {
        try {
            startActivity(PermissionManager.appDetailsIntent(this))
        } catch (_: Exception) {
            AgentStateStore.setError("Could not open the app details page.")
        }
    }

    private fun requestScreenControl() {
        try {
            val mpm = getSystemService(MediaProjectionManager::class.java)
                ?: return AgentStateStore.setError("Screen capture is unavailable.")
            screenCapture.launch(mpm.createScreenCaptureIntent())
        } catch (_: Exception) {
            AgentStateStore.setError("This device cannot capture the screen.")
        }
    }

    private fun maybeStartService() {
        // Always run the foreground service: it is the keep-alive for the local
        // engine (wake lock + watchdog), not just the PC-gateway relay. Without
        // it Android kills the process in on-device mode and the engine dies.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            pendingServiceStart = true
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
            return
        }
        startGatewayService()
    }

    private fun startGatewayService() {
        // The service handles both local engine keep-alive and PC-gateway relay.
        val intent = Intent(this, StellaConnectForegroundService::class.java)
        ContextCompat.startForegroundService(this, intent)
    }

    companion object {
        @Suppress("unused")
        fun previewK2(): Boolean = LocalEngineManager.bundled
    }
}
