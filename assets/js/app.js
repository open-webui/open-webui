/* ============================================================
   Open WebUI — PHP Edition · Frontend App
   ============================================================ */

(() => {
  'use strict';

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const API = {
    async req(url, opts = {}) {
      const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
        ...opts
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `خطای ${res.status}`);
      return data;
    },
    get:  (url) => API.req(url),
    post: (url, body) => API.req(url, { method: 'POST', body: JSON.stringify(body) }),
    del:  (url) => API.req(url, { method: 'DELETE' }),
  };

  const ESC = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  // ─── State ─────────────────────────────────────────────
  const state = {
    user: null,
    chats: [],
    currentChat: null,   // {id, title, model, messages}
    models: [],
    currentModel: localStorage.getItem('owui_model') || 'ChatRayovin',
    sending: false,
    abort: null,
  };

  // ─── Toast ─────────────────────────────────────────────
  function toast(msg, type = '') {
    const wrap = $('.toast-wrap') || (() => {
      const d = document.createElement('div');
      d.className = 'toast-wrap';
      document.body.appendChild(d);
      return d;
    })();
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    wrap.appendChild(t);
    setTimeout(() => t.remove(), 3200);
  }

  // ─── Auth Screen ───────────────────────────────────────
  function renderAuth() {
    const app = $('#app');
    app.innerHTML = `
      <div class="auth-screen">
        <div class="auth-card">
          <div class="auth-logo">🤖</div>
          <h1>Open WebUI</h1>
          <p class="auth-sub">نسخه PHP — آماده اجرا روی هر هاست</p>
          <div class="auth-error" id="authError"></div>
          <form id="authForm">
            <div class="field" id="nameField" style="display:none">
              <label>نام</label>
              <input type="text" id="authName" placeholder="نام شما" autocomplete="name">
            </div>
            <div class="field">
              <label>ایمیل</label>
              <input type="email" id="authEmail" placeholder="you@example.com" autocomplete="email" required>
            </div>
            <div class="field">
              <label>رمز عبور</label>
              <input type="password" id="authPass" placeholder="••••••••" autocomplete="current-password" required>
            </div>
            <button class="btn btn-primary" id="authBtn" type="submit">ورود</button>
          </form>
          <div class="auth-switch">
            حساب ندارید؟ <a href="#" id="authToggle">ثبت‌نام کنید</a>
          </div>
        </div>
      </div>`;

    let isRegister = false;
    const form = $('#authForm');
    const btn = $('#authBtn');
    const errBox = $('#authError');
    const nameField = $('#nameField');

    $('#authToggle').addEventListener('click', (e) => {
      e.preventDefault();
      isRegister = !isRegister;
      nameField.style.display = isRegister ? 'block' : 'none';
      btn.textContent = isRegister ? 'ثبت‌نام' : 'ورود';
      $('#authToggle').textContent = isRegister ? 'قبلاً ثبت‌نام کرده‌اید؟ ورود' : 'حساب ندارید؟ ثبت‌نام کنید';
      $('#authPass').autocomplete = isRegister ? 'new-password' : 'current-password';
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errBox.classList.remove('show');
      btn.disabled = true;
      btn.textContent = '...';
      try {
        const action = isRegister ? 'register' : 'login';
        await API.post(`api/auth.php?action=${action}`, {
          name: $('#authName').value,
          email: $('#authEmail').value,
          password: $('#authPass').value,
        });
        await boot();
      } catch (err) {
        errBox.textContent = err.message;
        errBox.classList.add('show');
        btn.disabled = false;
        btn.textContent = isRegister ? 'ثبت‌نام' : 'ورود';
      }
    });
  }

  // ─── Main App ──────────────────────────────────────────
  function renderApp() {
    const app = $('#app');
    app.innerHTML = `
      <div class="app">
        <div class="sidebar-backdrop" id="sbBackdrop"></div>
        <aside class="sidebar" id="sidebar">
          <div class="sidebar-header">
            <button class="new-chat-btn" id="newChatBtn"><span class="plus">+</span> گفتگوی جدید</button>
          </div>
          <div class="chat-list" id="chatList">
            <div class="chat-list-title">گفتگوها</div>
          </div>
          <div class="sidebar-footer">
            <div class="user-row">
              <div class="avatar" id="userAvatar">?</div>
              <div class="user-info">
                <div class="user-name" id="userName"></div>
                <div class="user-email" id="userEmail"></div>
              </div>
              <div class="user-actions">
                <button class="icon-btn" id="settingsBtn" title="تنظیمات">⚙️</button>
                <button class="icon-btn danger" id="logoutBtn" title="خروج">⎋</button>
              </div>
            </div>
          </div>
        </aside>

        <main class="main">
          <header class="chat-header">
            <button class="icon-btn menu-btn" id="menuBtn">☰</button>
            <div class="model-badge"><span class="dot"></span><span id="headerModel">—</span></div>
          </header>
          <div class="messages" id="messages"></div>
          <div class="composer-wrap">
            <div class="composer">
              <textarea id="input" placeholder="پیام خود را بنویسید… (Enter برای ارسال)" rows="1"></textarea>
              <div class="composer-footer">
                <select class="model-select" id="modelSelect"></select>
                <button class="send-btn" id="sendBtn" title="ارسال">➤</button>
              </div>
            </div>
            <div class="composer-hint">تاریخچه گفتگوها به‌صورت محلی ذخیره می‌شود</div>
          </div>
        </main>
      </div>

      <!-- Settings modal -->
      <div class="modal-overlay" id="settingsModal">
        <div class="modal modal-outer">
          <button class="icon-btn modal-close" id="settingsClose">✕</button>
          <h2>⚙️ تنظیمات</h2>
          <form id="settingsForm">
            <div class="field"><label>نام نمایشی</label><input type="text" id="setName"></div>
            <div class="field"><label>API Key (OpenAI / DeepSeek / …)</label><input type="password" id="setApiKey" placeholder="sk-..."></div>
            <div class="field"><label>Base URL (اختیاری — مثلاً DeepSeek)</label><input type="text" id="setBase" placeholder="https://api.openai.com/v1"></div>
            <div class="field"><label>Ollama URL (اختیاری)</label><input type="text" id="setOllama" placeholder="http://localhost:11434"></div>
            <div class="modal-actions">
              <button type="button" class="btn btn-ghost" id="settingsCancel">انصراف</button>
              <button type="submit" class="btn btn-primary" style="width:auto">ذخیره</button>
            </div>
          </form>
        </div>
      </div>`;

    bindApp();
  }

  // ─── Bindings ──────────────────────────────────────────
  function bindApp() {
    // Sidebar
    $('#newChatBtn').addEventListener('click', newChat);
    $('#menuBtn').addEventListener('click', () => { $('#sidebar').classList.add('open'); $('#sbBackdrop').classList.add('show'); });
    $('#sbBackdrop').addEventListener('click', () => { $('#sidebar').classList.remove('open'); $('#sbBackdrop').classList.remove('show'); });
    $('#settingsBtn').addEventListener('click', openSettings);
    $('#logoutBtn').addEventListener('click', logout);

    // Composer
    const input = $('#input');
    const sendBtn = $('#sendBtn');
    input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 200) + 'px'; });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    sendBtn.addEventListener('click', () => sendBtn.classList.contains('stop') ? stopSending() : send());

    // Model select
    $('#modelSelect').addEventListener('change', (e) => {
      state.currentModel = e.target.value;
      localStorage.setItem('owui_model', state.currentModel);
      updateHeaderModel();
    });

    // Settings modal
    $('#settingsClose').addEventListener('click', closeSettings);
    $('#settingsCancel').addEventListener('click', closeSettings);
    $('#settingsModal').addEventListener('click', (e) => { if (e.target.id === 'settingsModal') closeSettings(); });
    $('#settingsForm').addEventListener('submit', saveSettings);

    // Chat list delegation
    $('#chatList').addEventListener('click', (e) => {
      const item = e.target.closest('.chat-item');
      if (!item) return;
      if (e.target.closest('.del')) { deleteChat(item.dataset.id); return; }
      openChat(item.dataset.id);
    });

    loadChats();
    loadModels();
  }

  // ─── Chat list ─────────────────────────────────────────
  async function loadChats() {
    try {
      const { chats } = await API.get('api/chat.php?action=list');
      state.chats = chats;
      renderChatList();
    } catch (err) { toast(err.message, 'error'); }
  }

  function renderChatList() {
    const list = $('#chatList');
    if (!state.chats.length) {
      list.innerHTML = `<div class="chat-list-title">گفتگوها</div><div style="color:var(--text-muted);font-size:13px;padding:10px;text-align:center">هنوز گفتگویی ندارید</div>`;
      return;
    }
    list.innerHTML = `<div class="chat-list-title">گفتگوها</div>` + state.chats.map(c => `
      <div class="chat-item ${state.currentChat?.id === c.id ? 'active' : ''}" data-id="${ESC(c.id)}">
        <span class="title">${ESC(c.title)}</span>
        <button class="del" title="حذف">🗑</button>
      </div>`).join('');
  }

  // ─── Chat CRUD ─────────────────────────────────────────
  function newChat() {
    state.currentChat = null;
    $('#messages').innerHTML = renderEmptyState();
    $('#input').value = '';
    $('#input').focus();
    renderChatList();
    updateHeaderModel();
  }

  function renderEmptyState() {
    const suggestions = [
      'تفاوت بین SQL و NoSQL چیست؟',
      'یک ایمیل رسمی برای جلسه کاری بنویس',
      'کد پایتون برای خواندن فایل CSV بنویس',
      'مفهوم یادگیری ماشین را ساده توضیح بده',
    ];
    return `
      <div class="empty-state">
        <div class="empty-logo">🤖</div>
        <h2>چه کاری می‌توانم برایت انجام دهم؟</h2>
        <p>یک مدل انتخاب کن و گفتگو را شروع کن. تاریخچه گفتگوها به‌صورت خودکار ذخیره می‌شود.</p>
        <div class="suggestions">
          ${suggestions.map(s => `<button class="suggestion" data-prompt="${ESC(s)}">${ESC(s)}</button>`).join('')}
        </div>
      </div>`;
  }

  $('#app').addEventListener('click', (e) => {
    const sug = e.target.closest('.suggestion');
    if (sug) { $('#input').value = sug.dataset.prompt; $('#input').focus(); }
  });

  async function openChat(id) {
    try {
      const { chat } = await API.get(`api/chat.php?action=get&id=${encodeURIComponent(id)}`);
      state.currentChat = chat;
      if (chat.model) { state.currentModel = chat.model; localStorage.setItem('owui_model', chat.model); }
      $('#modelSelect').value = state.currentModel;
      renderMessages(chat.messages || []);
      renderChatList();
      updateHeaderModel();
      $('#sidebar').classList.remove('open'); $('#sbBackdrop').classList.remove('show');
    } catch (err) { toast(err.message, 'error'); }
  }

  async function deleteChat(id) {
    if (!confirm('این گفتگو حذف شود؟')) return;
    try {
      await API.del(`api/chat.php?action=delete&id=${encodeURIComponent(id)}`);
      if (state.currentChat?.id === id) newChat();
      await loadChats();
    } catch (err) { toast(err.message, 'error'); }
  }

  // ─── Messages rendering ────────────────────────────────
  function renderMessages(messages) {
    const box = $('#messages');
    if (!messages.length) { box.innerHTML = renderEmptyState(); return; }
    box.innerHTML = messages.map(m => renderMsg(m.role, m.content)).join('');
    box.scrollTop = box.scrollHeight;
  }

  function renderMsg(role, content) {
    const isUser = role === 'user';
    return `
      <div class="msg ${isUser ? 'user' : 'assistant'}">
        <div class="msg-avatar">${isUser ? '👤' : '🤖'}</div>
        <div class="bubble">
          <div class="role-label">${isUser ? 'شما' : 'دستیار'}</div>
          <div class="content">${formatContent(content)}</div>
        </div>
      </div>`;
  }

  function formatContent(text) {
    if (!text) return '';
    // Split into plain / code-block segments; escape each separately
    const parts = String(text).split(/```(\w*)\n?([\s\S]*?)```/g);
    let out = '';
    for (let i = 0; i < parts.length; i += 3) {
      out += ESC(parts[i]).replace(/\n/g, '<br>');
      if (i + 2 < parts.length) {
        out += `<pre><code>${ESC(parts[i + 2])}</code></pre>`;
      }
    }
    return out;
  }

  // ─── Sending ───────────────────────────────────────────
  async function send() {
    const input = $('#input');
    const text = input.value.trim();
    if (!text || state.sending) return;

    if (!state.currentChat) {
      try {
        const { chat } = await API.post('api/chat.php?action=create', { model: state.currentModel });
        state.currentChat = chat;
        await loadChats();
      } catch (err) { toast(err.message, 'error'); return; }
    }

    const messages = state.currentChat.messages || [];
    messages.push({ role: 'user', content: text });
    messages.push({ role: 'assistant', content: '' });
    input.value = '';
    input.style.height = 'auto';

    const box = $('#messages');
    if (box.querySelector('.empty-state')) box.innerHTML = '';
    const msgHtml = renderMsg('user', text) + `
      <div class="msg assistant typing" id="pendingMsg">
        <div class="msg-avatar">🤖</div>
        <div class="bubble">
          <div class="role-label">دستیار</div>
          <div class="content"><div class="dots"><span></span><span></span><span></span></div></div>
        </div>
      </div>`;
    box.insertAdjacentHTML('beforeend', msgHtml);
    box.scrollTop = box.scrollHeight;

    state.sending = true;
    const sendBtn = $('#sendBtn');
    sendBtn.classList.add('stop');
    sendBtn.innerHTML = '■';
    sendBtn.title = 'توقف';

    const ac = new AbortController();
    state.abort = ac;

    try {
      // Optimistic save of user message
      state.currentChat.messages = messages;
      saveChat();

      const resp = await fetch('api/proxy.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: ac.signal,
        body: JSON.stringify({
          provider: getProvider(),
          model: state.currentModel,
          messages: messages.filter(m => m.role !== 'assistant' || m.content).map(m => ({ role: m.role, content: m.content })),
        }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.error || `خطای ${resp.status}`);

      const answer = data.choices?.[0]?.message?.content ?? '';
      messages[messages.length - 1].content = answer;

      // Replace typing with real answer
      const pending = $('#pendingMsg');
      if (pending) pending.outerHTML = renderMsg('assistant', answer);

      state.currentChat.messages = messages;
      // Auto-title from first user message
      if (state.currentChat.title === 'New Chat') {
        state.currentChat.title = text.slice(0, 40) + (text.length > 40 ? '…' : '');
      }
      saveChat();
      loadChats();
    } catch (err) {
      if (err.name === 'AbortError') {
        // Keep partial; mark as stopped
        messages[messages.length - 1].content = '⏹ ارسال متوقف شد.';
      } else {
        messages[messages.length - 1].content = '';
        const pending = $('#pendingMsg');
        if (pending) pending.outerHTML = renderMsg('assistant', `⚠️ خطا: ${ESC(err.message)}`);
      }
      state.currentChat.messages = messages;
      saveChat();
    } finally {
      state.sending = false;
      sendBtn.classList.remove('stop');
      sendBtn.innerHTML = '➤';
      sendBtn.title = 'ارسال';
      state.abort = null;
    }
  }

  function stopSending() { state.abort?.abort(); }

  async function saveChat() {
    try {
      await API.post('api/chat.php?action=save', {
        id: state.currentChat.id,
        title: state.currentChat.title,
        messages: state.currentChat.messages,
      });
    } catch (err) { /* silent */ }
  }

  function getProvider() {
    const m = state.models.find(x => x.id === state.currentModel);
    return m?.provider || 'openai';
  }

  // ─── Models ────────────────────────────────────────────
  async function loadModels() {
    try {
      const { models } = await API.get('api/models.php');
      state.models = models;
      const sel = $('#modelSelect');
      if (!sel) return;
      sel.innerHTML = models.map(m => `<option value="${ESC(m.id)}" data-provider="${m.provider}">${ESC(m.name)}</option>`).join('');
      if (models.some(m => m.id === state.currentModel)) sel.value = state.currentModel;
      updateHeaderModel();
    } catch (err) { toast(err.message, 'error'); }
  }

  function updateHeaderModel() {
    const h = $('#headerModel');
    if (h) h.textContent = state.currentModel;
  }

  // ─── Settings ──────────────────────────────────────────
  function openSettings() {
    $('#setName').value = state.user?.name || '';
    $('#setApiKey').value = '';
    $('#setBase').value = '';
    $('#setOllama').value = '';
    $('#settingsModal').classList.add('show');
  }

  function closeSettings() { $('#settingsModal').classList.remove('show'); }

  async function saveSettings(e) {
    e.preventDefault();
    try {
      await API.post('api/auth.php?action=update', {
        name: $('#setName').value,
        api_key: $('#setApiKey').value,
        openai_base: $('#setBase').value,
        ollama_base: $('#setOllama').value,
      });
      toast('تنظیمات ذخیره شد ✓', 'success');
      closeSettings();
      const me = await API.get('api/auth.php?action=me');
      state.user = me.user;
      $('#userName').textContent = me.user.name;
      $('#userAvatar').textContent = me.user.name.trim()[0] || '?';
      loadModels();
    } catch (err) { toast(err.message, 'error'); }
  }

  // ─── Auth actions ──────────────────────────────────────
  async function logout() {
    try { await API.post('api/auth.php?action=logout', {}); } catch (e) {}
    location.reload();
  }

  // ─── Boot ──────────────────────────────────────────────
  async function boot() {
    try {
      const me = await API.get('api/auth.php?action=me');
      state.user = me.user;
      renderApp();
      $('#userName').textContent = me.user.name;
      $('#userEmail').textContent = me.user.email;
      $('#userAvatar').textContent = me.user.name.trim()[0] || '?';
      newChat();
    } catch {
      renderAuth();
    }
  }

  boot();
})();
