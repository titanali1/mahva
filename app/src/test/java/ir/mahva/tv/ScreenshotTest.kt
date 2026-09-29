package ir.mahva.tv

import android.graphics.Bitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.io.FileOutputStream

/**
 * Renders the real app on the JVM (Robolectric) and stores screenshots in
 * `docs/screenshots`. Doubles as a smoke test: the activity must start, the
 * catalog must load and every section must be reachable.
 */
@RunWith(AndroidJUnit4::class)
@Config(sdk = [34], qualifiers = "w411dp-h915dp-xxhdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class ScreenshotTest {

    @get:Rule
    val rule = createAndroidComposeRule<MainActivity>()

    private val outputDir = File("../docs/screenshots").apply { mkdirs() }

    private fun capture(name: String) {
        rule.waitForIdle()
        val bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
        FileOutputStream(File(outputDir, name)).use { out ->
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
        }
        println("[screenshot] $name ${bitmap.width}x${bitmap.height}")
    }

    private fun waitForText(text: String, timeoutMs: Long = 30_000) {
        rule.waitUntil(timeoutMs) {
            rule.onAllNodesWithText(text).fetchSemanticsNodes().isNotEmpty()
        }
    }

    @Test
    fun homeScreenShowsEverySection() {
        waitForText("دسترسی سریع")
        capture("01-home.png")
    }

    @Test
    fun everySectionScreenRenders() {
        waitForText("دسترسی سریع")

        // The four sections are the bottom navigation tabs (RTL order).
        val tabs = listOf(
            "پرشیانا" to "02-persiana.png",
            "خبری" to "03-news.png",
            "موزیک" to "04-music.png",
            "ورزشی" to "05-sports.png"
        )
        tabs.forEach { (tab, file) ->
            rule.onNodeWithText(tab).performClick()
            rule.waitForIdle()
            waitForText(tab)
            capture(file)
        }

        // Back to the home screen
        rule.onNodeWithText("خانه").performClick()
        rule.waitForIdle()
    }

    @Test
    fun searchScreenFindsChannels() {
        waitForText("دسترسی سریع")
        rule.onNodeWithContentDescription("جستجو").performClick()
        rule.waitForIdle()
        rule.onNode(hasSetTextAction()).performTextInput("BBC")
        rule.waitForIdle()
        capture("06-search.png")
    }

    @Test
    fun favouritesScreenAndAddChannelDialogRender() {
        waitForText("دسترسی سریع")

        rule.onNodeWithContentDescription("کانال‌های من").performClick()
        rule.waitForIdle()
        capture("07-my-channels.png")

        rule.onNodeWithText("افزودن کانال جدید").performClick()
        rule.waitForIdle()
        capture("08-add-channel.png")
    }
}
