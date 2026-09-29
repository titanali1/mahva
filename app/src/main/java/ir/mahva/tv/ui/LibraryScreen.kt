package ir.mahva.tv.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import ir.mahva.tv.data.Channel

/** "کانال‌های من": user added channels, favourites and recently watched channels. */
@Composable
fun LibraryScreen(
    customChannels: List<Channel>,
    favoriteChannels: List<Channel>,
    recents: List<Channel>,
    onOpenChannel: (Channel) -> Unit,
    onToggleFavorite: (Channel) -> Unit,
    onDeleteChannel: (Channel) -> Unit,
    onAddChannel: () -> Unit,
    modifier: Modifier = Modifier
) {
    LazyColumn(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(top = 8.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        item {
            Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                Text(
                    text = "کانال‌های من",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Text(
                    text = "کانال‌های افزوده‌شده، مورد علاقه‌ها و بازدیدهای اخیر",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(10.dp))
                Button(onClick = onAddChannel) {
                    Icon(Icons.Filled.Add, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("افزودن کانال جدید")
                }
            }
        }

        if (customChannels.isNotEmpty()) {
            item(key = "title-custom") {
                SectionTitle(title = "کانال‌های افزوده‌شده", trailing = "${customChannels.size}")
            }
            items(customChannels, key = { "custom-${it.id}" }) { channel ->
                ChannelRow(
                    channel = channel,
                    isFavorite = favoriteChannels.any { it.id == channel.id },
                    onClick = { onOpenChannel(channel) },
                    onToggleFavorite = { onToggleFavorite(channel) },
                    onDelete = { onDeleteChannel(channel) }
                )
            }
        }

        if (favoriteChannels.isNotEmpty()) {
            item(key = "title-fav") {
                SectionTitle(title = "مورد علاقه‌ها", trailing = "${favoriteChannels.size}")
            }
            items(favoriteChannels, key = { "fav-${it.id}" }) { channel ->
                ChannelRow(
                    channel = channel,
                    isFavorite = true,
                    onClick = { onOpenChannel(channel) },
                    onToggleFavorite = { onToggleFavorite(channel) }
                )
            }
        }

        if (recents.isNotEmpty()) {
            item(key = "title-recent") {
                SectionTitle(title = "اخیراً دیده‌شده", trailing = "${recents.size}")
            }
            items(recents, key = { "recent-${it.id}" }) { channel ->
                ChannelRow(
                    channel = channel,
                    isFavorite = favoriteChannels.any { it.id == channel.id },
                    onClick = { onOpenChannel(channel) },
                    onToggleFavorite = { onToggleFavorite(channel) }
                )
            }
        }

        if (customChannels.isEmpty() && favoriteChannels.isEmpty() && recents.isEmpty()) {
            item {
                EmptyState(
                    title = "هنوز کانالی اضافه نکرده‌اید",
                    subtitle = "با دکمهٔ بالا آدرس پخش (m3u8) دلخواه خود را اضافه کنید، " +
                        "یا از بخش‌های پرشیانا، خبری، موزیک و ورزشی کانال‌ها را نشان کنید."
                )
            }
        }
    }
}
