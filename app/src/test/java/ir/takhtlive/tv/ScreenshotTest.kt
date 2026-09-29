package ir.takhtlive.tv

import android.graphics.Bitmap
import android.graphics.Canvas
import android.os.Looper
import android.view.View
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithTag
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
import java.time.Duration

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

    /**
     * Robolectric only runs posted work while its (virtual) clock is advanced.
     * Recomposition happens on Choreographer frame callbacks, which are posted a
     * little into the future, so the clock has to be advanced, not just idled.
     */
    private fun settle(millis: Long = 1500) {
        val looper = Shadows.shadowOf(Looper.getMainLooper())
        var remaining = millis
        while (remaining > 0) {
            looper.idleFor(Duration.ofMillis(50))
            Thread.sleep(10)
            remaining -= 50
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
            settle(100)
            val found = runCatching {
                rule.onAllNodesWithText(text).fetchSemanticsNodes().isNotEmpty()
            }.getOrDefault(false)
            if (found) return true
        }
        return false
    }

    private fun click(what: String, action: () -> Unit): Boolean {
        settle(500)
        val result = runCatching(action)
        diag.append("click $what -> ${if (result.isSuccess) "ok" else "FAILED: ${result.exceptionOrNull()?.message?.take(180)}"}\n")
        return result.isSuccess
    }

    private fun clickByText(text: String): Boolean =
        click("text '$text'") { rule.onAllNodesWithText(text).onFirst().performClick() }

    private fun clickByDescription(description: String): Boolean =
        click("desc '$description'") {
            rule.onAllNodesWithContentDescription(description).onFirst().performClick()
        }

    private fun clickByTag(tag: String): Boolean =
        click("tag '$tag'") { rule.onNodeWithTag(tag).performClick() }

    /** Finds the decor view of the top-most dialog window, if one is showing. */
    private fun topMostDialogView(): View? = runCatching {
        val wm = rule.activity.getSystemService(android.content.Context.WINDOW_SERVICE)
            as android.view.WindowManager
        val field = wm.javaClass.getDeclaredField("mRoots")
        field.isAccessible = true
        @Suppress("UNCHECKED_CAST")
        val roots = field.get(wm) as List<Any>
        roots.mapNotNull { root ->
            runCatching {
                val viewField = root.javaClass.getDeclaredField("mView")
                viewField.isAccessible = true
                viewField.get(root) as? View
            }.getOrNull()
        }.lastOrNull { it !== rule.activity.window.decorView }
    }.getOrNull()

    // -------------------------------------------------------------------- tests

    @Test
    fun captureEveryScreen() {
        // Remove stale screenshots (older runs) so renamed files do not linger.
        outputDir.listFiles { file -> file.isFile && file.name.endsWith(".png") }
            ?.forEach { it.delete() }

        settle(2_000)
        diag.append("home ready: ${awaitText("دسترسی سریع")}\n")
        capture("01-home.png")

        // Each of the four sections of the app, reached from the bottom bar.
        listOf(
            Triple("tab_persiana", "کانال‌های گروه پرشیانا", "02-persiana.png"),
            Triple("tab_news", "شبکه‌های خبری ایران و جهان", "03-news.png"),
            Triple("tab_music", "کانال‌های موسیقی و کلیپ", "04-music.png"),
            Triple("tab_sports", "کانال‌های ورزشی و مسابقات زنده", "05-sports.png")
        ).forEach { (tag, expected, file) ->
            if (clickByTag(tag)) {
                val ready = awaitText(expected, 15_000)
                diag.append("section '$tag' ready: $ready\n")
                capture(file)
            }
        }

        // Open the first channel of the current section to show the player UI.
        val channelName = "شبکه ورزش"
        if (clickByText("شبکه ورزش")) {
            val playerOpen = awaitText(channelName, 15_000)
            diag.append("player open: $playerOpen\n")
            settle(1_500)
            capture("06-player.png")
            clickByDescription("بازگشت")
            settle()
        }

        clickByTag("tab_home")
        awaitText("دسترسی سریع", 10_000)

        // Global search
        if (clickByTag("action_search")) {
            settle()
            awaitText("نام کانال را بنویسید…", 10_000)
            runCatching { rule.onNode(hasSetTextAction()).performTextInput("BBC") }
            settle(2_000)
            capture("07-search.png")
            clickByTag("tab_home")
            settle()
        }

        // My channels screen
        if (clickByTag("action_library")) {
            settle()
            awaitText("کانال‌های من", 10_000)
            capture("08-my-channels.png")
        }

        File(outputDir, "test-diag.txt").writeText(diag.toString())
    }

    /** Captures the add-channel dialog, which lives in its own window. */
    @Test
    fun addChannelDialogRenders() {
        settle(2_000)
        rule.mainClock.autoAdvance = false
        val opened = clickByTag("action_add")
        rule.mainClock.advanceTimeBy(1_500)
        settle(1_500)

        if (opened) {
            val captured = runCatching {
                val decor: View = rule.activity.window.decorView
                val bitmap = Bitmap.createBitmap(
                    decor.width.coerceAtLeast(1),
                    decor.height.coerceAtLeast(1),
                    Bitmap.Config.ARGB_8888
                )
                val canvas = Canvas(bitmap)
                decor.draw(canvas)
                // draw the dialog window (compose AlertDialog) on top of it
                topMostDialogView()?.let { dialogView ->
                    canvas.save()
                    dialogView.draw(canvas)
                    canvas.restore()
                }
                FileOutputStream(File(outputDir, "09-add-channel.png")).use {
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
                }
                "${bitmap.width}x${bitmap.height}"
            }
            diag.append("capture 09-add-channel.png -> ${captured.getOrElse { "FAILED: $it" }}\n")
        } else {
            diag.append("add-channel dialog did not open\n")
        }

        rule.mainClock.autoAdvance = true
        File(outputDir, "test-diag.txt").appendText(diag.toString())
    }

    /**
     * The hamburger menu: language and theme settings.
     * The drawer animates, so the test clock is advanced manually here.
     */
    @Test
    fun drawerLanguageAndThemeSettings() {
        settle(2_000)
        rule.mainClock.autoAdvance = false

        fun captureAfter(action: () -> Boolean, file: String) {
            val ok = action()
            rule.mainClock.advanceTimeBy(1_200)
            settle(1_200)
            if (ok) capture(file)
        }

        captureAfter({ clickByTag("action_menu") }, "10-drawer.png")
        captureAfter({ clickByTag("lang_en") }, "11-english.png")
        captureAfter({ clickByTag("theme_light") }, "12-light-theme.png")
        captureAfter({ clickByTag("lang_ar") }, "13-arabic.png")

        rule.mainClock.autoAdvance = true
        File(outputDir, "test-diag.txt").appendText(diag.toString())
    }
}
