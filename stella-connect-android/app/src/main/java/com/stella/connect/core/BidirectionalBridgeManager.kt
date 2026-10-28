package com.stella.connect.core

import android.content.Context
import com.stella.connect.core.BridgeSettings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import java.net.ServerSocket

/**
 * Bidirectional PC bridge manager.
 * 
 * Enables mobile-as-host mode for device control and power sharing.
 * Integrates with Google Artemis for targeted ADB device control.
 */
object BidirectionalBridgeManager {
    
    private const val DEFAULT_HOST_PORT = 8765
    private const val MOBILE_HOST_MODE_PREF = "mobile_host_mode"
    private var serverJob: Job? = null
    private var serverSocket: ServerSocket? = null
    
    fun isMobileHostEnabled(context: Context): Boolean {
        val prefs = context.getSharedPreferences("stella_bridge", Context.MODE_PRIVATE)
        return prefs.getBoolean(MOBILE_HOST_MODE_PREF, false)
    }
    
    fun setMobileHostEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences("stella_bridge", Context.MODE_PRIVATE)
            .edit().putBoolean(MOBILE_HOST_MODE_PREF, enabled).apply()
    }
    
    fun getMobileHostEndpoint(context: Context): Pair<String, Int> {
        return Pair("0.0.0.0", DEFAULT_HOST_PORT)
    }
    
    fun startBidirectionalBridge(context: Context) {
        if (!BridgeSettings.isEnabled(context) || !isMobileHostEnabled(context)) return
        
        serverJob = CoroutineScope(Dispatchers.IO).launch {
            try {
                serverSocket = ServerSocket(DEFAULT_HOST_PORT)
                while (true) {
                    val client = serverSocket?.accept()
                    client?.let {
                        // Handle desktop connection for power sharing and device control
                        // Route to ArtemisDeviceController
                    }
                }
            } catch (e: Exception) {
                // Log error
            }
        }
    }
    
    fun stopBidirectionalBridge(context: Context) {
        serverJob?.cancel()
        serverSocket?.close()
        serverSocket = null
        serverJob = null
    }
}
