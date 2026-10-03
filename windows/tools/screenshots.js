#!/usr/bin/env node
/**
 * Renders the TakhtLive renderer with a real Chromium and writes screenshots to
 * docs/screenshots/windows/. Used for CI verification and the README.
 *
 * Uses @sparticuz/chromium + puppeteer-core (both optional dev dependencies) so
 * the very same markup/CSS/JS that Electron loads is validated on any machine,
 * including Linux CI where Electron cannot show a window.
 *
 * Set SHOTS_KEEP_LOGOS=1 to keep the remote channel logos (used on CI runners,
 * which do have internet access); otherwise the bundled placeholder is shown so
 * the images are not full of broken images on offline machines.
 *
 *   node tools/screenshots.js
 */

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const REPO = path.join(ROOT, '..');
const OUT_DIR = process.env.SHOT_DIR || path.join(REPO, 'docs', 'screenshots', 'windows');

/**
 * The bundled Chromium build targets Amazon Linux; its shared libraries (NSS,
 * NSPR) ship compressed inside @sparticuz/chromium. Extract them to a temp
 * folder and point LD_LIBRARY_PATH at it.
 */
function extractChromiumLibs() {
  const zlib = require('zlib');
  const { execFileSync } = require('child_process');
  const bundle = path.join(ROOT, 'node_modules', '@sparticuz', 'chromium', 'bin', 'al2023.tar.br');
  if (!fs.existsSync(bundle)) return null;
  const dir = path.join(os.tmpdir(), 'takhtlive-chromium-libs');
  const done = path.join(dir, 'lib', 'libnspr4.so');
  if (fs.existsSync(done)) return path.join(dir, 'lib');
  fs.mkdirSync(dir, { recursive: true });
  const tar = path.join(os.tmpdir(), 'takhtlive-al2023.tar');
  fs.writeFileSync(tar, zlib.brotliDecompressSync(fs.readFileSync(bundle)));
  execFileSync('tar', ['-xf', tar, '-C', dir]);
  return path.join(dir, 'lib');
}

/** Chromium (ESM) needs a dynamic import; puppeteer-core is CommonJS. */
async function importLoose(name) {
  try {
    return await import(name);
  } catch (err) {
    return await import('file://' + path.join(ROOT, 'node_modules', name, 'package.json'))
      .then(async () => import(path.join(ROOT, 'node_modules', name, 'build', 'index.js')));
  }
}

async function makeFixture() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'takhtlive-web-'));
  // the renderer expects assets/ and src/ as siblings of renderer/
  fs.mkdirSync(path.join(dir, 'renderer'), { recursive: true });
  fs.cpSync(path.join(ROOT, 'renderer'), path.join(dir, 'renderer'), { recursive: true });
  fs.cpSync(path.join(ROOT, 'assets'), path.join(dir, 'assets'), { recursive: true });
  fs.mkdirSync(path.join(dir, 'src'), { recursive: true });
  fs.copyFileSync(path.join(ROOT, 'src', 'i18n.js'), path.join(dir, 'src', 'i18n.js'));

  const catalog = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets', 'channels.json'), 'utf8'));
  const parsed = require(path.join(ROOT, 'src', 'catalog.js')).parseCatalog(catalog);

  // the fallback bridge (no Electron) reads this global instead of IPC; a real
  // file keeps the app's Content-Security-Policy (script-src 'self') happy.
  // The sandbox has no internet, so the channel logos of the catalog are
  // replaced here by the bundled placeholder to keep the shots representative.
  const offline = {
    categories: parsed.categories,
    channels: parsed.channels.map((channel) => Object.assign({}, channel, { logo: '' })),
  };
  fs.writeFileSync(
    path.join(dir, 'src', 'test-catalog.js'),
    `window.TAKHT_CATALOG = ${JSON.stringify(process.env.SHOTS_KEEP_LOGOS ? parsed : offline)};\nwindow.TAKHT_FIXTURE = true;\n`
  );
  const html = fs.readFileSync(path.join(ROOT, 'renderer', 'index.html'), 'utf8')
    .replace('<script src="../src/i18n.js"></script>',
      '<script src="../src/i18n.js"></script>\n  <script src="../src/test-catalog.js"></script>');

  // keep the fixture next to index.html so ../assets and ../src resolve
  fs.writeFileSync(path.join(dir, 'renderer', 'fixture.html'), html);
  return { dir, file: path.join(dir, 'renderer', 'fixture.html') };
}

async function main() {
  const chromium = (await import('@sparticuz/chromium')).default;
  const puppeteer = require('puppeteer-core');

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const { dir, file } = await makeFixture();

  const args = (chromium.args || []).filter((a) => !a.includes('--single-process'));
  const libDir = extractChromiumLibs();
  const env = Object.assign({}, process.env);
  if (libDir) {
    env.LD_LIBRARY_PATH = [libDir, env.LD_LIBRARY_PATH].filter(Boolean).join(':');
  }
  const browser = await puppeteer.launch({
    env,
    args: [...args, '--no-sandbox', '--disable-dev-shm-usage', '--font-render-hinting=none'],
    defaultViewport: { width: 1360, height: 860, deviceScaleFactor: 1 },
    executablePath: await chromium.executablePath(),
    headless: true,
  });

  const shots = [];
  const page = await browser.newPage();
  // Remote logos/streams are unreachable in a sandboxed CI; only real JS errors
  // should fail the check, network failures are reported separately.
  const errors = [];
  const network = [];
  page.on('pageerror', (err) => errors.push(String(err)));
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    if (/Failed to load resource|net::ERR_/.test(msg.text()) || /Failed to load resource|net::ERR_/.test(msg.location() && msg.location().url || '')) {
      network.push(msg.text());
    } else {
      errors.push(msg.text());
    }
  });

  page.on('requestfailed', (req) => network.push(`${req.url().slice(0, 100)} ${(req.failure() || {}).errorText || ''}`.trim()));
  await page.goto('file://' + file, { waitUntil: 'load' });
  try {
    await page.waitForFunction('window.takhtLiveApp && document.querySelectorAll(".channel-card, .tile").length > 0');
  } catch (err) {
    console.error('renderer did not render:', errors.join('\n'));
    console.error('state:', await page.evaluate(() => ({
      hasApp: !!window.takhtLiveApp,
      hasCatalog: !!window.TAKHT_CATALOG,
      hasStrings: !!window.TAKHT_STRINGS,
      tiles: document.querySelectorAll('.tile').length,
      body: document.body.innerHTML.slice(0, 400),
    })).catch((e) => String(e)));
    throw err;
  }
  await page.evaluate(() => document.fonts.ready);
  await sleep(400);

  const shoot = async (name) => {
    await sleep(250);
    const target = path.join(OUT_DIR, `${name}.png`);
    await page.screenshot({ path: target });
    shots.push(`${name}.png`);
    console.log(`captured ${name}.png`);
  };

  // 01 – home (Persian, dark)
  await shoot('01-home');

  // 02..05 – the four sections
  const sections = await page.evaluate(() => window.takhtLiveApp.state.categories.map((c) => c.id));
  for (let i = 0; i < sections.length; i += 1) {
    await page.evaluate((id) => window.takhtLiveApp.setView({ name: 'category', categoryId: id, query: '' }), sections[i]);
    await shoot(`${String(i + 2).padStart(2, '0')}-${sections[i]}`);
  }

  // 06 – search
  await page.evaluate(() => window.takhtLiveApp.setView({ name: 'search', categoryId: null, query: '' }));
  await page.type('#global-search', 'news', { delay: 15 });
  await page.evaluate(() => {
    const input = document.querySelector('#global-search');
    input.value = 'پرس';
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await shoot('06-search');

  // 07 – library with a favourite and a custom channel
  await page.evaluate(async () => {
    const app = window.takhtLiveApp;
    const catalog = window.TAKHT_CATALOG;
    await window.takhtLive.toggleFavorite(catalog.channels[1].id);
    await window.takhtLive.toggleFavorite(catalog.channels[3].id);
    window.__customChannelId = (await window.takhtLive.addChannel({
      name: 'کانال آزمایشی من',
      url: 'https://example.com/live/index.m3u8',
      category: 'custom',
    })).channel.id;
    await window.takhtLive.markRecent(catalog.channels[0].id);
    const next = await window.takhtLive.getState();
    app.state.favorites = next.favorites;
    app.state.recents = next.recents;
    app.state.channels = next.channels;
    app.setView({ name: 'library', categoryId: null, query: '' });
  });
  await shoot('07-library');

  // 08 – add channel dialog
  await page.evaluate(() => window.takhtLiveApp.openDialog());
  await page.evaluate(() => {
    document.querySelector('#dialog-name').value = 'شبکهٔ نمونه';
    document.querySelector('#dialog-url').value = 'https://example.com/live/index.m3u8';
  });
  await shoot('08-add-channel');
  // drop the demo channel again so the remaining screenshots show the 109 built in channels
  await page.evaluate(async () => {
    window.takhtLiveApp.closeDialog();
    const next = await window.takhtLive.removeChannel(window.__customChannelId);
    window.takhtLiveApp.state.channels = next.channels;
    window.takhtLiveApp.render();
  });

  // 09 – player. The sandbox cannot reach the real HLS origin, so a canvas
  // capture-stream stands in for the live feed: the screenshot then shows the
  // real player chrome (title, favourites, zapping, fit/zoom menu) over video.
  await page.evaluate(() => {
    const catalog = window.TAKHT_CATALOG;
    window.takhtLiveApp.openPlayer(catalog.channels[0].id);
  });
  await page.evaluate(async () => {
    const video = document.querySelector('#video');
    const canvas = document.createElement('canvas');
    canvas.width = 1280;
    canvas.height = 720;
    const ctx = canvas.getContext('2d');
    const bars = ['#ffffff', '#ffe600', '#00d0ff', '#00d64a', '#ff2d9a', '#ff2b2b', '#0a35ff'];
    let phase = 0;
    setInterval(() => {
      phase += 0.35;
      ctx.fillStyle = '#0a0a14';
      ctx.fillRect(0, 0, 1280, 720);
      const width = 1280 / bars.length;
      bars.forEach((color, index) => {
        ctx.fillStyle = color;
        ctx.fillRect(index * width, 150, width, 340);
      });
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.font = 'bold 52px sans-serif';
      ctx.fillText('TAKHTLIVE', 640, 580);
      ctx.font = '28px sans-serif';
      ctx.fillText('live signal preview', 640, 625);
      ctx.beginPath();
      ctx.arc(640 + Math.cos(phase / 12) * 240, 90, 24, 0, Math.PI * 2);
      ctx.fillStyle = '#ff5c8a';
      ctx.fill();
    }, 40);
    video.srcObject = canvas.captureStream(30);
    await video.play().catch(() => {});
    // the app hides its own connecting overlay on 'playing'
    video.dispatchEvent(new Event('playing'));
  });
  await sleep(350);
  await shoot('09-player');
  await page.evaluate(() => window.takhtLiveApp.closePlayer());

  // 10 – drawer open (settings: language + theme)
  await page.evaluate(() => document.querySelector('#drawer').classList.remove('collapsed'));
  await page.evaluate(() => window.takhtLiveApp.setView({ name: 'home', categoryId: null, query: '' }));
  await shoot('10-drawer');

  // 11 – English
  await page.evaluate(async () => {
    const next = await window.takhtLive.setLanguage('en');
    window.takhtLiveApp.state.language = next.language;
    window.takhtLiveApp.render();
  });
  await shoot('11-english');

  // 12 – light theme
  await page.evaluate(async () => {
    const next = await window.takhtLive.setTheme('light');
    window.takhtLiveApp.state.theme = next.theme;
    window.takhtLiveApp.render();
  });
  await shoot('12-light-theme');

  // 13 – Arabic (RTL), back to dark theme
  await page.evaluate(async () => {
    const next = await window.takhtLive.setLanguage('ar');
    window.takhtLiveApp.state.language = next.language;
    const theme = await window.takhtLive.setTheme('dark');
    window.takhtLiveApp.state.theme = theme.theme;
    window.takhtLiveApp.render();
  });
  await shoot('13-arabic');

  const signatureVisible = await page.evaluate(() => {
    const bar = document.querySelector('#signature-bar');
    const style = getComputedStyle(bar);
    return bar.textContent.trim().length > 0 && style.display !== 'none' && bar.getBoundingClientRect().height > 0;
  });

  await browser.close();
  fs.rmSync(dir, { recursive: true, force: true });

  const summary = [
    `windows screenshots: ${shots.length}`,
    `files: ${shots.join(', ')}`,
    `signature visible: ${signatureVisible}`,
    `javascript errors: ${errors.length}`,
    ...errors.slice(0, 20),
    `blocked network requests (offline sandbox): ${network.length}`,
  ].join('\n');
  fs.writeFileSync(path.join(OUT_DIR, 'diagnostics.txt'), summary + '\n');
  console.log(summary);

  if (errors.length) process.exitCode = 2;
  if (!signatureVisible) process.exitCode = 3;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
