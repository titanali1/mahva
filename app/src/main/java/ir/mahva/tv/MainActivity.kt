package ir.mahva.tv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import ir.mahva.tv.ui.MahvaApp
import ir.mahva.tv.ui.theme.MahvaTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MahvaTheme {
                MahvaApp()
            }
        }
    }
}
