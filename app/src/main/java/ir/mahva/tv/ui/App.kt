package ir.mahva.tv.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import ir.mahva.tv.R
import ir.mahva.tv.data.CatalogRepository
import ir.mahva.tv.data.Channel
import ir.mahva.tv.data.ChannelCatalog
import ir.mahva.tv.data.PrefsStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Navigation targets of the application. */
private sealed interface Screen {
    data object Home : Screen
    data object Search : Screen
    data object Library : Screen
    data class Category(val id: String) : Screen
    data class Player(val channelId: String) : Screen
}

internal const val HOME_TAB = "home"
internal const val CUSTOM_CATEGORY = "custom"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MahvaApp() {
    val context = LocalContext.current
    val prefs = remember(context) { PrefsStore(context) }
    val repository = remember(context) { CatalogRepository(context) }

    var baseCatalog by remember { mutableStateOf(ChannelCatalog.EMPTY) }
    var customChannels by remember { mutableStateOf(prefs.customChannels()) }
    var favorites by remember { mutableStateOf(prefs.favorites()) }
    var recentIds by remember { mutableStateOf(prefs.recents()) }
    var showAddDialog by remember { mutableStateOf(false) }

    val backStack = remember { mutableStateListOf<Screen>() }
    var screen by remember { mutableStateOf<Screen>(Screen.Home) }

    LaunchedEffect(Unit) {
        baseCatalog = withContext(Dispatchers.IO) { repository.load() }
    }

    val catalog = remember(baseCatalog, customChannels) { baseCatalog.withExtra(customChannels) }
    val favoriteChannels = remember(catalog, favorites) {
        catalog.channels.filter { favorites.contains(it.id) }
    }
    val recentChannels = remember(catalog, recentIds) {
        recentIds.mapNotNull { id -> catalog.channel(id) }
    }

    fun navigate(target: Screen) {
        if (target == screen) return
        backStack.add(screen)
        screen = target
    }

    fun back() {
        val previous = backStack.removeLastOrNull()
        screen = previous ?: Screen.Home
    }

    fun openChannel(channel: Channel) {
        prefs.markRecent(channel.id)
        recentIds = prefs.recents()
        navigate(Screen.Player(channel.id))
    }

    fun toggleFavorite(channel: Channel) {
        prefs.toggleFavorite(channel.id)
        favorites = prefs.favorites()
    }

    fun deleteCustomChannel(channel: Channel) {
        prefs.removeCustomChannel(channel.id)
        customChannels = prefs.customChannels()
    }

    BackHandler(enabled = backStack.isNotEmpty()) { back() }

    val current = screen
    if (current is Screen.Player) {
        val channel = catalog.channel(current.channelId)
        if (channel == null) {
            LaunchedEffect(current.channelId) { screen = Screen.Home }
        } else {
            val siblings = catalog.channelsOf(channel.category).ifEmpty { catalog.channels }
            PlayerScreen(
                channel = channel,
                categoryTitle = catalog.category(channel.category)?.title.orEmpty(),
                siblings = siblings,
                isFavorite = favorites.contains(channel.id),
                onBack = { back() },
                onOpenChannel = { openChannel(it) },
                onToggleFavorite = { toggleFavorite(channel) }
            )
            return
        }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Column {
                        Text(
                            text = stringResource(R.string.app_name),
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text(
                            text = stringResource(R.string.app_tagline),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                navigationIcon = {
                    Icon(
                        imageVector = Icons.Filled.PlayArrow,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(start = 14.dp)
                    )
                },
                actions = {
                    IconButton(onClick = { navigate(Screen.Search) }) {
                        Icon(Icons.Filled.Search, contentDescription = "جستجو")
                    }
                    IconButton(onClick = { navigate(Screen.Library) }) {
                        Icon(Icons.Filled.Favorite, contentDescription = "کانال‌های من")
                    }
                    IconButton(onClick = { showAddDialog = true }) {
                        Icon(Icons.Filled.Add, contentDescription = "افزودن کانال")
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                    titleContentColor = MaterialTheme.colorScheme.onBackground
                )
            )
        },
        bottomBar = {
            MahvaBottomBar(
                selected = when (val s = screen) {
                    is Screen.Category -> s.id
                    Screen.Home -> HOME_TAB
                    else -> ""
                },
                onSelect = { id ->
                    backStack.clear()
                    screen = if (id == HOME_TAB) Screen.Home else Screen.Category(id)
                }
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (val s = screen) {
                Screen.Home -> HomeScreen(
                    catalog = catalog,
                    favorites = favorites,
                    recents = recentChannels,
                    onOpenChannel = { openChannel(it) },
                    onOpenCategory = { navigate(Screen.Category(it)) },
                    onAddChannel = { showAddDialog = true },
                    onOpenLibrary = { navigate(Screen.Library) }
                )

                Screen.Search -> SearchScreen(
                    catalog = catalog,
                    favorites = favorites,
                    onOpenChannel = { openChannel(it) },
                    onToggleFavorite = { toggleFavorite(it) }
                )

                Screen.Library -> LibraryScreen(
                    customChannels = customChannels,
                    favoriteChannels = favoriteChannels,
                    recents = recentChannels,
                    onOpenChannel = { openChannel(it) },
                    onToggleFavorite = { toggleFavorite(it) },
                    onDeleteChannel = { deleteCustomChannel(it) },
                    onAddChannel = { showAddDialog = true }
                )

                is Screen.Category -> {
                    val category = catalog.category(s.id)
                    if (category == null) {
                        EmptyState(title = "این بخش خالی است", subtitle = "به خانه بازگردید.")
                    } else {
                        CategoryScreen(
                            category = category,
                            channels = catalog.channelsOf(category.id),
                            onOpenChannel = { openChannel(it) },
                            onToggleFavorite = { toggleFavorite(it) },
                            onDeleteChannel = { deleteCustomChannel(it) }
                        )
                    }
                }

                is Screen.Player -> Box(Modifier.fillMaxSize())
            }
        }
    }

    if (showAddDialog) {
        AddChannelDialog(
            categories = catalog.categories,
            onDismiss = { showAddDialog = false },
            onConfirm = { name, url, categoryId ->
                prefs.addCustomChannel(name, url, categoryId)
                customChannels = prefs.customChannels()
                showAddDialog = false
                if (categoryId == CUSTOM_CATEGORY) {
                    navigate(Screen.Library)
                } else {
                    navigate(Screen.Category(categoryId))
                }
            }
        )
    }
}

@Composable
private fun MahvaBottomBar(selected: String, onSelect: (String) -> Unit) {
    val items = listOf(
        BottomBarItem(HOME_TAB, "خانه", Icons.Filled.Home),
        BottomBarItem("persiana", "پرشیانا", null, R.drawable.ic_tab_tv),
        BottomBarItem("news", "خبری", null, R.drawable.ic_tab_news),
        BottomBarItem("music", "موزیک", null, R.drawable.ic_tab_music),
        BottomBarItem("sports", "ورزشی", null, R.drawable.ic_tab_sports)
    )
    NavigationBar(
        containerColor = MaterialTheme.colorScheme.surface,
        tonalElevation = 0.dp
    ) {
        items.forEach { item ->
            NavigationBarItem(
                selected = selected == item.id,
                onClick = { onSelect(item.id) },
                icon = {
                    val painter = item.painterRes?.let { painterResource(it) }
                    val imageVector = item.imageVector
                    when {
                        painter != null -> Icon(painter = painter, contentDescription = item.label)
                        imageVector != null ->
                            Icon(imageVector = imageVector, contentDescription = item.label)
                    }
                },
                label = { Text(item.label, style = MaterialTheme.typography.labelSmall) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = Color.White,
                    selectedTextColor = MaterialTheme.colorScheme.primary,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            )
        }
    }
}

private data class BottomBarItem(
    val id: String,
    val label: String,
    val imageVector: ImageVector? = null,
    val painterRes: Int? = null
)
