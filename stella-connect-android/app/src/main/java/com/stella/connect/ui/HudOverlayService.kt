package com.stella.connect.ui

import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.IBinder
import android.view.Gravity
import android.view.ViewGroup
import android.view.WindowManager
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.ComposeView
import com.stella.connect.ui.theme.StellaTheme

class HudOverlayService : Service() {
    private var windowManager: WindowManager? = null
    private var overlayView: ComposeView? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        overlayView = ComposeView(this).apply {
            setContent {
                HudCard(onDismiss = { stopSelf() })
            }
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
            y = 200
        }
        windowManager?.addView(overlayView, params)
    }

    override fun onDestroy() {
        overlayView?.let { windowManager?.removeView(it) }
        super.onDestroy()
    }
}

@Composable
fun HudCard(onDismiss: () -> Unit) {
    // Compact system overlay UI
}
