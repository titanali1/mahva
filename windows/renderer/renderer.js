/**
 * TakhtLive – renderer (UI) logic.
 *
 * Runs inside Electron through the `takhtLive` preload bridge. When no bridge is
 * available (plain browser / screenshot test) it falls back to an in-memory
 * store, so the very same UI can be rendered outside Electron.
 */

'use strict';

(function () {
  const LANGUAGES = {
    fa: { code: 'fa', label: 'فارسی', rtl: true },
    en: { code: 'en', label: 'English', rtl: false },
    ar: { code: 'ar', label: 'العربية', rtl: true },
  };
  const THEME_MODES = ['dark', 'light', 'system'];

  const STRINGS = window.TAKHT_STRINGS || {};

  const $ = (id) => document.getElementById(id);

  // ---------------------------------------------------------------- icon set
  // Inline SVG icons (Fluent-like) instead of emoji: emoji fonts are not
  // guaranteed to exist on every Windows or CI installation.
  function svg(paths, size = 18) {
    return `<svg class="icon" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none"
      stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"
      aria-hidden="true">${paths}</svg>`;
  }

  const ICONS = {
    search: '<circle cx="11" cy="11" r="6.6"/><path d="m16 16 4 4"/>',
    heart: '<path d="M12 20.2s-7.2-4.5-7.2-9.6A4.2 4.2 0 0 1 12 7.6a4.2 4.2 0 0 1 7.2 3c0 5.1-7.2 9.6-7.2 9.6Z"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    home: '<path d="M4 10.7 12 4l8 6.7V19a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H5.5A1.5 1.5 0 0 1 4 19z"/>',
    tv: '<rect x="3" y="5" width="18" height="13" rx="2.5"/><path d="M8.5 21h7M12 18v3"/>',
    news: '<path d="M4 5h13v14.5H5.5A1.5 1.5 0 0 1 4 18z"/><path d="M17 8h3v9.5A2.5 2.5 0 0 1 17.5 20M7 9h7M7 12.5h7M7 16h4"/>',
    music: '<path d="M9.5 17.5V6l9-1.8v11.3"/><circle cx="7" cy="17.6" r="2.5"/><circle cx="16.5" cy="15.5" r="2.4"/>',
    sports: '<circle cx="12" cy="12" r="8.4"/><path d="m12 7.8 3.7 2.7-1.4 4.4H9.7L8.3 10.5z"/>',
    star: '<path d="m12 4.2 2.3 4.7 5.2.8-3.8 3.6.9 5.2-4.6-2.5-4.6 2.5.9-5.2-3.8-3.6 5.2-.8z"/>',
    trash: '<path d="M4.5 7h15M9.5 7V4.8h5V7M6.5 7l1 13h9l1-13"/>',
    copy: '<rect x="9" y="9" width="11" height="11" rx="2.4"/><path d="M15 6.5H6.4A2.4 2.4 0 0 0 4 8.9V15"/>',
    pip: '<rect x="3" y="5" width="18" height="14" rx="2.4"/><rect x="12" y="12" width="6.6" height="4.6" rx="1.2"/>',
    fullscreen: '<path d="M4 9V4.5h4.5M20 9V4.5h-4.5M4 15v4.5h4.5M20 15v4.5h-4.5"/>',
    back: '<path d="M14.5 6 8.5 12l6 6"/>',
    more: '<circle cx="12" cy="6" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="12" cy="18" r="1.4"/>',
    sparkle: '<path d="M12 4.5 13.7 9l4.5 1.7-4.5 1.7L12 17l-1.7-4.6L5.8 10.7 10.3 9z"/>',
  };

  const CATEGORY_ICON = { persiana: 'tv', news: 'news', music: 'music', sports: 'sports', custom: 'star' };
  const iconFor = (name, size) => svg(ICONS[name] || ICONS.tv, size);
  const categoryIcon = (category, size) => iconFor(CATEGORY_ICON[category && category.id] || 'tv', size);

  // ------------------------------------------------------------------ state

  const state = {
    categories: [],
    channels: [],
    favorites: [],
    recents: [],
    language: 'fa',
    theme: 'dark',
    version: '1.0.0',
    view: { name: 'home', categoryId: null, query: '' },
    player: { channelId: null, mode: 'fit', attempts: 0 },
    pendingCategory: 'custom',
  };

  let bridge = window.takhtLive || null;
  if (!bridge) {
    // plain browser (screenshot tooling / preview): in-memory fallback store
    bridge = createFallbackBridge();
    window.takhtLive = bridge;
  }

  // ------------------------------------------------------------------ helpers

  function strings() {
    const table = STRINGS[state.language] || STRINGS.fa || {};
    return table;
  }

  function t(key, ...args) {
    const value = strings()[key];
    if (typeof value === 'function') return value(...args);
    if (value === undefined) return key;
    return value;
  }

  function channelName(channel) {
    if (!channel) return '';
    if (state.language === 'en') return channel.nameEn || channel.name || '';
    if (state.language === 'ar') return channel.nameAr || channel.name || '';
    return channel.name || '';
  }

  function channelSubtitle(channel) {
    if (!channel) return '';
    return state.language === 'en' ? (channel.name || '') : (channel.nameEn || '');
  }

  function categoryTitle(category) {
    if (!category) return '';
    if (state.language === 'en') return category.titleEn || category.title;
    if (state.language === 'ar') return category.titleAr || category.title;
    return category.title;
  }

  function categorySubtitle(category) {
    if (!category) return '';
    if (state.language === 'en') return category.subtitleEn || category.subtitle;
    if (state.language === 'ar') return category.subtitleAr || category.subtitle;
    return category.subtitle;
  }

  function categoriesWithCustom() {
    const cats = state.categories.slice();
    if (state.channels.some((c) => c.category === 'custom') &&
        !cats.some((c) => c.id === 'custom')) {
      cats.push({
        id: 'custom',
        title: 'کانال‌های من',
        titleEn: 'My channels',
        titleAr: 'قنواتي',
        subtitle: 'کانال‌های افزوده‌شده توسط شما',
        subtitleEn: 'Channels you added',
        subtitleAr: 'القنوات التي أضفتها',
        emoji: '⭐',
        color: '#7C4DFF',
      });
    }
    return cats;
  }

  const channelsOf = (categoryId) => state.channels.filter((c) => c.category === categoryId);
  const channelById = (id) => state.channels.find((c) => c.id === id) || null;

  function search(query) {
    const q = (query || '').trim().toLowerCase();
    if (!q) return [];
    return state.channels.filter((c) =>
      (c.name || '').toLowerCase().includes(q) ||
      (c.nameEn || '').toLowerCase().includes(q) ||
      (c.nameAr || '').toLowerCase().includes(q)
    );
  }

  const FALLBACK_LOGO = '../assets/icon-192.png';

  function logoImg(channel, className) {
    const src = channel.logo ? channel.logo : FALLBACK_LOGO;
    return `<img class="${className}" src="${escapeAttr(src)}" alt="" loading="lazy" />`;
  }

  /**
   * Replaces logos that cannot be loaded (offline, blocked CDN, dead link) with
   * the bundled app icon. Uses a capturing listener because `error` does not
   * bubble and inline handlers are forbidden by the app's Content-Security-Policy.
   */
  function wireLogoFallbacks() {
    window.addEventListener('error', (event) => {
      const target = event.target;
      if (!target || target.tagName !== 'IMG' || target.dataset.fallback === 'true') return;
      target.dataset.fallback = 'true';
      target.src = FALLBACK_LOGO;
    }, true);
  }

  function escapeAttr(value) {
    return String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  let toastTimer = null;
  function toast(message) {
    const el = $('toast');
    el.textContent = message;
    el.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.add('hidden'), 1800);
  }

  // ------------------------------------------------------------------- chrome

  function applyLanguageChrome() {
    const info = LANGUAGES[state.language] || LANGUAGES.fa;
    document.body.setAttribute('dir', info.rtl ? 'rtl' : 'ltr');
    document.documentElement.setAttribute('lang', info.code);
    $('app-name').textContent = t('appName');
    $('app-tagline').textContent = t('tagline');
    $('drawer-app-name').textContent = t('appName');
    $('drawer-tagline').textContent = t('tagline');
    $('drawer-sections-label').textContent = t('sections');
    $('drawer-settings-label').textContent = t('settings');
    $('drawer-about-label').textContent = t('about');
    $('about-line').textContent = `${t('appName')} — ${t('version', state.version)}`;
    $('signature-bar').textContent = `${t('signaturePrefix')} ${t('signature')}`;
    $('btn-search').innerHTML = iconFor('search', 18);
    $('btn-library').innerHTML = iconFor('heart', 18);
    $('btn-add').innerHTML = iconFor('plus', 18);
    $('btn-menu').innerHTML = iconFor('menu', 18);
    $('player-back').innerHTML = iconFor('back', 20);
    $('player-copy').innerHTML = iconFor('copy', 18);
    $('player-pip').innerHTML = iconFor('pip', 18);
    $('player-fullscreen').innerHTML = iconFor('fullscreen', 18);
    $('player-menu-btn').innerHTML = iconFor('more', 18);
    $('player-fav').innerHTML = iconFor('heart', 18);
    $('drawer-signature').textContent = `✦ ${t('signaturePrefix')} ${t('signature')} ✦`;
    $('dialog-title').textContent = t('addChannelTitle') || t('addChannel');
    $('dialog-hint').textContent = t('addChannelUrlHint');
    $('dialog-cancel').textContent = t('cancel');
    $('dialog-confirm').textContent = t('add');
    $('player-live').textContent = t('live');
    $('player-retry').textContent = t('retry');
    $('player-back2').textContent = t('backToList');
    $('player-external').textContent = t('playWithExternal');
    $('zap-prev-label').textContent = t('previousChannel');
    $('zap-next-label').textContent = t('nextChannel');

    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      el.textContent = t(key);
    });
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
  }

  function applyTheme() {
    let mode = state.theme;
    if (mode === 'system') {
      const prefersLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
      mode = prefersLight ? 'light' : 'dark';
    }
    document.body.setAttribute('data-theme', mode);
  }

  function renderDrawer() {
    const nav = $('drawer-sections');
    const currentSection = state.view.name === 'category' ? state.view.categoryId : (state.view.name === 'home' ? 'home' : '');

    const homeItem = `<button class="drawer__item ${currentSection === 'home' ? 'is-active' : ''}"
        data-section="home"><span class="drawer__icon">${iconFor('home', 19)}</span><span>${escapeHtml(t('tabHome'))}</span></button>`;

    const sectionItems = categoriesWithCustom().map((category) => {
      const count = channelsOf(category.id).length;
      return `<button class="drawer__item ${currentSection === category.id ? 'is-active' : ''}"
          data-section="${escapeAttr(category.id)}">
          <span class="drawer__icon">${categoryIcon(category, 19)}</span>
          <span>${escapeHtml(categoryTitle(category))}</span>
          <span class="drawer__count">${escapeHtml(t('channels', count))}</span>
        </button>`;
    }).join('');

    nav.innerHTML = homeItem + sectionItems;

    const chips = $('language-chips');
    chips.innerHTML = Object.values(LANGUAGES).map((lang) =>
      `<button class="chip ${state.language === lang.code ? 'is-selected' : ''}"
        data-language="${lang.code}">${escapeHtml(lang.label)}</button>`).join('');

    const themeLabels = { dark: t('themeDark'), light: t('themeLight'), system: t('themeSystem') };
    $('theme-chips').innerHTML = THEME_MODES.map((mode) =>
      `<button class="chip ${state.theme === mode ? 'is-selected' : ''}"
        data-theme="${mode}">${escapeHtml(themeLabels[mode])}</button>`).join('');
  }

  // -------------------------------------------------------------------- views

  function render() {
    applyLanguageChrome();
    applyTheme();
    renderDrawer();

    const content = $('content');
    if (state.view.name === 'home') content.innerHTML = viewHome();
    else if (state.view.name === 'category') content.innerHTML = viewCategory();
    else if (state.view.name === 'search') content.innerHTML = viewSearch();
    else if (state.view.name === 'library') content.innerHTML = viewLibrary();
  }

  function channelCard(channel, withDelete) {
    const deleteButton = withDelete
      ? `<button class="channel-card__delete" data-delete="${escapeAttr(channel.id)}" title="${escapeAttr(t('delete'))}">${iconFor('trash', 15)}</button>`
      : '';
    return `<article class="channel-card" data-channel="${escapeAttr(channel.id)}">
        ${deleteButton}
        ${logoImg(channel, 'channel-card__logo')}
        <span class="channel-card__name">${escapeHtml(channelName(channel))}</span>
        <span class="channel-card__sub">${escapeHtml(channelSubtitle(channel))}</span>
        <span class="channel-card__row">
          <span class="quality">${escapeHtml(channel.quality)}</span>
          <span class="badge">${escapeHtml(t('live'))}</span>
        </span>
      </article>`;
  }

  function channelRail(channels) {
    if (!channels.length) return '';
    return `<div class="rail">${channels.map((c) => `
      <button class="card" data-channel="${escapeAttr(c.id)}">
        ${logoImg(c, 'card__logo')}
        <span class="card__name">${escapeHtml(channelName(c))}</span>
      </button>`).join('')}</div>`;
  }

  function viewHome() {
    const favorites = state.channels.filter((c) => state.favorites.includes(c.id));
    const recents = state.recents.map(channelById).filter(Boolean);

    const tiles = categoriesWithCustom().map((category) => {
      const accent = category.color || '#7C4DFF';
      return `<button class="tile" data-section="${escapeAttr(category.id)}"
          style="background: linear-gradient(135deg, ${escapeAttr(accent)}, ${escapeAttr(accent)}55)">
          <span class="tile__emoji">${categoryIcon(category, 22)}</span>
          <span>
            <span class="tile__title">${escapeHtml(categoryTitle(category))}</span><br />
            <span class="tile__sub">${escapeHtml(t('channels', channelsOf(category.id).length))}</span>
          </span>
        </button>`;
    }).join('');

    const sections = categoriesWithCustom().map((category) => {
      const channels = channelsOf(category.id);
      if (!channels.length) return '';
      return `<div class="section-head"><h2>${categoryIcon(category, 17)} ${escapeHtml(categoryTitle(category))}</h2>
          <span>${escapeHtml(t('channels', channels.length))}</span></div>
        ${channelRail(channels.slice(0, 14))}
        <button class="see-all" data-section="${escapeAttr(category.id)}">${escapeHtml(t('seeAll', categoryTitle(category)))}</button>`;
    }).join('');

    return `
      <section class="hero">
        <h1>${escapeHtml(t('appName'))}</h1>
        <p>${escapeHtml(t('heroSubtitle'))}</p>
        <span class="badge">${escapeHtml(t('liveChannels', state.channels.length))}</span>
      </section>

      <div class="section-head"><h2>${escapeHtml(t('quickAccess'))}</h2>
        <span>${escapeHtml(t('sectionsCount', categoriesWithCustom().length))}</span></div>
      <div class="tiles">
        ${tiles}
        <button class="tile tile--ghost" data-action="add">
          <span>
            <span class="tile__title">${iconFor('plus', 16)} ${escapeHtml(t('addChannel'))}</span><br />
            <span class="tile__sub">${escapeHtml(t('noChannelsYetHint'))}</span>
          </span>
        </button>
      </div>

      ${favorites.length ? `<div class="section-head"><h2>${escapeHtml(t('favourites'))}</h2>
        <span>${escapeHtml(t('channels', favorites.length))}</span></div>${channelRail(favorites)}` : ''}

      ${recents.length ? `<div class="section-head"><h2>${escapeHtml(t('recentlyWatched'))}</h2></div>${channelRail(recents)}` : ''}

      ${sections}`;
  }

  function viewCategory() {
    const category = categoriesWithCustom().find((c) => c.id === state.view.categoryId);
    if (!category) return `<div class="empty"><h3>${escapeHtml(t('noChannelFound'))}</h3></div>`;
    const query = state.view.query || '';
    const all = channelsOf(category.id);
    const visible = query
      ? all.filter((c) => channelName(c).toLowerCase().includes(query.toLowerCase()) ||
          (c.nameEn || '').toLowerCase().includes(query.toLowerCase()))
      : all;

    const grid = visible.length
      ? `<div class="grid">${visible.map((c) => channelCard(c, c.custom)).join('')}</div>`
      : `<div class="empty"><h3>${escapeHtml(t('noChannelFound'))}</h3><p>${escapeHtml(t('noChannelFoundHint'))}</p></div>`;

    return `
      <div class="page-head">
        <span class="page-head__icon">${categoryIcon(category, 30)}</span>
        <div>
          <h1>${escapeHtml(categoryTitle(category))}</h1>
          <p>${escapeHtml(categorySubtitle(category))}</p>
        </div>
      </div>
      <div class="toolbar">
        <input id="section-search" class="search-input" type="search"
          placeholder="${escapeAttr(t('searchIn', categoryTitle(category)))}" value="${escapeAttr(query)}" />
      </div>
      ${grid}`;
  }

  function viewSearch() {
    const query = state.view.query || '';
    const results = search(query);
    const body = !query
      ? `<div class="empty"><h3>${escapeHtml(t('searchTitle', state.channels.length))}</h3>
           <p>${escapeHtml(t('searchSubtitle'))}</p></div>`
      : (results.length
        ? `<div class="grid">${results.map((c) => channelCard(c, false)).join('')}</div>`
        : `<div class="empty"><h3>${escapeHtml(t('noResults'))}</h3><p>${escapeHtml(t('noResultsHint'))}</p></div>`);

    return `
      <div class="page-head"><h1>${escapeHtml(t('search'))}</h1></div>
      <div class="toolbar">
        <input id="global-search" class="search-input" type="search" autofocus
          placeholder="${escapeAttr(t('searchPlaceholder'))}" value="${escapeAttr(query)}" />
      </div>
      ${body}`;
  }

  function viewLibrary() {
    const custom = state.channels.filter((c) => c.custom);
    const favorites = state.channels.filter((c) => state.favorites.includes(c.id));
    const recents = state.recents.map(channelById).filter(Boolean);

    const group = (title, channels, withDelete) => {
      if (!channels.length) return '';
      return `<div class="section-head"><h2>${escapeHtml(title)}</h2>
          <span>${escapeHtml(t('channels', channels.length))}</span></div>
        ${channels.map((c) => `
          <div class="row-item" data-channel="${escapeAttr(c.id)}">
            ${logoImg(c, 'row-item__logo')}
            <div class="row-item__text">
              <span class="row-item__name">${escapeHtml(channelName(c))}</span>
              <span class="row-item__sub">${escapeHtml(channelSubtitle(c))}</span>
            </div>
            <span class="quality">${escapeHtml(c.quality)}</span>
            <span class="badge">${escapeHtml(t('live'))}</span>
            ${withDelete ? `<button class="icon-btn" data-delete="${escapeAttr(c.id)}" title="${escapeAttr(t('delete'))}">${iconFor('trash', 18)}</button>` : ''}
            <button class="icon-btn ${state.favorites.includes(c.id) ? 'is-active' : ''}"
              data-favorite="${escapeAttr(c.id)}" title="${escapeAttr(t('favourite'))}">${iconFor('heart', 18)}</button>
          </div>`).join('')}`;
    };

    const empty = !custom.length && !favorites.length && !recents.length;

    return `
      <div class="page-head">
        <div>
          <h1>${escapeHtml(t('myChannels'))}</h1>
          <p>${escapeHtml(t('myChannelsSubtitle'))}</p>
        </div>
      </div>
      <div class="toolbar"><button class="btn btn--primary" data-action="add">${iconFor('plus', 16)} ${escapeHtml(t('addNewChannel'))}</button></div>
      ${empty ? `<div class="empty"><h3>${escapeHtml(t('noChannelsYet'))}</h3><p>${escapeHtml(t('noChannelsYetHint'))}</p></div>` : ''}
      ${group(t('addedChannels'), custom, true)}
      ${group(t('favourites'), favorites, false)}
      ${group(t('recentlyWatched'), recents, false)}`;
  }

  // ------------------------------------------------------------------- player

  let hls = null;

  function openPlayer(channelId) {
    const channel = channelById(channelId);
    if (!channel) return;
    state.player.channelId = channelId;
    state.player.attempts = 0;
    state.player.mode = 'fit';

    $('player').classList.remove('hidden');
    $('player-title').textContent = channelName(channel);
    const category = state.categories.find((c) => c.id === channel.category);
    $('player-category').textContent = category ? categoryTitle(category) : '';
    $('player-logo').src = channel.logo || '../assets/icon-192.png';
    updatePlayerFavorite();
    updateZapping();

    startPlayback(channel);
    bridge.markRecent(channel.id).then((recents) => {
      state.recents = recents || state.recents;
      renderDrawer();
    });
  }

  function startPlayback(channel) {
    const video = $('video');
    showPlayerStatus(t('connecting'));
    video.classList.remove('zoom', 'stretch');

    if (hls) { try { hls.destroy(); } catch (err) { /* ignore */ } hls = null; }

    if (window.Hls && window.Hls.isSupported()) {
      hls = new window.Hls({
        lowLatencyMode: false,
        liveDurationInfinity: true,
        manifestLoadingMaxRetry: 4,
        levelLoadingMaxRetry: 4,
        fragLoadingMaxRetry: 6,
        manifestLoadingRetryDelay: 800,
      });
      hls.on(window.Hls.Events.ERROR, (_evt, data) => {
        if (!data || !data.fatal) return;
        handlePlaybackProblem(data.details || data.type);
      });
      hls.loadSource(channel.url);
      hls.attachMedia(video);
      hls.on(window.Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => { /* autoplay might need a click */ });
      });
    } else {
      // Safari-style fallback (also used when hls.js is unavailable)
      video.src = channel.url;
      video.play().catch(() => { /* ignore */ });
    }

    video.onplaying = () => hidePlayerStatus();
    video.onwaiting = () => showPlayerStatus(t('reconnecting'));
    video.onerror = () => handlePlaybackProblem('media');
  }

  const MAX_RETRIES = 6;

  function handlePlaybackProblem(details) {
    if (state.player.attempts < MAX_RETRIES) {
      state.player.attempts += 1;
      showPlayerStatus(t('reconnecting'));
      setTimeout(() => {
        const channel = channelById(state.player.channelId);
        if (channel && !$('player').classList.contains('hidden')) startPlayback(channel);
      }, Math.min(1000 * state.player.attempts, 6000));
      return;
    }
    showPlayerError(details ? `${t('connectionFailed')} (${details})` : t('connectionFailed'));
  }

  function showPlayerStatus(text) {
    $('player-error').classList.add('hidden');
    $('player-status').classList.remove('hidden');
    $('player-status-text').textContent = text;
  }

  function hidePlayerStatus() {
    $('player-status').classList.add('hidden');
    $('player-error').classList.add('hidden');
  }

  function showPlayerError(message) {
    $('player-status').classList.add('hidden');
    $('player-error').classList.remove('hidden');
    $('player-error-text').textContent = message;
  }

  function closePlayer() {
    if (hls) { try { hls.destroy(); } catch (err) { /* ignore */ } hls = null; }
    const video = $('video');
    video.pause();
    video.removeAttribute('src');
    video.load();
    $('player').classList.add('hidden');
    state.player.channelId = null;
    render();
  }

  function updatePlayerFavorite() {
    const channel = channelById(state.player.channelId);
    const button = $('player-fav');
    if (!channel) return;
    button.classList.toggle('is-active', state.favorites.includes(channel.id));
    button.style.color = state.favorites.includes(channel.id) ? 'var(--pink)' : '#fff';
  }

  function playerSiblings() {
    const channel = channelById(state.player.channelId);
    if (!channel) return [];
    const list = channelsOf(channel.category);
    return list.length ? list : state.channels;
  }

  function updateZapping() {
    const siblings = playerSiblings();
    const index = siblings.findIndex((c) => c.id === state.player.channelId);
    const previous = index > 0 ? siblings[index - 1] : null;
    const next = index >= 0 && index < siblings.length - 1 ? siblings[index + 1] : null;
    $('zap-prev').classList.toggle('hidden', !previous);
    $('zap-next').classList.toggle('hidden', !next);
    if (previous) $('zap-prev-label').textContent = channelName(previous);
    if (next) $('zap-next-label').textContent = channelName(next);
  }

  function zap(direction) {
    const siblings = playerSiblings();
    const index = siblings.findIndex((c) => c.id === state.player.channelId);
    const target = siblings[index + direction];
    if (target) openPlayer(target.id);
  }

  function renderPlayerMenu() {
    const items = [
      ['fit', t('originalSize')],
      ['zoom', t('zoomToFill')],
      ['stretch', t('stretchToFill')],
      ['external', t('playWithExternal')],
      ['pip', t('pictureInPicture')],
      ['copy', t('copyLink')],
      ['fullscreen', t('fullscreen')],
    ];
    $('player-menu').innerHTML = items.map(([action, label]) =>
      `<button data-player-action="${action}"
        class="${state.player.mode === action ? 'is-selected' : ''}">${escapeHtml(label)}</button>`).join('');
  }

  // ------------------------------------------------------------------- dialog

  function openDialog() {
    $('dialog').classList.remove('hidden');
    $('dialog-name').value = '';
    $('dialog-url').value = '';
    $('dialog-error').classList.add('hidden');
    state.pendingCategory = 'custom';

    const cats = categoriesWithCustom().filter((c) => c.id !== 'custom');
    const chips = cats.map((c) =>
      `<button class="chip" data-dialog-section="${escapeAttr(c.id)}">${categoryIcon(c, 15)} ${escapeHtml(categoryTitle(c))}</button>`).join('') +
      `<button class="chip is-selected" data-dialog-section="custom">${iconFor('star', 15)} ${escapeHtml(t('noSection'))}</button>`;
    $('dialog-sections').innerHTML = chips;
    $('dialog-name').focus();
  }

  function closeDialog() {
    $('dialog').classList.add('hidden');
  }

  async function confirmDialog() {
    const name = $('dialog-name').value.trim();
    const url = $('dialog-url').value.trim();
    const error = $('dialog-error');

    if (!name) {
      error.textContent = t('nameRequired') || 'نام کانال را وارد کنید.';
      error.classList.remove('hidden');
      return;
    }
    if (!/^https?:\/\//i.test(url)) {
      error.textContent = t('urlMustStart');
      error.classList.remove('hidden');
      return;
    }

    const result = await bridge.addChannel({ name, url, category: state.pendingCategory });
    if (result && result.state) applyState(result.state);
    closeDialog();
    state.view = state.pendingCategory === 'custom'
      ? { name: 'library', categoryId: null, query: '' }
      : { name: 'category', categoryId: state.pendingCategory, query: '' };
    render();
  }

  // ------------------------------------------------------------------- events

  function applyState(next) {
    if (!next) return;
    state.categories = next.categories || state.categories;
    state.channels = next.channels || state.channels;
    state.favorites = next.favorites || state.favorites;
    state.recents = next.recents || state.recents;
    if (next.language) state.language = next.language;
    if (next.theme) state.theme = next.theme;
    if (next.version) state.version = next.version;
  }

  function bindEvents() {
    // window buttons
    $('btn-menu').addEventListener('click', () => $('drawer').classList.toggle('collapsed'));
    $('btn-search').addEventListener('click', () => { state.view = { name: 'search', categoryId: null, query: '' }; render(); });
    $('btn-library').addEventListener('click', () => { state.view = { name: 'library', categoryId: null, query: '' }; render(); });
    $('btn-add').addEventListener('click', openDialog);

    // drawer: sections + actions
    $('drawer').addEventListener('click', (event) => {
      const section = event.target.closest('[data-section]');
      if (section) {
        const id = section.getAttribute('data-section');
        state.view = id === 'home'
          ? { name: 'home', categoryId: null, query: '' }
          : { name: 'category', categoryId: id, query: '' };
        render();
        return;
      }
      const action = event.target.closest('[data-action]');
      if (action) {
        const name = action.getAttribute('data-action');
        if (name === 'add') openDialog();
        else { state.view = { name, categoryId: null, query: '' }; render(); }
        return;
      }
      const language = event.target.closest('[data-language]');
      if (language) {
        bridge.setLanguage(language.getAttribute('data-language')).then((next) => { applyState(next); render(); });
        return;
      }
      const theme = event.target.closest('[data-theme]');
      if (theme) {
        bridge.setTheme(theme.getAttribute('data-theme')).then((next) => { applyState(next); render(); });
      }
    });

    // content: channels, sections, favourites, delete
    $('content').addEventListener('click', async (event) => {
      const remove = event.target.closest('[data-delete]');
      if (remove) {
        event.stopPropagation();
        const next = await bridge.removeChannel(remove.getAttribute('data-delete'));
        applyState(next);
        render();
        return;
      }
      const favorite = event.target.closest('[data-favorite]');
      if (favorite) {
        event.stopPropagation();
        const result = await bridge.toggleFavorite(favorite.getAttribute('data-favorite'));
        if (result) state.favorites = result.favorites;
        render();
        return;
      }
      const channelEl = event.target.closest('[data-channel]');
      if (channelEl) { openPlayer(channelEl.getAttribute('data-channel')); return; }

      const section = event.target.closest('[data-section]');
      if (section) {
        const id = section.getAttribute('data-section');
        state.view = { name: 'category', categoryId: id, query: '' };
        render();
        return;
      }
      const action = event.target.closest('[data-action]');
      if (action && action.getAttribute('data-action') === 'add') openDialog();
    });

    // live filtering inside a section / the search page
    $('content').addEventListener('input', (event) => {
      if (event.target.id === 'section-search') {
        state.view.query = event.target.value;
        const caret = event.target.selectionStart;
        render();
        const input = $('section-search');
        if (input) { input.focus(); input.setSelectionRange(caret, caret); }
      } else if (event.target.id === 'global-search') {
        state.view.query = event.target.value;
        const caret = event.target.selectionStart;
        render();
        const input = $('global-search');
        if (input) { input.focus(); input.setSelectionRange(caret, caret); }
      }
    });

    // player controls
    $('player-back').addEventListener('click', closePlayer);
    $('player-back2').addEventListener('click', closePlayer);
    $('player-retry').addEventListener('click', () => {
      state.player.attempts = 0;
      const channel = channelById(state.player.channelId);
      if (channel) startPlayback(channel);
    });
    $('player-external').addEventListener('click', () => {
      const channel = channelById(state.player.channelId);
      if (channel) bridge.openExternal(channel.url);
    });
    $('player-fav').addEventListener('click', async () => {
      const result = await bridge.toggleFavorite(state.player.channelId);
      if (result) state.favorites = result.favorites;
      updatePlayerFavorite();
      renderDrawer();
    });
    $('player-copy').addEventListener('click', async () => {
      const channel = channelById(state.player.channelId);
      if (channel && await bridge.copyLink(channel.url)) toast(t('copied'));
    });
    $('player-pip').addEventListener('click', togglePictureInPicture);
    $('player-fullscreen').addEventListener('click', async () => {
      const video = $('video');
      if (document.fullscreenElement) document.exitFullscreen();
      else if (video.requestFullscreen) video.requestFullscreen();
      else if (bridge.toggleFullscreen) bridge.toggleFullscreen();
    });
    $('player-menu-btn').addEventListener('click', () => {
      const menu = $('player-menu');
      renderPlayerMenu();
      menu.classList.toggle('hidden');
    });
    $('player-menu').addEventListener('click', async (event) => {
      const button = event.target.closest('[data-player-action]');
      if (!button) return;
      const action = button.getAttribute('data-player-action');
      $('player-menu').classList.add('hidden');
      const video = $('video');

      if (action === 'fit' || action === 'zoom' || action === 'stretch') {
        state.player.mode = action;
        video.classList.remove('zoom', 'stretch');
        if (action !== 'fit') video.classList.add(action);
      } else if (action === 'external') {
        const channel = channelById(state.player.channelId);
        if (channel) bridge.openExternal(channel.url);
      } else if (action === 'pip') {
        togglePictureInPicture();
      } else if (action === 'copy') {
        const channel = channelById(state.player.channelId);
        if (channel && await bridge.copyLink(channel.url)) toast(t('copied'));
      } else if (action === 'fullscreen') {
        if (document.fullscreenElement) document.exitFullscreen();
        else if (video.requestFullscreen) video.requestFullscreen();
      }
    });

    $('zap-prev').addEventListener('click', () => zap(-1));
    $('zap-next').addEventListener('click', () => zap(1));

    // dialog
    $('dialog-cancel').addEventListener('click', closeDialog);
    $('dialog-confirm').addEventListener('click', confirmDialog);
    $('dialog-sections').addEventListener('click', (event) => {
      const chip = event.target.closest('[data-dialog-section]');
      if (!chip) return;
      state.pendingCategory = chip.getAttribute('data-dialog-section');
      document.querySelectorAll('[data-dialog-section]').forEach((el) =>
        el.classList.toggle('is-selected', el === chip));
    });
    $('dialog-url').addEventListener('keydown', (event) => {
      if (event.key === 'Enter') confirmDialog();
    });

    // keyboard shortcuts (desktop friendly)
    document.addEventListener('keydown', (event) => {
      const inField = ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);
      if (event.key === 'Escape') {
        if (!$('dialog').classList.contains('hidden')) closeDialog();
        else if (!$('player').classList.contains('hidden')) closePlayer();
        else if (!$('player-menu').classList.contains('hidden')) $('player-menu').classList.add('hidden');
        return;
      }
      if (inField) return;
      if (!$('player').classList.contains('hidden')) {
        if (event.key === 'ArrowRight' || event.key === 'PageDown') zap(1);
        if (event.key === 'ArrowLeft' || event.key === 'PageUp') zap(-1);
        if (event.key === 'f' || event.key === 'F') $('player-fullscreen').click();
        if (event.key === 'p' || event.key === 'P') togglePictureInPicture();
      } else if (event.key === '/') {
        event.preventDefault();
        state.view = { name: 'search', categoryId: null, query: '' };
        render();
      }
    });

    document.addEventListener('click', (event) => {
      if (!event.target.closest('.menu-wrap')) $('player-menu').classList.add('hidden');
    });
  }

  async function togglePictureInPicture() {
    const video = $('video');
    try {
      if (document.pictureInPictureElement) await document.exitPictureInPicture();
      else if (video.requestPictureInPicture) await video.requestPictureInPicture();
    } catch (err) {
      toast(t('pictureInPicture'));
    }
  }

  // ------------------------------------------------------ fallback (no Electron)

  function createFallbackBridge() {
    const memory = { favorites: [], recents: [], custom: [], language: 'fa', theme: 'dark' };
    try {
      const saved = JSON.parse(localStorage.getItem('takhtlive') || '{}');
      Object.assign(memory, saved);
    } catch (err) { /* ignore */ }

    const persist = () => {
      try { localStorage.setItem('takhtlive', JSON.stringify(memory)); } catch (err) { /* ignore */ }
    };
    const catalog = window.TAKHT_CATALOG || { categories: [], channels: [] };

    const getState = async () => ({
      categories: catalog.categories,
      channels: catalog.channels.concat(memory.custom),
      favorites: memory.favorites,
      recents: memory.recents,
      language: memory.language,
      theme: memory.theme,
      version: window.TAKHT_VERSION || '1.0.0',
    });

    return {
      isDesktop: false,
      getState,
      getAppInfo: async () => ({ version: '1.0.0', platform: 'browser' }),
      setLanguage: async (code) => { memory.language = code; persist(); return getState(); },
      setTheme: async (mode) => { memory.theme = mode; persist(); return getState(); },
      toggleFavorite: async (id) => {
        const set = new Set(memory.favorites);
        if (set.has(id)) set.delete(id); else set.add(id);
        memory.favorites = Array.from(set);
        persist();
        return { id, isFavorite: set.has(id), favorites: memory.favorites };
      },
      markRecent: async (id) => {
        memory.recents = [id].concat(memory.recents.filter((x) => x !== id)).slice(0, 20);
        persist();
        return memory.recents;
      },
      addChannel: async (payload) => {
        const channel = Object.assign({ id: `custom-${Date.now()}`, quality: 'LIVE', custom: true }, payload);
        memory.custom = memory.custom.concat([channel]);
        persist();
        return { channel, state: await getState() };
      },
      removeChannel: async (id) => {
        memory.custom = memory.custom.filter((c) => c.id !== id);
        persist();
        return getState();
      },
      openExternal: async (url) => { window.open(url, '_blank'); return true; },
      copyLink: async (url) => { try { await navigator.clipboard.writeText(url); } catch (e) { /* ignore */ } return true; },
      toggleFullscreen: async () => false,
      onSystemThemeChanged: () => () => {},
    };
  }

  // --------------------------------------------------------------------- boot

  async function boot() {
    wireLogoFallbacks();
    bindEvents();
    const next = await bridge.getState();
    applyState(next);
    render();

    const info = await bridge.getAppInfo();
    if (info && info.platform === 'win32') {
      $('about-system').textContent =
        `Electron ${info.electron} · Chromium ${info.chrome} · Windows ${info.windowsBuild}`;
    }

    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
        if (state.theme === 'system') applyTheme();
      });
    }
    bridge.onSystemThemeChanged(() => { if (state.theme === 'system') applyTheme(); });

    // exposed for tests and the screenshot tooling
    window.takhtLiveApp = {
      state,
      render,
      openPlayer,
      closePlayer,
      openDialog,
      closeDialog,
      setView: (view) => { Object.assign(state.view, view); render(); },
      t,
    };
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
