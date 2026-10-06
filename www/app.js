const STORAGE_KEY = 'mahva.app.v1';
const SYSTEM_PROMPT = 'تو مهوا هستی، یک دستیار هوشمند، دقیق، صمیمی و مفید. به زبان کاربر پاسخ بده و اگر کاربر فارسی می‌نویسد، فارسی روان و طبیعی بنویس. پاسخ را روشن و کاربردی نگه دار؛ اگر مطمئن نیستی، صادقانه بگو. ادعای انجام کاری که انجام نداده‌ای نکن.';
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const elements = {
  chatList: $('#chatList'),
  conversationTitle: $('#conversationTitle'),
  connectionStatus: $('#connectionStatus'),
  sidebarConnectionText: $('#sidebarConnectionText'),
  welcomePanel: $('#welcomePanel'),
  messageList: $('#messageList'),
  conversationScroll: $('#conversationScroll'),
  typingIndicator: $('#typingIndicator'),
  composerForm: $('#composerForm'),
  promptInput: $('#promptInput'),
  sendButton: $('#sendButton'),
  settingsDialog: $('#settingsDialog'),
  settingsForm: $('#settingsForm'),
  apiUrl: $('#apiUrl'),
  apiModel: $('#apiModel'),
  apiKey: $('#apiKey'),
  settingsError: $('#settingsError'),
  toastRegion: $('#toastRegion'),
};

function readSavedState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    const chats = Array.isArray(parsed.chats) ? parsed.chats.filter((chat) => chat && typeof chat.id === 'string' && Array.isArray(chat.messages)) : [];
    return {
      chats,
      activeChatId: typeof parsed.activeChatId === 'string' ? parsed.activeChatId : null,
      theme: parsed.theme === 'dark' ? 'dark' : 'light',
      settings: {
        apiUrl: typeof parsed.settings?.apiUrl === 'string' ? parsed.settings.apiUrl : '',
        model: typeof parsed.settings?.model === 'string' ? parsed.settings.model : '',
        apiKey: typeof parsed.settings?.apiKey === 'string' ? parsed.settings.apiKey : '',
      },
    };
  } catch {
    return { chats: [], activeChatId: null, theme: 'light', settings: { apiUrl: '', model: '', apiKey: '' } };
  }
}

const state = {
  ...readSavedState(),
  busy: false,
  pendingChatId: null,
  installPrompt: null,
};

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      chats: state.chats,
      activeChatId: state.activeChatId,
      theme: state.theme,
      settings: state.settings,
    }));
  } catch {
    showToast('ذخیره‌سازی در این دستگاه در دسترس نیست.', true);
  }
}

function makeId() {
  return globalThis.crypto?.randomUUID?.() || `chat-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function createChat() {
  const chat = { id: makeId(), title: 'گفت‌وگوی تازه', updatedAt: Date.now(), messages: [] };
  state.chats.unshift(chat);
  state.activeChatId = chat.id;
  persist();
  renderApp();
  closeMobileSidebar();
  elements.promptInput.focus({ preventScroll: true });
}

function activeChat() {
  return state.chats.find((chat) => chat.id === state.activeChatId) || null;
}

function titleFromMessage(text) {
  const shortText = text.replace(/\s+/g, ' ').trim();
  return shortText.length > 32 ? `${shortText.slice(0, 32).trim()}…` : shortText;
}

function renderSidebar() {
  elements.chatList.replaceChildren();
  const chats = [...state.chats].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  if (chats.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'chat-empty';
    empty.textContent = 'گفت‌وگوی تازه‌ای شروع کنید تا اینجا نمایش داده شود.';
    elements.chatList.append(empty);
  }

  for (const chat of chats) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `chat-item${chat.id === state.activeChatId ? ' active' : ''}`;
    button.setAttribute('aria-current', chat.id === state.activeChatId ? 'page' : 'false');
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', '#i-message');
    icon.append(use);
    const title = document.createElement('span');
    title.textContent = chat.title || 'گفت‌وگوی تازه';
    button.append(icon, title);
    button.addEventListener('click', () => {
      state.activeChatId = chat.id;
      persist();
      renderApp();
      closeMobileSidebar();
    });
    elements.chatList.append(button);
  }

  const configured = Boolean(state.settings.apiUrl && state.settings.model);
  elements.sidebarConnectionText.textContent = configured ? `مدل ${state.settings.model}` : 'اتصال مدل هوش مصنوعی';
}

function createAssistantAvatar() {
  const avatar = document.createElement('span');
  avatar.className = 'assistant-avatar';
  avatar.setAttribute('aria-hidden', 'true');
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', '#i-spark');
  icon.append(use);
  avatar.append(icon);
  return avatar;
}

function renderMessage(message) {
  const row = document.createElement('article');
  row.className = `message-row ${message.role === 'user' ? 'user' : 'assistant'}`;

  const author = document.createElement('div');
  author.className = 'message-author';
  if (message.role === 'user') {
    const avatar = document.createElement('span');
    avatar.className = 'user-avatar';
    avatar.setAttribute('aria-hidden', 'true');
    avatar.textContent = 'ش';
    const label = document.createElement('span');
    label.textContent = 'شما';
    author.append(avatar, label);
  } else {
    const label = document.createElement('span');
    label.textContent = 'مهوا';
    author.append(createAssistantAvatar(), label);
  }

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.textContent = message.content;
  row.append(author, bubble);

  if (message.role === 'assistant') {
    const actions = document.createElement('div');
    actions.className = 'message-actions';
    if (message.localOnly) {
      const note = document.createElement('span');
      note.className = 'local-message-tag';
      note.textContent = 'پاسخ محلی';
      actions.append(note);
    }
    const copyButton = document.createElement('button');
    copyButton.type = 'button';
    copyButton.className = 'copy-message-button';
    copyButton.setAttribute('aria-label', 'کپی پاسخ');
    const copyIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const copyUse = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    copyUse.setAttribute('href', '#i-copy');
    copyIcon.append(copyUse);
    const copyLabel = document.createElement('span');
    copyLabel.textContent = 'کپی';
    copyButton.append(copyIcon, copyLabel);
    copyButton.addEventListener('click', async () => {
      const copied = await copyText(message.content);
      showToast(copied ? 'پاسخ کپی شد.' : 'کپی‌کردن در این مرورگر در دسترس نیست.', !copied);
    });
    actions.append(copyButton);
    row.append(actions);
  }
  return row;
}

function renderConversation() {
  const chat = activeChat();
  if (!chat) return;
  const messages = chat.messages.filter((message) => message && ['user', 'assistant'].includes(message.role) && typeof message.content === 'string');
  elements.conversationTitle.textContent = chat.title || 'گفت‌وگوی تازه';
  elements.welcomePanel.hidden = messages.length > 0;
  elements.messageList.hidden = messages.length === 0;
  elements.messageList.replaceChildren(...messages.map(renderMessage));
  elements.typingIndicator.hidden = !(state.busy && state.pendingChatId === chat.id);
  if (messages.length > 0 || !elements.typingIndicator.hidden) scrollToBottom();
}

function renderConnectionStatus() {
  const configured = Boolean(state.settings.apiUrl && state.settings.model);
  elements.connectionStatus.classList.toggle('connected', configured);
  elements.connectionStatus.lastElementChild.textContent = configured ? 'آماده‌ی اتصال' : 'حالت نمایشی';
}

function renderTheme() {
  document.documentElement.dataset.theme = state.theme;
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  if (metaTheme) metaTheme.content = state.theme === 'dark' ? '#171822' : '#f7f7fb';
}

function renderApp() {
  renderSidebar();
  renderConversation();
  renderConnectionStatus();
  renderTheme();
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    elements.conversationScroll.scrollTop = elements.conversationScroll.scrollHeight;
  });
}

function closeMobileSidebar() {
  document.body.classList.remove('menu-open');
}

function showToast(message, isError = false) {
  const toast = document.createElement('div');
  toast.className = `toast${isError ? ' error' : ''}`;
  toast.textContent = message;
  elements.toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), 2800);
}

function delay(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function appendAssistantMessage(chatId, content, localOnly = false) {
  const chat = state.chats.find((item) => item.id === chatId);
  if (!chat) return;
  chat.messages.push({ role: 'assistant', content, localOnly, createdAt: Date.now() });
  chat.updatedAt = Date.now();
  persist();
  renderSidebar();
  if (state.activeChatId === chatId) renderConversation();
}

function offlineReply() {
  return 'سلام! من مهوا هستم؛ یک رابط گفت‌وگوی هوشمند که روی دستگاه شما اجرا می‌شود. برای پاسخ‌دادن به پرسش‌ها، از «تنظیمات اتصال» یک نشانی API سازگار و نام مدل وارد کنید. بدون اتصال به مدل، پاسخ ساختگی نمی‌دهم؛ پیام‌هایتان فعلاً فقط روی همین دستگاه ذخیره می‌شوند.';
}

async function requestCompletion(chat) {
  const url = state.settings.apiUrl.trim();
  const model = state.settings.model.trim();
  const key = state.settings.apiKey.trim();
  if (!url || !model) return null;

  let parsedUrl;
  try {
    parsedUrl = new URL(url);
  } catch {
    throw new Error('نشانی API معتبر نیست. آن را در تنظیمات بررسی کنید.');
  }
  if (!['https:', 'http:'].includes(parsedUrl.protocol)) {
    throw new Error('نشانی API باید با http:// یا https:// آغاز شود.');
  }

  const history = chat.messages
    .filter((message) => !message.localOnly && ['user', 'assistant'].includes(message.role))
    .slice(-40)
    .map(({ role, content }) => ({ role, content }));
  const headers = { 'Content-Type': 'application/json' };
  if (key) headers.Authorization = `Bearer ${key}`;

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 90000);
  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ model, messages: [{ role: 'system', content: SYSTEM_PROMPT }, ...history] }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw new Error('زمان انتظار برای پاسخ تمام شد. دوباره تلاش کنید.');
    throw new Error('اتصال برقرار نشد. نشانی API و دسترسی شبکه یا CORS را بررسی کنید.');
  } finally {
    window.clearTimeout(timeout);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const providerMessage = data?.error?.message || data?.message;
    const statusHint = response.status === 401 || response.status === 403
      ? 'کلید API یا مجوز دسترسی را بررسی کنید.'
      : response.status === 429
        ? 'محدودیت درخواست یا اعتبار حساب ارائه‌دهنده را بررسی کنید.'
        : `سرویس با کد ${response.status} پاسخ داد.`;
    throw new Error(typeof providerMessage === 'string' ? providerMessage : statusHint);
  }

  const content = data?.choices?.[0]?.message?.content;
  if (typeof content === 'string' && content.trim()) return content.trim();
  if (Array.isArray(content)) {
    const text = content.map((part) => typeof part?.text === 'string' ? part.text : '').join('').trim();
    if (text) return text;
  }
  throw new Error('پاسخ سرویس قابل خواندن نبود. سازگاری با قالب OpenAI Chat Completions را بررسی کنید.');
}

async function sendMessage(value) {
  const content = value.trim();
  const chat = activeChat();
  if (!content || !chat || state.busy) return;

  chat.messages.push({ role: 'user', content, createdAt: Date.now() });
  if (chat.messages.filter((message) => message.role === 'user').length === 1) chat.title = titleFromMessage(content) || 'گفت‌وگوی تازه';
  chat.updatedAt = Date.now();
  state.busy = true;
  state.pendingChatId = chat.id;
  persist();
  renderApp();
  elements.promptInput.value = '';
  resizeComposer();
  elements.sendButton.disabled = true;

  try {
    const reply = await requestCompletion(chat);
    if (reply) {
      appendAssistantMessage(chat.id, reply, false);
    } else {
      await delay(380);
      appendAssistantMessage(chat.id, offlineReply(), true);
    }
  } catch (error) {
    appendAssistantMessage(chat.id, `در دریافت پاسخ مشکلی پیش آمد: ${error.message}`, true);
  } finally {
    state.busy = false;
    state.pendingChatId = null;
    elements.sendButton.disabled = false;
    persist();
    renderApp();
  }
}

function resizeComposer() {
  elements.promptInput.style.height = 'auto';
  elements.promptInput.style.height = `${Math.min(elements.promptInput.scrollHeight, 150)}px`;
}

function openSettings() {
  elements.apiUrl.value = state.settings.apiUrl;
  elements.apiModel.value = state.settings.model;
  elements.apiKey.value = state.settings.apiKey;
  elements.apiKey.type = 'password';
  $('#toggleKeyVisibility').textContent = 'نمایش';
  elements.settingsError.hidden = true;
  closeMobileSidebar();
  if (!elements.settingsDialog.open) elements.settingsDialog.showModal();
}

function closeSettings() {
  if (elements.settingsDialog.open) elements.settingsDialog.close();
}

async function copyText(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    const temporary = document.createElement('textarea');
    temporary.value = text;
    temporary.style.position = 'fixed';
    temporary.style.opacity = '0';
    document.body.append(temporary);
    temporary.select();
    const succeeded = document.execCommand('copy');
    temporary.remove();
    return succeeded;
  } catch {
    return false;
  }
}

$('#newChatButton').addEventListener('click', createChat);
$('#openSettingsButton').addEventListener('click', openSettings);
$('#topbarSettingsButton').addEventListener('click', openSettings);
$('#mobileMenuButton').addEventListener('click', () => document.body.classList.add('menu-open'));
$('#sidebarClose').addEventListener('click', closeMobileSidebar);
$('#sidebarBackdrop').addEventListener('click', closeMobileSidebar);
$('#closeSettingsButton').addEventListener('click', closeSettings);
$('#cancelSettingsButton').addEventListener('click', closeSettings);
$('#clearLocalDataButton').addEventListener('click', () => {
  if (state.busy) {
    showToast('تا پایان پاسخ فعلی نمی‌توان داده‌ها را پاک کرد.', true);
    return;
  }
  if (!window.confirm('همه‌ی گفت‌وگوها و کلید API ذخیره‌شده از این دستگاه پاک شوند؟')) return;
  state.chats = [{ id: makeId(), title: 'گفت‌وگوی تازه', updatedAt: Date.now(), messages: [] }];
  state.activeChatId = state.chats[0].id;
  state.settings = { apiUrl: '', model: '', apiKey: '' };
  state.theme = 'light';
  persist();
  renderApp();
  closeSettings();
  showToast('داده‌های مهوا از این دستگاه پاک شد.');
});

$('#themeToggle').addEventListener('click', () => {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  persist();
  renderTheme();
});

$('#toggleKeyVisibility').addEventListener('click', () => {
  const show = elements.apiKey.type === 'password';
  elements.apiKey.type = show ? 'text' : 'password';
  $('#toggleKeyVisibility').textContent = show ? 'پنهان‌کردن' : 'نمایش';
});

elements.settingsForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const apiUrl = elements.apiUrl.value.trim();
  const model = elements.apiModel.value.trim();
  const apiKey = elements.apiKey.value.trim();
  elements.settingsError.hidden = true;

  if ((apiUrl || model || apiKey) && (!apiUrl || !model)) {
    elements.settingsError.textContent = 'برای اتصال، نشانی API و نام مدل را هر دو وارد کنید. کلید API بسته به سرویس اختیاری است.';
    elements.settingsError.hidden = false;
    return;
  }
  if (apiUrl) {
    try {
      const parsed = new URL(apiUrl);
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error();
    } catch {
      elements.settingsError.textContent = 'نشانی API معتبر نیست؛ نشانی باید با http:// یا https:// شروع شود.';
      elements.settingsError.hidden = false;
      return;
    }
  }

  state.settings = { apiUrl, model, apiKey };
  persist();
  renderApp();
  closeSettings();
  showToast(apiUrl ? 'تنظیمات اتصال ذخیره شد.' : 'اتصال آنلاین غیرفعال شد.');
});

elements.composerForm.addEventListener('submit', (event) => {
  event.preventDefault();
  sendMessage(elements.promptInput.value);
});

elements.promptInput.addEventListener('input', resizeComposer);
elements.promptInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    sendMessage(elements.promptInput.value);
  }
});

$$('.suggestion-card').forEach((button) => {
  button.addEventListener('click', () => {
    const prompt = button.dataset.prompt || '';
    elements.promptInput.value = prompt;
    resizeComposer();
    elements.promptInput.focus();
    if (!prompt.endsWith(': ')) sendMessage(prompt);
  });
});

document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    createChat();
  }
  if (event.key === 'Escape') closeMobileSidebar();
});

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  state.installPrompt = event;
  $('#installButton').hidden = false;
});

$('#installButton').addEventListener('click', async () => {
  if (!state.installPrompt) {
    showToast('برای نصب، از منوی مرورگر گزینه‌ی «افزودن به صفحه‌ی اصلی» را انتخاب کنید.');
    return;
  }
  state.installPrompt.prompt();
  await state.installPrompt.userChoice;
  state.installPrompt = null;
  $('#installButton').hidden = true;
});

window.addEventListener('appinstalled', () => {
  state.installPrompt = null;
  $('#installButton').hidden = true;
  showToast('مهوا با موفقیت نصب شد.');
});

if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {
      // The app remains usable when service workers are unavailable.
    });
  });
}

if (!state.chats.some((chat) => chat.id === state.activeChatId)) {
  const existing = state.chats[0];
  if (existing) state.activeChatId = existing.id;
  else {
    const firstChat = { id: makeId(), title: 'گفت‌وگوی تازه', updatedAt: Date.now(), messages: [] };
    state.chats.push(firstChat);
    state.activeChatId = firstChat.id;
  }
  persist();
}

renderApp();
