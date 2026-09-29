package ir.takhtlive.tv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import ir.takhtlive.tv.data.PrefsStore
import ir.takhtlive.tv.ui.TakhtLiveApp
import ir.takhtlive.tv.ui.i18n.AppLanguage
import ir.takhtlive.tv.ui.i18n.AppThemeMode
import ir.takhtlive.tv.ui.theme.TakhtLiveTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val prefs = remember { PrefsStore(this) }
            var language by remember { mutableStateOf(AppLanguage.from(prefs.languageCode)) }
            var themeMode by remember { mutableStateOf(AppThemeMode.from(prefs.themeModeId)) }

            TakhtLiveTheme(language = language, themeMode = themeMode) {
                TakhtLiveApp(
                    language = language,
                    themeMode = themeMode,
                    onLanguageChange = { language = it },
                    onThemeChange = { themeMode = it }
                )
            }
        }
    }
}
