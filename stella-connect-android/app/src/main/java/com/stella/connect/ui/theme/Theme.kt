package com.stella.connect.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.stella.connect.R

private val StellaDarkColors = darkColorScheme(
    primary = Color(0xFF00E5FF),
    onPrimary = Color(0xFF020305),
    secondary = Color(0xFF7C6EE6),
    background = Color(0xFF020305),
    surface = Color(0xFF0B0D12),
    surfaceVariant = Color(0xFF10131A),
    onSurface = Color(0xFFF4F6F8),
    onSurfaceVariant = Color(0xFFB7BEC8),
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

// Futuristic type. Orbitron is the wide, geometric display face used for the
// brand + headers; Exo 2 is its legible sibling for body/UI text. Both are
// variable fonts (weight axis) bundled under res/font, so no extra downloads.
val Orbitron = FontFamily(Font(R.font.orbitron, FontWeight.Normal))
val Exo2 = FontFamily(Font(R.font.exo2, FontWeight.Normal))

private val StellaTypography = Typography(
    displayLarge = TextStyle(fontFamily = Orbitron, fontWeight = FontWeight.Black, fontSize = 40.sp, letterSpacing = 2.sp),
    displayMedium = TextStyle(fontFamily = Orbitron, fontWeight = FontWeight.Bold, fontSize = 32.sp, letterSpacing = 1.5.sp),
    headlineSmall = TextStyle(fontFamily = Orbitron, fontWeight = FontWeight.Bold, fontSize = 22.sp, letterSpacing = 1.sp),
    titleLarge = TextStyle(fontFamily = Orbitron, fontWeight = FontWeight.Bold, fontSize = 20.sp, letterSpacing = 1.sp),
    titleMedium = TextStyle(fontFamily = Exo2, fontWeight = FontWeight.SemiBold, fontSize = 16.sp),
    bodyLarge = TextStyle(fontFamily = Exo2, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 22.sp),
    bodyMedium = TextStyle(fontFamily = Exo2, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontFamily = Exo2, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 16.sp),
    labelLarge = TextStyle(fontFamily = Exo2, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, letterSpacing = 0.5.sp),
    labelSmall = TextStyle(fontFamily = Exo2, fontWeight = FontWeight.Medium, fontSize = 11.sp, letterSpacing = 0.5.sp),
)

@Composable
fun StellaConnectTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = StellaDarkColors,
        typography = StellaTypography,
        content = content,
    )
}

