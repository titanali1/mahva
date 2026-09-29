package ir.takhtlive.tv.ui

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
import ir.takhtlive.tv.data.Channel
import ir.takhtlive.tv.ui.i18n.LocalAppStrings

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
    val strings = LocalAppStrings.current
    LazyColumn(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(top = 8.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        item {
            Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
                Text(
                    text = strings.myChannelsSection,
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Text(
                    text = strings.myChannelsSubtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(10.dp))
                Button(onClick = onAddChannel) {
                    Icon(Icons.Filled.Add, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(strings.addNewChannel)
                }
            }
        }

        if (customChannels.isNotEmpty()) {
            item(key = "title-custom") {
                SectionTitle(
                    title = strings.addedChannels,
                    trailing = strings.channelsCount(customChannels.size)
                )
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
                SectionTitle(
                    title = strings.favourites,
                    trailing = strings.channelsCount(favoriteChannels.size)
                )
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
                SectionTitle(
                    title = strings.recentlyWatched,
                    trailing = strings.channelsCount(recents.size)
                )
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

        item(key = "signature") { SignatureFooter() }

        if (customChannels.isEmpty() && favoriteChannels.isEmpty() && recents.isEmpty()) {
            item {
                EmptyState(
                    title = strings.noChannelsYet,
                    subtitle = strings.noChannelsYetHint
                )
            }
        }
    }
}
