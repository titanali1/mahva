/**
 * Persistent user data of the desktop app (settings, favourites, recents and
 * user defined channels). Stored as a small JSON file in the user data folder,
 * so it survives updates.
 */

'use strict';

const fs = require('fs');
const path = require('path');

const MAX_RECENTS = 20;
const DEFAULTS = {
  language: 'fa',
  theme: 'dark',
  favorites: [],
  recents: [],
  customChannels: [],
};

class Store {
  constructor(filePath) {
    this.filePath = filePath;
    this.data = Object.assign({}, DEFAULTS);
    this.load();
  }

  load() {
    try {
      const raw = fs.readFileSync(this.filePath, 'utf8');
      const parsed = JSON.parse(raw);
      this.data = Object.assign({}, DEFAULTS, parsed);
      if (!Array.isArray(this.data.favorites)) this.data.favorites = [];
      if (!Array.isArray(this.data.recents)) this.data.recents = [];
      if (!Array.isArray(this.data.customChannels)) this.data.customChannels = [];
    } catch (err) {
      // first run (or a corrupt file): start from the defaults
      this.data = Object.assign({}, DEFAULTS);
    }
    return this.data;
  }

  save() {
    try {
      fs.mkdirSync(path.dirname(this.filePath), { recursive: true });
      fs.writeFileSync(this.filePath, JSON.stringify(this.data, null, 2), 'utf8');
    } catch (err) {
      console.error('could not save settings:', err.message);
    }
  }

  // ------------------------------------------------------------------ setters

  get(key) {
    return this.data[key];
  }

  set(key, value) {
    this.data[key] = value;
    this.save();
    return value;
  }

  setLanguage(code) {
    return this.set('language', code);
  }

  setTheme(mode) {
    return this.set('theme', mode);
  }

  // ---------------------------------------------------------------- favourites

  isFavorite(id) {
    return this.data.favorites.includes(id);
  }

  /** Returns the new state of the favourite flag. */
  toggleFavorite(id) {
    const favorites = new Set(this.data.favorites);
    if (favorites.has(id)) favorites.delete(id);
    else favorites.add(id);
    this.set('favorites', Array.from(favorites));
    return favorites.has(id);
  }

  // ------------------------------------------------------------------- recents

  markRecent(id) {
    const recents = [id].concat(this.data.recents.filter((x) => x !== id)).slice(0, MAX_RECENTS);
    this.set('recents', recents);
    return recents;
  }

  // ----------------------------------------------------------- custom channels

  addCustomChannel({ name, url, category }) {
    const channel = {
      id: `custom-${Date.now()}`,
      name: (name || '').trim() || 'کانال من',
      nameEn: '',
      nameAr: '',
      category: category || 'custom',
      logo: '',
      url: (url || '').trim(),
      quality: 'LIVE',
      custom: true,
    };
    this.set('customChannels', this.data.customChannels.concat([channel]));
    return channel;
  }

  removeCustomChannel(id) {
    this.set('customChannels', this.data.customChannels.filter((c) => c.id !== id));
  }
}

module.exports = { Store, DEFAULTS, MAX_RECENTS };
