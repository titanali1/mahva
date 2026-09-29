package ir.takhtlive.tv

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import ir.takhtlive.tv.data.CatalogRepository
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.annotation.Config

/** Validates the bundled channel catalog and its four sections. */
@RunWith(AndroidJUnit4::class)
@Config(sdk = [34])
class CatalogTest {

    private val catalog by lazy {
        CatalogRepository(ApplicationProvider.getApplicationContext<Context>()).load()
    }

    @Test
    fun catalogIsNotEmpty() {
        assertTrue("catalog should expose categories", catalog.categories.isNotEmpty())
        assertTrue("catalog should expose channels", catalog.channels.size >= 100)
    }

    @Test
    fun allFourRequestedSectionsExistAndArePopulated() {
        val expected = mapOf(
            "persiana" to "پرشیانا گروپ",
            "news" to "خبری",
            "music" to "موزیک",
            "sports" to "ورزشی"
        )
        expected.forEach { (id, title) ->
            val category = catalog.category(id)
            assertTrue("section $id should exist", category != null)
            assertEquals("section $id title", title, category!!.title)
            assertTrue(
                "section $id should contain channels",
                catalog.channelsOf(id).size >= 10
            )
        }
    }

    @Test
    fun everyChannelHasAUsableStreamUrlAndSection() {
        val sectionIds = catalog.categories.map { it.id }.toSet()
        catalog.channels.forEach { channel ->
            assertTrue(
                "channel ${channel.id} has a bad url: ${channel.url}",
                channel.url.startsWith("http://") || channel.url.startsWith("https://")
            )
            assertTrue(
                "channel ${channel.id} points at an unknown section: ${channel.category}",
                sectionIds.contains(channel.category)
            )
            assertTrue("channel ${channel.id} has no name", channel.name.isNotBlank())
        }
    }

    @Test
    fun channelIdsAreUnique() {
        val ids = catalog.channels.map { it.id }
        assertEquals("channel ids must be unique", ids.size, ids.toSet().size)
    }

    @Test
    fun requestedNewsChannelsArePresent() {
        val news = catalog.channelsOf("news")
        val ids = news.map { it.id }
        listOf("iran-national-revolution", "kalemeh-tv", "israel-pars-tv").forEach { id ->
            assertTrue("news section should contain $id (found: $ids)", ids.contains(id))
        }
        val added = news.filter { it.id in setOf("iran-national-revolution", "kalemeh-tv", "israel-pars-tv") }
        added.forEach {
            assertTrue("${it.id} needs a stream url", it.url.startsWith("https://"))
            assertTrue("${it.id} needs a logo", it.logo.isNotBlank())
        }
    }

    @Test
    fun everySectionIsTranslatedIntoAllLanguages() {
        ir.takhtlive.tv.ui.i18n.AppLanguage.entries.forEach { language ->
            catalog.categories.forEach { category ->
                assertTrue(
                    "section ${category.id} has no ${language.code} title",
                    category.titleFor(language).isNotBlank()
                )
                assertTrue(
                    "section ${category.id} has no ${language.code} subtitle",
                    category.subtitleFor(language).isNotBlank()
                )
            }
        }
    }

    @Test
    fun channelNamesFallBackWhenTranslationIsMissing() {
        val channel = catalog.channelsOf("music").first()
        ir.takhtlive.tv.ui.i18n.AppLanguage.entries.forEach { language ->
            assertTrue(
                "channel ${channel.id} has no name for ${language.code}",
                channel.nameFor(language).isNotBlank()
            )
        }
    }

    @Test
    fun searchFindsChannelsAcrossSections() {
        assertTrue(catalog.search("پرشیانا").isNotEmpty())
        assertTrue(catalog.search("BBC").isNotEmpty())
        assertTrue(catalog.search("موزیک").isNotEmpty())
        assertTrue(catalog.search("ورزش").isNotEmpty())
    }
}
