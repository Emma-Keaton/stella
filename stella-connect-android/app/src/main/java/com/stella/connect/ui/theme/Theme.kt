package com.stella.connect.ui.theme

import android.content.Context
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.stella.connect.R

/**
 * Stella's four complete themes, one id per themes.json entry:
 *
 *  - [StellaThemeStyle.VOID]   - the brand: deep void, mint/cyan/violet, neon glow. Default.
 *  - [StellaThemeStyle.OLED]   - true black surfaces for AMOLED, reduced glow.
 *  - [StellaThemeStyle.AURORA] - violet-tinted night: surfaces, borders and type all shift.
 *  - [StellaThemeStyle.LIGHT]  - daylight: off-white surfaces, deep-mint actions, no glow.
 *
 * Every theme carries the full 32-token contract from themes.json (see
 * [STELLA_TOKENS]) plus a complete Material3 [ColorScheme] derived from those
 * tokens. Screens read colours through [StellaTheme.colors] or
 * `MaterialTheme.colorScheme`, so switching the style restyles everything on
 * the next frame.
 */
enum class StellaThemeStyle(val id: String) {
    VOID("void"),
    OLED("oled"),
    AURORA("aurora"),
    LIGHT("light");

    companion object {
        /** Parse a stored id; unknown/legacy values (old "DARK") fall back to VOID. */
        fun fromId(raw: String?): StellaThemeStyle =
            values().firstOrNull { it.id.equals(raw, ignoreCase = true) }
                ?: when (raw?.uppercase()) {
                    "DARK" -> VOID          // legacy pref from the 3-style era
                    "LIGHT" -> LIGHT
                    "AURORA" -> AURORA
                    else -> VOID
                }
    }
}

/** Process-wide theme selection, persisted in stella_prefs (theme_style key). */
object StellaThemeState {
    val style = mutableStateOf(StellaThemeStyle.VOID)
    val largeText = mutableStateOf(false)
    private const val PREF = "stella_prefs"
    private const val KEY = "theme_style"
    private const val KEY_TEXT = "text_size_large"

    /** Read the persisted theme (call once before setContent). */
    fun init(context: Context) {
        try {
            val prefs = context.getSharedPreferences(PREF, Context.MODE_PRIVATE)
            style.value = StellaThemeStyle.fromId(prefs.getString(KEY, null))
            largeText.value = prefs.getBoolean(KEY_TEXT, false)
        } catch (_: Exception) {
            style.value = StellaThemeStyle.VOID
            largeText.value = false
        }
    }

    /** Persist + apply a new theme. */
    fun set(context: Context, value: StellaThemeStyle) {
        style.value = value
        try {
            context.getSharedPreferences(PREF, Context.MODE_PRIVATE)
                .edit().putString(KEY, value.id).apply()
        } catch (_: Exception) {}
    }

    /** Persist + apply the Normal/Large text-size step. */
    fun setLargeText(context: Context, value: Boolean) {
        largeText.value = value
        try {
            context.getSharedPreferences(PREF, Context.MODE_PRIVATE)
                .edit().putBoolean(KEY_TEXT, value).apply()
        } catch (_: Exception) {}
    }

    /**
     * Non-composable accessor for view-based surfaces (HudOverlay, widgets)
     * that cannot read a CompositionLocal. Composables should prefer
     * [StellaTheme.colors] so they recompose on switches.
     */
    val colors: StellaColors
        get() = StellaColors.forStyle(style.value)
}

/**
 * Mirror of themes.json (repo root) - the THEMES CONTRACT. Every theme
 * defines all 32 tokens. ThemeContractTest parses the real themes.json and
 * fails this map on any drift, so treat it as generated, not hand-editable.
 */
val STELLA_TOKENS: Map<String, Map<String, String>> = mapOf(
    "void" to mapOf(
        "bg" to "#0C0D14",
        "surface" to "#12141F",
        "surface-raised" to "#161926",
        "glass" to "rgba(18, 20, 31, 0.72)",
        "glass-border" to "rgba(255, 255, 255, 0.08)",
        "text-primary" to "#F4F6F8",
        "text-secondary" to "#8A93A6",
        "text-muted" to "#7E879B",
        "border" to "#1E2233",
        "border-strong" to "#5C637A",
        "primary" to "#00E5A3",
        "on-primary" to "#020305",
        "secondary" to "#00F0FF",
        "on-secondary" to "#020305",
        "tertiary" to "#8D80F0",
        "on-tertiary" to "#020305",
        "success" to "#00E5A3",
        "on-success" to "#020305",
        "warning" to "#FFB300",
        "on-warning" to "#020305",
        "error" to "#FF6B6B",
        "on-error" to "#020305",
        "focus-ring" to "#00F0FF",
        "bubble-user" to "#13141E",
        "bubble-stella" to "rgba(18, 20, 30, 0.75)",
        "bubble-user-text" to "#F4F6F8",
        "bubble-stella-text" to "#F4F6F8",
        "button-content" to "#020305",
        "button-content-disabled" to "#5C6478",
        "scrim" to "rgba(2, 3, 5, 0.55)",
        "glow" to "0 0 16px rgba(0, 240, 255, 0.35)",
        "elevation-shadow" to "0 8px 32px rgba(0, 0, 0, 0.60)",
    ),
    "oled" to mapOf(
        "bg" to "#000000",
        "surface" to "#0A0A0C",
        "surface-raised" to "#121215",
        "glass" to "rgba(10, 10, 12, 0.85)",
        "glass-border" to "rgba(255, 255, 255, 0.10)",
        "text-primary" to "#F4F6F8",
        "text-secondary" to "#8A93A6",
        "text-muted" to "#7E879B",
        "border" to "#1A1A1E",
        "border-strong" to "#5C637A",
        "primary" to "#00E5A3",
        "on-primary" to "#020305",
        "secondary" to "#00F0FF",
        "on-secondary" to "#020305",
        "tertiary" to "#8D80F0",
        "on-tertiary" to "#020305",
        "success" to "#00E5A3",
        "on-success" to "#020305",
        "warning" to "#FFB300",
        "on-warning" to "#020305",
        "error" to "#FF6B6B",
        "on-error" to "#020305",
        "focus-ring" to "#00F0FF",
        "bubble-user" to "#0A0A0C",
        "bubble-stella" to "rgba(18, 18, 21, 0.85)",
        "bubble-user-text" to "#F4F6F8",
        "bubble-stella-text" to "#F4F6F8",
        "button-content" to "#020305",
        "button-content-disabled" to "#5C6478",
        "scrim" to "rgba(0, 0, 0, 0.65)",
        "glow" to "0 0 8px rgba(0, 229, 163, 0.18)",
        "elevation-shadow" to "0 8px 32px rgba(0, 0, 0, 0.80)",
    ),
    "aurora" to mapOf(
        "bg" to "#0B0A14",
        "surface" to "#14122A",
        "surface-raised" to "#1B1836",
        "glass" to "rgba(20, 18, 42, 0.75)",
        "glass-border" to "rgba(141, 128, 240, 0.22)",
        "text-primary" to "#F2F0FF",
        "text-secondary" to "#9C95C4",
        "text-muted" to "#8C85B4",
        "border" to "#241F45",
        "border-strong" to "#6A6390",
        "primary" to "#6C5EE0",
        "on-primary" to "#FFFFFF",
        "secondary" to "#00E5A3",
        "on-secondary" to "#020305",
        "tertiary" to "#00F0FF",
        "on-tertiary" to "#020305",
        "success" to "#00E5A3",
        "on-success" to "#020305",
        "warning" to "#FFB300",
        "on-warning" to "#020305",
        "error" to "#FF6B6B",
        "on-error" to "#020305",
        "focus-ring" to "#00F0FF",
        "bubble-user" to "#1B1836",
        "bubble-stella" to "rgba(20, 18, 42, 0.80)",
        "bubble-user-text" to "#F2F0FF",
        "bubble-stella-text" to "#F2F0FF",
        "button-content" to "#FFFFFF",
        "button-content-disabled" to "#6A648F",
        "scrim" to "rgba(6, 4, 16, 0.60)",
        "glow" to "0 0 16px rgba(141, 128, 240, 0.35)",
        "elevation-shadow" to "0 8px 32px rgba(4, 2, 14, 0.65)",
    ),
    "light" to mapOf(
        "bg" to "#F4F7F5",
        "surface" to "#FFFFFF",
        "surface-raised" to "#EAF1EE",
        "glass" to "rgba(255, 255, 255, 0.75)",
        "glass-border" to "rgba(12, 13, 20, 0.08)",
        "text-primary" to "#0C0D14",
        "text-secondary" to "#46544D",
        "text-muted" to "#5E6B64",
        "border" to "#C7D2CC",
        "border-strong" to "#7E8783",
        "primary" to "#007A57",
        "on-primary" to "#FFFFFF",
        "secondary" to "#007C8A",
        "on-secondary" to "#FFFFFF",
        "tertiary" to "#5A4BD1",
        "on-tertiary" to "#FFFFFF",
        "success" to "#0F7B4F",
        "on-success" to "#FFFFFF",
        "warning" to "#8A5A00",
        "on-warning" to "#FFFFFF",
        "error" to "#B3261E",
        "on-error" to "#FFFFFF",
        "focus-ring" to "#007A57",
        "bubble-user" to "#E7F6F1",
        "bubble-stella" to "#FFFFFF",
        "bubble-user-text" to "#0C0D14",
        "bubble-stella-text" to "#0C0D14",
        "button-content" to "#FFFFFF",
        "button-content-disabled" to "#8A9490",
        "scrim" to "rgba(12, 13, 20, 0.40)",
        "glow" to "none",
        "elevation-shadow" to "0 2px 8px rgba(12, 13, 20, 0.10)",
    ),
)

/** Raw contract value for [token] in [style]; null when unknown. */
fun stellaTokenRaw(style: StellaThemeStyle, token: String): String? =
    STELLA_TOKENS[style.id]?.get(token)

/**
 * Parse a themes.json colour value: `#RRGGBB`, `rgba(r, g, b, a)` or
 * `none` (-> transparent). Used by both the runtime palette and the
 * ThemeContractTest assertions.
 */
fun parseStellaColor(raw: String): Color = when {
    raw.startsWith("#") -> {
        val rgb = raw.substring(1).toLong(16).toInt()
        Color((0xFF000000L or rgb.toLong()).toInt())
    }
    raw.startsWith("rgba(") -> {
        val parts = raw.removePrefix("rgba(").removeSuffix(")")
            .split(",").map { it.trim() }
        val r = parts[0].toFloat(); val g = parts[1].toFloat()
        val b = parts[2].toFloat(); val a = parts[3].toFloat()
        Color(red = r / 255f, green = g / 255f, blue = b / 255f, alpha = a)
    }
    else -> Color.Transparent // "none" (light theme glow)
}

private fun styleTokens(style: StellaThemeStyle): Map<String, String> =
    STELLA_TOKENS.getValue(style.id)

private fun tok(style: StellaThemeStyle, name: String): Color =
    parseStellaColor(styleTokens(style).getValue(name))

private fun glowColorOf(raw: String): Color {
    if (raw == "none") return Color.Transparent
    val rgba = raw.substringAfter("rgba(", "").substringBefore(')') + ")"
    if (!raw.contains("rgba(")) return Color.Transparent
    return parseStellaColor("rgba($rgba")
}

/**
 * The 32-token Stella palette for one theme, as typed [Color]s.
 *
 * Non-Material roles (glass, bubbles, glow, focus ring, button content...)
 * live here; Material roles are derived from these in [stellaColorScheme].
 * Access in composables through [StellaTheme.colors].
 */
@Immutable
data class StellaColors(
    val bg: Color,
    val surface: Color,
    val surfaceRaised: Color,
    val glass: Color,
    val glassBorder: Color,
    val textPrimary: Color,
    val textSecondary: Color,
    val textMuted: Color,
    val border: Color,
    val borderStrong: Color,
    val primary: Color,
    val onPrimary: Color,
    val secondary: Color,
    val onSecondary: Color,
    val tertiary: Color,
    val onTertiary: Color,
    val success: Color,
    val onSuccess: Color,
    val warning: Color,
    val onWarning: Color,
    val error: Color,
    val onError: Color,
    val focusRing: Color,
    val bubbleUser: Color,
    val bubbleStella: Color,
    val bubbleUserText: Color,
    val bubbleStellaText: Color,
    val buttonContent: Color,
    val buttonContentDisabled: Color,
    val scrim: Color,
    /** Raw CSS shadow from the contract; "none" on the light theme. */
    val glow: String,
    val elevationShadow: String,
) {
    /** Parsed glow colour; transparent when the theme defines no glow (light). */
    val glowColor: Color = glowColorOf(glow)

    companion object {
        private val cache = HashMap<String, StellaColors>()

        fun forStyle(style: StellaThemeStyle): StellaColors =
            cache.getOrPut(style.id) { from(style) }

        fun from(style: StellaThemeStyle) = StellaColors(
            bg = tok(style, "bg"),
            surface = tok(style, "surface"),
            surfaceRaised = tok(style, "surface-raised"),
            glass = tok(style, "glass"),
            glassBorder = tok(style, "glass-border"),
            textPrimary = tok(style, "text-primary"),
            textSecondary = tok(style, "text-secondary"),
            textMuted = tok(style, "text-muted"),
            border = tok(style, "border"),
            borderStrong = tok(style, "border-strong"),
            primary = tok(style, "primary"),
            onPrimary = tok(style, "on-primary"),
            secondary = tok(style, "secondary"),
            onSecondary = tok(style, "on-secondary"),
            tertiary = tok(style, "tertiary"),
            onTertiary = tok(style, "on-tertiary"),
            success = tok(style, "success"),
            onSuccess = tok(style, "on-success"),
            warning = tok(style, "warning"),
            onWarning = tok(style, "on-warning"),
            error = tok(style, "error"),
            onError = tok(style, "on-error"),
            focusRing = tok(style, "focus-ring"),
            bubbleUser = tok(style, "bubble-user"),
            bubbleStella = tok(style, "bubble-stella"),
            bubbleUserText = tok(style, "bubble-user-text"),
            bubbleStellaText = tok(style, "bubble-stella-text"),
            buttonContent = tok(style, "button-content"),
            buttonContentDisabled = tok(style, "button-content-disabled"),
            scrim = tok(style, "scrim"),
            glow = styleTokens(style).getValue("glow"),
            elevationShadow = styleTokens(style).getValue("elevation-shadow"),
        )
    }
}

/** Composition-local palette: [StellaTheme.colors] in every composable. */
val LocalStellaColors = compositionLocalOf { StellaColors.forStyle(StellaThemeStyle.VOID) }

/** Theme token accessor, mirroring `MaterialTheme.colorScheme`. */
object StellaTheme {
    val colors: StellaColors
        @Composable @ReadOnlyComposable get() = LocalStellaColors.current
}

/** Linear blend: t=0 keeps [a], t=1 is [b]. Used for derived M3 container roles. */
private fun mix(a: Color, b: Color, t: Float): Color = Color(
    red = a.red + (b.red - a.red) * t,
    green = a.green + (b.green - a.green) * t,
    blue = a.blue + (b.blue - a.blue) * t,
    alpha = a.alpha + (b.alpha - a.alpha) * t,
)

/**
 * Full Material3 scheme for one palette. Contract tokens map 1:1 onto their
 * roles (background=bg, onSurface=text-primary, outline=border,
 * outlineVariant=border-strong, surfaceVariant/surfaceContainer=
 * surface-raised, scrim=scrim, ...). Container roles that have no raw token
 * are derived by blending the role colour into bg/text so they stay
 * theme-correct on all four themes.
 */
fun stellaColorScheme(c: StellaColors, light: Boolean): ColorScheme {
    val base = if (light) lightColorScheme() else darkColorScheme()
    return base.copy(
        primary = c.primary,
        onPrimary = c.onPrimary,
        primaryContainer = mix(c.bg, c.primary, 0.18f),
        onPrimaryContainer = mix(c.primary, c.textPrimary, 0.5f),
        secondary = c.secondary,
        onSecondary = c.onSecondary,
        secondaryContainer = mix(c.bg, c.secondary, 0.18f),
        onSecondaryContainer = mix(c.secondary, c.textPrimary, 0.5f),
        tertiary = c.tertiary,
        onTertiary = c.onTertiary,
        tertiaryContainer = mix(c.bg, c.tertiary, 0.18f),
        onTertiaryContainer = mix(c.tertiary, c.textPrimary, 0.5f),
        background = c.bg,
        onBackground = c.textPrimary,
        surface = c.surface,
        onSurface = c.textPrimary,
        surfaceVariant = c.surfaceRaised,
        onSurfaceVariant = c.textSecondary,
        surfaceTint = c.primary,
        inverseSurface = c.textPrimary,
        inverseOnSurface = c.bg,
        inversePrimary = c.primary,
        error = c.error,
        onError = c.onError,
        errorContainer = mix(c.bg, c.error, 0.18f),
        onErrorContainer = mix(c.error, c.textPrimary, 0.5f),
        outline = c.border,
        outlineVariant = c.borderStrong,
        scrim = c.scrim,
        surfaceBright = c.surface,
        surfaceDim = c.bg,
        surfaceContainerLowest = c.surface,
        surfaceContainerLow = c.surface,
        surfaceContainer = c.surfaceRaised,
        surfaceContainerHigh = c.surfaceRaised,
        surfaceContainerHighest = c.surfaceRaised,
    )
}

/**
 * Canonical Stella brand tokens - fixed constants for non-UI surfaces that
 * must render the *dark* brand regardless of theme (marketing art, static
 * assets). In-app screens should read [StellaTheme.colors] instead so they
 * restyle with the active theme.
 */
object StellaBrand {
    /** Stella's voice - mint/emerald green. The primary brand colour. */
    val primary = Color(0xFF00E5A3)
    /** Glow / energy accent - soft cyan. */
    val accent = Color(0xFF00F0FF)
    /** Depth / tertiary - violet. */
    val tertiary = Color(0xFF7C6EE6)
    /** Deep void background. */
    val void = Color(0xFF0C0D14)
    /** Base surface. */
    val surface = Color(0xFF12141F)
    /** Raised card surface. */
    val surfaceCard = Color(0xFF161926)
    /** Hairline border. */
    val surfaceBorder = Color(0xFF212638)
    /** Muted body text. */
    val textMuted = Color(0xFF8A93A6)
    /** Warm-white primary text. */
    val textBright = Color(0xFFF4F6F8)
    /** Pure ink for on-primary text. */
    val ink = Color(0xFF020305)
    /** Pure accent white (logo highlight). */
    val accentWhite = Color(0xFFFFFFFF)
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
    val style = StellaThemeState.style.value
    val largeText = StellaThemeState.largeText.value
    val colors = StellaColors.forStyle(style)
    val baseDensity = LocalDensity.current
    val density = Density(
        density = baseDensity.density,
        fontScale = if (largeText) baseDensity.fontScale * 1.15f else baseDensity.fontScale,
    )
    CompositionLocalProvider(
        LocalDensity provides density,
        LocalStellaColors provides colors,
    ) {
        MaterialTheme(
            colorScheme = stellaColorScheme(colors, light = style == StellaThemeStyle.LIGHT),
            typography = StellaTypography,
            content = content,
        )
    }
}
