package ir.mahva.tv.data

import org.json.JSONArray
import org.json.JSONObject

/** A section of the app (پرشیانا گروپ، خبری، موزیک، ورزشی …). */
data class ChannelCategory(
    val id: String,
    val title: String,
    val subtitle: String,
    val emoji: String,
    val colorHex: String
)

/** A single live TV channel. */
data class Channel(
    val id: String,
    val name: String,
    val nameEn: String,
    val category: String,
    val logo: String,
    val url: String,
    val quality: String,
    val custom: Boolean = false
)

/** The whole catalog, read from `assets/channels.json`. */
data class ChannelCatalog(
    val categories: List<ChannelCategory>,
    val channels: List<Channel>
) {
    fun channelsOf(categoryId: String): List<Channel> =
        channels.filter { it.category == categoryId }

    fun category(id: String): ChannelCategory? =
        categories.firstOrNull { it.id == id }

    fun channel(id: String): Channel? =
        channels.firstOrNull { it.id == id }

    fun search(query: String): List<Channel> {
        val q = query.trim()
        if (q.isEmpty()) return channels
        return channels.filter {
            it.name.contains(q, ignoreCase = true) ||
                it.nameEn.contains(q, ignoreCase = true) ||
                it.category.contains(q, ignoreCase = true)
        }
    }

    /** Adds `extra` channels (user defined) in front of the built-in ones. */
    fun withExtra(extra: List<Channel>): ChannelCatalog =
        if (extra.isEmpty()) this else copy(channels = extra + channels)

    companion object {
        val EMPTY = ChannelCatalog(emptyList(), emptyList())

        fun parse(json: String): ChannelCatalog {
            val root = JSONObject(json)
            val catsJson: JSONArray = root.optJSONArray("categories") ?: JSONArray()
            val channelsJson: JSONArray = root.optJSONArray("channels") ?: JSONArray()

            val categories = ArrayList<ChannelCategory>(catsJson.length())
            for (i in 0 until catsJson.length()) {
                val o = catsJson.optJSONObject(i) ?: continue
                val id = o.optString("id")
                if (id.isBlank()) continue
                categories.add(
                    ChannelCategory(
                        id = id,
                        title = o.optString("title"),
                        subtitle = o.optString("subtitle"),
                        emoji = o.optString("emoji", "📺"),
                        colorHex = o.optString("color", "#7C4DFF")
                    )
                )
            }

            val channels = ArrayList<Channel>(channelsJson.length())
            for (i in 0 until channelsJson.length()) {
                val o = channelsJson.optJSONObject(i) ?: continue
                val url = o.optString("url").trim()
                if (url.isBlank()) continue
                val id = o.optString("id").ifBlank { "ch-$i" }
                channels.add(
                    Channel(
                        id = id,
                        name = o.optString("name").ifBlank { id },
                        nameEn = o.optString("nameEn"),
                        category = o.optString("category"),
                        logo = o.optString("logo"),
                        url = url,
                        quality = o.optString("quality", "HD")
                    )
                )
            }
            return ChannelCatalog(categories, channels)
        }
    }
}
