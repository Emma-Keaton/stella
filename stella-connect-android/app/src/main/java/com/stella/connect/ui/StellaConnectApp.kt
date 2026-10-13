package com.stella.connect.ui

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.HorizontalDivider
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.stella.connect.StellaConnectForegroundService
import com.stella.connect.core.AgentStateStore
import com.stella.connect.core.BridgeSettings
import com.stella.connect.core.ChatMessage
import com.stella.connect.core.ConnectionState
import com.stella.connect.core.DeviceCredential
import com.stella.connect.core.GatewayEndpoint
import com.stella.connect.core.K2Manager
import com.stella.connect.core.PairingOffer
import com.stella.connect.core.PermissionManager
import com.stella.connect.network.StellaGatewayDiscovery
import com.stella.connect.pairing.PairingPayloadParser
import com.stella.connect.pairing.PairingStorage
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.launch
import java.util.concurrent.Executors

import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.compose.ui.draw.clip
import kotlinx.coroutines.delay
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.material3.Icon
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts



@Composable
fun HolographicBackground() {
    AndroidView(
        factory = { ctx ->
            WebView(ctx).apply {
                settings.javaScriptEnabled = true
                settings.allowFileAccess = true
                settings.allowContentAccess = true
                settings.domStorageEnabled = true
                webViewClient = WebViewClient()
                setBackgroundColor(android.graphics.Color.TRANSPARENT)
                loadUrl("file:///android_asset/web_background/index.html")
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}

@Composable
fun StellaConnectApp(
    onRequestCameraPermission: () -> Unit,
    onRequestNotificationPermission: () -> Unit,
    onRequestAllPermissions: () -> Unit = {},
    onOpenSettings: (String) -> Unit = {},
    onRequestScreenControl: () -> Unit = {},
    onStartService: () -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val discovery = remember { StellaGatewayDiscovery(context) }
    val storage = remember { PairingStorage(context) }
    val connectionState by AgentStateStore.connectionState.collectAsState()
    val gateway by AgentStateStore.gateway.collectAsState()
    val credential by AgentStateStore.credential.collectAsState()
    val pairingOffer by AgentStateStore.pairingOffer.collectAsState()
    val status by AgentStateStore.statusText.collectAsState()
    val lastError by AgentStateStore.lastError.collectAsState()
    val logs by AgentStateStore.logs.collectAsState()
    val grantedPermissions by AgentStateStore.grantedPermissions.collectAsState()

    var showManual by rememberSaveable { mutableStateOf(false) }
    var manualHost by rememberSaveable { mutableStateOf("") }
    var manualPort by rememberSaveable { mutableStateOf("8765") }
    var scanError by rememberSaveable { mutableStateOf<String?>(null) }

    DisposableEffect(Unit) {
        onDispose { discovery.stop() }
    }

    val cameraGranted = grantedPermissions.contains("camera")
    val notificationsGranted = grantedPermissions.contains("notifications")

    // Nothing here is mandatory: the user decides how much Stella can reach,
    // so we always offer a way forward rather than a wall.
    val setupMissing = remember(grantedPermissions) {
        PermissionManager.capabilities
            .filter { it.id != "notifications" || !notificationsGranted }
            .filterNot { grantedPermissions.contains(it.id) }
    }

    val navController = rememberNavController()

    // The PC bridge is a setting, not a build flag: available in both
    // variants, on by default only for the personal K2 build.
    var bridgeOn by rememberSaveable {
        mutableStateOf(BridgeSettings.isEnabled(context))
    }

    // Determine start destination. With the bridge on and nothing paired yet,
    // the user most likely wants to reach their PC, so offer that first.
    val startDest = when {
        setupMissing.isNotEmpty() -> "permissions"
        credential != null -> "home"
        bridgeOn -> "connect"
        else -> "welcome"
    }

    LaunchedEffect(credential) {
        if (credential != null && navController.currentDestination?.route != "home" && navController.currentDestination?.route != "connected_anim") {
            navController.navigate("connected_anim") {
                popUpTo(0)
            }
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        // Render 3D Background
        HolographicBackground()

        // UI Overlay
        NavHost(
            navController = navController, 
            startDestination = startDest,
            modifier = Modifier.fillMaxSize(),
            enterTransition = { fadeIn(tween(500)) },
            exitTransition = { fadeOut(tween(500)) }
        ) {
            composable("permissions") {
                SetupScreen(
                    granted = grantedPermissions,
                    onRequestAll = onRequestAllPermissions,
                    onOpenSettings = onOpenSettings,
                    onRequestScreenControl = onRequestScreenControl,
                    onContinue = {
                        if (credential != null) navController.navigate("home") { popUpTo(0) }
                        else navController.navigate("welcome") { popUpTo(0) }
                    }
                )
            }
            composable("welcome") {
                WelcomeScreen(
                    onNext = { navController.navigate("about") }
                )
            }
            composable("about") {
                AboutScreen(
                    bridgeOn = bridgeOn,
                    onBridgeChange = { value ->
                        bridgeOn = value
                        BridgeSettings.setEnabled(context, value)
                    },
                    onNext = {
                        if (bridgeOn) navController.navigate("connect")
                        else navController.navigate("home")
                    },
                )
            }
            composable("connect") {
                // If they have an offer, jump to pairing
                if (pairingOffer != null) {
                    PairingPendingScreen(
                        offer = pairingOffer!!,
                        gateway = gateway,
                        state = connectionState,
                        status = status,
                        error = lastError,
                        onRequestPairing = onStartService,
                        onCancel = { AgentStateStore.setPairingOffer(null) },
                    )
                } else if (showManual) {
                    ManualConnectDialog(
                        host = manualHost, port = manualPort,
                        onHostChange = { manualHost = it }, onPortChange = { manualPort = it },
                        onDismiss = { showManual = false },
                        onConnect = {
                            val p = manualPort.toIntOrNull() ?: 8765
                            AgentStateStore.setGateway(GatewayEndpoint(name = "Stella PC", host = manualHost.trim(), port = p))
                            AgentStateStore.setStatus("Manual endpoint selected")
                            onStartService()
                            showManual = false
                            navController.navigate("connected_anim")
                        }
                    )
                } else {
                    ConnectChoiceScreen(
                        onScanQr = { 
                            if (!cameraGranted) onRequestCameraPermission()
                            navController.navigate("scanner") 
                        },
                        onEnterIp = { showManual = true },
                        onFindLocal = {
                            discovery.start(
                                onFound = {
                                    AgentStateStore.setGateway(it)
                                    AgentStateStore.setStatus("Gateway Online")
                                    onStartService()
                                    navController.navigate("connected_anim")
                                },
                                onError = { AgentStateStore.setError(it) }
                            )
                        },
                        // Just defer: bridge stays armed, so pairing is still one
                        // tap away from home next time.
                        onSkipForNow = {
                            AgentStateStore.setStatus("Running on-device - connect to your PC any time")
                            navController.navigate("home") { popUpTo(0) }
                        },
                        // Opt out permanently. This is what actually stops startup
                        // routing here - without it the K2 build defaults the
                        // bridge on and the user has no way past this screen.
                        onNeverAsk = {
                            bridgeOn = false
                            BridgeSettings.setEnabled(context, false)
                            AgentStateStore.setStatus("PC bridge off - you can turn it on in Settings")
                            navController.navigate("home") { popUpTo(0) }
                        }
                    )
                }
            }
            composable("scanner") {
                QrScannerScreen(
                    onBack = { navController.popBackStack() },
                    onRequestPermission = onRequestCameraPermission,
                    errorText = scanError,
                    onScanned = { raw ->
                        val offer = PairingPayloadParser.parse(raw)
                        if (offer == null) {
                            scanError = "That QR code does not look like a Stella pairing code."
                            AgentStateStore.setError(scanError)
                        } else {
                            scanError = null
                            storage.saveGatewayHint(offer)
                            AgentStateStore.setPairingOffer(offer)
                            AgentStateStore.setGateway(GatewayEndpoint(name = "Stella PC", host = offer.host, port = offer.port))
                            AgentStateStore.setStatus("Pairing payload loaded")
                            navController.popBackStack()
                        }
                    }
                )
            }
            composable("connected_anim") {
                ConnectedAnimatedScreen(
                    onFinished = { navController.navigate("home") { popUpTo(0) } }
                )
            }
            composable("home") {
                // `credential` is only set once paired with a PC. Skipping the
                // bridge leaves it null, and that used to render literally
                // nothing on top of the animated background. Standalone home
                // now exists: on-device status, K2 readiness, entry points
                // into chat and settings, bridge re-arm included.
                if (credential != null) {
                    ConnectedScreen(
                        credential = credential!!,
                        gateway = gateway,
                        state = connectionState,
                        logs = logs,
                        status = status,
                        onDisconnect = {
                            context.startService(Intent(context, StellaConnectForegroundService::class.java).apply {
                                action = StellaConnectForegroundService.ACTION_STOP
                            })
                            navController.navigate("welcome") { popUpTo(0) }
                        },
                        onOpenPermissions = {
                            val intent = Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                data = Uri.fromParts("package", context.packageName, null)
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                            context.startActivity(intent)
                        },
                        onOpenChat = { navController.navigate("chat") },
                        onOpenLocalModels = { navController.navigate("local_models") }
                    )
                } else {
                    StandaloneHomeScreen(
                        status = status,
                        onOpenChat = { navController.navigate("chat") },
                        onOpenLocalModels = { navController.navigate("local_models") },
                        onOpenSettings = {
                            val intent = Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                                data = Uri.fromParts("package", context.packageName, null)
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            }
                            context.startActivity(intent)
                        },
                        onPairPc = { navController.navigate("connect") }
                    )
                }
            }
            composable("chat") {
                ChatScreen(
                    onBack = { navController.popBackStack() },
                    onSendMessage = { text ->
                        val intent = Intent(context, StellaConnectForegroundService::class.java).apply {
                            action = StellaConnectForegroundService.ACTION_SEND_CHAT
                            putExtra(StellaConnectForegroundService.EXTRA_CHAT_TEXT, text)
                        }
                        context.startService(intent)
                    }
                )
            composable("local_models") {
                LocalModelsScreen(onBack = { navController.popBackStack() })
            }
            }
        }
    }
}

// --- NEW ONBOARDING SCREENS ---

@Composable
fun GlassCard(content: @Composable () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp),
        colors = CardDefaults.cardColors(
            containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.55f)
        ),
        shape = RoundedCornerShape(24.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))
    ) {
        Column(modifier = Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            content()
        }
    }
}

@Composable
fun WelcomeScreen(onNext: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
        Text("STELLA", style = MaterialTheme.typography.displayLarge, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
        Text("CONNECT", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Light, color = androidx.compose.ui.graphics.Color.White)
        Spacer(modifier = Modifier.height(60.dp))
        GlassCard {
            Text("Welcome to the neural bridge.", style = MaterialTheme.typography.bodyLarge, color = androidx.compose.ui.graphics.Color.White)
            Spacer(modifier = Modifier.height(24.dp))
            Button(onClick = onNext, modifier = Modifier.fillMaxWidth()) {
                Text("Get Started")
            }
        }
    }
}

@Composable
fun AboutScreen(
    bridgeOn: Boolean,
    onBridgeChange: (Boolean) -> Unit,
    onNext: () -> Unit,
) {
Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
        GlassCard {
            Text("Hardware Bridge", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
            Spacer(modifier = Modifier.height(16.dp))
            Text("This agent acts as a secure bridge between your Android device and your PC's Stella.", color = androidx.compose.ui.graphics.Color.White, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
            Spacer(modifier = Modifier.height(16.dp))
            Text("Turn this on when you want your phone to use the larger models running on your PC - most phones can't run them locally.", color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.65f), textAlign = androidx.compose.ui.text.style.TextAlign.Center, style = MaterialTheme.typography.bodySmall)
            Spacer(modifier = Modifier.height(16.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Connect to my PC", color = androidx.compose.ui.graphics.Color.White)
                Switch(
                    checked = bridgeOn,
                    onCheckedChange = onBridgeChange,
                )
            }
            Spacer(modifier = Modifier.height(24.dp))
            Button(onClick = onNext, modifier = Modifier.fillMaxWidth()) {
                Text(if (bridgeOn) "Next" else "Continue without bridge")
            }
        }
    }
}

@Composable
fun ConnectChoiceScreen(
    onScanQr: () -> Unit,
    onEnterIp: () -> Unit,
    onFindLocal: () -> Unit,
    onSkipForNow: () -> Unit,
    onNeverAsk: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        GlassCard {
            Text("Pair Device", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                "Linking to your PC is optional. Stella runs fully on this device until you connect.",
                color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.65f),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(modifier = Modifier.height(24.dp))
            Button(onClick = onScanQr, modifier = Modifier.fillMaxWidth()) { Text("Scan QR Code") }
            Spacer(modifier = Modifier.height(12.dp))
            OutlinedButton(onClick = onFindLocal, modifier = Modifier.fillMaxWidth()) { Text("Auto Discover") }
            Spacer(modifier = Modifier.height(12.dp))
            TextButton(onClick = onEnterIp, modifier = Modifier.fillMaxWidth()) { Text("Enter IP Manually", color = androidx.compose.ui.graphics.Color.White) }

            Spacer(modifier = Modifier.height(24.dp))
            HorizontalDivider(color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.12f))
            Spacer(modifier = Modifier.height(12.dp))

            // "Skip for now" keeps the bridge armed for a later launch.
            // "Not now" is the real exit: it also stops startup asking again.
            Button(onClick = onSkipForNow, modifier = Modifier.fillMaxWidth()) {
                Text("Skip for now - use Stella on this phone")
            }
            TextButton(onClick = onNeverAsk, modifier = Modifier.fillMaxWidth()) {
                Text("Don't ask me at startup", color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.7f))
            }
        }
    }
}

@Composable
fun ConnectedAnimatedScreen(onFinished: () -> Unit) {
    LaunchedEffect(Unit) {
        delay(2000)
        onFinished()
    }
    Column(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
        GlassCard {
            Text("Connection Established", style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.primary)
            Spacer(modifier = Modifier.height(16.dp))
            StellaSpinner(color = MaterialTheme.colorScheme.primary)
        }
    }
}


/**
 * Capabilities the user can hand to Stella.
 *
 * Every row is optional and the primary button is always live - the point of
 * the screen is to let the user decide the blast radius of the assistant, not
 * to gate entry behind a permission wall. Declining everything still yields a
 * working app, just a more limited one.
 */
@Composable
private fun SetupScreen(
    granted: Set<String>,
    onRequestAll: () -> Unit,
    onOpenSettings: (String) -> Unit,
    onRequestScreenControl: () -> Unit,
    onContinue: () -> Unit,
) {
    val caps = remember { PermissionManager.capabilities }
    val missing = caps.count { it.id !in granted }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp)
            .background(androidx.compose.ui.graphics.Color.Transparent)
            .verticalScroll(rememberScrollState()),
    ) {
        Text("SETUP", style = MaterialTheme.typography.headlineMedium,
             fontWeight = FontWeight.Black, color = androidx.compose.ui.graphics.Color.White)
        Spacer(Modifier.height(8.dp))
        Text(
            "Choose what Stella is allowed to reach. Everything is optional - " +
            "you can grant more later in Settings, and nothing here blocks launch.",
            color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.7f),
        )
        Spacer(Modifier.height(16.dp))

        Button(onClick = onRequestAll, modifier = Modifier.fillMaxWidth()) {
            Text("Grant all permissions ($missing missing)")
        }
        Spacer(Modifier.height(16.dp))

        caps.forEach { cap ->
            val isGranted = cap.id in granted
            Card(
                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                colors = CardDefaults.cardColors(
                    containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.55f),
                    contentColor = androidx.compose.ui.graphics.Color.White,
                ),
                border = androidx.compose.foundation.BorderStroke(
                    1.dp,
                    MaterialTheme.colorScheme.primary.copy(alpha = 0.3f),
                ),
            ) {
                Column(Modifier.padding(14.dp)) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(cap.label, fontWeight = FontWeight.Bold)
                        Text(
                            if (isGranted) "Granted" else "Optional",
                            color = if (isGranted) MaterialTheme.colorScheme.primary
                            else androidx.compose.ui.graphics.Color.White.copy(alpha = 0.5f),
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                    Spacer(Modifier.height(4.dp))
                    Text(
                        cap.why,
                        style = MaterialTheme.typography.bodySmall,
                        color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.65f),
                    )
                    if (!isGranted) {
                        Spacer(Modifier.height(8.dp))
                        when (cap.id) {
                            // Screen capture has its own per-use consent dialog.
                            "screen" -> OutlinedButton(
                                onClick = onRequestScreenControl,
                                modifier = Modifier.fillMaxWidth(),
                            ) { Text("Start screen control") }
                            // Accessibility + special perms live in Settings.
                            "autopilot", "files", "overlay", "install" -> OutlinedButton(
                                onClick = { onOpenSettings(cap.id) },
                                modifier = Modifier.fillMaxWidth(),
                            ) { Text("Open Settings") }
                            else -> OutlinedButton(
                                onClick = onRequestAll,
                                modifier = Modifier.fillMaxWidth(),
                            ) { Text("Allow") }
                        }
                    }
                }
            }
        }

        Spacer(Modifier.height(20.dp))
        // Always enabled on purpose: the user stays in control of what the AI
        // can see, rather than being forced into a full grant to get in.
        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                when {
                    missing == 0 -> "Continue"
                    missing == 1 -> "Continue without 1"
                    else -> "Continue without $missing"
                }
            )
        }
        Spacer(Modifier.height(8.dp))
        Text(
            "You can change any of this later in Android Settings.",
            style = MaterialTheme.typography.labelSmall,
            color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.45f),
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun PermissionRow(label: String, granted: Boolean) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label)
        Text(if (granted) "Granted" else "Needed", color = if (granted) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error)
    }
}

@Composable
private fun DiscoveryScreen(
    gateway: GatewayEndpoint?,
    status: String,
    error: String?,
    onConnect: (() -> Unit)?,
    onFindStella: () -> Unit,
    onScanQr: () -> Unit,
    onEnterIp: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp).background(androidx.compose.ui.graphics.Color.Transparent).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("STELLA", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black, color = androidx.compose.ui.graphics.Color.White)
        Spacer(Modifier.height(8.dp))
        Text("Connect this device to Stella AI.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(24.dp))
        Card(colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.55f), contentColor = androidx.compose.ui.graphics.Color.White), border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))) {
            Column(Modifier.padding(20.dp)) {
                Text("Connection", fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(6.dp))
                Text(gateway?.let { "${it.name} Â· ${it.host}:${it.port}" } ?: "No gateway selected")
                Spacer(Modifier.height(4.dp))
                Text(status, color = MaterialTheme.colorScheme.onSurfaceVariant)
                error?.let {
                    Spacer(Modifier.height(6.dp))
                    Text(it, color = MaterialTheme.colorScheme.error)
                }
            }
        }
        Spacer(Modifier.height(20.dp))
        if (gateway != null && onConnect != null) {
            Button(onClick = onConnect, modifier = Modifier.fillMaxWidth()) { Text("Connect") }
            Spacer(Modifier.height(12.dp))
        }
        Button(onClick = onFindStella, modifier = Modifier.fillMaxWidth()) { Text("Find Stella") }
        Spacer(Modifier.height(12.dp))
        FilledTonalButton(onClick = onScanQr, modifier = Modifier.fillMaxWidth()) { Text("Scan QR") }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(onClick = onEnterIp, modifier = Modifier.fillMaxWidth()) { Text("Enter IP") }
    }
}

@Composable
private fun PairingPendingScreen(
    offer: PairingOffer,
    gateway: GatewayEndpoint?,
    state: ConnectionState,
    status: String,
    error: String?,
    onRequestPairing: () -> Unit,
    onCancel: () -> Unit,
) {
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("CONNECT TO STELLA?", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
        Spacer(Modifier.height(8.dp))
        Text("${gateway?.name ?: "Stella PC"}\n${gateway?.host ?: offer.host}:${offer.port}", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(20.dp))
        Card(colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.55f), contentColor = androidx.compose.ui.graphics.Color.White), border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))) {
            Column(Modifier.padding(16.dp)) {
                Text("Pair this device?")
                Text("Code ${offer.pairingCode}", fontWeight = FontWeight.Bold)
                Text("State: $state")
                Text("Status: $status")
                error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }
        }
        Spacer(Modifier.height(20.dp))
        Button(onClick = onRequestPairing, modifier = Modifier.fillMaxWidth()) { Text("Request Pairing") }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(onClick = onCancel, modifier = Modifier.fillMaxWidth()) { Text("Cancel") }
    }
}

@Composable
private fun ConnectedScreen(
    credential: DeviceCredential,
    gateway: GatewayEndpoint?,
    state: ConnectionState,
    logs: List<String>,
    status: String,
    onDisconnect: () -> Unit,
    onOpenPermissions: () -> Unit,
    onOpenChat: () -> Unit,
    onOpenLocalModels: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp).background(androidx.compose.ui.graphics.Color.Transparent).verticalScroll(rememberScrollState()),
    ) {
        Text("STELLA", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black, color = androidx.compose.ui.graphics.Color.White)
        Spacer(Modifier.height(8.dp))
        Text("â— Connected", color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(20.dp))
        Card(colors = CardDefaults.cardColors(containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.55f), contentColor = androidx.compose.ui.graphics.Color.White), border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))) {
            Column(Modifier.padding(16.dp)) {
                Text(gateway?.name ?: "Stella PC", fontWeight = FontWeight.Bold)
                Text(credential.deviceName)
                Text("Battery status is reported by the agent.")
                Text("Network: Wi-Fi")
                Text("State: $state")
                Text(status)
            }
        }
        Spacer(Modifier.height(16.dp))
        
        Card(
            onClick = onOpenChat,
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                contentColor = MaterialTheme.colorScheme.primary
            ),
            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.4f))
        ) {
            Row(
                modifier = Modifier.padding(16.dp).fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Stella Chat", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(4.dp))
                    Text("Synchronized with your PC", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary.copy(alpha = 0.8f))
                }
                Icon(
                    imageVector = androidx.compose.material.icons.Icons.Default.Send,
                    contentDescription = "Open Chat",
                    tint = MaterialTheme.colorScheme.primary
                )
            }
        }
        Spacer(Modifier.height(16.dp))
        
        Button(onClick = onDisconnect, modifier = Modifier.fillMaxWidth()) { Text("Disconnect") }
        Spacer(Modifier.height(12.dp))
        FilledTonalButton(onClick = onOpenLocalModels, modifier = Modifier.fillMaxWidth()) {
            Text("Local Model")
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = onOpenPermissions, 
            modifier = Modifier.fillMaxWidth(),
            colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(
                containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.5f),
                contentColor = androidx.compose.ui.graphics.Color.White
            )
        ) {
            Text("Permissions", color = androidx.compose.ui.graphics.Color.White)
        }
        Spacer(Modifier.height(20.dp))
        Text("Recent Logs", fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        logs.takeLast(8).forEach { line ->
            Text(line, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/**
 * Local model manager - the mobile counterpart of the desktop "Local AI"
 * block, redesigned for a small screen: one action per full-width card.
 *
 * Three ways to get a running on-device model:
 *   1. Already on the phone -> pick a .gguf from device storage and Stella
 *      copies it in. No download, no network. This is what desktop had and
 *      mobile was missing.
 *   2. Download K2 Horizon  -> the one-tap pull (public, non-bundled build).
 *   3. Remove               -> free the space back.
 *
 * Everything routes through K2Manager so llama-server picks the file up the
 * same way however it arrived.
 */
@Composable
private fun LocalModelsScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val k2Status by K2Manager.statusLine.collectAsState()
    val progress by K2Manager.downloadProgress.collectAsState()
    val present = remember { mutableStateOf(K2Manager.modelPresent(context)) }

    LaunchedEffect(k2Status, progress) {
        if (progress !in 0f..0.999f) present.value = K2Manager.modelPresent(context)
    }

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: Exception) {}
            scope.launch {
                val ok = K2Manager.importLocalModel(context, uri)
                present.value = K2Manager.modelPresent(context)
                if (ok) K2Manager.start(context)
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp)
            .background(androidx.compose.ui.graphics.Color.Transparent)
            .verticalScroll(rememberScrollState()),
    ) {
        Text(
            "LOCAL MODEL",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Black,
            color = androidx.compose.ui.graphics.Color.White,
        )
        Spacer(Modifier.height(6.dp))
        Text(
            "Run Stella fully on this phone. Load a model you already have, or " +
                "download one.",
            style = MaterialTheme.typography.bodySmall,
            color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.65f),
        )
        Spacer(Modifier.height(16.dp))
        Card(
            colors = CardDefaults.cardColors(
                containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.55f),
                contentColor = androidx.compose.ui.graphics.Color.White,
            ),
            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f)),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(Modifier.padding(16.dp)) {
                Text("Status", fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(6.dp))
                Text(
                    when {
                        progress in 0f..0.999f -> "Loading ${(progress * 100).toInt()}%"
                        present.value -> "Model ready - on-device"
                        K2Manager.bundled -> k2Status
                        else -> "No model installed yet"
                    },
                    color = if (present.value) MaterialTheme.colorScheme.primary
                    else androidx.compose.ui.graphics.Color.White.copy(alpha = 0.7f),
                )
                Text(
                    if (K2Manager.bundled) "Build: on-device runtime bundled"
                    else "Build: download runtime",
                    style = MaterialTheme.typography.labelSmall,
                    color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.45f),
                )
            }
        }
        Spacer(Modifier.height(16.dp))
        if (progress in 0f..0.999f) {
            LinearProgressIndicator(
                progress = { progress.coerceIn(0f, 1f) },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(16.dp))
        }
        LocalModelsActions(
            present = present.value,
            progress = progress,
            onPick = { picker.launch(arrayOf("*/*")) },
            onDownload = {
                scope.launch {
                    if (K2Manager.prepare(context)) K2Manager.start(context)
                    present.value = K2Manager.modelPresent(context)
                }
            },
            onRemove = {
                K2Manager.deleteLocalModel(context)
                present.value = false
            },
        )
        Spacer(Modifier.height(24.dp))
        OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
            Text("Back", color = androidx.compose.ui.graphics.Color.White)
        }
    }
}


@Composable
private fun LocalModelsActions(
    present: Boolean,
    progress: Float,
    onPick: () -> Unit,
    onDownload: () -> Unit,
    onRemove: () -> Unit,
) {
    val busy = progress in 0f..0.999f
    Button(onClick = onPick, modifier = Modifier.fillMaxWidth(), enabled = !busy) {
        Text("Load a model from this phone")
    }
    Spacer(Modifier.height(8.dp))
    Text(
        "Pick any .gguf file already on your device (Downloads, Files, SD " +
            "card). Stella copies it in - nothing is uploaded.",
        style = MaterialTheme.typography.labelSmall,
        color = androidx.compose.ui.graphics.Color.White.copy(alpha = 0.5f),
    )
    Spacer(Modifier.height(20.dp))
    if (!K2Manager.bundled) {
        FilledTonalButton(
            onClick = onDownload,
            modifier = Modifier.fillMaxWidth(),
            enabled = !busy,
        ) {
            Text("Download K2 Horizon (~0.6 GB)")
        }
        Spacer(Modifier.height(20.dp))
    }
    OutlinedButton(
        onClick = onRemove,
        modifier = Modifier.fillMaxWidth(),
        enabled = present && !busy,
    ) {
        Text("Remove local model")
    }
}


/**
 * Standalone home: what the user sees when they skipped / dismissed the PC
 * bridge. Status card (K2 + bridge state), greeting, chat entry, settings
 * entry, and a route back into pairing.
 *
 * On first entry we also seed a greeting into the chat history so opening
 * "Stella Chat" feels alive instead of an empty thread. The guard is local
 * to this composable (rememberSaveable): rotation won't double-post it.
 */
@Composable
private fun StandaloneHomeScreen(
    status: String,
    onOpenChat: () -> Unit,
    onOpenLocalModels: () -> Unit,
    onOpenSettings: () -> Unit,
    onPairPc: () -> Unit,
) {
    val context = LocalContext.current
    val k2Mode by K2Manager.mode.collectAsState()
    val k2Status by K2Manager.statusLine.collectAsState()
    val k2Progress by K2Manager.downloadProgress.collectAsState()
    var greeted by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        if (greeted) return@LaunchedEffect
        greeted = true
        if (K2Manager.bundled) {
            if (K2Manager.modelPresent(context)) {
                K2Manager.start(context)
            } else {
                kotlinx.coroutines.CoroutineScope(kotlinx.coroutines.Dispatchers.IO).launch {
                    if (K2Manager.prepare(context)) K2Manager.start(context)
                }
            }
        }
        val welcomes = listOf(
            "Hey, I'm Stella - running right here on your phone.",
            "No PC needed. Ask me anything, or open Chat to talk.",
        )
        val now = java.util.UUID.randomUUID().toString()
        AgentStateStore.addChatMessage(
            ChatMessage(
                id = "stella-hello-$now",
                role = "assistant",
                text = welcomes.joinToString(" "),
                timestamp = System.currentTimeMillis(),
                status = "sent",
            )
        )
        AgentStateStore.addLog("Stella: standalone home shown (bridge skipped)")
    }

    val k2Line = when {
        k2Progress in 0f..0.999f -> "K2 model downloading ${(k2Progress * 100).toInt()}%"
        K2Manager.bundled && (k2Mode == "LOCAL") -> "K2 on-device ready"
        K2Manager.bundled -> k2Status
        else -> "On-device. No PC linked."
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp).verticalScroll(rememberScrollState()),
    ) {
        Text("STELLA", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black, color = androidx.compose.ui.graphics.Color.White)
        Spacer(Modifier.height(8.dp))
        Text("● On this device", color = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.height(20.dp))
        Card(
            colors = CardDefaults.cardColors(
                containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.55f),
                contentColor = androidx.compose.ui.graphics.Color.White
            ),
            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))
        ) {
            Column(Modifier.padding(16.dp)) {
                Text("Running on this phone", fontWeight = FontWeight.Bold)
                Text(k2Line)
                Text(status)
            }
        }
        Spacer(Modifier.height(16.dp))
        if (k2Progress in 0f..0.999f) {
            LinearProgressIndicator(
                progress = { k2Progress.coerceIn(0f, 1f) },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(16.dp))
        }

        Card(
            onClick = onOpenChat,
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f),
                contentColor = MaterialTheme.colorScheme.primary
            ),
            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.4f))
        ) {
            Row(
                modifier = Modifier.padding(16.dp).fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Stella Chat", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(4.dp))
                    Text(
                        "Talk to Stella on this phone",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary.copy(alpha = 0.8f)
                    )
                }
                Icon(
                    imageVector = androidx.compose.material.icons.Icons.Default.Send,
                    contentDescription = "Open Chat",
                    tint = MaterialTheme.colorScheme.primary
                )
            }
        }
        Spacer(Modifier.height(16.dp))

        Button(onClick = onPairPc, modifier = Modifier.fillMaxWidth()) { Text("Link to my PC") }
        Spacer(Modifier.height(12.dp))
        FilledTonalButton(onClick = onOpenLocalModels, modifier = Modifier.fillMaxWidth()) {
            Text("Local Model")
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = onOpenSettings,
            modifier = Modifier.fillMaxWidth(),
            colors = androidx.compose.material3.ButtonDefaults.outlinedButtonColors(
                containerColor = androidx.compose.ui.graphics.Color.Black.copy(alpha = 0.5f),
                contentColor = androidx.compose.ui.graphics.Color.White
            )
        ) {
            Text("Permissions", color = androidx.compose.ui.graphics.Color.White)
        }
        Spacer(Modifier.height(20.dp))
        Text("Recent Logs", fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
    }
}

@Composable
private fun ManualConnectDialog(
    host: String,
    port: String,
    onHostChange: (String) -> Unit,
    onPortChange: (String) -> Unit,
    onDismiss: () -> Unit,
    onConnect: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Enter IP") },
        text = {
            Column {
                OutlinedTextField(value = host, onValueChange = onHostChange, label = { Text("Host") }, singleLine = true)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(value = port, onValueChange = onPortChange, label = { Text("Port") }, singleLine = true)
            }
        },
        confirmButton = { TextButton(onClick = onConnect) { Text("Connect") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

@Composable
private fun QrScannerScreen(
    onBack: () -> Unit,
    onRequestPermission: () -> Unit,
    errorText: String?,
    onScanned: (String) -> Unit,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var previewReady by remember { mutableStateOf(false) }
    var scanHandled by remember { mutableStateOf(false) }
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }

    DisposableEffect(Unit) {
        onDispose {
            cameraExecutor.shutdown()
        }
    }

    Column(Modifier.fillMaxSize().padding(24.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TextButton(onClick = onBack) { Text("Back") }
            Text("Scan QR", fontWeight = FontWeight.Bold)
            Spacer(Modifier.size(48.dp))
        }
        Spacer(Modifier.height(16.dp))
        Card(modifier = Modifier.fillMaxWidth().height(420.dp), shape = RoundedCornerShape(20.dp)) {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { viewContext ->
                    PreviewView(viewContext).also { previewView ->
                        val cameraProviderFuture = ProcessCameraProvider.getInstance(viewContext)
                        cameraProviderFuture.addListener({
                            val cameraProvider = cameraProviderFuture.get()
                            val preview = Preview.Builder().build()
                            val imageAnalysis = ImageAnalysis.Builder()
                                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                                .build()
                            val scanner = BarcodeScanning.getClient(
                                BarcodeScannerOptions.Builder()
                                    .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                                    .build(),
                            )
                            imageAnalysis.setAnalyzer(cameraExecutor) { imageProxy ->
                                val mediaImage = imageProxy.image
                                if (mediaImage != null) {
                                    val image = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)
                                    scanner.process(image)
                                        .addOnSuccessListener { codes ->
                                            if (!scanHandled) {
                                                codes.firstOrNull()?.rawValue?.let { raw ->
                                                    scanHandled = true
                                                    onScanned(raw)
                                                }
                                            }
                                        }
                                        .addOnCompleteListener {
                                            imageProxy.close()
                                        }
                                } else {
                                    imageProxy.close()
                                }
                            }
                            cameraProvider.unbindAll()
                            cameraProvider.bindToLifecycle(
                                lifecycleOwner,
                                CameraSelector.DEFAULT_BACK_CAMERA,
                                preview,
                                imageAnalysis,
                            )
                            preview.setSurfaceProvider(previewView.surfaceProvider)
                            previewReady = true
                        }, ContextCompat.getMainExecutor(viewContext))
                    }
                }
            )
        }
        if (!previewReady) {
            Spacer(Modifier.height(12.dp))
            Text("Camera is preparing.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (!errorText.isNullOrBlank()) {
            Spacer(Modifier.height(8.dp))
            Text(errorText, color = MaterialTheme.colorScheme.error)
        }
    }
}

