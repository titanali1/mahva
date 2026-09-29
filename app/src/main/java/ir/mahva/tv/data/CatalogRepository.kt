package ir.mahva.tv.data

import android.content.Context

/** Loads the bundled channel catalog from the application assets. */
class CatalogRepository(private val context: Context) {

    fun load(): ChannelCatalog = runCatching {
        context.assets.open(ASSET_NAME).bufferedReader().use { it.readText() }
    }.map { json -> ChannelCatalog.parse(json) }
        .getOrElse { ChannelCatalog.EMPTY }

    private companion object {
        const val ASSET_NAME = "channels.json"
    }
}
