package com.stella.connect.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.stella.connect.ui.theme.Exo2
import com.stella.connect.ui.theme.Orbitron
import com.stella.connect.ui.theme.StellaTheme

/**
 * The Stella logo used as a spinner, loading screen, or splash screen.
 *
 * Modes:
 *  - [SpinnerMode.Inline] — small rotating mark for inline busy states (buttons,
 *    list items, dialogs). This is the original widget behavior.
 *  - [SpinnerMode.Loading] — full-screen loading screen: mark centered over a
 *    void-black background with an optional status line beneath it.
 *  - [SpinnerMode.Splash] — branded launch screen: large mark above the "Stella"
 *    wordmark, centered, fading content. Use on app launch while the engine or
 *    preferences initialize.
 *
 * Every busy state in the app shows the mark rotating with a comet-tail
 * gradient rather than a generic Material progress arc, so loading reads as
 * "Stella is working" instead of a stock widget.
 *
 * The tail is a conic-style sweep rendered as a stack of segments whose alpha
 * decays with angular distance from the head, which keeps it cheap enough to
 * animate at 60fps without shaders.
 */
enum class SpinnerMode {
    /** Small inline spinner for button/list busy states. */
    Inline,
    /** Full-screen loading screen with optional status line. */
    Loading,
    /** Branded splash screen with Stella wordmark. */
    Splash,
}

@Composable
fun StellaSpinner(
    modifier: Modifier = Modifier,
    mode: SpinnerMode = SpinnerMode.Inline,
    size: Dp = 40.dp,
    strokeWidth: Dp = 3.dp,
    color: Color = Color.Unspecified,
    /** Full rotation period; lower = faster. */
    periodMillis: Int = 1100,
    /** Status line shown beneath the mark in Loading mode. */
    status: String = "",
    /** Status line text color; defaults to the theme's secondary text. */
    statusColor: Color = Color.Unspecified,
    /** Status line text size. */
    statusSize: TextUnit = 14.sp,
) {
    val markColor = if (color == Color.Unspecified) StellaTheme.colors.primary else color
    val resolvedStatusColor =
        if (statusColor == Color.Unspecified) StellaTheme.colors.textSecondary else statusColor
    val transition = rememberInfiniteTransition(label = "stella-spinner")
    val angle by transition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(periodMillis, easing = LinearEasing),
            repeatMode = RepeatMode.Restart,
        ),
        label = "stella-spinner-angle",
    )

    when (mode) {
        SpinnerMode.Inline -> {
            StellaMark(
                angle = angle,
                markSize = size,
                strokeWidth = strokeWidth,
                color = markColor,
                modifier = modifier,
            )
        }
        SpinnerMode.Loading -> {
            Box(
                modifier = modifier
                    .fillMaxSize()
                    .background(StellaTheme.colors.bg),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    StellaMark(
                        angle = angle,
                        markSize = 64.dp,
                        strokeWidth = strokeWidth,
                        color = markColor,
                    )
                    if (status.isNotBlank()) {
                        Spacer(modifier = Modifier.height(20.dp))
                        Text(
                            text = status,
                            style = TextStyle(
                                fontFamily = Exo2,
                                fontWeight = FontWeight.Medium,
                                fontSize = statusSize,
                                color = resolvedStatusColor,
                            ),
                        )
                    }
                }
            }
        }
        SpinnerMode.Splash -> {
            Box(
                modifier = modifier
                    .fillMaxSize()
                    .background(StellaTheme.colors.bg),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    StellaMark(
                        angle = angle,
                        markSize = 100.dp,
                        strokeWidth = strokeWidth,
                        color = markColor,
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Text(
                        text = "Stella",
                        style = TextStyle(
                            fontFamily = Orbitron,
                            fontWeight = FontWeight.Black,
                            fontSize = 40.sp,
                            letterSpacing = 2.sp,
                            color = StellaTheme.colors.textPrimary,
                        ),
                    )
                    Text(
                        text = "on-device AI",
                        style = TextStyle(
                            fontFamily = Exo2,
                            fontWeight = FontWeight.Medium,
                            fontSize = 14.sp,
                            letterSpacing = 1.sp,
                            color = StellaTheme.colors.textSecondary,
                        ),
                    )
                }
            }
        }
    }
}

/**
 * The rotating comet-tail mark itself, extracted so every mode renders the
 * same widget at whatever size the caller asks for.
 */
@Composable
private fun StellaMark(
    angle: Float,
    markSize: Dp,
    strokeWidth: Dp,
    color: Color,
    modifier: Modifier = Modifier,
) {
    Canvas(modifier = modifier.size(markSize)) {
        val stroke = strokeWidth.toPx()
        val inset = stroke / 2f
        val side = this.size.minDimension - stroke
        val topLeft = Offset(inset, inset)
        val diameter = side.coerceAtLeast(1f)

        drawArc(
            brush = Brush.sweepGradient(
                // alpha falls off around the circle -> comet tail
                0.00f to color.copy(alpha = 0.0f),
                0.55f to color.copy(alpha = 0.15f),
                0.85f to color.copy(alpha = 0.55f),
                0.98f to color.copy(alpha = 0.95f),
                1.00f to color,
                center = center,
            ),
            startAngle = angle,
            sweepAngle = 268f,
            useCenter = false,
            topLeft = topLeft,
            size = androidx.compose.ui.geometry.Size(diameter, diameter),
            style = Stroke(width = stroke, cap = androidx.compose.ui.graphics.StrokeCap.Round),
        )
    }
}