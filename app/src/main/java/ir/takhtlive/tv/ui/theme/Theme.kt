package ir.takhtlive.tv.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import ir.takhtlive.tv.R
import ir.takhtlive.tv.ui.i18n.AppLanguage
import ir.takhtlive.tv.ui.i18n.AppThemeMode
import ir.takhtlive.tv.ui.i18n.LocalAppLanguage
import ir.takhtlive.tv.ui.i18n.LocalAppStrings
import ir.takhtlive.tv.ui.i18n.stringsFor

val TakhtPurple = Color(0xFF7C4DFF)
val TakhtBlue = Color(0xFF1A80F6)
val TakhtTeal = Color(0xFF37D6C0)
val TakhtPink = Color(0xFFFF5C8A)
val TakhtGreen = Color(0xFF2ED573)

val Vazirmatn = FontFamily(
    Font(R.font.vazirmatn_regular, FontWeight.Normal),
    Font(R.font.vazirmatn_medium, FontWeight.Medium),
    Font(R.font.vazirmatn_bold, FontWeight.Bold)
)

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFF9B8CFF),
    onPrimary = Color(0xFF13093B),
    primaryContainer = Color(0xFF2A1D5E),
    onPrimaryContainer = Color(0xFFE9E3FF),
    secondary = TakhtTeal,
    onSecondary = Color(0xFF00382F),
    secondaryContainer = Color(0xFF11413A),
    onSecondaryContainer = Color(0xFFC7FFF2),
    tertiary = TakhtPink,
    onTertiary = Color(0xFF3B0020),
    background = Color(0xFF0B0B14),
    onBackground = Color(0xFFEDEAF7),
    surface = Color(0xFF12121F),
    onSurface = Color(0xFFEDEAF7),
    surfaceVariant = Color(0xFF1C1B2B),
    onSurfaceVariant = Color(0xFFB9B4D0),
    error = Color(0xFFFF6B6B),
    onError = Color(0xFF3A0000),
    outline = Color(0xFF3A374F),
    outlineVariant = Color(0xFF272538),
    inverseSurface = Color(0xFFEDEAF7),
    inverseOnSurface = Color(0xFF1A1A24),
    inversePrimary = Color(0xFF5B3FE0),
    scrim = Color(0xCC000000)
)

private val LightColorScheme = lightColorScheme(
    primary = Color(0xFF5B3FE0),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE6DEFF),
    onPrimaryContainer = Color(0xFF1B0C55),
    secondary = Color(0xFF0E8C7C),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFC9F5EC),
    onSecondaryContainer = Color(0xFF00352E),
    tertiary = Color(0xFFD6336C),
    onTertiary = Color.White,
    background = Color(0xFFF7F6FC),
    onBackground = Color(0xFF17162B),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF17162B),
    surfaceVariant = Color(0xFFEAE7F6),
    onSurfaceVariant = Color(0xFF5A5773),
    error = Color(0xFFC62828),
    onError = Color.White,
    outline = Color(0xFFC3BFDA),
    outlineVariant = Color(0xFFE2DFF0),
    inverseSurface = Color(0xFF2A2838),
    inverseOnSurface = Color(0xFFF4F2FA),
    inversePrimary = Color(0xFFB9AAFF),
    scrim = Color(0x99000000)
)

private val baseTypography = Typography()

private val TakhtTypography = Typography(
    displaySmall = baseTypography.displaySmall.copy(fontFamily = Vazirmatn),
    headlineMedium = baseTypography.headlineMedium.copy(fontFamily = Vazirmatn),
    headlineSmall = baseTypography.headlineSmall.copy(fontFamily = Vazirmatn),
    titleLarge = baseTypography.titleLarge.copy(fontFamily = Vazirmatn, fontWeight = FontWeight.Bold),
    titleMedium = baseTypography.titleMedium.copy(fontFamily = Vazirmatn, fontWeight = FontWeight.Medium),
    titleSmall = baseTypography.titleSmall.copy(fontFamily = Vazirmatn),
    bodyLarge = baseTypography.bodyLarge.copy(fontFamily = Vazirmatn),
    bodyMedium = baseTypography.bodyMedium.copy(fontFamily = Vazirmatn),
    bodySmall = baseTypography.bodySmall.copy(fontFamily = Vazirmatn),
    labelLarge = baseTypography.labelLarge.copy(fontFamily = Vazirmatn),
    labelMedium = baseTypography.labelMedium.copy(fontFamily = Vazirmatn),
    labelSmall = baseTypography.labelSmall.copy(fontFamily = Vazirmatn)
)

/** Resolves the theme mode into an actual light/dark decision. */
@Composable
fun TakhtThemeMode.resolveIsDark(): Boolean = when (this) {
    AppThemeMode.DARK -> true
    AppThemeMode.LIGHT -> false
    AppThemeMode.SYSTEM -> isSystemInDarkTheme()
}

/**
 * Material 3 theme of the app. Language and theme mode are driven by the user
 * settings in the navigation drawer, so the whole UI switches instantly.
 */
@Composable
fun TakhtLiveTheme(
    language: AppLanguage = AppLanguage.PERSIAN,
    themeMode: AppThemeMode = AppThemeMode.DARK,
    content: @Composable () -> Unit
) {
    val dark = themeMode.resolveIsDark()
    val colorScheme = if (dark) DarkColorScheme else LightColorScheme
    val layoutDirection = if (language.isRtl) LayoutDirection.Rtl else LayoutDirection.Ltr

    CompositionLocalProvider(
        LocalAppLanguage provides language,
        LocalAppStrings provides stringsFor(language),
        LocalLayoutDirection provides layoutDirection
    ) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = TakhtTypography,
            content = content
        )
    }
}
