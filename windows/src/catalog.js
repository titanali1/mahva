/**
 * Channel catalog helpers. Shared by the Electron main process and the
 * renderer (the renderer receives the catalog through the preload bridge).
 */

'use strict';

/** Returns the display name of a channel for a language, with fallbacks. */
function channelName(channel, language) {
  if (language === 'en') return channel.nameEn || channel.name || '';
  if (language === 'ar') return channel.nameAr || channel.name || '';
  return channel.name || '';
}

/** Secondary (latin) name shown under the main title in RTL layouts. */
function channelSubtitle(channel, language) {
  if (language === 'en') return channel.name || '';
  return channel.nameEn || '';
}

function categoryTitle(category, language) {
  if (language === 'en') return category.titleEn || category.title;
  if (language === 'ar') return category.titleAr || category.title;
  return category.title;
}

function categorySubtitle(category, language) {
  if (language === 'en') return category.subtitleEn || category.subtitle;
  if (language === 'ar') return category.subtitleAr || category.subtitle;
  return category.subtitle;
}

/** Case insensitive search across the Persian, English and Arabic names. */
function searchChannels(channels, query) {
  const q = (query || '').trim().toLowerCase();
  if (!q) return [];
  return channels.filter((c) =>
    (c.name || '').toLowerCase().includes(q) ||
    (c.nameEn || '').toLowerCase().includes(q) ||
    (c.nameAr || '').toLowerCase().includes(q) ||
    (c.category || '').toLowerCase().includes(q)
  );
}

/** Validates the catalog read from assets/channels.json. */
function parseCatalog(json) {
  if (!json || !Array.isArray(json.categories) || !Array.isArray(json.channels)) {
    throw new Error('invalid channel catalog');
  }
  const categories = json.categories.filter((c) => c && c.id);
  const knownCategories = new Set(categories.map((c) => c.id));
  const channels = json.channels
    .filter((c) => c && typeof c.url === 'string' && c.url.startsWith('http'))
    .filter((c) => knownCategories.has(c.category))
    .map((c) => ({
      id: String(c.id),
      name: c.name || c.id,
      nameEn: c.nameEn || '',
      nameAr: c.nameAr || '',
      category: c.category,
      logo: c.logo || '',
      url: c.url,
      quality: c.quality || 'HD',
      custom: false,
    }));
  return { categories, channels };
}

/** Adds the user defined channels in front of the built in ones. */
function withCustomChannels(catalog, custom) {
  if (!custom || !custom.length) return catalog;
  const normalized = custom.map((c) => ({
    id: c.id,
    name: c.name,
    nameEn: c.nameEn || '',
    nameAr: c.nameAr || '',
    category: c.category || 'custom',
    logo: c.logo || '',
    url: c.url,
    quality: c.quality || 'LIVE',
    custom: true,
  }));
  const ids = new Set(normalized.map((c) => c.id));
  return {
    categories: catalog.categories,
    channels: normalized.concat(catalog.channels.filter((c) => !ids.has(c.id))),
  };
}

module.exports = {
  channelName,
  channelSubtitle,
  categoryTitle,
  categorySubtitle,
  searchChannels,
  parseCatalog,
  withCustomChannels,
};
