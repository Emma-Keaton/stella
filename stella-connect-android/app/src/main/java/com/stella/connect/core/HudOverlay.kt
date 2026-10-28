package com.stella.connect.core

import android.content.Context
import android.content.SharedPreferences
import android.graphics.PixelFormat
import android.os.Build
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import androidx.compose.ui.graphics.toArgb
import com.stella.connect.ui.theme.StellaThemeState

/**
 * HUD overlay: a draggable floating panel shown on top of all other apps.
 * Requires `SYSTEM_ALERT_WINDOW` (declared in AndroidManifest.xml).
 *
 * Shows Stella's live voice/chat status and streams response text.
 * Dragging the header repositions the panel; position is persisted.
 *
 * Controls: title chip + status pill (Listening/Speaking/Idle), mic toggle,
 * close button. Drag the header to move.
 */
class HudOverlay private constructor(
    private val context: Context,
    private val windowManager: WindowManager,
    private val prefs: SharedPreferences,
) {
    private var rootView: View? = null
    private var params: WindowManager.LayoutParams? = null
    private var statusView: TextView? = null
    private var textView: TextView? = null

    private var touchX = 0f
    private var touchY = 0f
    private var viewX = 0
    private var viewY = 0

    private val listener = View.OnTouchListener { _, event ->
        when (event.action and MotionEvent.ACTION_MASK) {
            MotionEvent.ACTION_DOWN -> {
                touchX = event.rawX
                touchY = event.rawY
                viewX = params?.x ?: 0
                viewY = params?.y ?: 0
                true
            }
            MotionEvent.ACTION_MOVE -> {
                val dx = (event.rawX - touchX).toInt()
                val dy = (event.rawY - touchY).toInt()
                viewX += dx
                viewY += dy
                touchX = event.rawX
                touchY = event.rawY
                params?.let { p ->
                    p.x = viewX
                    p.y = viewY
                    windowManager.updateViewLayout(rootView, p)
                    prefs.edit().putInt("hud_x", viewX).putInt("hud_y", viewY).apply()
                }
                true
            }
            else -> false
        }
    }

    fun show() {
        if (rootView != null) return
        // Read the active theme once at creation; the HUD restyles on next show.
        val palette = StellaThemeState.colors
        val panel = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(palette.bg.toArgb())
                cornerRadius = 16f * context.resources.displayMetrics.density
                setStroke((1f * context.resources.displayMetrics.density).toInt(), palette.surfaceRaised.toArgb())
            }
            setPadding(16, 12, 16, 12)
            elevation = 8f * context.resources.displayMetrics.density
        }

        // Header: title + status + controls, draggable
        val header = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val title = TextView(context).apply {
            text = "Stella"
            setTextColor(palette.textPrimary.toArgb())
            textSize = 16f
            setTypeface(null, android.graphics.Typeface.BOLD)
        }
        val status = TextView(context).apply {
            text = "Idle"
            setTextColor(palette.primary.toArgb())
            textSize = 12f
        }
        statusView = status

        val micBtn = makeChip(context, "Mic", palette.surfaceRaised.toArgb(), palette.textPrimary.toArgb()) { }
        val closeBtn = makeChip(context, "✕", palette.borderStrong.toArgb(), palette.textPrimary.toArgb()) {
            hide()
        }

        header.addView(title)
        header.addView(TextView(context).apply {
            text = "  •  "
            setTextColor(palette.textMuted.toArgb())
            textSize = 12f
        })
        header.addView(status)
        header.addView(View(context).apply { layoutParams = LinearLayout.LayoutParams(0, 0, 1f) })
        header.addView(micBtn)
        header.addView(closeBtn)

        // Body: streaming text
        val body = TextView(context).apply {
            text = ""
            setTextColor(palette.textPrimary.toArgb())
            textSize = 13f
            maxLines = 4
            ellipsize = android.text.TextUtils.TruncateAt.END
        }
        textView = body

        panel.addView(header)
        panel.addView(body)
        header.setOnTouchListener(listener)

        val density = context.resources.displayMetrics.density
        val savedX = prefs.getInt("hud_x", -1)
        val savedY = prefs.getInt("hud_y", -1)
        params = WindowManager.LayoutParams(
            (PANEL_WIDTH_DP * density).toInt(),
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                @Suppress("DEPRECATION") WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = if (savedX >= 0) savedX else 24
            y = if (savedY >= 0) savedY else 100
        }
        windowManager.addView(panel, params)
        rootView = panel
    }

    private val PANEL_WIDTH_DP = 300f

    /** Show or replace the HUD text. Creates the HUD if not showing. */
    fun showText(text: String) {
        show()
        textView?.text = text
    }

    /** Append text to the HUD (for streaming). Creates the HUD if not showing. */
    fun appendText(chunk: String) {
        show()
        val cur = textView?.text?.toString() ?: ""
        textView?.text = cur + chunk
    }

    /** Clear the HUD text. */
    fun clearText() {
        textView?.text = ""
    }

    fun hide() {
        rootView?.let { windowManager.removeView(it) }
        rootView = null
        params = null
        statusView = null
        textView = null
    }

    val isShowing: Boolean
        get() = rootView != null

    companion object {
        @Volatile private var instance: HudOverlay? = null

        fun init(context: Context): HudOverlay {
            return synchronized(this) {
                instance ?: HudOverlay(
                    context.applicationContext,
                    context.getSystemService(Context.WINDOW_SERVICE) as WindowManager,
                    context.getSharedPreferences("stella_hud", Context.MODE_PRIVATE),
                ).also { instance = it }
            }
        }

        fun get(): HudOverlay? = instance

        fun shutdown() {
            synchronized(this) {
                instance?.hide()
                instance = null
            }
        }
    }

    private fun makeChip(
        context: Context,
        label: String,
        bg: Int,
        fg: Int,
        onClick: () -> Unit
    ): TextView {
        return TextView(context).apply {
            text = label
            setTextColor(fg)
            textSize = 12f
            setBackgroundColor(bg)
            setPadding(8, 4, 8, 4)
            clipToOutline = true
            setOnClickListener { onClick() }
        }
    }
}