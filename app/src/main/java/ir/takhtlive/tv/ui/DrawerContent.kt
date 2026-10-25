package ir.takhtlive.tv.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import ir.takhtlive.tv.BuildConfig
import ir.takhtlive.tv.R
import ir.takhtlive.tv.data.ChannelCatalog
import ir.takhtlive.tv.ui.i18n.AppLanguage
import ir.takhtlive.tv.ui.i18n.AppThemeMode
import ir.takhtlive.tv.ui.i18n.LocalAppStrings
import ir.takhtlive.tv.ui.theme.TakhtBlue
import ir.takhtlive.tv.ui.theme.TakhtPurple
import ir.takhtlive.tv.ui.theme.TakhtTeal

/**
 * Content of the hamburger (navigation) drawer.
 *
 * The sections are shown as colourful gradient tiles (one per section, so the
 * menu stays at exactly four sections) followed by the quick actions, the
 * language/theme switches and the signature.
 */
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
        DrawerHeader(channelCount = catalog.channels.size)

        Spacer(Modifier.height(10.dp))
        DrawerSectionLabel(strings.menuSections)

        DrawerSectionTile(
            title = strings.tabHome,
            subtitle = strings.quickAccess,
            icon = Icons.Filled.Home,
            accent = TakhtBlue,
            badge = null,
            selected = selectedTab == HOME_TAB,
            testTag = "drawer_home",
            onClick = { onSelectTab(HOME_TAB) }
        )

        catalog.categories.forEach { category ->
            DrawerSectionTile(
                title = category.titleFor(language),
                subtitle = category.subtitleFor(language),
                painter = sectionPainter(category.id),
                leadingEmoji = category.emoji,
                accent = parseColor(category.colorHex, TakhtPurple),
                badge = catalog.channelsOf(category.id).size.toString(),
                selected = selectedTab == category.id,
                testTag = "drawer_${category.id}",
                onClick = { onSelectTab(category.id) }
            )
        }

        HorizontalDivider(Modifier.padding(horizontal = 16.dp, vertical = 10.dp))

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
                    modifier = Modifier.testTag("lang_${entry.code}"),
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
                    modifier = Modifier.testTag("theme_${entry.id}"),
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

        // ---------------------------------------------------------------- about
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
private fun DrawerHeader(channelCount: Int) {
    val strings = LocalAppStrings.current
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(12.dp)
            .clip(RoundedCornerShape(26.dp))
            .background(
                Brush.linearGradient(listOf(Color(0xFF7C4DFF), Color(0xFF2F80ED), Color(0xFF12B8A6)))
            )
            .padding(16.dp)
    ) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Image(
                    painter = painterResource(R.drawable.ic_brand_logo),
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .size(46.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color.White.copy(alpha = 0.14f))
                )
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = strings.appName,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Text(
                        text = strings.channelsCount(channelCount),
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White.copy(alpha = 0.9f)
                    )
                }
                LiveBadge()
            }
            Spacer(Modifier.height(10.dp))
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
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier
                .size(width = 4.dp, height = 14.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary)
        )
        Spacer(Modifier.width(8.dp))
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.primary
        )
    }
}

/** One colourful section tile of the drawer (home + the four sections). */
@Composable
private fun DrawerSectionTile(
    title: String,
    selected: Boolean,
    onClick: () -> Unit,
    accent: Color,
    subtitle: String? = null,
    badge: String? = null,
    icon: ImageVector? = null,
    painter: Painter? = null,
    leadingEmoji: String? = null,
    testTag: String? = null
) {
    val titleColor = if (selected) Color.White else MaterialTheme.colorScheme.onSurface
    val subColor = if (selected) {
        Color.White.copy(alpha = 0.85f)
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 3.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(
                if (selected) {
                    Brush.linearGradient(listOf(accent, accent.copy(alpha = 0.62f)))
                } else {
                    Brush.linearGradient(
                        listOf(accent.copy(alpha = 0.22f), accent.copy(alpha = 0.07f))
                    )
                }
            )
            .clickable { onClick() }
            .let { if (testTag != null) it.testTag(testTag) else it }
            .padding(horizontal = 10.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(38.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(
                    if (selected) Color.White.copy(alpha = 0.22f) else accent.copy(alpha = 0.22f)
                ),
            contentAlignment = Alignment.Center
        ) {
            when {
                painter != null -> Icon(
                    painter = painter,
                    contentDescription = null,
                    tint = if (selected) Color.White else accent,
                    modifier = Modifier.size(21.dp)
                )

                icon != null -> Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = if (selected) Color.White else accent,
                    modifier = Modifier.size(21.dp)
                )

                leadingEmoji != null -> Text(leadingEmoji)
            }
        }
        Spacer(Modifier.width(10.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = titleColor,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            if (subtitle != null) {
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.labelSmall,
                    color = subColor,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
        if (badge != null) {
            Box(
                modifier = Modifier
                    .clip(CircleShape)
                    .background(
                        if (selected) Color.White.copy(alpha = 0.24f) else accent.copy(alpha = 0.18f)
                    )
                    .padding(horizontal = 9.dp, vertical = 3.dp)
            ) {
                Text(
                    text = badge,
                    style = MaterialTheme.typography.labelSmall,
                    color = if (selected) Color.White else accent
                )
            }
        }
    }
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
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 2.dp)
            .clip(RoundedCornerShape(16.dp))
            .clickable { onClick() }
            .padding(horizontal = 10.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(RoundedCornerShape(11.dp))
                .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.07f)),
            contentAlignment = Alignment.Center
        ) {
            when {
                painter != null -> Icon(
                    painter = painter,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.size(18.dp)
                )

                icon != null -> Icon(
                    imageVector = icon,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.size(18.dp)
                )

                leadingEmoji != null -> Text(leadingEmoji)
            }
        }
        Spacer(Modifier.width(10.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f)
        )
        if (badge != null) {
            Text(
                text = badge,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/** Drawable icon resource for a section id, if it has a custom one. */
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
