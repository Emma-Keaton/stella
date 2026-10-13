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
import com.stella.connect.core.K2Manager
import com.stella.connect.core.PermissionManager
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
        // Special permissions are toggled in Settings, so refresh on return.
        AgentStateStore.setGrantedPermissions(PermissionManager.grantedIds(this))
    }

    /**
     * Ask for every dangerous permission still missing, in one system dialog.
     * Declined ones are simply skipped later - nothing here is required.
     */
    private fun requestAllPermissions() {
        val missing = PermissionManager.missingRuntime(this)
        if (missing.isEmpty()) {
            AgentStateStore.setStatus("All permissions already granted")
            return
        }
        bulkPermissions.launch(missing.toTypedArray())
    }

    private fun openSettings(capId: String) {
        val cap = PermissionManager.capabilities.firstOrNull { it.id == capId }
        val intent = cap?.let { PermissionManager.settingsIntent(this, it) }
            ?: PermissionManager.appDetailsIntent(this)
        try {
            startActivity(intent)
        } catch (_: Exception) {
            startActivity(PermissionManager.appDetailsIntent(this))
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
        val endpoint = AgentStateStore.gateway.value
        if (endpoint != null || AgentStateStore.credential.value != null) {
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
    }

    private fun startGatewayService() {
        val endpoint = AgentStateStore.gateway.value
        if (endpoint != null || AgentStateStore.credential.value != null) {
            val intent = Intent(this, StellaConnectForegroundService::class.java)
            ContextCompat.startForegroundService(this, intent)
        }
    }

    companion object {
        @Suppress("unused")
        fun previewK2(): Boolean = K2Manager.bundled
    }
}