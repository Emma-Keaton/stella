package com.stella.connect.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.stella.connect.ui.theme.StellaBrand

/**
 * The Stella logo used as a spinner.
 *
 * Every busy state in the app shows the mark rotating with a comet-tail
 * gradient rather than a generic Material progress arc, so loading reads as
 * "Stella is working" instead of a stock widget.
 *
 * The tail is a conic-style sweep rendered as a stack of segments whose alpha
 * decays with angular distance from the head, which keeps it cheap enough to
 * animate at 60fps without shaders.
 */
@Composable
fun StellaSpinner(
    modifier: Modifier = Modifier,
    size: Dp = 40.dp,
    strokeWidth: Dp = 3.dp,
    color: Color = StellaBrand.primary,
    /** Full rotation period; lower = faster. */
    periodMillis: Int = 1100,
) {
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

    Canvas(modifier = modifier.size(size)) {
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