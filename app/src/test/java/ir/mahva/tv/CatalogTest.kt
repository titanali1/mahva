package ir.mahva.tv

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import ir.mahva.tv.data.CatalogRepository
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
    fun searchFindsChannelsAcrossSections() {
        assertTrue(catalog.search("پرشیانا").isNotEmpty())
        assertTrue(catalog.search("BBC").isNotEmpty())
        assertTrue(catalog.search("موزیک").isNotEmpty())
        assertTrue(catalog.search("ورزش").isNotEmpty())
    }
}
