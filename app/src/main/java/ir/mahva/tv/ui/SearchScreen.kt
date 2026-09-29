package ir.mahva.tv.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import ir.mahva.tv.data.Channel
import ir.mahva.tv.data.ChannelCatalog

/** Searches every channel of every section at once. */
@Composable
fun SearchScreen(
    catalog: ChannelCatalog,
    favorites: Set<String>,
    onOpenChannel: (Channel) -> Unit,
    onToggleFavorite: (Channel) -> Unit,
    modifier: Modifier = Modifier
) {
    var query by rememberSaveable { mutableStateOf("") }
    val results = remember(catalog, query) {
        if (query.trim().isEmpty()) emptyList() else catalog.search(query)
    }

    Column(modifier = modifier.fillMaxWidth()) {
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            singleLine = true,
            placeholder = { Text("نام کانال را بنویسید…") },
            leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
            trailingIcon = {
                if (query.isNotEmpty()) {
                    IconButton(onClick = { query = "" }) {
                        Icon(Icons.Filled.Close, contentDescription = "پاک کردن")
                    }
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp)
        )

        if (query.isBlank()) {
            EmptyState(
                title = "جستجو در ${catalog.channels.size} کانال",
                subtitle = "بخش پرشیانا، خبری، موزیک، ورزشی و کانال‌های شخصی شما جستجو می‌شوند."
            )
        } else if (results.isEmpty()) {
            EmptyState(title = "نتیجه‌ای یافت نشد", subtitle = "املای نام کانال را بررسی کنید.")
        } else {
            LazyColumn(
                contentPadding = PaddingValues(vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                items(results, key = { it.id }) { channel ->
                    val category = catalog.category(channel.category)
                    ChannelRow(
                        channel = channel,
                        isFavorite = favorites.contains(channel.id),
                        onClick = { onOpenChannel(channel) },
                        onToggleFavorite = { onToggleFavorite(channel) }
                    )
                    Text(
                        text = category?.title ?: "",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(start = 84.dp, bottom = 4.dp)
                    )
                }
            }
        }
    }
}
