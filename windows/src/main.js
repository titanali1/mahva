/**
 * TakhtLive – Windows desktop app (Electron main process).
 *
 * Windows 11 integration:
 *  - native window controls overlay + rounded corners (titleBarStyle: hidden),
 *    always on the physical right even in RTL layouts
 *  - follows the system theme when the "system" setting is selected
 */

'use strict';

const { app, BrowserWindow, ipcMain, shell, nativeTheme, dialog } = require('electron');
const fs = require('fs');
const path = require('path');

const { Store } = require('./store');
const catalogLib = require('./catalog');

const isWindows = process.platform === 'win32';
let mainWindow = null;
let store = null;
let catalog = null;

function assetsPath(...parts) {
  // packaged: resources/app.asar/assets, development: windows/assets
  return path.join(__dirname, '..', 'assets', ...parts);
}

function loadCatalog() {
  const file = assetsPath('channels.json');
  const json = JSON.parse(fs.readFileSync(file, 'utf8'));
  const parsed = catalogLib.parseCatalog(json);
  return { categories: parsed.categories, channels: parsed.channels, raw: json };
}

/** Snapshot of everything the renderer needs to draw the UI. */
function stateForRenderer() {
  const merged = catalogLib.withCustomChannels(catalog, store.get('customChannels'));
  return {
    categories: merged.categories,
    channels: merged.channels,
    favorites: store.get('favorites'),
    recents: store.get('recents'),
    language: store.get('language'),
    theme: store.get('theme'),
    version: app.getVersion(),
    platform: process.platform,
  };
}

function applyThemeToWindow(mode) {
  if (!mainWindow) return;
  const dark = mode === 'dark' || (mode === 'system' && nativeTheme.shouldUseDarkColors);
  mainWindow.setBackgroundColor(dark ? '#0B0B14' : '#F7F6FC');

  const overlay = {
    color: dark ? '#0B0B14' : '#F7F6FC',
    symbolColor: dark ? '#EDEAF7' : '#17162B',
    height: 42,
  };
  if (isWindows && typeof mainWindow.setTitleBarOverlay === 'function') {
    try {
      mainWindow.setTitleBarOverlay(overlay);
    } catch (err) {
      /* not supported before Windows 10 1809 */
    }
  }
}

function createWindow() {
  const mode = store.get('theme');
  const dark = mode === 'dark' || (mode === 'system' && nativeTheme.shouldUseDarkColors);

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 900,
    minHeight: 600,
    show: false,
    backgroundColor: dark ? '#0B0B14' : '#F7F6FC',
    title: 'TakhtLive',
    icon: assetsPath('icon-256.png'),
    autoHideMenuBar: true,
    // Windows 11 style: rounded window with native controls drawn over our title bar
    ...(isWindows
      ? {
          titleBarStyle: 'hidden',
          titleBarOverlay: {
            color: dark ? '#0B0B14' : '#F7F6FC',
            symbolColor: dark ? '#EDEAF7' : '#17162B',
            height: 42,
          },
        }
      : {}),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      backgroundThrottling: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    applyThemeToWindow(store.get('theme'));
  });

  // External links open in the default browser instead of inside the app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ---------------------------------------------------------------------- IPC

function registerIpc() {
  ipcMain.handle('app:state', () => stateForRenderer());

  ipcMain.handle('settings:setLanguage', (_event, code) => {
    store.setLanguage(code);
    return stateForRenderer();
  });

  ipcMain.handle('settings:setTheme', (_event, mode) => {
    store.setTheme(mode);
    applyThemeToWindow(mode);
    return stateForRenderer();
  });

  ipcMain.handle('favorites:toggle', (_event, id) => {
    const isFavorite = store.toggleFavorite(id);
    return { id, isFavorite, favorites: store.get('favorites') };
  });

  ipcMain.handle('recents:mark', (_event, id) => store.markRecent(id));

  ipcMain.handle('channels:add', (_event, payload) => {
    const channel = store.addCustomChannel(payload || {});
    return { channel, state: stateForRenderer() };
  });

  ipcMain.handle('channels:remove', (_event, id) => {
    store.removeCustomChannel(id);
    return stateForRenderer();
  });

  ipcMain.handle('player:openExternal', async (_event, url) => {
    if (typeof url !== 'string' || !url.startsWith('http')) return false;
    await shell.openExternal(url);
    return true;
  });

  ipcMain.handle('link:copy', (_event, url) => {
    if (typeof url !== 'string' || !url.startsWith('http')) return false;
    require('electron').clipboard.writeText(url);
    return true;
  });

  ipcMain.handle('window:toggleFullscreen', () => {
    if (!mainWindow) return false;
    mainWindow.setFullScreen(!mainWindow.isFullScreen());
    return mainWindow.isFullScreen();
  });

  ipcMain.handle('app:info', () => ({
    version: app.getVersion(),
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    platform: process.platform,
    arch: process.arch,
    windowsBuild: isWindows ? require('os').release() : '',
  }));
}

// -------------------------------------------------------------------- life cycle

const singleInstance = app.requestSingleInstanceLock();
if (!singleInstance) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    app.setAppUserModelId('ir.takhtlive.tv');
    store = new Store(path.join(app.getPath('userData'), 'takhtlive-settings.json'));
    try {
      catalog = loadCatalog();
    } catch (err) {
      dialog.showErrorBox('TakhtLive', `Could not read the channel list:\n${err.message}`);
      catalog = { categories: [], channels: [], raw: {} };
    }

    registerIpc();
    createWindow();

    nativeTheme.on('updated', () => {
      if (store.get('theme') === 'system') {
        applyThemeToWindow('system');
        if (mainWindow) mainWindow.webContents.send('system:themeChanged', nativeTheme.shouldUseDarkColors);
      }
    });

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
  });
}
