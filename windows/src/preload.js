/**
 * Bridge between the Electron main process and the renderer.
 * The renderer never talks to Node directly (context isolation stays on).
 */

'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('takhtLive', {
  isDesktop: true,

  /** Everything the UI needs to render (catalog + user data). */
  getState: () => ipcRenderer.invoke('app:state'),
  getAppInfo: () => ipcRenderer.invoke('app:info'),

  setLanguage: (code) => ipcRenderer.invoke('settings:setLanguage', code),
  setTheme: (mode) => ipcRenderer.invoke('settings:setTheme', mode),

  toggleFavorite: (id) => ipcRenderer.invoke('favorites:toggle', id),
  markRecent: (id) => ipcRenderer.invoke('recents:mark', id),

  addChannel: (payload) => ipcRenderer.invoke('channels:add', payload),
  removeChannel: (id) => ipcRenderer.invoke('channels:remove', id),

  openExternal: (url) => ipcRenderer.invoke('player:openExternal', url),
  copyLink: (url) => ipcRenderer.invoke('link:copy', url),
  toggleFullscreen: () => ipcRenderer.invoke('window:toggleFullscreen'),

  onSystemThemeChanged: (callback) => {
    const listener = (_event, isDark) => callback(isDark);
    ipcRenderer.on('system:themeChanged', listener);
    return () => ipcRenderer.removeListener('system:themeChanged', listener);
  },
});
