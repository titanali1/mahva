package ir.takhtlive.tv.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import ir.takhtlive.tv.BuildConfig
import ir.takhtlive.tv.R
import ir.takhtlive.tv.data.ChannelCatalog
import ir.takhtlive.tv.ui.i18n.AppLanguage
import ir.takhtlive.tv.ui.i18n.AppThemeMode
import ir.takhtlive.tv.ui.i18n.LocalAppLanguage
import ir.takhtlive.tv.ui.i18n.LocalAppStrings
import ir.takhtlive.tv.ui.theme.TakhtBlue
import ir.takhtlive.tv.ui.theme.TakhtPurple
import ir.takhtlive.tv.ui.theme.TakhtTeal

/** Content of the hamburger (navigation) drawer: sections plus language/theme settings. */
@Composable
fun TakhtDrawerContent(
    catalog: ChannelCatalog,
    selectedTab: String,
    language: AppLanguage,
    themeMode: AppThemeMode,
    favoriteCount: Int,
    customCount: Int,
    onSelectTab: (String) -> Unit,
    onOpenSearch: () -> Unit,
    onOpenLibrary: () -> Unit,
    onAddChannel: () -> Unit,
    onLanguageChange: (AppLanguage) -> Unit,
    onThemeChange: (AppThemeMode) -> Unit,
    modifier: Modifier = Modifier
) {
    val strings = LocalAppStrings.current

    Column(
        modifier = modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(bottom = 12.dp)
    ) {
        DrawerHeader()

        Spacer(Modifier.height(4.dp))
        DrawerSectionLabel(strings.menuSections)

        DrawerEntry(
            icon = Icons.Filled.Home,
            label = strings.tabHome,
            selected = selectedTab == HOME_TAB,
            onClick = { onSelectTab(HOME_TAB) }
        )

        catalog.categories.forEach { category ->
            DrawerEntry(
                icon = null,
                painter = sectionPainter(category.id),
                leadingEmoji = category.emoji,
                label = category.titleFor(language),
                badge = strings.channelsCount(catalog.channelsOf(category.id).size),
                selected = selectedTab == category.id,
                onClick = { onSelectTab(category.id) }
            )
        }

        HorizontalDivider(Modifier.padding(horizontal = 16.dp, vertical = 8.dp))

        DrawerEntry(
            icon = Icons.Filled.Search,
            label = strings.search,
            selected = false,
            onClick = onOpenSearch
        )
        DrawerEntry(
            icon = Icons.Filled.Favorite,
            label = strings.myChannels,
            badge = if (favoriteCount + customCount > 0) "$favoriteCount / $customCount" else null,
            selected = false,
            onClick = onOpenLibrary
        )
        DrawerEntry(
            icon = Icons.Filled.Add,
            label = strings.addChannel,
            selected = false,
            onClick = onAddChannel
        )

        HorizontalDivider(Modifier.padding(horizontal = 16.dp, vertical = 8.dp))

        // ------------------------------------------------------------- settings
        DrawerSectionLabel(strings.settings)

        Text(
            text = strings.language,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 6.dp, bottom = 2.dp)
        )
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            AppLanguage.entries.forEach { entry ->
                FilterChip(
                    selected = language == entry,
                    onClick = { onLanguageChange(entry) },
                    label = { Text(entry.label) },
                    leadingIcon = if (language == entry) {
                        { Icon(Icons.Filled.Check, contentDescription = null, Modifier.size(16.dp)) }
                    } else null,
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                )
            }
        }

        Spacer(Modifier.height(10.dp))
        Text(
            text = strings.theme,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 20.dp, end = 20.dp, bottom = 2.dp)
        )
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            val themeLabels = mapOf(
                AppThemeMode.DARK to strings.themeDark,
                AppThemeMode.LIGHT to strings.themeLight,
                AppThemeMode.SYSTEM to strings.themeSystem
            )
            AppThemeMode.entries.forEach { entry ->
                FilterChip(
                    selected = themeMode == entry,
                    onClick = { onThemeChange(entry) },
                    label = { Text(themeLabels[entry] ?: entry.id) },
                    leadingIcon = if (themeMode == entry) {
                        { Icon(Icons.Filled.Check, contentDescription = null, Modifier.size(16.dp)) }
                    } else null,
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                )
            }
        }

        HorizontalDivider(Modifier.padding(horizontal = 16.dp, vertical = 12.dp))

        // ------------------------------------------------------------- about
        Text(
            text = strings.about,
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 20.dp, end = 20.dp, bottom = 2.dp)
        )
        Text(
            text = "${strings.appName} — ${strings.version(BuildConfig.VERSION_NAME)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 4.dp)
        )

        SignatureFooter()
    }
}

@Composable
private fun DrawerHeader() {
    val strings = LocalAppStrings.current
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(12.dp)
            .clip(RoundedCornerShape(24.dp))
            .background(Brush.linearGradient(listOf(TakhtPurple, TakhtBlue, TakhtTeal)))
            .padding(16.dp)
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Filled.PlayArrow,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(28.dp)
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    text = strings.appName,
                    style = MaterialTheme.typography.titleLarge,
                    color = Color.White
                )
            }
            Spacer(Modifier.height(4.dp))
            Text(
                text = strings.tagline,
                style = MaterialTheme.typography.bodySmall,
                color = Color.White.copy(alpha = 0.92f),
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun DrawerSectionLabel(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 4.dp)
    )
}

@Composable
private fun DrawerEntry(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    icon: ImageVector? = null,
    painter: Painter? = null,
    leadingEmoji: String? = null,
    badge: String? = null
) {
    NavigationDrawerItem(
        label = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(label, style = MaterialTheme.typography.titleSmall)
                if (badge != null) {
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = badge,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        },
        selected = selected,
        onClick = onClick,
        icon = {
            when {
                painter != null -> Icon(painter = painter, contentDescription = null)
                icon != null -> Icon(icon, contentDescription = null)
                leadingEmoji != null -> Text(leadingEmoji)
            }
        },
        colors = NavigationDrawerItemDefaults.colors(
            selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
            selectedTextColor = MaterialTheme.colorScheme.onPrimaryContainer,
            unselectedTextColor = MaterialTheme.colorScheme.onSurface
        ),
        modifier = Modifier.padding(horizontal = 12.dp, vertical = 2.dp)
    )
}

/** Drawer icon resource for a section id, if it has a custom one. */
fun sectionDrawableRes(categoryId: String): Int? = when (categoryId) {
    "persiana" -> R.drawable.ic_tab_tv
    "news" -> R.drawable.ic_tab_news
    "music" -> R.drawable.ic_tab_music
    "sports" -> R.drawable.ic_tab_sports
    else -> null
}

/** Painter helper kept for call sites that need a drawable painter. */
@Composable
fun sectionPainter(categoryId: String): Painter? =
    sectionDrawableRes(categoryId)?.let { painterResource(it) }
