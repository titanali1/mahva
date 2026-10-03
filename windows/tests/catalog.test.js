'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const catalogLib = require('../src/catalog');
const { Store } = require('../src/store');

const channelsJson = path.join(__dirname, '..', 'assets', 'channels.json');

test('the catalog parses and keeps the four sections', () => {
  const parsed = catalogLib.parseCatalog(JSON.parse(fs.readFileSync(channelsJson, 'utf8')));
  assert.deepStrictEqual(parsed.categories.map((c) => c.id), ['persiana', 'news', 'music', 'sports']);
  assert.ok(parsed.channels.length >= 100, `expected at least 100 channels, got ${parsed.channels.length}`);
});

test('every channel has a https/http HLS url and a known section', () => {
  const parsed = catalogLib.parseCatalog(JSON.parse(fs.readFileSync(channelsJson, 'utf8')));
  const ids = new Set(parsed.categories.map((c) => c.id));
  for (const channel of parsed.channels) {
    assert.ok(/^https?:\/\//.test(channel.url), `${channel.id} has an invalid url`);
    assert.ok(ids.has(channel.category), `${channel.id} has an unknown section`);
    assert.ok(channel.name.length > 0, `${channel.id} has no name`);
  }
  const unique = new Set(parsed.channels.map((c) => c.id));
  assert.strictEqual(unique.size, parsed.channels.length, 'channel ids must be unique');
});

test('the three interface languages are complete', () => {
  const { STRINGS } = require('../src/i18n');
  const languages = Object.keys(STRINGS);
  assert.deepStrictEqual(languages, ['fa', 'en', 'ar']);
  const reference = Object.keys(STRINGS.fa).sort();
  for (const language of languages) {
    assert.deepStrictEqual(Object.keys(STRINGS[language]).sort(), reference, `${language} is out of sync`);
  }
});

test('every translation key used by the UI exists in all three languages', () => {
  const { STRINGS } = require('../src/i18n');
  const source = fs.readFileSync(path.join(__dirname, '..', 'renderer', 'renderer.js'), 'utf8');
  const used = new Set(Array.from(source.matchAll(/t\('([A-Za-z0-9_]+)'/g), (m) => m[1]));
  const html = fs.readFileSync(path.join(__dirname, '..', 'renderer', 'index.html'), 'utf8');
  for (const match of html.matchAll(/data-i18n(?:-title)?="([A-Za-z0-9_]+)"/g)) used.add(match[1]);
  assert.ok(used.size > 50, `expected many keys, found ${used.size}`);
  for (const language of Object.keys(STRINGS)) {
    const missing = Array.from(used).filter((key) => !(key in STRINGS[language]));
    assert.deepStrictEqual(missing, [], `${language} is missing: ${missing.join(', ')}`);
  }
});

test('rtl flags match the languages', () => {
  const { LANGUAGES } = require('../src/i18n');
  assert.strictEqual(LANGUAGES.fa.rtl, true);
  assert.strictEqual(LANGUAGES.ar.rtl, true);
  assert.strictEqual(LANGUAGES.en.rtl, false);
});

test('search finds channels in all three languages', () => {
  const parsed = catalogLib.parseCatalog(JSON.parse(fs.readFileSync(channelsJson, 'utf8')));
  assert.ok(catalogLib.searchChannels(parsed.channels, 'persiana').length > 0);
  assert.ok(catalogLib.searchChannels(parsed.channels, 'پرشیانا').length > 0);
  assert.deepStrictEqual(catalogLib.searchChannels(parsed.channels, ''), []);
});

test('custom channels are merged and flagged', () => {
  const parsed = catalogLib.parseCatalog(JSON.parse(fs.readFileSync(channelsJson, 'utf8')));
  const merged = catalogLib.withCustomChannels(parsed, [
    { id: 'custom-1', name: 'کانال من', url: 'https://example.com/live/index.m3u8', category: 'custom' },
  ]);
  assert.strictEqual(merged.channels[0].id, 'custom-1');
  assert.strictEqual(merged.channels[0].custom, true);
  assert.strictEqual(merged.channels.length, parsed.channels.length + 1);
});

test('the store persists settings, favourites, recents and custom channels', () => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'takht-live-')), 'settings.json');
  const store = new Store(file);
  assert.strictEqual(store.get('language'), 'fa');
  assert.strictEqual(store.get('theme'), 'dark');

  store.setLanguage('ar');
  store.setTheme('light');
  assert.strictEqual(store.toggleFavorite('ch-1'), true);
  assert.strictEqual(store.toggleFavorite('ch-2'), true);
  assert.strictEqual(store.toggleFavorite('ch-1'), false);
  store.markRecent('ch-3');
  store.markRecent('ch-4');
  store.markRecent('ch-3');
  const custom = store.addCustomChannel({ name: '  کانال من  ', url: ' https://example.com/a.m3u8 ' , category: 'news' });

  // reload from disk to prove persistence
  const reloaded = new Store(file);
  assert.strictEqual(reloaded.get('language'), 'ar');
  assert.strictEqual(reloaded.get('theme'), 'light');
  assert.deepStrictEqual(reloaded.get('favorites'), ['ch-2']);
  assert.deepStrictEqual(reloaded.get('recents'), ['ch-3', 'ch-4']);
  assert.strictEqual(reloaded.get('customChannels').length, 1);
  assert.strictEqual(reloaded.get('customChannels')[0].name, 'کانال من');
  assert.strictEqual(reloaded.get('customChannels')[0].url, 'https://example.com/a.m3u8');
  assert.strictEqual(reloaded.get('customChannels')[0].category, 'news');
  assert.strictEqual(custom.custom, true);

  reloaded.removeCustomChannel(custom.id);
  assert.strictEqual(reloaded.get('customChannels').length, 0);
});

test('a corrupt settings file falls back to the defaults', () => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'takht-live-')), 'settings.json');
  fs.writeFileSync(file, '{not json');
  const store = new Store(file);
  assert.strictEqual(store.get('language'), 'fa');
  assert.deepStrictEqual(store.get('favorites'), []);
});
