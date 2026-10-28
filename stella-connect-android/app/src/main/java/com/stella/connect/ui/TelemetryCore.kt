package com.stella.connect.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.stella.connect.ui.theme.StellaTheme
import kotlin.math.cos
import kotlin.math.sin

/**
 * The Welcome telemetry core — the "Holographic Particle Core" from
 * screens.md: a glow halo (breathing at 6 s), an outer ring of 12 ticks
 * rotating clockwise at 24 s/rev, an inner ring of 8 ticks
 * counter-rotating at 18 s/rev, and a mint energy centre.
 *
 * Pure Canvas — no images, no WebView, 60 fps cheap. Used by the Welcome /
 * Setup screen; also works as a compact status widget anywhere else.
 */
@Composable
fun TelemetryCore(
    modifier: Modifier = Modifier,
    coreSize: Dp = 144.dp,
) {
    val transition = rememberInfiniteTransition(label = "telemetry-core")
    val cw by transition.animateFloat(
        initialValue = 0f, targetValue = 360f,
        animationSpec = infiniteRepeatable(tween(24000, easing = LinearEasing)),
        label = "cw",
    )
    val ccw by transition.animateFloat(
        initialValue = 360f, targetValue = 0f,
        animationSpec = infiniteRepeatable(tween(18000, easing = LinearEasing)),
        label = "ccw",
    )
    val halo by transition.animateFloat(
        initialValue = 1f, targetValue = 1.12f,
        animationSpec = infiniteRepeatable(tween(3000, easing = LinearEasing), RepeatMode.Reverse),
        label = "halo",
    )

    val palette = StellaTheme.colors
    Box(modifier = modifier.size(coreSize), contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.matchParentSize()) {
            val center = Offset(size.width / 2f, size.height / 2f)
            val base = size.minDimension / 2f

            // --- diffuse glowing ambient sphere (halo) ---
            drawCircle(
                brush = Brush.radialGradient(
                    0.0f to palette.secondary.copy(alpha = 0.25f),
                    0.6f to palette.primary.copy(alpha = 0.18f),
                    1.0f to Color.Transparent,
                    center = center,
                    radius = (base * halo).coerceAtLeast(1f),
                ),
                radius = (base * halo).coerceAtLeast(1f),
                center = center,
            )

            // --- outer ring: 12 ticks, clockwise ---
            tickRing(center = center, radius = base * 0.86f, ticks = 12, offsetDeg = cw,
                color = palette.secondary.copy(alpha = 0.6f), tickDp = 5.dp.toPx())

            // --- inner ring: 8 ticks, counter-rotating ---
            tickRing(center = center, radius = base * 0.64f, ticks = 8, offsetDeg = ccw,
                color = palette.primary.copy(alpha = 0.7f), tickDp = 4.dp.toPx())

            // --- core energy centre ---
            val core = base * 0.22f
            drawCircle(
                brush = Brush.radialGradient(
                    0.0f to palette.primary,
                    0.7f to palette.primary.copy(alpha = 0.5f),
                    1.0f to Color.Transparent,
                    center = center,
                    radius = (core * 2f).coerceAtLeast(1f),
                ),
                radius = (core * 2f).coerceAtLeast(1f),
                center = center,
            )
            drawCircle(color = palette.textPrimary.copy(alpha = 0.92f), radius = core * 0.45f, center = center)
        }
    }
}

/** Draw [ticks] short radial ticks on a ring, rotated by [offsetDeg]. */
private fun androidx.compose.ui.graphics.drawscope.DrawScope.tickRing(
    center: Offset,
    radius: Float,
    ticks: Int,
    offsetDeg: Float,
    color: Color,
    tickDp: Float,
) {
    for (i in 0 until ticks) {
        val a = Math.toRadians((offsetDeg + i * (360f / ticks)).toDouble())
        val dir = Offset(cos(a).toFloat(), sin(a).toFloat())
        drawLine(
            color = color,
            start = center + dir * (radius - tickDp),
            end = center + dir * (radius + tickDp),
            strokeWidth = 2.dp.toPx(),
        )
    }
}