package com.stella.connect.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val StellaDarkColors = darkColorScheme(
    primary = Color(0xFFFFFFFF),
    onPrimary = Color.Black,
    secondary = Color(0xFF00E5FF),
    background = Color(0xFF020305),
    surface = Color(0xFF0B0D12),
    surfaceVariant = Color(0xFF10131A),
    onSurface = Color(0xFFF4F6F8),
    onSurfaceVariant = Color(0xFF8E949D),
    error = Color(0xFFFF6B6B),
)

/**
 * Brand tokens kept out of the Material scheme so the logo spinner and any
 * future marketing surface can use them without inheriting theme semantics.
 */
object StellaBrand {
    val primary = Color(0xFF00E5FF)
    val accent = Color(0xFFFFFFFF)
    val ink = Color(0xFF020305)
}

@Composable
fun StellaConnectTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = StellaDarkColors,
        typography = androidx.compose.material3.Typography(),
        content = content,
    )
}
