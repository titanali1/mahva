package ir.takhtlive.tv.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import ir.takhtlive.tv.data.Channel
import ir.takhtlive.tv.data.ChannelCatalog
import ir.takhtlive.tv.ui.i18n.LocalAppLanguage
import ir.takhtlive.tv.ui.i18n.LocalAppStrings
import ir.takhtlive.tv.ui.theme.TakhtBlue
import ir.takhtlive.tv.ui.theme.TakhtPurple
import ir.takhtlive.tv.ui.theme.TakhtTeal

@Composable
fun HomeScreen(
    catalog: ChannelCatalog,
    favorites: Set<String>,
    recents: List<Channel>,
    onOpenChannel: (Channel) -> Unit,
    onOpenCategory: (String) -> Unit,
    onAddChannel: () -> Unit,
    onOpenLibrary: () -> Unit,
    modifier: Modifier = Modifier
) {
    val strings = LocalAppStrings.current
    val language = LocalAppLanguage.current
    val favoriteChannels = catalog.channels.filter { favorites.contains(it.id) }
    val customChannels = catalog.channels.filter { it.custom }

    LazyColumn(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(top = 8.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        item { HeroBanner(strings.liveChannels(catalog.channels.size)) }

        // ------------------------------------------------------- shortcuts row
        item {
            SectionTitle(
                title = strings.quickAccess,
                trailing = strings.sectionsCount(catalog.categories.size)
            )
        }
        item {
            LazyRow(
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(catalog.categories, key = { it.id }) { category ->
                    CategoryCard(
                        category = category,
                        channelCount = catalog.channelsOf(category.id).size,
                        onClick = { onOpenCategory(category.id) }
                    )
                }
                item(key = "add") { AddChannelTile(onClick = onAddChannel) }
            }
        }

        // ---------------------------------------------------------- favourites
        if (favoriteChannels.isNotEmpty()) {
            item {
                SectionTitle(
                    title = strings.favourites,
                    trailing = strings.channelsCount(favoriteChannels.size)
                )
            }
            item { ChannelRail(favoriteChannels, onOpenChannel) }
        }

        // ------------------------------------------------------------- recents
        if (recents.isNotEmpty()) {
            item { SectionTitle(title = strings.recentlyWatched) }
            item { ChannelRail(recents, onOpenChannel) }
        }

        // -------------------------------------------------- one rail per section
        catalog.categories.forEach { category ->
            val channels = catalog.channelsOf(category.id)
            if (channels.isEmpty()) return@forEach
            item(key = "title-${category.id}") {
                SectionTitle(
                    title = "${category.emoji}  ${category.titleFor(language)}",
                    trailing = strings.channelsCount(channels.size)
                )
            }
            item(key = "rail-${category.id}") {
                ChannelRail(channels.take(14), onOpenChannel)
            }
            item(key = "more-${category.id}") {
                SeeAllRow(
                    title = strings.seeAll(category.titleFor(language)),
                    onClick = { onOpenCategory(category.id) }
                )
            }
        }

        if (catalog.channels.isEmpty()) {
            item {
                EmptyState(
                    title = strings.loadingChannels,
                    subtitle = strings.loadingHint
                )
            }
        }

        if (customChannels.isNotEmpty()) {
            item {
                SectionTitle(
                    title = strings.myChannelsSection,
                    trailing = strings.channelsCount(customChannels.size)
                )
            }
            item { SeeAllRow(title = strings.manageMyChannels, onClick = onOpenLibrary) }
        }

        // Developer signature, pinned to the bottom of the app's content.
        item(key = "signature") { SignatureFooter() }
    }
}

@Composable
private fun HeroBanner(liveLabel: String) {
    val strings = LocalAppStrings.current
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp)
            .clip(RoundedCornerShape(26.dp))
            .background(Brush.linearGradient(listOf(TakhtPurple, TakhtBlue, TakhtTeal)))
            .padding(18.dp)
    ) {
        Column {
            Text(
                text = strings.appName,
                style = MaterialTheme.typography.headlineSmall,
                color = Color.White
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = strings.heroSubtitle,
                style = MaterialTheme.typography.bodySmall,
                color = Color.White.copy(alpha = 0.92f)
            )
            Spacer(Modifier.height(10.dp))
            LiveBadge(label = liveLabel)
        }
    }
}

@Composable
private fun AddChannelTile(onClick: () -> Unit) {
    val strings = LocalAppStrings.current
    Card(
        modifier = Modifier
            .width(150.dp)
            .height(112.dp)
            .clickable { onClick() },
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = Icons.Filled.Add,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = strings.addChannelShort,
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = strings.selfLinkHint,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun SeeAllRow(title: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .clip(RoundedCornerShape(14.dp))
            .clickable { onClick() }
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.primary
        )
    }
}

@Composable
fun ChannelRail(channels: List<Channel>, onOpenChannel: (Channel) -> Unit) {
    LazyRow(
        contentPadding = PaddingValues(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        items(channels, key = { it.id }) { channel ->
            ChannelChip(channel = channel, onClick = { onOpenChannel(channel) })
        }
    }
}
