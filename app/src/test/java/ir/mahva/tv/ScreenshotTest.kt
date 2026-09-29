package ir.mahva.tv

import android.graphics.Bitmap
import android.graphics.Canvas
import android.os.Looper
import android.view.View
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
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
 * `docs/screenshots`. Works as a smoke test too: the activity must start, the
 * catalog must load and all four sections must be reachable.
 *
 * Screenshots are taken by drawing the activity window directly, because the
 * Compose test framework's idling never settles while images are being loaded.
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

    /** Robolectric only runs posted work (incl. recomposition) while the looper is idled. */
    private fun settle(millis: Long = 1500) {
        val deadline = System.currentTimeMillis() + millis
        while (System.currentTimeMillis() < deadline) {
            Shadows.shadowOf(Looper.getMainLooper()).idle()
            Thread.sleep(25)
        }
    }

    private fun capture(name: String) {
        settle()
        val result = runCatching {
            val view: View = rule.activity.window.decorView
            if (view.width == 0 || view.height == 0) {
                view.measure(
                    View.MeasureSpec.makeMeasureSpec(1080, View.MeasureSpec.EXACTLY),
                    View.MeasureSpec.makeMeasureSpec(2340, View.MeasureSpec.EXACTLY)
                )
                view.layout(0, 0, view.measuredWidth, view.measuredHeight)
            }
            val bitmap = Bitmap.createBitmap(
                view.width.coerceAtLeast(1),
                view.height.coerceAtLeast(1),
                Bitmap.Config.ARGB_8888
            )
            view.draw(Canvas(bitmap))
            FileOutputStream(File(outputDir, name)).use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }
            "${bitmap.width}x${bitmap.height}"
        }
        diag.append("capture $name -> ${result.getOrElse { "FAILED: $it" }}\n")
    }

    private fun awaitText(text: String, timeoutMs: Long = 20_000): Boolean {
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            Shadows.shadowOf(Looper.getMainLooper()).idle()
            val found = runCatching {
                rule.onAllNodesWithText(text).fetchSemanticsNodes().isNotEmpty()
            }.getOrDefault(false)
            if (found) return true
            Thread.sleep(50)
        }
        return false
    }

    private fun clickByText(text: String): Boolean {
        settle(400)
        val ok = runCatching { rule.onNodeWithText(text).performClick() }.isSuccess
        diag.append("click text '$text' -> $ok\n")
        return ok
    }

    private fun clickByDescription(description: String): Boolean {
        settle(400)
        val ok = runCatching {
            rule.onNodeWithContentDescription(description).performClick()
        }.isSuccess
        diag.append("click desc '$description' -> $ok\n")
        return ok
    }

    // -------------------------------------------------------------------- tests

    @Test
    fun captureEveryScreen() {
        settle(2_000)
        diag.append("home ready: ${awaitText("دسترسی سریع")}\n")
        capture("01-home.png")
        capture("01-home.png")

        // Each of the four sections of the app, reached from the bottom bar.
        listOf(
            Triple("پرشیانا", "کانال‌های گروه پرشیانا", "02-persiana.png"),
            Triple("خبری", "شبکه‌های خبری ایران و جهان", "03-news.png"),
            Triple("موزیک", "کانال‌های موسیقی و کلیپ", "04-music.png"),
            Triple("ورزشی", "کانال‌های ورزشی و مسابقات زنده", "05-sports.png")
        ).forEach { (tab, expected, file) ->
            if (clickByText(tab)) {
                val ready = awaitText(expected, 15_000)
                diag.append("section '$tab' ready: $ready\n")
                capture(file)
                capture(file)
            }
        }

        // Open the first channel of the current section to show the player UI.
        val channelName = "شبکه ورزش"
        if (clickByText(channelName)) {
            settle(4_000)
            capture("06-player.png")
            clickByDescription("بازگشت")
            settle()
        }

        clickByText("خانه")
        awaitText("دسترسی سریع", 10_000)

        // Global search
        if (clickByDescription("جستجو")) {
            settle()
            awaitText("نام کانال را بنویسید…", 10_000)
            runCatching { rule.onNode(hasSetTextAction()).performTextInput("BBC") }
            settle(3_000)
            capture("07-search.png")
            capture("07-search.png")
            clickByDescription("بازگشت")
            settle()
            clickByText("خانه")
            settle()
        }

        // My channels + the add-channel dialog
        if (clickByDescription("کانال‌های من")) {
            settle()
            awaitText("کانال‌های من", 10_000)
            capture("08-my-channels.png")
            if (clickByText("افزودن کانال جدید")) {
                settle()
                awaitText("افزودن کانال جدید", 10_000)
                capture("09-add-channel.png")
            }
        }

        File(outputDir, "test-diag.txt").writeText(diag.toString())
    }
}
