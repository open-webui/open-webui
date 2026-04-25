/* ClapNClaw — Open WebUI Loader
   Loaded via /static/loader.js on every page */
(function () {
  'use strict';

  // ── 1. Suppress changelog popup ──────────────────────────────
  if (!localStorage.version) localStorage.version = '99.99.99';
  setInterval(function () {
    if (!localStorage.version) localStorage.version = '99.99.99';
  }, 3000);

  // ── 2. Favicon replacement ───────────────────────────────────
  (function replaceFavicon() {
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">' +
      '<polygon points="14,82 28,18 42,82" fill="#0D5C3F"/>' +
      '<polygon points="26,18 40,82 54,18" fill="#E07020" opacity="0.7"/>' +
      '<polygon points="38,82 52,18 66,82" fill="#0D5C3F" opacity="0.45"/>' +
      '</svg>';
    var url = 'data:image/svg+xml,' + encodeURIComponent(svg);
    var existing = document.querySelectorAll('link[rel*="icon"]');
    existing.forEach(function (l) { l.href = url; });
    if (!existing.length) {
      var link = document.createElement('link');
      link.rel = 'icon'; link.type = 'image/svg+xml'; link.href = url;
      document.head.appendChild(link);
    }
  })();

  // ── 3. Logout redirect ───────────────────────────────────────
  // Detect hub + API URLs from tenant hostname.
  // staging-*.clapnclaw.io → staging hub / api-staging
  var _hostname = window.location.hostname;
  var _hubUrl = 'https://clapnclaw.io';
  var _apiUrl = 'https://api.clapnclaw.io';
  if (_hostname.indexOf('staging') >= 0) {
    _hubUrl = 'https://staging.clapnclaw.io';
    _apiUrl = 'https://api-staging.clapnclaw.io';
  }

  // ── Autologin: onboarding passes JWT via ?token= query param ──
  // Store it in localStorage so OWI SPA treats user as authenticated.
  (function checkAutoLogin() {
    var params = new URLSearchParams(location.search);
    var t = params.get('token');
    if (!t) return;
    localStorage.setItem('token', t);
    sessionStorage.setItem('cnc-session', '1');
    // Clean the token from the URL and go to root
    window.location.replace(location.origin + '/');
  })();

  // ClapNClaw users NEVER log in via Open WebUI directly — always via hub autologin.
  // Any landing on /auth means logout or expired session → redirect to home.
  (function checkLogout() {
    if (!(location.pathname === '/auth' || location.pathname.startsWith('/auth/'))) return;
    localStorage.removeItem('token');
    localStorage.removeItem('clapnclaw_token');
    localStorage.removeItem('clapnclaw_onboarded');
    localStorage.removeItem('clapnclaw_slug');
    sessionStorage.removeItem('cnc-session');
    window.location.replace(_hubUrl);
  })();

  // Reveal #app — custom.css hides it to prevent /auth flash while defer script loads.
  // If checkLogout() redirected, we never reach this line.
  (function revealApp() {
    var app = document.getElementById('app');
    if (app) { app.style.visibility = 'visible'; return; }
    document.addEventListener('DOMContentLoaded', function () {
      var a = document.getElementById('app'); if (a) a.style.visibility = 'visible';
    });
  })();

  // Track session flag (used by SPA navigation watcher below)
  if (localStorage.getItem('token')) {
    sessionStorage.setItem('cnc-session', '1');
  }

  function _doLogout() {
    var app = document.getElementById('app');
    if (app) app.style.visibility = 'hidden';
    localStorage.removeItem('token');
    localStorage.removeItem('clapnclaw_token');
    localStorage.removeItem('clapnclaw_onboarded');
    localStorage.removeItem('clapnclaw_slug');
    sessionStorage.removeItem('cnc-session');
    window.location.replace(_hubUrl);
  }

  // Watch for SPA navigation to /auth AND token removal (OWI v0.8+ logout)
  var _lastPath = location.pathname;
  setInterval(function () {
    if (location.pathname !== _lastPath) {
      _lastPath = location.pathname;
      if (location.pathname.startsWith('/auth')) { _doLogout(); return; }
    }
    var hasToken = !!localStorage.getItem('token');
    if (hasToken) {
      sessionStorage.setItem('cnc-session', '1');
    } else if (sessionStorage.getItem('cnc-session') && !hasToken) {
      // Token was removed while session was active — user logged out
      _doLogout();
    }
  }, 400);

  // ── 3. Splash screen (animated logo while OWI SPA loads) ────────────
  function showSplash() {
    if (!localStorage.getItem('token')) return; // login page handles itself
    if (document.getElementById('cnc-splash')) return;
    _injectLogoStyles();
    var splash = document.createElement('div');
    splash.id = 'cnc-splash';
    splash.style.cssText =
      'position:fixed;inset:0;z-index:99999;background:#ffffff;' +
      'display:flex;align-items:center;justify-content:center;' +
      'transition:opacity 0.5s ease;';
    var spinnerWrap = document.createElement('div');
    spinnerWrap.style.cssText = 'position:relative;width:88px;height:88px;';
    var spinSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    spinSvg.setAttribute('width', '88'); spinSvg.setAttribute('height', '88');
    spinSvg.setAttribute('viewBox', '0 0 88 88');
    spinSvg.style.cssText = 'position:absolute;top:0;left:0;animation:cncSpin 1s linear infinite;';
    var arc = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    arc.setAttribute('cx', '44'); arc.setAttribute('cy', '44'); arc.setAttribute('r', '38');
    arc.setAttribute('fill', 'none'); arc.setAttribute('stroke', '#0D5C3F');
    arc.setAttribute('stroke-width', '4'); arc.setAttribute('stroke-dasharray', '60 180');
    arc.setAttribute('stroke-linecap', 'round');
    spinSvg.appendChild(arc);
    spinnerWrap.appendChild(spinSvg);
    var logoCenter = document.createElement('div');
    logoCenter.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);';
    logoCenter.appendChild(_makeLogoEl(36));
    spinnerWrap.appendChild(logoCenter);
    splash.appendChild(spinnerWrap);
    document.documentElement.appendChild(splash);
    var checks = 0;
    var iv = setInterval(function () {
      checks++;
      var sidebar = document.querySelector('nav, #sidebar, [id*="sidebar"], [class*="sidebar"]');
      if ((sidebar && sidebar.children.length > 1) || checks > 50) {
        clearInterval(iv);
        splash.style.opacity = '0';
        setTimeout(function () { if (splash.parentNode) splash.parentNode.removeChild(splash); }, 500);
      }
    }, 150);
  }

  // ── 4. ClapNClaw logo SVG helpers ────────────────────────────────────
  var _logoStylesInjected = false;
  function _injectLogoStyles() {
    if (_logoStylesInjected) return;
    _logoStylesInjected = true;
    var s = document.createElement('style');
    s.textContent =
      '@keyframes cncFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}' +
      '@keyframes cncSpin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}' +
      '@keyframes cncL{0%,100%{transform:translateX(0) rotate(0deg)}20%{transform:translateX(5px) rotate(10deg)}40%{transform:translateX(-3px) rotate(-5deg)}60%{transform:translateX(2px) rotate(3deg)}}' +
      '@keyframes cncC{0%,100%{transform:translateY(0) scale(1)}20%{transform:translateY(-6px) scale(1.12)}40%{transform:translateY(1px) scale(.96)}60%{transform:translateY(-3px) scale(1.05)}}' +
      '@keyframes cncR{0%,100%{transform:translateX(0) rotate(0deg)}20%{transform:translateX(-5px) rotate(-10deg)}40%{transform:translateX(3px) rotate(5deg)}60%{transform:translateX(-2px) rotate(-3deg)}}';
    (document.head || document.documentElement).appendChild(s);
  }

  // Returns a live DOM element — use for direct insertion
  function _makeLogoEl(h) {
    _injectLogoStyles();
    var w = Math.round(44 * h / 30);
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', w); svg.setAttribute('height', h);
    svg.setAttribute('viewBox', '0 0 44 30'); svg.setAttribute('fill', 'none');
    svg.style.cssText = 'display:block;animation:cncFloat 2.5s ease-in-out infinite;flex-shrink:0;';
    [
      {pts:'7,27 14,3 21,27',  fill:'#0D5C3F', op:null, anim:'cncL 2s ease-in-out infinite'},
      {pts:'15,3 22,27 29,3',  fill:'#E07020', op:'.7', anim:'cncC 2s ease-in-out infinite'},
      {pts:'23,27 30,3 37,27', fill:'#0D5C3F', op:'.45',anim:'cncR 2s ease-in-out infinite'},
    ].forEach(function(p) {
      var poly = document.createElementNS(NS, 'polygon');
      poly.setAttribute('points', p.pts);
      poly.setAttribute('fill', p.fill);
      if (p.op) poly.setAttribute('opacity', p.op);
      poly.style.cssText = 'animation:' + p.anim + ';transform-origin:center;';
      svg.appendChild(poly);
    });
    return svg;
  }

  // Static (non-animated) logo — for inside the OWI sidebar
  function _makeStaticLogoEl(h) {
    var w = Math.round(44 * h / 30);
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', w); svg.setAttribute('height', h);
    svg.setAttribute('viewBox', '0 0 44 30'); svg.setAttribute('fill', 'none');
    svg.style.cssText = 'display:block;flex-shrink:0;';
    [
      {pts:'7,27 14,3 21,27',  fill:'#0D5C3F', op:null},
      {pts:'15,3 22,27 29,3',  fill:'#E07020', op:'.7'},
      {pts:'23,27 30,3 37,27', fill:'#0D5C3F', op:'.45'},
    ].forEach(function (p) {
      var poly = document.createElementNS(NS, 'polygon');
      poly.setAttribute('points', p.pts);
      poly.setAttribute('fill', p.fill);
      if (p.op) poly.setAttribute('opacity', p.op);
      svg.appendChild(poly);
    });
    return svg;
  }

  // Returns an SVG string — use inside innerHTML (styles already injected)
  function _logoSVG(h) {
    _injectLogoStyles();
    var w = Math.round(44 * h / 30);
    return '<svg width="' + w + '" height="' + h + '" viewBox="0 0 44 30" fill="none" ' +
      'style="display:block;animation:cncFloat 2.5s ease-in-out infinite;flex-shrink:0;">' +
      '<polygon points="7,27 14,3 21,27" fill="#0D5C3F" style="animation:cncL 2s ease-in-out infinite;transform-origin:center;"/>' +
      '<polygon points="15,3 22,27 29,3" fill="#E07020" opacity=".7" style="animation:cncC 2s ease-in-out infinite;transform-origin:center;"/>' +
      '<polygon points="23,27 30,3 37,27" fill="#0D5C3F" opacity=".45" style="animation:cncR 2s ease-in-out infinite;transform-origin:center;"/>' +
      '</svg>';
  }

  // ── 4. Login page enhancements ───────────────────────────────
  function enhanceLogin() {
    var pwInput = document.querySelector('input[type="password"]');
    var hasSidebar = document.querySelector('nav, [aria-label="Sidebar"]');
    if (!pwInput || hasSidebar) return;
    if (document.body.classList.contains('cnc-login')) return;
    document.body.classList.add('cnc-login');

    // Inject ClapNClaw logo above the form
    if (!document.querySelector('.cnc-login-logo')) {
      var form = document.querySelector('form');
      if (form) {
        var logoWrap = document.createElement('div');
        logoWrap.className = 'cnc-login-logo';
        logoWrap.style.cssText = 'text-align:center;margin-bottom:24px;';
        var logoEl = _makeLogoEl(52);
        logoEl.style.cssText += 'margin:0 auto;';
        logoWrap.appendChild(logoEl);
        form.parentElement.insertBefore(logoWrap, form);
      }
    }

    // Forgot password link
    var submitBtn = document.querySelector('button[type="submit"]');
    if (submitBtn && !document.querySelector('.cnc-forgot-pw')) {
      var a = document.createElement('a');
      a.className = 'cnc-forgot-pw';
      a.href = 'https://clapnclaw.io/forgot-password';
      a.textContent = 'Passwort vergessen?';
      a.style.cssText = 'display:block;text-align:right;margin-top:10px;color:#0D5C3F;font-size:13px;text-decoration:none;opacity:0.75;';
      a.onmouseenter = function () { this.style.opacity = '1'; };
      a.onmouseleave = function () { this.style.opacity = '0.75'; };
      submitBtn.parentElement.insertBefore(a, submitBtn.nextSibling);
    }

    // Google sign-in button — only show for new users, not returning ones
    var form = document.querySelector('form');
    var alreadyOnboarded = localStorage.getItem('clapnclaw_onboarded');
    if (form && !alreadyOnboarded && !document.querySelector('.cnc-google-btn')) {
      var divider = document.createElement('div');
      divider.style.cssText = 'display:flex;align-items:center;margin:20px 0 14px;';
      divider.innerHTML =
        '<hr style="flex:1;border:none;border-top:1px solid #e5e7eb;">' +
        '<span style="padding:0 12px;color:#9ca3af;font-size:13px;white-space:nowrap;">oder</span>' +
        '<hr style="flex:1;border:none;border-top:1px solid #e5e7eb;">';

      var btn = document.createElement('button');
      btn.className = 'cnc-google-btn';
      btn.type = 'button';
      btn.innerHTML =
        '<svg width="18" height="18" viewBox="0 0 48 48" style="flex-shrink:0">' +
        '<path fill="#4285F4" d="M47.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h13.1c-.6 3-2.3 5.5-4.9 7.2v6h7.9c4.6-4.3 7.4-10.6 7.4-17.2z"/>' +
        '<path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.9-6c-2.1 1.4-4.8 2.3-8 2.3-6.1 0-11.3-4.1-13.2-9.7H2.7v6.2C6.7 42.9 14.8 48 24 48z"/>' +
        '<path fill="#FBBC05" d="M10.8 28.8c-.5-1.4-.8-2.9-.8-4.8s.3-3.4.8-4.8v-6.2H2.7C1 17.1 0 20.5 0 24s1 6.9 2.7 9.7l8.1-4.9z"/>' +
        '<path fill="#EA4335" d="M24 9.5c3.4 0 6.5 1.2 8.9 3.5l6.7-6.7C35.9 2.4 30.5 0 24 0 14.8 0 6.7 5.1 2.7 14.3l8.1 4.9C12.7 13.6 17.9 9.5 24 9.5z"/>' +
        '</svg> Weiter mit Google';
      btn.style.cssText =
        'width:100%;display:flex;align-items:center;justify-content:center;gap:10px;' +
        'padding:11px;border:1.5px solid #e5e7eb;border-radius:12px;background:#fff;' +
        'font-size:14px;font-weight:500;color:#374151;cursor:pointer;transition:border-color 0.15s;';
      btn.onmouseenter = function () { this.style.borderColor = '#0D5C3F'; };
      btn.onmouseleave = function () { this.style.borderColor = '#e5e7eb'; };
      btn.onclick = function () {
        window.location.href = _apiUrl + '/api/auth/google?login=true';
      };

      form.appendChild(divider);
      form.appendChild(btn);

      // Security badge
      var badge = document.createElement('div');
      badge.style.cssText = 'text-align:center;font-size:12px;color:#9ca3af;margin-top:24px;padding-top:16px;border-top:1px solid #f3f4f6;';
      badge.innerHTML = '&#127465;&#127466; In Frankfurt gehostet &middot; DSGVO-konform';
      form.parentElement.appendChild(badge);
    }
  }

  // ── 4. Dismiss onboarding wizard ─────────────────────────────
  // The Svelte store reads localStorage.getItem('onboarding_completed') — set it directly.
  function dismissOnboarding() {
    localStorage.setItem('onboarding_completed', 'true');
  }

  showSplash();
  setTimeout(dismissOnboarding, 2000);
  setInterval(enhanceLogin, 500);

  // ── 5. Sidebar logo + ClapNClaw panel ────────────────────────

  function tryReplaceLogo() {
    // Strategy 1: expanded sidebar — logo is inside <a href="/">
    var sidebar = document.querySelector('#sidebar, [id*="sidebar"], nav, aside');
    if (sidebar) {
      var logoEl = sidebar.querySelector('a[href="/"] svg, a[href="/"] img');
      if (logoEl && !logoEl.dataset.cncDone) {
        logoEl.dataset.cncDone = '1';
        logoEl.replaceWith(_makeStaticLogoEl(28));
        return;
      }
    }

    // Strategy 2: collapsed/icon sidebar — logo is always in the top-left corner.
    // Use bounding rect: x < 80px, y < 80px, rendered size ≤ 80px.
    // This reliably distinguishes the logo from nav icons further down the sidebar.
    var all = Array.from(document.querySelectorAll('svg, img'));
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      if (el.dataset.cncDone) continue;
      var r = el.getBoundingClientRect();
      if (r.width > 0 && r.width <= 80 && r.left < 80 && r.top < 80) {
        el.dataset.cncDone = '1';
        el.replaceWith(_makeStaticLogoEl(28));
        return;
      }
    }
  }

  // Replace OI model badges with ClapNClaw logo.
  // OWI renders model initials ("OI") as styled div/span — we swap the content in-place
  // so OWI's SPA refs stay intact. MutationObserver re-runs this after any re-render.
  function replaceModelIcon() {
    _injectLogoStyles();
    var all = Array.from(document.querySelectorAll('div, span'));
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      // Skip elements that already contain our logo
      if (el.querySelector('svg[data-cnc-icon]')) continue;
      var txt = (el.textContent || '').trim();
      if (!/^O[Ii]$/.test(txt)) continue;
      var cs = window.getComputedStyle(el);
      var hasBg = cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent';
      var hasRadius = parseFloat(cs.borderRadius) > 4;
      if (!hasBg && !hasRadius) continue;
      var r = el.getBoundingClientRect();
      if (r.width <= 0) continue;
      // Replace OI text with ClapNClaw logo, keeping element in place
      var h = Math.max(12, Math.min(Math.round(r.height * 0.65), 20));
      el.innerHTML = '';
      el.style.background = 'transparent';
      el.style.border = 'none';
      el.style.overflow = 'visible';
      el.style.display = 'flex';
      el.style.alignItems = 'center';
      el.style.justifyContent = 'center';
      var logo = _makeStaticLogoEl(h);
      logo.setAttribute('data-cnc-icon', '1');
      el.appendChild(logo);
    }
  }

  // ── 5a. Sidebar: token bar + models panel ────────────────────────
  var _CNC_API = '/api/v1/clapnclaw';
  var _tokenData = { used: 0, limit: 0 };
  var _modelsOpen = false;

  function injectTokenBar() {
    if (document.getElementById('cnc-token-bar-wrap')) return;
    var sidebar = document.querySelector('#sidebar, [id*="sidebar"], nav, aside');
    if (!sidebar) return;
    var footer = sidebar.querySelector('[id*="footer"], div:last-child') || sidebar;

    var wrap = document.createElement('div');
    wrap.id = 'cnc-token-bar-wrap';
    wrap.style.cssText =
      'padding:8px 10px 4px;margin:0 4px 2px;';
    wrap.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +
        '<span style="font-size:11px;color:var(--color-gray-400,#888);font-family:-apple-system,sans-serif;">Tokens</span>' +
        '<span id="cnc-token-txt" style="font-size:11px;color:var(--color-gray-300,#ccc);font-family:-apple-system,sans-serif;">\u2013</span>' +
      '</div>' +
      '<div style="background:rgba(255,255,255,0.1);border-radius:3px;height:3px;overflow:hidden;">' +
        '<div id="cnc-token-fill" style="background:#0D5C3F;height:3px;width:0%;border-radius:3px;transition:width .5s;"></div>' +
      '</div>';
    footer.prepend(wrap);

    // Load token data
    var _tok = localStorage.getItem('token') || '';
    fetch(_CNC_API + '/tokens/usage', {
      headers: _tok ? { 'Authorization': 'Bearer ' + _tok } : {}
    })
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) {
        if (!d) return;
        _tokenData = { used: d.tokens_used || 0, limit: d.token_limit || 0 };
        var pct = _tokenData.limit > 0 ? Math.min(100, (_tokenData.used / _tokenData.limit) * 100) : 0;
        var fill = document.getElementById('cnc-token-fill');
        if (fill) {
          fill.style.width = pct + '%';
          fill.style.background = pct > 85 ? '#e53e3e' : pct > 65 ? '#d97706' : '#0D5C3F';
        }
        var txt = document.getElementById('cnc-token-txt');
        if (txt) txt.textContent = _fmt(d.tokens_used || 0) + ' / ' + _fmt(d.token_limit || 0);
      })
      .catch(function() {});
  }

  function _fmt(n) {
    return n >= 1000000 ? (n / 1000000).toFixed(1) + 'M' : n >= 1000 ? Math.round(n / 1000) + 'K' : String(n);
  }

  // ── Models panel ─────────────────────────────────────────────
  var _MODELS = [
    { id: 'claude-haiku-4-5',   name: 'Claude Haiku 4.5',    provider: 'Anthropic',  bg: '#CC785C', label: 'A', active: true  },
    { id: 'claude-sonnet-4-6',  name: 'Claude Sonnet 4.6',   provider: 'Anthropic',  bg: '#CC785C', label: 'A', active: true  },
    { id: 'claude-opus-4-6',    name: 'Claude Opus 4.6',     provider: 'Anthropic',  bg: '#CC785C', label: 'A', active: true  },
    { id: 'claude-3-5-sonnet',  name: 'Claude 3.5 Sonnet',   provider: 'Anthropic',  bg: '#CC785C', label: 'A', active: true  },
    { id: 'claude-3-5-haiku',   name: 'Claude 3.5 Haiku',    provider: 'Anthropic',  bg: '#CC785C', label: 'A', active: true  },
    { id: 'mistral-large',      name: 'Mistral Large',        provider: 'Mistral',    bg: '#F54E2E', label: 'M', active: true  },
    { id: 'mistral-small',      name: 'Mistral Small',        provider: 'Mistral',    bg: '#F54E2E', label: 'M', active: true  },
    { id: 'codestral',          name: 'Codestral',            provider: 'Mistral',    bg: '#F54E2E', label: 'M', active: true  },
  ];

  function _modelBadge(m) {
    return '<div style="width:24px;height:24px;border-radius:6px;background:' + m.bg + ';' +
      'display:flex;align-items:center;justify-content:center;flex-shrink:0;' +
      'font-size:10px;font-weight:700;color:#fff;font-family:-apple-system,sans-serif;">' + m.label + '</div>';
  }

  function injectModelsLink() {
    if (document.getElementById('cnc-models-link')) return;
    var sidebar = document.querySelector('#sidebar, [id*="sidebar"], nav, aside');
    if (!sidebar) return;
    var dashLink = document.getElementById('cnc-dash-link');

    var anchor = document.createElement('button');
    anchor.id = 'cnc-models-link';
    anchor.style.cssText =
      'display:flex;align-items:center;gap:8px;width:100%;padding:8px 10px;border-radius:8px;' +
      'background:none;border:none;color:var(--color-gray-300,#ccc);cursor:pointer;font-size:13px;font-weight:500;' +
      'text-align:left;transition:background 0.15s;margin-bottom:4px;';
    anchor.innerHTML =
      '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="flex-shrink:0;">' +
        '<rect x="1" y="9" width="3" height="6" rx="1" fill="currentColor" opacity="0.9"/>' +
        '<rect x="6" y="6" width="3" height="9" rx="1" fill="currentColor" opacity="0.7"/>' +
        '<rect x="11" y="3" width="3" height="12" rx="1" fill="currentColor" opacity="0.5"/>' +
        '<path d="M2.5 8.5L7.5 5.5L12.5 2.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>' +
      '</svg>' +
      '<span>Modelos</span>';
    anchor.onmouseenter = function() { this.style.background = 'rgba(13,92,63,0.15)'; };
    anchor.onmouseleave = function() { this.style.background = 'none'; };
    anchor.onclick = function() { toggleModelsPanel(); };

    if (dashLink && dashLink.nextSibling) dashLink.parentNode.insertBefore(anchor, dashLink.nextSibling);
    else if (dashLink) dashLink.parentNode.appendChild(anchor);
    else sidebar.prepend(anchor);
  }

  function toggleModelsPanel() {
    var panel = document.getElementById('cnc-models-panel');
    if (panel) { panel.parentNode.removeChild(panel); _modelsOpen = false; return; }
    _modelsOpen = true;

    var p = document.createElement('div');
    p.id = 'cnc-models-panel';
    p.style.cssText =
      'position:fixed;left:260px;top:60px;z-index:9999;width:320px;' +
      'background:var(--color-gray-900,#111);border:1px solid var(--color-gray-700,#333);' +
      'border-radius:14px;padding:20px;box-shadow:0 12px 40px rgba(0,0,0,.6);' +
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;';

    var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">' +
      '<span style="font-size:14px;font-weight:600;color:#f0f0f0;">Verf\xfcgbare Modelle</span>' +
      '<button onclick="document.getElementById(\'cnc-models-panel\').remove()" ' +
        'style="background:none;border:none;color:#666;cursor:pointer;font-size:18px;line-height:1;">\xd7</button>' +
    '</div>';

    // Group by provider
    var providers = {};
    _MODELS.forEach(function(m) {
      if (!providers[m.provider]) providers[m.provider] = [];
      providers[m.provider].push(m);
    });

    Object.keys(providers).forEach(function(prov) {
      html += '<div style="font-size:10px;font-family:monospace;letter-spacing:.1em;text-transform:uppercase;' +
        'color:#555;margin-bottom:8px;margin-top:12px;">' + prov + '</div>';
      providers[prov].forEach(function(m) {
        html += '<div style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:8px;' +
          'margin-bottom:4px;background:#1a1a1a;">' +
          _modelBadge(m) +
          '<div style="flex:1;min-width:0;">' +
            '<div style="font-size:13px;color:#e0e0e0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + m.name + '</div>' +
            '<div style="font-size:11px;color:#555;margin-top:1px;">' + m.provider + ' \xb7 EU Frankfurt</div>' +
          '</div>' +
          '<div style="width:7px;height:7px;border-radius:50%;background:' + (m.active ? '#0D5C3F' : '#555') + ';flex-shrink:0;"></div>' +
        '</div>';
      });
    });

    p.innerHTML = html;
    document.body.appendChild(p);

    // Close on outside click
    setTimeout(function() {
      document.addEventListener('click', function handler(e) {
        var panel = document.getElementById('cnc-models-panel');
        var btn = document.getElementById('cnc-models-link');
        if (panel && !panel.contains(e.target) && e.target !== btn && !(btn && btn.contains(e.target))) {
          panel.remove(); _modelsOpen = false;
          document.removeEventListener('click', handler);
        }
      });
    }, 0);
  }

  // ── 5b. Hide unneeded OWI nav items ──────────────────────────────
  // Controls = model parameter sliders (dev tool). Playground = sandbox (dev tool). Notes = notepad.
  // German equivalents included since OWI may be localized.
  var _HIDDEN_LABELS = [
    'Controls', 'Playground', 'Notes', 'Steuerung', 'Notizen',
    'Model Options', 'Modelloptionen', 'Admin', 'Admin Panel', 'Workspace',
    'Documentation', 'Dokumentation', 'Release Notes', 'Releases',
    'Keyboard Shortcuts', 'Tastenkombinationen'
  ];
  var _HIDDEN_HREFS = ['/playground', '/admin', '/workspace'];

  function hideUnneededItems() {
    // Hide by aria-label / title across the whole document (catches toolbar buttons)
    document.querySelectorAll(
      '[aria-label="Controls"], [aria-label="Steuerung"], [aria-label="Model Options"],' +
      '[aria-label="Modelloptionen"], [aria-label="Playground"], [aria-label="Notes"],' +
      '[aria-label="Notizen"], [title="Controls"], [title="Playground"], [title="Notes"],' +
      '[title="Steuerung"], [title="Notizen"],' +
      '[aria-label="Open User Menu"], [aria-label="User Menu"], [aria-label="Open menu"],' +
      '[aria-label="Benutzerprofil"], [aria-label="Account"], [aria-label="Profile"]'
    ).forEach(function(el) {
      el.style.setProperty('display', 'none', 'important');
      var li = el.closest('li');
      if (li) li.style.setProperty('display', 'none', 'important');
    });

    // Hide by href
    _HIDDEN_HREFS.forEach(function(href) {
      document.querySelectorAll('a[href="' + href + '"], a[href*="' + href.slice(1) + '"]').forEach(function(el) {
        el.style.setProperty('display', 'none', 'important');
        var li = el.closest('li');
        if (li) li.style.setProperty('display', 'none', 'important');
      });
    });

    // Hide sidebar items by text label
    var sidebar = document.querySelector('#sidebar, [id*="sidebar"], nav, aside');
    if (!sidebar) return;
    sidebar.querySelectorAll('a[href], button').forEach(function(el) {
      if (el.dataset.cncHideChecked) return;
      el.dataset.cncHideChecked = '1';
      var label = (el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim();
      if (_HIDDEN_LABELS.indexOf(label) >= 0) {
        el.style.setProperty('display', 'none', 'important');
        var li = el.closest('li');
        if (li) li.style.setProperty('display', 'none', 'important');
      }
    });
  }

  // ── 5c. Model logos ───────────────────────────────────────────────
  var _MODEL_LOGO_RULES = [
    { match: /claude|anthropic/i,    bg: '#CC785C', label: 'A',  shape: 'tri' },
    { match: /gpt|openai|o[13]-/i,   bg: '#10a37f', label: 'O',  shape: 'circle' },
    { match: /mistral|mixtral/i,     bg: '#F54E2E', label: 'M',  shape: 'rect' },
    { match: /gemini|google/i,       bg: '#4285F4', label: 'G',  shape: 'rect' },
    { match: /llama|meta/i,          bg: '#0866FF', label: 'Ll', shape: 'rect' },
    { match: /deepseek/i,            bg: '#6c47ff', label: 'DS', shape: 'rect' },
  ];

  function _modelLogoSVG(rule) {
    var b = rule.bg;
    var inner = rule.shape === 'tri'
      ? '<polygon points="8,2 14,14 2,14" fill="white" opacity="0.9"/>'
      : rule.shape === 'circle'
        ? '<circle cx="8" cy="8" r="4.5" fill="none" stroke="white" stroke-width="1.8"/>'
        : '<text x="8" y="11.5" font-size="7" font-weight="700" fill="white" text-anchor="middle" font-family="system-ui">' + rule.label + '</text>';
    return '<svg width="16" height="16" viewBox="0 0 16 16" data-cnc-mlogo="1" ' +
      'style="flex-shrink:0;display:inline-block;vertical-align:middle;margin-right:5px;border-radius:3px;">' +
      '<rect width="16" height="16" rx="3" fill="' + b + '"/>' + inner + '</svg>';
  }

  function injectModelLogos() {
    // Target model name spans in the selector dropdown and model list
    document.querySelectorAll(
      '[data-model-id], [class*="model-name"], [class*="modelName"], ' +
      '.model-item span, [class*="option"] span'
    ).forEach(function(el) {
      if (el.dataset.cncMlogo || el.querySelector('[data-cnc-mlogo]')) return;
      var name = (el.dataset.modelId || el.textContent || '').trim();
      if (!name) return;
      for (var i = 0; i < _MODEL_LOGO_RULES.length; i++) {
        if (_MODEL_LOGO_RULES[i].match.test(name)) {
          el.dataset.cncMlogo = '1';
          var wrapper = document.createElement('span');
          wrapper.style.cssText = 'display:inline-flex;align-items:center;gap:0;';
          wrapper.innerHTML = _modelLogoSVG(_MODEL_LOGO_RULES[i]);
          el.insertBefore(wrapper, el.firstChild);
          break;
        }
      }
    });
  }

  // ── 5d. Dashboard shortcut in sidebar ────────────────────────────
  function injectDashboardLink() {
    if (document.getElementById('cnc-dash-link')) return;
    var sidebar = document.querySelector('#sidebar, [id*="sidebar"], nav, aside');
    if (!sidebar) return;
    // Place it at the top of the sidebar, before history
    var target = sidebar.querySelector('a[href="/"], a[href*="new"], button[title*="New"]');
    var anchor = document.createElement('a');
    anchor.id = 'cnc-dash-link';
    anchor.href = _hubUrl;
    anchor.target = '_blank';
    anchor.title = 'Dashboard';
    anchor.style.cssText =
      'display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;' +
      'color:var(--color-gray-300,#ccc);text-decoration:none;font-size:13px;font-weight:500;' +
      'transition:background 0.15s;margin-bottom:4px;';
    anchor.innerHTML =
      '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="flex-shrink:0;">' +
      '<rect x="1" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.9"/>' +
      '<rect x="9" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.6"/>' +
      '<rect x="1" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.6"/>' +
      '<rect x="9" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.3"/>' +
      '</svg>' +
      '<span>Dashboard</span>';
    anchor.onmouseenter = function() { this.style.background = 'rgba(13,92,63,0.15)'; };
    anchor.onmouseleave = function() { this.style.background = 'none'; };
    if (target) target.parentNode.insertBefore(anchor, target);
    else sidebar.prepend(anchor);
  }

  // ── V1 cleanup: rename models, hide OWI branding, clean settings ──────────
  var _MODEL_NAMES = { 'default': 'Claude Haiku', 'complex': 'Claude Sonnet' };
  // Models that should remain visible — all others are hidden (admin bypass safety net)
  // clapnclaw-ai = personalized sector assistant created by configure_owui.py
  var _ALLOWED_MODELS = ['default', 'complex', 'mistral', 'clapnclaw-ai',
    'Claude Haiku', 'Claude Sonnet', 'Mistral',
    'Rechtsassistent', 'Praxisassistent', 'Steuerberater-Assistent', 'Unternehmensassistent'];

  function cleanupOwi() {
    // 1. Rename model display names in selector and chat header
    document.querySelectorAll('button, span, div, option').forEach(function (el) {
      if (el.children.length > 0) return; // skip elements with children
      var t = el.textContent.trim();
      if (_MODEL_NAMES[t]) {
        el.textContent = _MODEL_NAMES[t];
      }
    });

    // 1b. Hide non-ClapNClaw models from model selector (handles admin bypass)
    // OWI renders models as list items with data-value or data-model-id attributes
    document.querySelectorAll('[data-model-id], [data-value]').forEach(function (el) {
      var name = (el.getAttribute('data-model-id') || el.getAttribute('data-value') || '').trim();
      if (!name) return;
      if (_ALLOWED_MODELS.indexOf(name) < 0) {
        var row = el.closest('li, [role="option"], [role="listitem"]') || el.parentElement;
        if (row && row !== el) row.style.setProperty('display', 'none', 'important');
        else el.style.setProperty('display', 'none', 'important');
      }
    });
    // Also hide option elements in native selects
    document.querySelectorAll('select option').forEach(function (opt) {
      var v = (opt.value || opt.textContent || '').trim();
      if (v && _ALLOWED_MODELS.indexOf(v) < 0) {
        opt.style.setProperty('display', 'none', 'important');
      }
    });

    // 2. Replace OI circular logos in model list with ClapNClaw icon
    var cncSvg = '<svg viewBox="0 0 44 30" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">' +
      '<polygon points="7,27 14,3 21,27" fill="#0D5C3F"/>' +
      '<polygon points="15,3 22,27 29,3" fill="#E07020" opacity="0.7"/>' +
      '<polygon points="23,27 30,3 37,27" fill="#0D5C3F" opacity="0.45"/>' +
      '</svg>';
    document.querySelectorAll('img.rounded-full, img[alt="OpenAI"], img[src*="openai"]').forEach(function (img) {
      if (img.dataset.cncReplaced) return;
      img.dataset.cncReplaced = '1';
      var wrap = document.createElement('span');
      wrap.style.cssText = 'display:inline-flex;width:' + (img.width || 20) + 'px;height:' + (img.height || 20) + 'px;border-radius:6px;overflow:hidden;flex-shrink:0;';
      wrap.innerHTML = cncSvg;
      img.parentNode.replaceChild(wrap, img);
    });

    // 3. Hide about dialog OWI branding elements by text
    document.querySelectorAll('a').forEach(function (a) {
      var href = a.href || '';
      if (href.includes('discord.gg') || href.includes('open-webui') || href.includes('tjbck')) {
        var parent = a.closest('div, p, span');
        if (parent) parent.style.display = 'none';
        else a.style.display = 'none';
      }
    });

    // 4. Hide settings nav items by text label (Audio, Connections, Memory)
    var _hideNavLabels = ['audio', 'sprache', 'verbindung', 'connection', 'erinnerung', 'memory', 'tool-server', 'terminal'];
    document.querySelectorAll('nav button, [role="tab"], [role="menuitem"]').forEach(function (btn) {
      var label = (btn.textContent || btn.getAttribute('aria-label') || '').toLowerCase();
      if (_hideNavLabels.some(function (k) { return label.includes(k); })) {
        btn.style.display = 'none';
      }
    });

    // 5. Hide webhook input row in profile settings
    document.querySelectorAll('input').forEach(function (inp) {
      var ph = (inp.placeholder || inp.name || '').toLowerCase();
      if (ph.includes('webhook')) {
        var row = inp.closest('div.flex, div.form-group, label') || inp.parentElement;
        if (row) row.style.display = 'none';
      }
    });

    // 6. Hide "Nach Updates suchen" / "Check for updates" button in about
    document.querySelectorAll('button').forEach(function (btn) {
      var t = (btn.textContent || '').trim().toLowerCase();
      if (t.includes('update') && (t.includes('suchen') || t.includes('check'))) {
        btn.style.display = 'none';
      }
    });

    // 7. Hide blue cross / scroll-to-bottom / fixed bottom-right buttons
    document.querySelectorAll(
      '[data-testid="scroll-to-bottom-button"], [aria-label="Scroll to bottom"],' +
      '[aria-label="Nach unten scrollen"], button[class*="scroll-bottom"],' +
      'button[class*="scrollBottom"], .scroll-to-bottom'
    ).forEach(function(el) {
      el.style.setProperty('display', 'none', 'important');
    });
    // Generic: hide any fixed-position button at bottom-right corner with blue color
    document.querySelectorAll('button[style*="fixed"], button[class*="fixed"]').forEach(function(btn) {
      var s = window.getComputedStyle(btn);
      if (s.position === 'fixed' && parseInt(s.bottom || '999') < 120 && parseInt(s.right || '999') < 120) {
        btn.style.setProperty('display', 'none', 'important');
      }
    });

    // 8. Pre-select default model (Claude Haiku) if none chosen
    if (!localStorage.getItem('model')) {
      localStorage.setItem('model', 'default');
    }
  }

  var _debounce = null;
  var _observer = new MutationObserver(function () {
    clearTimeout(_debounce);
    _debounce = setTimeout(function () {
      tryReplaceLogo();
      replaceModelIcon();
      hideUnneededItems();
      injectModelLogos();
      injectDashboardLink();
      injectModelsLink();
      injectTokenBar();
      cleanupOwi();
    }, 200);
  });

  function bootPanel() {
    tryReplaceLogo();
    replaceModelIcon();
    hideUnneededItems();
    injectModelLogos();
    injectDashboardLink();
    injectModelsLink();
    injectTokenBar();
    cleanupOwi();
    _observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootPanel);
  } else {
    bootPanel();
  }

})();
