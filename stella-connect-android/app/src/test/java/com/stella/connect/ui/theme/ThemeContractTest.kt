package com.stella.connect.ui.theme

import androidx.compose.ui.graphics.Color
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/**
 * Phase 1.5 contract test: the Kotlin mirror [STELLA_TOKENS] must be
 * byte-identical to `themes.json` (all 32 tokens across the 4 themes),
 * every value must parse to a [Color], and the Material3 scheme must derive
 * cleanly from each theme.
 */
class ThemeContractTest {

    private fun themesFile(): File {
        val candidates = listOf(
            File("../../themes.json"), // gradle test cwd = stella-connect-android/app
            File("../themes.json"),     // cwd = stella-connect-android
            File("themes.json"),        // cwd = repo root
        )
        val found = candidates.firstOrNull { it.isFile }
        assertNotNull(
            "themes.json not found; searched: " +
                candidates.joinToString { it.absolutePath },
            found,
        )
        return found!!
    }

    private val themes: JSONObject by lazy {
        JSONObject(themesFile().readText(Charsets.UTF_8))
    }

    private val themeIds = listOf("void", "oled", "aurora", "light")

    @Test
    fun mirrorMatchesThemesJsonByteForByte() {
        for (id in themeIds) {
            val json = themes.getJSONObject(id)
            val keys = json.keys().asSequence().toList()
            assertEquals("theme '$id' must expose exactly 32 tokens", 32, keys.size)
            for (key in keys) {
                assertEquals(
                    "theme '$id' token '$key'",
                    json.getString(key),
                    STELLA_TOKENS[id]?.get(key),
                )
            }
        }
        assertEquals(
            "mirror must hold exactly 4 themes x 32 tokens",
            themeIds.size * 32,
            STELLA_TOKENS.entries.sumOf { it.value.size },
        )
        for (id in STELLA_TOKENS.keys) {
            assertTrue("unknown theme in mirror: $id", id in themeIds)
        }
    }

    @Test
    fun everyTokenValueParsesToAColor() {
        val hex = Regex("^#[0-9A-Fa-f]{6}$")
        val rgba = Regex("^rgba\\(\\s*\\d+\\s*,\\s*\\d+\\s*,\\s*\\d+\\s*,\\s*[01](\\.\\d+)?\\s*\\)$")
        for ((themeId, tokens) in STELLA_TOKENS) {
            for ((key, raw) in tokens) {
                val shapeOk = raw == "none" || hex.matches(raw) || rgba.matches(raw)
                assertTrue("'$themeId/$key' has unsupported format: $raw", shapeOk)
                val parsed = parseStellaColor(raw) // must not throw
                if (raw == "none") {
                    assertEquals("'$themeId/$key' none -> transparent", Color.Transparent, parsed)
                }
            }
        }
        assertEquals(Color(0xFF000000), parseStellaColor("#000000"))
        assertEquals(Color.White, parseStellaColor("#FFFFFF"))
    }

    @Test
    fun materialSchemeDerivesFromEveryTheme() {
        for (style in StellaThemeStyle.values()) {
            val colors = StellaColors.forStyle(style)
            val scheme = stellaColorScheme(colors, light = style == StellaThemeStyle.LIGHT)
            assertEquals(style.id, colors.primary, scheme.primary)
            assertEquals(style.id, colors.bg, scheme.background)
            assertEquals(style.id, colors.textPrimary, scheme.onBackground)
            assertEquals(style.id, colors.textSecondary, scheme.onSurfaceVariant)
            assertEquals(style.id, colors.error, scheme.error)
            assertEquals(style.id, colors.border, scheme.outline)
            assertEquals(style.id, colors.borderStrong, scheme.outlineVariant)
            assertEquals(style.id, colors.surfaceRaised, scheme.surfaceContainer)
        }
    }

    @Test
    fun legacyStyleIdsMapOntoTheFourThemes() {
        assertEquals(StellaThemeStyle.VOID, StellaThemeStyle.fromId(null))
        assertEquals(StellaThemeStyle.VOID, StellaThemeStyle.fromId("DARK"))
        assertEquals(StellaThemeStyle.VOID, StellaThemeStyle.fromId("dark"))
        assertEquals(StellaThemeStyle.VOID, StellaThemeStyle.fromId("nonsense"))
        assertEquals(StellaThemeStyle.LIGHT, StellaThemeStyle.fromId("LIGHT"))
        for (style in StellaThemeStyle.values()) {
            assertEquals(style, StellaThemeStyle.fromId(style.id))
            assertEquals(style, StellaThemeStyle.fromId(style.id.uppercase()))
        }
    }
}
