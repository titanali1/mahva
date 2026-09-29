package ir.mahva.tv.ui

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
import androidx.compose.foundation.layout.size
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
import ir.mahva.tv.data.Channel
import ir.mahva.tv.data.ChannelCatalog
import ir.mahva.tv.ui.theme.MahvaBlue
import ir.mahva.tv.ui.theme.MahvaPurple
import ir.mahva.tv.ui.theme.MahvaTeal

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
    val favoriteChannels = catalog.channels.filter { favorites.contains(it.id) }
    val customChannels = catalog.channels.filter { it.custom }

    LazyColumn(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(top = 8.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        item { HeroBanner(channelCount = catalog.channels.size) }

        // ------------------------------------------------------- shortcuts row
        item {
            SectionTitle(title = "دسترسی سریع", trailing = "${catalog.categories.size} بخش")
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
                item(key = "add") {
                    AddChannelTile(onClick = onAddChannel)
                }
            }
        }

        // ---------------------------------------------------------- favourites
        if (favoriteChannels.isNotEmpty()) {
            item {
                SectionTitle(
                    title = "مورد علاقه‌ها",
                    trailing = "${favoriteChannels.size} کانال"
                )
            }
            item { ChannelRail(favoriteChannels, onOpenChannel) }
        }

        // ------------------------------------------------------------- recents
        if (recents.isNotEmpty()) {
            item { SectionTitle(title = "اخیراً دیده‌شده") }
            item { ChannelRail(recents, onOpenChannel) }
        }

        // -------------------------------------------------- one rail per section
        catalog.categories.forEach { category ->
            val channels = catalog.channelsOf(category.id)
            if (channels.isEmpty()) return@forEach
            item(key = "title-${category.id}") {
                SectionTitle(
                    title = "${category.emoji}  ${category.title}",
                    trailing = "${channels.size} کانال"
                )
            }
            item(key = "rail-${category.id}") {
                ChannelRail(channels.take(14), onOpenChannel)
            }
            item(key = "more-${category.id}") {
                SeeAllRow(
                    title = "مشاهدهٔ همهٔ کانال‌های ${category.title}",
                    onClick = { onOpenCategory(category.id) }
                )
            }
        }

        if (catalog.channels.isEmpty()) {
            item {
                EmptyState(
                    title = "در حال بارگذاری فهرست کانال‌ها…",
                    subtitle = "اگر این پیام باقی ماند، برنامه را دوباره باز کنید."
                )
            }
        }

        if (customChannels.isNotEmpty()) {
            item { SectionTitle(title = "کانال‌های من", trailing = "${customChannels.size} کانال") }
            item {
                SeeAllRow(title = "مدیریت کانال‌های من", onClick = onOpenLibrary)
            }
        }
    }
}

@Composable
private fun HeroBanner(channelCount: Int) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp)
            .clip(RoundedCornerShape(26.dp))
            .background(
                Brush.linearGradient(listOf(MahvaPurple, MahvaBlue, MahvaTeal))
            )
            .padding(18.dp)
    ) {
        Column {
            Text(
                text = "ماهوا",
                style = MaterialTheme.typography.headlineSmall,
                color = Color.White
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "پخش زندهٔ کانال‌های ماهواره‌ای؛ پرشیانا، خبری، موزیک و ورزشی",
                style = MaterialTheme.typography.bodySmall,
                color = Color.White.copy(alpha = 0.92f)
            )
            Spacer(Modifier.height(10.dp))
            LiveBadge(label = "$channelCount کانال زنده")
        }
    }
}

@Composable
private fun AddChannelTile(onClick: () -> Unit) {
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
                text = "افزودن کانال",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                text = "لینک پخش خودت",
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
