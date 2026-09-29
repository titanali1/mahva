package ir.takhtlive.tv.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Small key/value store for favourites, recently watched channels and custom channels. */
class PrefsStore(context: Context) {

    private val prefs =
        context.applicationContext.getSharedPreferences("takhtlive_prefs", Context.MODE_PRIVATE)

    // --------------------------------------------------------------- appearance

    /** Selected interface language: fa | en | ar */
    var languageCode: String
        get() = prefs.getString(KEY_LANGUAGE, "fa") ?: "fa"
        set(value) = prefs.edit().putString(KEY_LANGUAGE, value).apply()

    /** Selected theme: dark | light | system */
    var themeModeId: String
        get() = prefs.getString(KEY_THEME, "dark") ?: "dark"
        set(value) = prefs.edit().putString(KEY_THEME, value).apply()

    // ---------------------------------------------------------------- favourites

    fun favorites(): Set<String> =
        HashSet(prefs.getStringSet(KEY_FAVORITES, emptySet()) ?: emptySet())

    fun isFavorite(id: String): Boolean = favorites().contains(id)

    /** Returns the new favourite state. */
    fun toggleFavorite(id: String): Boolean {
        val current = favorites().toMutableSet()
        val nowFavorite = !current.contains(id)
        if (nowFavorite) current.add(id) else current.remove(id)
        prefs.edit().putStringSet(KEY_FAVORITES, current).apply()
        return nowFavorite
    }

    // ------------------------------------------------------------------- recents

    fun recents(): List<String> =
        prefs.getString(KEY_RECENTS, "").orEmpty()
            .split("|")
            .filter { it.isNotBlank() }

    fun markRecent(id: String) {
        val updated = (listOf(id) + recents().filter { it != id }).take(MAX_RECENTS)
        prefs.edit().putString(KEY_RECENTS, updated.joinToString("|")).apply()
    }

    // ------------------------------------------------------- custom (user) channels

    fun customChannels(): List<Channel> {
        val raw = prefs.getString(KEY_CUSTOM, null) ?: return emptyList()
        return runCatching {
            val array = JSONArray(raw)
            (0 until array.length()).mapNotNull { index ->
                val o = array.optJSONObject(index) ?: return@mapNotNull null
                val url = o.optString("url").trim()
                if (url.isBlank()) return@mapNotNull null
                Channel(
                    id = o.optString("id").ifBlank { "custom-${url.hashCode()}" },
                    name = o.optString("name").ifBlank { "کانال من" },
                    nameEn = o.optString("nameEn"),
                    category = o.optString("category", "custom"),
                    logo = o.optString("logo"),
                    url = url,
                    quality = o.optString("quality", "LIVE"),
                    custom = true
                )
            }
        }.getOrElse { emptyList() }
    }

    fun addCustomChannel(name: String, url: String, category: String): Channel {
        val channel = Channel(
            id = "custom-${System.currentTimeMillis()}",
            name = name.trim().ifBlank { "کانال من" },
            nameEn = "",
            category = category,
            logo = "",
            url = url.trim(),
            quality = "LIVE",
            custom = true
        )
        val list = customChannels() + channel
        saveCustom(list)
        return channel
    }

    fun removeCustomChannel(id: String) {
        saveCustom(customChannels().filterNot { it.id == id })
    }

    private fun saveCustom(channels: List<Channel>) {
        val array = JSONArray()
        channels.forEach { c ->
            array.put(
                JSONObject().apply {
                    put("id", c.id)
                    put("name", c.name)
                    put("url", c.url)
                    put("nameEn", c.nameEn)
                    put("nameAr", c.nameAr)
                    put("category", c.category)
                }
            )
        }
        prefs.edit().putString(KEY_CUSTOM, array.toString()).apply()
    }

    private companion object {
        const val KEY_LANGUAGE = "language"
        const val KEY_THEME = "theme_mode"
        const val KEY_FAVORITES = "favorites"
        const val KEY_RECENTS = "recents"
        const val KEY_CUSTOM = "custom_channels"
        const val MAX_RECENTS = 20
    }
}
