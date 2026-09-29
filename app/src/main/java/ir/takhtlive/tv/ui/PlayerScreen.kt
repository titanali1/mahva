package ir.takhtlive.tv.ui

import android.app.Activity
import android.app.PictureInPictureParams
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.util.Rational
import androidx.annotation.OptIn
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.KeyboardArrowLeft
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LifecycleOwner
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DefaultHttpDataSource
import androidx.media3.exoplayer.DefaultLoadControl
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import androidx.media3.ui.AspectRatioFrameLayout
import androidx.media3.ui.PlayerView
import ir.takhtlive.tv.data.Channel
import ir.takhtlive.tv.ui.i18n.LocalAppLanguage
import ir.takhtlive.tv.ui.i18n.LocalAppStrings
import kotlinx.coroutines.delay

private const val USER_AGENT = "TakhtLiveTV/1.0 (Android; ExoPlayer)"
private const val MAX_RETRIES = 6

/**
 * Full screen live player.
 *
 * Live IPTV streams drop out regularly, so the player automatically retries
 * before showing an error to the user.
 */
@OptIn(UnstableApi::class)
@Composable
fun PlayerScreen(
    channel: Channel,
    categoryTitle: String,
    siblings: List<Channel>,
    isFavorite: Boolean,
    onBack: () -> Unit,
    onOpenChannel: (Channel) -> Unit,
    onToggleFavorite: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val activity = remember(context) { context.findActivity() }
    val strings = LocalAppStrings.current
    val language = LocalAppLanguage.current
    val channelTitle = channel.nameFor(language)

    var errorMessage by remember(channel.id) { mutableStateOf<String?>(null) }
    var isBuffering by remember(channel.id) { mutableStateOf(true) }
    var attempts by remember(channel.id) { mutableIntStateOf(0) }
    var retryKey by remember(channel.id) { mutableIntStateOf(0) }
    var resizeModeIndex by remember(channel.id) { mutableIntStateOf(0) }
    var menuExpanded by remember { mutableStateOf(false) }

    val resizeModes = listOf(
        AspectRatioFrameLayout.RESIZE_MODE_FIT to strings.originalSize,
        AspectRatioFrameLayout.RESIZE_MODE_ZOOM to strings.zoomToFill,
        AspectRatioFrameLayout.RESIZE_MODE_FILL to strings.stretchToFill
    )

    val exoPlayer = remember(channel.id) {
        val dataSourceFactory = DefaultHttpDataSource.Factory()
            .setUserAgent(USER_AGENT)
            .setConnectTimeoutMs(20_000)
            .setReadTimeoutMs(25_000)
            .setAllowCrossProtocolRedirects(true)

        val mediaSourceFactory = DefaultMediaSourceFactory(context)
            .setDataSourceFactory(dataSourceFactory)

        val loadControl = DefaultLoadControl.Builder()
            .setBufferDurationsMs(6_000, 45_000, 1_500, 3_000)
            .build()

        ExoPlayer.Builder(context)
            .setMediaSourceFactory(mediaSourceFactory)
            .setLoadControl(loadControl)
            .setHandleAudioBecomingNoisy(true)
            .build()
            .apply {
                setMediaItem(MediaItem.fromUri(channel.url))
                prepare()
                playWhenReady = true
            }
    }

    val playerView = remember(channel.id) {
        PlayerView(context).apply {
            useController = true
            controllerAutoShow = true
            controllerShowTimeoutMs = 3500
            setShowBuffering(PlayerView.SHOW_BUFFERING_NEVER)
            setShowNextButton(false)
            setShowPreviousButton(false)
            setShowFastForwardButton(false)
            setShowRewindButton(false)
            resizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT
            keepScreenOn = true
        }
    }

    // Autoplay state, errors and automatic reconnection.
    DisposableEffect(exoPlayer) {
        val listener = object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                isBuffering = playbackState == Player.STATE_BUFFERING
                if (playbackState == Player.STATE_ENDED) {
                    errorMessage = strings.streamEnded
                }
            }

            override fun onPlayerError(error: PlaybackException) {
                if (attempts < MAX_RETRIES) {
                    attempts += 1
                    retryKey += 1
                } else {
                    isBuffering = false
                    val code = error.errorCodeName
                    errorMessage = if (code.isBlank()) {
                        strings.connectionFailed
                    } else {
                        strings.connectionFailed + " ($code)"
                    }
                }
            }
        }
        exoPlayer.addListener(listener)
        onDispose { exoPlayer.removeListener(listener) }
    }

    // Reconnect with a growing delay.
    LaunchedEffect(retryKey) {
        if (retryKey == 0) return@LaunchedEffect
        errorMessage = null
        isBuffering = true
        delay((1_000L * attempts).coerceAtMost(6_000L))
        exoPlayer.prepare()
        exoPlayer.playWhenReady = true
    }

    DisposableEffect(exoPlayer) {
        onDispose {
            playerView.player = null
            exoPlayer.release()
        }
    }

    // Pause while the app is in the background.
    val lifecycleOwner = remember(context) { activity as? LifecycleOwner }
    DisposableEffect(lifecycleOwner, exoPlayer) {
        val owner = lifecycleOwner
        if (owner == null) {
            onDispose { }
        } else {
            val observer = LifecycleEventObserver { _, event ->
                when (event) {
                    Lifecycle.Event.ON_STOP -> exoPlayer.pause()
                    Lifecycle.Event.ON_START -> {
                        if (exoPlayer.playbackState == Player.STATE_IDLE) {
                            exoPlayer.prepare()
                        }
                        exoPlayer.playWhenReady = true
                    }
                    else -> Unit
                }
            }
            owner.lifecycle.addObserver(observer)
            onDispose { owner.lifecycle.removeObserver(observer) }
        }
    }

    val shareChannel: () -> Unit = {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, channelTitle)
            putExtra(Intent.EXTRA_TEXT, channelTitle + "\n" + channel.url)
        }
        runCatching {
            context.startActivity(Intent.createChooser(intent, strings.shareChannel))
        }
        Unit
    }

    val openExternally: () -> Unit = {
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(Uri.parse(channel.url), "application/x-mpegURL")
        }
        runCatching {
            context.startActivity(Intent.createChooser(intent, strings.playWithExternal))
        }
        Unit
    }

    val enterPipMode: () -> Unit = {
        val act = activity
        if (act != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            runCatching {
                act.enterPictureInPictureMode(
                    PictureInPictureParams.Builder()
                        .setAspectRatio(Rational(16, 9))
                        .build()
                )
            }
        }
        Unit
    }

    val index = siblings.indexOfFirst { it.id == channel.id }
    val previousChannel = if (index > 0) siblings[index - 1] else null
    val nextChannel = if (index >= 0 && index < siblings.size - 1) siblings[index + 1] else null

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        AndroidView(
            factory = { playerView },
            modifier = Modifier.fillMaxSize(),
            update = { view -> if (view.player !== exoPlayer) view.player = exoPlayer }
        )

        // ------------------------------------------------------------ top bar
        Row(
            modifier = Modifier
                .align(Alignment.TopStart)
                .fillMaxWidth()
                .background(
                    Brush.verticalGradient(
                        listOf(Color.Black.copy(alpha = 0.78f), Color.Transparent)
                    )
                )
                .statusBarsPadding()
                .padding(horizontal = 6.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = strings.back,
                    tint = Color.White
                )
            }
            ChannelLogo(channel, size = 38.dp, corner = 12.dp)
            Spacer(Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = channelTitle,
                    color = Color.White,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    LiveBadge()
                    if (categoryTitle.isNotBlank()) {
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = categoryTitle,
                            color = Color.White.copy(alpha = 0.85f),
                            style = MaterialTheme.typography.labelSmall,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                }
            }
            IconButton(onClick = onToggleFavorite) {
                Icon(
                    imageVector = if (isFavorite) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder,
                    contentDescription = strings.favourite,
                    tint = if (isFavorite) Color(0xFFFF7BA8) else Color.White
                )
            }
            IconButton(onClick = shareChannel) {
                Icon(
                    imageVector = Icons.Filled.Share,
                    contentDescription = strings.share,
                    tint = Color.White
                )
            }
            Box {
                IconButton(onClick = { menuExpanded = true }) {
                    Icon(
                        imageVector = Icons.Filled.MoreVert,
                        contentDescription = strings.moreOptions,
                        tint = Color.White
                    )
                }
                DropdownMenu(
                    expanded = menuExpanded,
                    onDismissRequest = { menuExpanded = false }
                ) {
                    resizeModes.forEachIndexed { position, entry ->
                        DropdownMenuItem(
                            text = { Text(entry.second) },
                            onClick = {
                                resizeModeIndex = position
                                playerView.resizeMode = entry.first
                                menuExpanded = false
                            },
                            leadingIcon = {
                                if (resizeModeIndex == position) {
                                    Icon(Icons.Filled.Check, contentDescription = null)
                                } else {
                                    Spacer(Modifier.size(24.dp))
                                }
                            }
                        )
                    }
                    HorizontalDivider()
                    DropdownMenuItem(
                        text = { Text(strings.openInOtherApp) },
                        onClick = {
                            menuExpanded = false
                            openExternally()
                        }
                    )
                    DropdownMenuItem(
                        text = { Text(strings.pictureInPicture) },
                        onClick = {
                            menuExpanded = false
                            enterPipMode()
                        }
                    )
                }
            }
        }

        // -------------------------------------------------------- loading state
        if (isBuffering && errorMessage == null) {
            Column(
                modifier = Modifier.align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                CircularProgressIndicator(color = Color.White)
                Spacer(Modifier.height(12.dp))
                Text(
                    text = if (attempts > 0) strings.reconnecting else strings.connecting,
                    color = Color.White.copy(alpha = 0.9f),
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        // ------------------------------------------------------------- error
        val message = errorMessage
        if (message != null) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.75f)),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    modifier = Modifier.padding(28.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        imageVector = Icons.Filled.Warning,
                        contentDescription = null,
                        tint = Color(0xFFFFC107),
                        modifier = Modifier.size(44.dp)
                    )
                    Spacer(Modifier.height(12.dp))
                    Text(
                        text = message,
                        color = Color.White,
                        textAlign = TextAlign.Center,
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Spacer(Modifier.height(18.dp))
                    Button(onClick = {
                        attempts = 0
                        errorMessage = null
                        retryKey += 1
                    }) {
                        Icon(Icons.Filled.Refresh, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text(strings.retry)
                    }
                    Spacer(Modifier.height(6.dp))
                    TextButton(onClick = onBack) { Text(strings.backTo) }
                    Spacer(Modifier.height(2.dp))
                    TextButton(onClick = openExternally) {
                        Text(strings.playWithExternal)
                    }
                }
            }
        }

        // --------------------------------------------------------- zapping bar
        Row(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(start = 24.dp, end = 24.dp, bottom = 74.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (previousChannel != null) {
                ZappingButton(
                    channel = previousChannel,
                    label = strings.previousChannel,
                    isRtl = true,
                    onClick = { onOpenChannel(previousChannel) }
                )
            } else {
                Spacer(Modifier.width(1.dp))
            }
            if (nextChannel != null) {
                ZappingButton(
                    channel = nextChannel,
                    label = strings.nextChannel,
                    isRtl = false,
                    onClick = { onOpenChannel(nextChannel) }
                )
            }
        }
    }
}

@Composable
private fun ZappingButton(
    channel: Channel,
    label: String,
    isRtl: Boolean,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .background(Color.Black.copy(alpha = 0.55f), RoundedCornerShape(50))
            .padding(horizontal = 4.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (isRtl) {
            IconButton(onClick = onClick) {
                Icon(
                    imageVector = Icons.Filled.KeyboardArrowRight,
                    contentDescription = label,
                    tint = Color.White
                )
            }
        }
        TextButton(onClick = onClick) {
            Text(
                text = channel.nameFor(LocalAppLanguage.current),
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
        if (!isRtl) {
            IconButton(onClick = onClick) {
                Icon(
                    imageVector = Icons.Filled.KeyboardArrowLeft,
                    contentDescription = label,
                    tint = Color.White
                )
            }
        }
    }
}

/** Walks up the context chain to find the hosting activity. */
internal fun Context.findActivity(): Activity? {
    var current: Context? = this
    while (current is ContextWrapper) {
        if (current is Activity) return current
        current = current.baseContext
    }
    return null
}
