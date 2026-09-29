package ir.takhtlive.tv.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import ir.takhtlive.tv.R
import ir.takhtlive.tv.data.CatalogRepository
import ir.takhtlive.tv.data.Channel
import ir.takhtlive.tv.data.ChannelCatalog
import ir.takhtlive.tv.data.PrefsStore
import ir.takhtlive.tv.ui.i18n.AppLanguage
import ir.takhtlive.tv.ui.i18n.AppThemeMode
import ir.takhtlive.tv.ui.i18n.LocalAppStrings
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
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
fun TakhtLiveApp(
    language: AppLanguage,
    themeMode: AppThemeMode,
    onLanguageChange: (AppLanguage) -> Unit,
    onThemeChange: (AppThemeMode) -> Unit
) {
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

    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()

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

    fun selectTab(tabId: String) {
        backStack.clear()
        screen = if (tabId == HOME_TAB) Screen.Home else Screen.Category(tabId)
        scope.launch { drawerState.close() }
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
                categoryTitle = catalog.category(channel.category)?.titleFor(language).orEmpty(),
                siblings = siblings,
                isFavorite = favorites.contains(channel.id),
                onBack = { back() },
                onOpenChannel = { openChannel(it) },
                onToggleFavorite = { toggleFavorite(channel) }
            )
            return
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        gesturesEnabled = backStack.isEmpty(),
        drawerContent = {
            ModalDrawerSheet(
                drawerContainerColor = MaterialTheme.colorScheme.surface,
                modifier = Modifier.padding(top = 8.dp)
            ) {
                TakhtDrawerContent(
                    catalog = catalog,
                    selectedTab = when (val s = screen) {
                        is Screen.Category -> s.id
                        Screen.Home -> HOME_TAB
                        else -> ""
                    },
                    language = language,
                    themeMode = themeMode,
                    favoriteCount = favoriteChannels.size,
                    customCount = customChannels.size,
                    onSelectTab = { selectTab(it) },
                    onOpenSearch = {
                        navigate(Screen.Search)
                        scope.launch { drawerState.close() }
                    },
                    onOpenLibrary = {
                        navigate(Screen.Library)
                        scope.launch { drawerState.close() }
                    },
                    onAddChannel = {
                        showAddDialog = true
                        scope.launch { drawerState.close() }
                    },
                    onLanguageChange = { selected ->
                        prefs.languageCode = selected.code
                        onLanguageChange(selected)
                    },
                    onThemeChange = { selected ->
                        prefs.themeModeId = selected.id
                        onThemeChange(selected)
                    }
                )
            }
        }
    ) {
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            topBar = {
                CenterAlignedTopAppBar(
                    title = {
                        val strings = LocalAppStrings.current
                        Column {
                            Text(
                                text = strings.appName,
                                style = MaterialTheme.typography.titleMedium
                            )
                            Text(
                                text = strings.tagline,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    },
                    navigationIcon = {
                        val strings = LocalAppStrings.current
                        IconButton(
                            onClick = { scope.launch { drawerState.open() } },
                            modifier = Modifier.testTag(TAG_MENU)
                        ) {
                            Icon(
                                imageVector = Icons.Filled.Menu,
                                contentDescription = strings.menu
                            )
                        }
                    },
                    actions = {
                        val strings = LocalAppStrings.current
                        Icon(
                            imageVector = Icons.Filled.PlayArrow,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(end = 6.dp)
                        )
                        IconButton(
                            onClick = { navigate(Screen.Search) },
                            modifier = Modifier.testTag(TAG_SEARCH)
                        ) {
                            Icon(Icons.Filled.Search, contentDescription = strings.search)
                        }
                        IconButton(
                            onClick = { navigate(Screen.Library) },
                            modifier = Modifier.testTag(TAG_LIBRARY)
                        ) {
                            Icon(Icons.Filled.Favorite, contentDescription = strings.myChannels)
                        }
                        IconButton(
                            onClick = { showAddDialog = true },
                            modifier = Modifier.testTag(TAG_ADD)
                        ) {
                            Icon(Icons.Filled.Add, contentDescription = strings.addChannel)
                        }
                    },
                    colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                        containerColor = MaterialTheme.colorScheme.background,
                        titleContentColor = MaterialTheme.colorScheme.onBackground,
                        navigationIconContentColor = MaterialTheme.colorScheme.onBackground,
                        actionIconContentColor = MaterialTheme.colorScheme.onBackground
                    )
                )
            },
            bottomBar = {
                Column {
                    TakhtBottomBar(
                        selected = when (val s = screen) {
                            is Screen.Category -> s.id
                            Screen.Home -> HOME_TAB
                            else -> ""
                        },
                        onSelect = { selectTab(it) }
                    )
                    // developer signature, always visible at the bottom of the app
                    SignatureStrip()
                }
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
                        val strings = LocalAppStrings.current
                        val category = catalog.category(s.id)
                        if (category == null) {
                            EmptyState(title = strings.sectionEmpty, subtitle = strings.backHome)
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
private fun TakhtBottomBar(selected: String, onSelect: (String) -> Unit) {
    val strings = LocalAppStrings.current
    val items = listOf(
        BottomBarItem(HOME_TAB, strings.tabHome, Icons.Filled.Home),
        BottomBarItem("persiana", strings.tabPersiana, null, R.drawable.ic_tab_tv),
        BottomBarItem("news", strings.tabNews, null, R.drawable.ic_tab_news),
        BottomBarItem("music", strings.tabMusic, null, R.drawable.ic_tab_music),
        BottomBarItem("sports", strings.tabSports, null, R.drawable.ic_tab_sports)
    )
    NavigationBar(
        containerColor = MaterialTheme.colorScheme.surface,
        tonalElevation = 0.dp
    ) {
        items.forEach { item ->
            NavigationBarItem(
                selected = selected == item.id,
                onClick = { onSelect(item.id) },
                modifier = Modifier.testTag("tab_${item.id}"),
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
                    selectedIconColor = MaterialTheme.colorScheme.onPrimaryContainer,
                    selectedTextColor = MaterialTheme.colorScheme.primary,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            )
        }
    }
}

/** Test tags used by the instrumentation/Robolectric tests. */
internal const val TAG_MENU = "action_menu"
internal const val TAG_SEARCH = "action_search"
internal const val TAG_LIBRARY = "action_library"
internal const val TAG_ADD = "action_add"

private data class BottomBarItem(
    val id: String,
    val label: String,
    val imageVector: ImageVector? = null,
    val painterRes: Int? = null
)
