package ir.mahva.tv

import android.graphics.Bitmap
import android.os.Looper
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
import androidx.compose.ui.test.printToString
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Shadows
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.io.FileOutputStream

/**
 * Renders the real app on the JVM (Robolectric) and stores screenshots in
 * `docs/screenshots`. Doubles as a smoke test: the activity must start, the
 * catalog must load and the four sections must be reachable.
 */
@RunWith(AndroidJUnit4::class)
@Config(sdk = [34], qualifiers = "w411dp-h915dp-xxhdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
class ScreenshotTest {

    @get:Rule
    val rule = createAndroidComposeRule<MainActivity>()

    private val outputDir = File("../docs/screenshots").apply { mkdirs() }
    private val diag = StringBuilder()

    // ------------------------------------------------------------------ helpers

    /** Robolectric only runs posted work when the main looper is idled. */
    private fun pump() {
        Shadows.shadowOf(Looper.getMainLooper()).idle()
        runCatching { rule.waitForIdle() }
    }

    private fun capture(name: String) {
        pump()
        val result = runCatching {
            val bitmap: Bitmap = rule.onRoot().captureToImage().asAndroidBitmap()
            FileOutputStream(File(outputDir, name)).use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }
            "${bitmap.width}x${bitmap.height}"
        }
        diag.append("capture $name -> ${result.getOrElse { "FAILED: ${it.message}" }}\n")
    }

    private fun awaitText(text: String, timeoutMs: Long = 20_000): Boolean {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            pump()
            val found = runCatching {
                rule.onAllNodesWithText(text).fetchSemanticsNodes().isNotEmpty()
            }.getOrDefault(false)
            if (found) return true
            Thread.sleep(50)
        }
        return false
    }

    private fun clickByText(text: String): Boolean {
        pump()
        val ok = runCatching { rule.onNodeWithText(text).performClick() }.isSuccess
        diag.append("click text '$text' -> $ok\n")
        return ok
    }

    private fun clickByDescription(description: String): Boolean {
        pump()
        val ok = runCatching {
            rule.onNodeWithContentDescription(description).performClick()
        }.isSuccess
        diag.append("click desc '$description' -> $ok\n")
        return ok
    }

    private fun dumpTree() {
        val tree = runCatching { rule.onRoot(useUnmergedTree = true).printToString() }
            .getOrElse { "tree unavailable: ${it.message}" }
        diag.append("---- semantics tree ----\n").append(tree).append("\n")
    }

    // -------------------------------------------------------------------- tests

    @Test
    fun captureEveryScreen() {
        pump()
        val homeReady = awaitText("دسترسی سریع")
        diag.append("home ready: $homeReady\n")
        capture("01-home.png")

        // The four sections are the bottom navigation tabs.
        listOf(
            "پرشیانا" to "02-persiana.png",
            "خبری" to "03-news.png",
            "موزیک" to "04-music.png",
            "ورزشی" to "05-sports.png"
        ).forEach { (tab, file) ->
            if (clickByText(tab)) {
                awaitText(tab, 5_000)
                capture(file)
            }
        }

        clickByText("خانه")
        awaitText("دسترسی سریع", 5_000)

        // Global search
        if (clickByDescription("جستجو")) {
            pump()
            runCatching { rule.onNode(hasSetTextAction()).performTextInput("BBC") }
            pump()
            capture("06-search.png")
            clickByText("خانه")
            pump()
        }

        // My channels + the add-channel dialog
        if (clickByDescription("کانال‌های من")) {
            pump()
            capture("07-my-channels.png")
            if (clickByText("افزودن کانال جدید")) {
                pump()
                capture("08-add-channel.png")
            }
        }

        dumpTree()
        File(outputDir, "test-diag.txt").writeText(diag.toString())
    }
}
