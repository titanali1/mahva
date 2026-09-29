package ir.mahva.tv.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import ir.mahva.tv.R

val MahvaPurple = Color(0xFF7C4DFF)
val MahvaBlue = Color(0xFF1A80F6)
val MahvaTeal = Color(0xFF37D6C0)
val MahvaPink = Color(0xFFFF5C8A)
val MahvaGreen = Color(0xFF2ED573)

val Vazirmatn = FontFamily(
    Font(R.font.vazirmatn_regular, FontWeight.Normal),
    Font(R.font.vazirmatn_medium, FontWeight.Medium),
    Font(R.font.vazirmatn_bold, FontWeight.Bold)
)

private val MahvaColorScheme = darkColorScheme(
    primary = Color(0xFF9B8CFF),
    onPrimary = Color(0xFF13093B),
    primaryContainer = Color(0xFF2A1D5E),
    onPrimaryContainer = Color(0xFFE9E3FF),
    secondary = MahvaTeal,
    onSecondary = Color(0xFF00382F),
    secondaryContainer = Color(0xFF11413A),
    onSecondaryContainer = Color(0xFFC7FFF2),
    tertiary = MahvaPink,
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

private val baseTypography = Typography()

private val MahvaTypography = Typography(
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

/** Dark, right-to-left Material 3 theme used across the app. */
@Composable
fun MahvaTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        MaterialTheme(
            colorScheme = MahvaColorScheme,
            typography = MahvaTypography,
            content = content
        )
    }
}
