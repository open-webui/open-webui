/* Swept rebrand — runtime DOM patch.
 *
 * Removes non-Swept theme presets (oled-dark, her) from any <select> the
 * Settings UI mounts. Doing this in JS rather than via `option { display: none }`
 * because Safari/iOS ignore CSS on <option> elements. Loaded before
 * %sveltekit.head% via the `<script src="/static/loader.js" defer>` tag in
 * src/app.html, but uses a MutationObserver because the picker isn't in the
 * DOM until the user opens Settings.
 */
(function () {
	var BLOCKED = ['oled-dark', 'her'];

	function purgeIn(node) {
		if (!node || node.nodeType !== 1) return;
		var sels = node.tagName === 'SELECT' ? [node] : node.querySelectorAll('select');
		for (var i = 0; i < sels.length; i++) {
			for (var j = 0; j < BLOCKED.length; j++) {
				var opt = sels[i].querySelector('option[value="' + BLOCKED[j] + '"]');
				if (opt) opt.remove();
			}
		}
	}

	function init() {
		purgeIn(document.body);
		var mo = new MutationObserver(function (mutations) {
			for (var i = 0; i < mutations.length; i++) {
				var added = mutations[i].addedNodes;
				for (var j = 0; j < added.length; j++) purgeIn(added[j]);
			}
		});
		mo.observe(document.body, { childList: true, subtree: true });
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

/* Swept embedded shell injector.
 *
 * Mounts a workbench-styled left rail when /api/config returns a non-empty
 * workbench_url. Pure DOM injection — no Svelte source edits — and no-op when
 * the env var is unset, so vanilla open-webui behavior is preserved.
 */
(function () {
	var ICONS = {
		'message-square':
			'<path d="M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z"/>',
		'shield-alert':
			'<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
		'layout-dashboard':
			'<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
		eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
		'book-open':
			'<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
		'sliders-horizontal':
			'<path d="M10 5H3"/><path d="M12 19H3"/><path d="M14 3v4"/><path d="M16 17v4"/><path d="M21 12h-9"/><path d="M21 19h-5"/><path d="M21 5h-7"/><path d="M8 10v4"/><path d="M8 12H3"/>',
		'shield-check':
			'<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
		'panel-left': '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/>',
		'panel-left-close':
			'<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="m16 15-3-3 3-3"/>',
		'panel-left-open':
			'<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="m14 9 3 3-3 3"/>',
		/* Added to cover icons that Workbench's sidebar endpoint can
		 * return for items that may appear in this shell (Usage,
		 * admin's API + Developer Tools when an admin signs in). */
		'chart-bar':
			'<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M7 16h8"/><path d="M7 11h12"/><path d="M7 6h3"/>',
		'key-round':
			'<path d="M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z"/><circle cx="16.5" cy="7.5" r=".5" fill="currentColor"/>',
		wrench:
			'<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>'
	};

	/* Cookie that controls collapse state. Shared with swept-workbench and
	 * with the inner Open WebUI sidebar (see src/lib/utils/sidebar-cookie.ts).
	 * When deployed under a *.swept.ai parent, the cookie carries
	 * Domain=.swept.ai so collapsing in one app propagates to all of them. */
	var COOKIE_NAME = 'swept_sidebar_collapsed';
	var COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
	/* Keep in sync with KNOWN_PARENTS in src/lib/utils/swept-cookies.ts. */
	var KNOWN_PARENTS = ['swept.ai', 'sweptai.psmic.com'];

	function cookieDomain() {
		var host = window.location.hostname;
		if (!host || host === 'localhost') return null;
		if (/^\d+\.\d+\.\d+\.\d+$/.test(host)) return null;
		if (host.indexOf(':') !== -1) return null;
		var matched = null;
		for (var i = 0; i < KNOWN_PARENTS.length; i++) {
			var p = KNOWN_PARENTS[i];
			if (
				(host === p || host.indexOf('.' + p, host.length - p.length - 1) !== -1) &&
				(!matched || p.length > matched.length)
			) {
				matched = p;
			}
		}
		if (!matched) return null;
		if (host === matched) return '.' + matched;
		var labels = host.split('.');
		return '.' + labels.slice(1).join('.');
	}

	function readCookie() {
		var m = document.cookie.match(new RegExp('(?:^|; )' + COOKIE_NAME + '=([^;]*)'));
		if (!m) return null;
		try {
			var v = decodeURIComponent(m[1]);
			if (v === 'true') return true;
			if (v === 'false') return false;
		} catch (e) {}
		return null;
	}

	function writeCookie(collapsed) {
		var parts = [
			COOKIE_NAME + '=' + encodeURIComponent(collapsed ? 'true' : 'false'),
			'Path=/',
			'Max-Age=' + COOKIE_MAX_AGE,
			'SameSite=Lax'
		];
		var dom = cookieDomain();
		if (dom) parts.push('Domain=' + dom);
		if (window.location.protocol === 'https:') parts.push('Secure');
		document.cookie = parts.join('; ');
	}

	function initialCollapsed() {
		var fouc = window.__sweptSidebarCollapsed;
		if (fouc === true || fouc === false) return fouc;
		var cookie = readCookie();
		if (cookie !== null) return cookie;
		return false;
	}

	/* Swept symbol (gradient mark). Same SVG used by swept-workbench's
	 * _swept_symbol partial and src/lib/components/icons/SweptSymbol.svelte —
	 * the gradient id is unique to the shell so it can co-exist with the
	 * Svelte sidebar's identical gradient on the same page. */
	var SYMBOL_SVG =
		'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 35 34" fill="none" class="swept-shell__symbol-svg" aria-hidden="true">' +
		'<path d="M0.5 16.9993C0.5 26.3734 8.21981 33.9986 17.7084 33.9986C27.1969 33.9986 34.9153 26.372 34.9153 16.9993C34.9153 7.62664 27.1955 0 17.7084 0C8.2212 0 0.5 7.62664 0.5 16.9993ZM12.4523 17.0172C12.4523 17.0406 12.4523 17.0626 12.4523 17.0846C12.4119 19.1471 9.22534 19.0989 9.2156 17.0365C9.21281 16.4613 9.26991 15.8766 9.38968 15.2918C10.0874 11.8754 12.9467 9.20481 16.4368 8.70123C21.6804 7.94585 26.1997 11.9607 26.1997 16.9993C26.1997 17.031 26.1997 17.0626 26.1997 17.0956C26.176 19.1471 23.0132 19.1567 22.9631 17.1053C22.9631 17.0709 22.9631 17.0351 22.9631 17.0007C22.9631 13.3628 19.154 10.5862 15.2697 12.3584C13.462 13.1839 12.462 15.0497 12.4537 17.0172H12.4523ZM15.1332 16.9993C15.1332 15.4941 16.4647 14.2902 18.0259 14.4759C19.3323 14.6314 20.2626 15.7981 20.2807 17.0984C20.3336 20.9151 23.4937 24.004 27.3696 24.004H27.8236C28.8501 24.004 29.825 23.7825 30.7065 23.3931C30.6982 23.4083 30.6912 23.4248 30.6829 23.4399C29.4447 25.8656 26.5772 27.0902 23.9394 26.3211C22.1748 25.8079 20.303 24.5847 18.9409 21.9457C18.7571 21.5893 18.4479 21.2908 18.0551 21.1889C17.4201 21.0252 16.7864 21.3252 16.5078 21.8755C15.1318 24.5861 13.2043 25.8175 11.3994 26.3238C8.77828 27.0586 5.94551 25.8285 4.72131 23.4248L4.7046 23.3931C5.58619 23.7825 6.56109 24.004 7.58751 24.004H8.04154C11.9509 24.004 15.1318 20.8615 15.1318 16.9993H15.1332ZM10.1376 29.2435C12.6946 29.0013 15.551 27.8855 17.7084 25.003C19.8643 27.8841 22.7207 29 25.2791 29.2435C23.0731 30.5795 20.4812 31.3514 17.7084 31.3514C14.9355 31.3514 12.3436 30.5795 10.1376 29.2435ZM32.2343 16.9993C32.2343 19.3521 30.3347 21.2701 27.9713 21.3486C28.5646 19.9837 28.8807 18.5114 28.8807 16.9993C28.8807 10.9123 23.8683 5.9618 17.7084 5.9618C11.5484 5.9618 6.53462 10.9137 6.53462 16.9993C6.53462 18.5114 6.84938 19.9837 7.44267 21.3486C5.07924 21.2715 3.17958 19.3535 3.17958 16.9993C3.17958 9.08648 9.69608 2.64862 17.707 2.64862C25.7178 2.64862 32.233 9.08648 32.233 16.9993H32.2343Z" fill="url(#sweptShellSymbolGradient)"/>' +
		'<defs>' +
		'<linearGradient id="sweptShellSymbolGradient" x1="5.5458" y1="29.0151" x2="29.5742" y2="4.69317" gradientUnits="userSpaceOnUse">' +
		'<stop stop-color="#1A237E"/>' +
		'<stop offset="0.69" stop-color="#1E88E5"/>' +
		'<stop offset="1" stop-color="#4DD0E1"/>' +
		'</linearGradient>' +
		'</defs>' +
		'</svg>';

	/* Swept wordmark — copied verbatim from
	 * swept-workbench/app/views/shared/_swept_wordmark.html.erb. The "S" mark
	 * uses a baked linear gradient (#1A237E → #1E88E5 → #4DD0E1); wordmark
	 * paths are currentColor so they pick up .swept-shell__logo's color. */
	var WORDMARK_SVG =
		'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 173 34" fill="none" class="h-7 w-auto">' +
		'<g clip-path="url(#sweptShellClip)">' +
		'<path d="M54.6486 10.9591C54.9286 11.3003 55.0692 11.6415 55.0692 11.9828C55.0692 12.3446 54.8854 12.6762 54.5191 12.9734C54.2823 13.144 53.9801 13.2293 53.6124 13.2293C53.0512 13.2293 52.5442 13.0271 52.0916 12.6212C51.5526 12.1314 50.9802 11.7846 50.3758 11.5824C49.7713 11.3801 49.0374 11.2783 48.1753 11.2783C47.1823 11.2783 46.3676 11.4434 45.7311 11.7736C45.0946 12.1038 44.7757 12.5675 44.7757 13.1647C44.7757 13.5912 44.8829 13.9475 45.1002 14.2365C45.3161 14.5241 45.7255 14.791 46.3299 15.0359C46.9344 15.2808 47.809 15.5202 48.9524 15.7555C51.3047 16.2247 52.9718 16.8755 53.9537 17.7065C54.9355 18.5376 55.4258 19.6149 55.4258 20.9371C55.4258 21.9182 55.1556 22.8084 54.6166 23.6078C54.0776 24.4072 53.2838 25.036 52.2378 25.4941C51.1905 25.9523 49.9343 26.1821 48.4664 26.1821C46.9985 26.1821 45.6183 25.9578 44.3231 25.5107C43.0278 25.0635 42.0139 24.476 41.28 23.7522C41 23.4757 40.8594 23.1441 40.8594 22.7616C40.8594 22.2498 41.0752 21.8342 41.507 21.515C41.9164 21.2165 42.2939 21.0665 42.6393 21.0665C43.071 21.0665 43.4805 21.2591 43.869 21.6416C44.2785 22.0902 44.8941 22.4782 45.7144 22.8098C46.5347 23.14 47.4079 23.3051 48.3368 23.3051C49.5666 23.3051 50.522 23.1028 51.2017 22.6969C51.8813 22.291 52.2211 21.7489 52.2211 21.0665C52.2211 20.384 51.8869 19.8571 51.217 19.4195C50.5485 18.9834 49.4148 18.6146 47.8188 18.316C43.6754 17.5277 41.6045 15.8435 41.6045 13.2637C41.6045 12.2194 41.9164 11.3347 42.5432 10.6096C43.1685 9.8845 43.9888 9.34101 45.0027 8.97915C46.018 8.61729 47.0959 8.43567 48.2408 8.43567C49.6432 8.43567 50.8994 8.65994 52.0122 9.10711C53.1236 9.55428 54.0024 10.1721 54.65 10.9618L54.6486 10.9591Z" fill="currentColor"/>' +
		'<path d="M79.7661 9.87212C79.7661 10.2133 79.7118 10.5229 79.6046 10.7995L74.8137 24.9974C74.7064 25.296 74.5114 25.5464 74.2301 25.7487C73.9502 25.951 73.6368 26.0528 73.2914 26.0528C72.9251 26.0528 72.5951 25.951 72.304 25.7487C72.0129 25.5464 71.8235 25.296 71.7372 24.9974L68.5646 13.3889L65.2304 24.9974C65.1232 25.296 64.9226 25.5464 64.6315 25.7487C64.3405 25.951 64.0215 26.0528 63.6761 26.0528C63.3307 26.0528 63.0132 25.951 62.7207 25.7487C62.4297 25.5464 62.2291 25.296 62.1219 24.9974L57.3309 10.7995C57.2446 10.5229 57.2014 10.2244 57.2014 9.90377C57.2014 9.00805 57.654 8.56088 58.5607 8.56088C58.9702 8.56088 59.31 8.67783 59.5802 8.91311C59.8504 9.14839 60.0718 9.52126 60.2431 10.0317L63.7402 20.8092L67.0409 9.77581C67.1482 9.41394 67.3376 9.12088 67.6078 8.8966C67.878 8.67233 68.2289 8.56088 68.6607 8.56088C69.0701 8.56088 69.4099 8.67233 69.6801 8.8966C69.9503 9.12088 70.1383 9.41394 70.247 9.77581L73.1605 21.0321L76.7203 10.0317C77.0225 9.05071 77.5838 8.56088 78.4041 8.56088C78.8581 8.56088 79.1979 8.67783 79.4235 8.91311C79.6492 9.14839 79.7634 9.4676 79.7634 9.87212H79.7661Z" fill="currentColor"/>' +
		'<path d="M83.7885 23.5816C82.0337 21.848 81.1562 19.7566 81.1562 17.3075C81.1562 14.8584 82.0337 12.767 83.7885 11.0334C85.5433 9.29974 87.6602 8.43292 90.1392 8.43292C92.6183 8.43292 94.7366 9.29974 96.49 11.0334C98.2448 12.767 99.1208 14.857 99.1208 17.3075C99.1208 17.7313 98.969 18.0932 98.6654 18.3931C98.3618 18.693 97.9955 18.843 97.5666 18.843H90.1379C89.7089 18.843 89.3426 18.693 89.039 18.3931C88.7354 18.0932 88.5836 17.7313 88.5836 17.3075C88.5836 16.8837 88.7354 16.5219 89.039 16.2219C89.3426 15.922 89.7089 15.772 90.1379 15.772H95.8062C95.4608 14.5282 94.7644 13.5059 93.7157 12.7051C92.667 11.903 91.4749 11.5026 90.1379 11.5026C88.5084 11.5026 87.1226 12.0681 85.9792 13.1977C84.8358 14.3273 84.2634 15.6963 84.2634 17.3061C84.2634 18.9159 84.8358 20.285 85.9792 21.4146C87.1226 22.5442 88.5098 23.1097 90.1379 23.1097C91.5347 23.1097 92.7729 22.6749 93.8508 21.8053C94.1823 21.537 94.5625 21.4242 94.9887 21.4669C95.4162 21.5095 95.7644 21.6953 96.0346 22.0227C96.3062 22.3502 96.4204 22.7258 96.3772 23.1469C96.334 23.5693 96.146 23.9132 95.8146 24.1802C94.1614 25.5134 92.2687 26.1794 90.1365 26.1794C87.6574 26.1794 85.5405 25.3125 83.7857 23.5789L83.7885 23.5816Z" fill="currentColor"/>' +
		'<path d="M120.582 17.3227C120.582 19.7718 119.705 21.8645 117.95 23.5968C116.195 25.329 114.078 26.1959 111.599 26.1959C109.364 26.1959 107.406 25.4749 105.724 24.0343V32.0297C105.724 32.4535 105.572 32.8153 105.268 33.1153C104.964 33.4152 104.598 33.5652 104.169 33.5652C103.74 33.5652 103.374 33.4152 103.07 33.1153C102.767 32.8153 102.615 32.4535 102.615 32.0297V17.3199C102.615 14.8708 103.492 12.7794 105.247 11.0458C107.002 9.31213 109.119 8.44531 111.598 8.44531C114.077 8.44531 116.194 9.31213 117.949 11.0458C119.704 12.7794 120.581 14.8708 120.581 17.3227H120.582ZM115.752 21.4229C116.9 20.2891 117.475 18.9215 117.475 17.3199C117.475 15.7183 116.901 14.3521 115.752 13.217C114.603 12.0818 113.219 11.515 111.599 11.515C110.537 11.515 109.555 11.775 108.652 12.2923C107.75 12.8111 107.037 13.5155 106.512 14.4071C105.987 15.2987 105.725 16.2687 105.725 17.3185C105.725 18.9187 106.3 20.2864 107.448 21.4215C108.595 22.5552 109.98 23.1235 111.601 23.1235C113.222 23.1235 114.605 22.5566 115.754 21.4215L115.752 21.4229Z" fill="currentColor"/>' +
		'<path d="M133.901 23.3188C134.214 23.627 134.37 24.0068 134.37 24.454C134.37 24.9011 134.214 25.2809 133.901 25.5891C133.589 25.8987 133.205 26.0528 132.752 26.0528C130.918 26.0528 129.354 25.413 128.059 24.1334C126.763 22.8538 126.116 21.3086 126.116 19.4966V4.59552C126.116 4.14698 126.272 3.76998 126.585 3.4604C126.897 3.1522 127.281 2.99672 127.734 2.99672C128.187 2.99672 128.57 3.1522 128.883 3.4604C129.195 3.76998 129.352 4.14835 129.352 4.59552V9.10436H132.234C132.643 9.10436 132.989 9.24333 133.27 9.51989C133.55 9.79644 133.691 10.139 133.691 10.5436C133.691 10.9481 133.55 11.2907 133.27 11.5672C132.99 11.8438 132.643 11.9828 132.234 11.9828H129.352V19.498C129.352 20.4143 129.687 21.2041 130.355 21.8645C131.024 22.5249 131.823 22.8552 132.751 22.8552C133.203 22.8552 133.586 23.0093 133.9 23.3188H133.901Z" fill="currentColor"/>' +
		'<path d="M165.444 24.4223C165.444 24.8695 165.283 25.2534 164.958 25.5739C164.634 25.8932 164.235 26.0541 163.761 26.0541C163.435 26.0541 163.128 25.9633 162.837 25.7831C162.546 25.6001 162.336 25.3497 162.206 25.0318L154.631 6.41997L146.928 25.0318C146.775 25.3524 146.561 25.6028 146.281 25.7831C146.001 25.9633 145.698 26.0541 145.374 26.0541C144.902 26.0541 144.508 25.889 144.192 25.5588C143.88 25.23 143.722 24.842 143.722 24.392C143.722 24.1788 143.776 23.9339 143.884 23.6573L152.98 2.20007C153.304 1.45432 153.832 1.08008 154.566 1.08008C155.343 1.08008 155.871 1.45295 156.152 2.20007L165.28 23.722C165.387 23.9985 165.442 24.2338 165.442 24.4264L165.444 24.4223Z" fill="currentColor"/>' +
		'<path d="M170.816 1.07733C171.312 1.07733 171.717 1.23281 172.031 1.54101C172.344 1.85059 172.5 2.2496 172.5 2.7408V24.3907C172.5 24.8599 172.344 25.2534 172.031 25.574C171.719 25.8932 171.313 26.0541 170.816 26.0541C170.319 26.0541 169.943 25.8945 169.618 25.574C169.295 25.2534 169.132 24.8599 169.132 24.3907V2.7408C169.132 2.25098 169.294 1.85059 169.618 1.54101C169.943 1.23281 170.341 1.07733 170.816 1.07733Z" fill="currentColor"/>' +
		'<path d="M0.5 16.9993C0.5 26.3734 8.21981 33.9986 17.7084 33.9986C27.1969 33.9986 34.9153 26.372 34.9153 16.9993C34.9153 7.62664 27.1955 0 17.7084 0C8.2212 0 0.5 7.62664 0.5 16.9993ZM12.4523 17.0172C12.4523 17.0406 12.4523 17.0626 12.4523 17.0846C12.4119 19.1471 9.22534 19.0989 9.2156 17.0365C9.21281 16.4613 9.26991 15.8766 9.38968 15.2918C10.0874 11.8754 12.9467 9.20481 16.4368 8.70123C21.6804 7.94585 26.1997 11.9607 26.1997 16.9993C26.1997 17.031 26.1997 17.0626 26.1997 17.0956C26.176 19.1471 23.0132 19.1567 22.9631 17.1053C22.9631 17.0709 22.9631 17.0351 22.9631 17.0007C22.9631 13.3628 19.154 10.5862 15.2697 12.3584C13.462 13.1839 12.462 15.0497 12.4537 17.0172H12.4523ZM15.1332 16.9993C15.1332 15.4941 16.4647 14.2902 18.0259 14.4759C19.3323 14.6314 20.2626 15.7981 20.2807 17.0984C20.3336 20.9151 23.4937 24.004 27.3696 24.004H27.8236C28.8501 24.004 29.825 23.7825 30.7065 23.3931C30.6982 23.4083 30.6912 23.4248 30.6829 23.4399C29.4447 25.8656 26.5772 27.0902 23.9394 26.3211C22.1748 25.8079 20.303 24.5847 18.9409 21.9457C18.7571 21.5893 18.4479 21.2908 18.0551 21.1889C17.4201 21.0252 16.7864 21.3252 16.5078 21.8755C15.1318 24.5861 13.2043 25.8175 11.3994 26.3238C8.77828 27.0586 5.94551 25.8285 4.72131 23.4248L4.7046 23.3931C5.58619 23.7825 6.56109 24.004 7.58751 24.004H8.04154C11.9509 24.004 15.1318 20.8615 15.1318 16.9993H15.1332ZM10.1376 29.2435C12.6946 29.0013 15.551 27.8855 17.7084 25.003C19.8643 27.8841 22.7207 29 25.2791 29.2435C23.0731 30.5795 20.4812 31.3514 17.7084 31.3514C14.9355 31.3514 12.3436 30.5795 10.1376 29.2435ZM32.2343 16.9993C32.2343 19.3521 30.3347 21.2701 27.9713 21.3486C28.5646 19.9837 28.8807 18.5114 28.8807 16.9993C28.8807 10.9123 23.8683 5.9618 17.7084 5.9618C11.5484 5.9618 6.53462 10.9137 6.53462 16.9993C6.53462 18.5114 6.84938 19.9837 7.44267 21.3486C5.07924 21.2715 3.17958 19.3535 3.17958 16.9993C3.17958 9.08648 9.69608 2.64862 17.707 2.64862C25.7178 2.64862 32.233 9.08648 32.233 16.9993H32.2343Z" fill="url(#sweptShellGradient)"/>' +
		'</g>' +
		'<defs>' +
		'<linearGradient id="sweptShellGradient" x1="5.5458" y1="29.0151" x2="29.5742" y2="4.69317" gradientUnits="userSpaceOnUse">' +
		'<stop stop-color="#1A237E"/>' +
		'<stop offset="0.69" stop-color="#1E88E5"/>' +
		'<stop offset="1" stop-color="#4DD0E1"/>' +
		'</linearGradient>' +
		'<clipPath id="sweptShellClip"><rect width="172" height="34" fill="white" transform="translate(0.5)"/></clipPath>' +
		'</defs>' +
		'</svg>';

	function iconSvg(name) {
		/* Match workbench's lucide-rails markup exactly: explicit width/height
		 * + stroke attributes on the <svg>, not just CSS. Subpixel rendering
		 * in some browsers diverges otherwise. */
		var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		svg.setAttribute('class', 'swept-shell__icon');
		svg.setAttribute('width', '24');
		svg.setAttribute('height', '24');
		svg.setAttribute('viewBox', '0 0 24 24');
		svg.setAttribute('fill', 'none');
		svg.setAttribute('stroke', 'currentColor');
		svg.setAttribute('stroke-width', '1.5');
		svg.setAttribute('stroke-linecap', 'round');
		svg.setAttribute('stroke-linejoin', 'round');
		svg.setAttribute('aria-hidden', 'true');
		svg.innerHTML = ICONS[name] || '';
		return svg;
	}

	function linkEl(item) {
		var a = document.createElement('a');
		a.href = item.href;
		a.target = '_self';
		a.className = 'swept-shell__link' + (item.active ? ' is-active' : '');
		a.setAttribute('aria-label', item.label);
		a.setAttribute('title', item.label);
		a.appendChild(iconSvg(item.icon));
		var label = document.createElement('span');
		label.className = 'swept-shell__label';
		label.textContent = item.label;
		a.appendChild(label);
		var tip = document.createElement('span');
		tip.className = 'swept-shell__tooltip';
		tip.setAttribute('aria-hidden', 'true');
		tip.textContent = item.label;
		a.appendChild(tip);
		return a;
	}

	function listEl(items) {
		var ul = document.createElement('ul');
		items.forEach(function (it) {
			var li = document.createElement('li');
			li.appendChild(linkEl(it));
			ul.appendChild(li);
		});
		return ul;
	}

	function toggleButton() {
		/* Mirrors swept-workbench's PR #655 logo bar: panel-left at rest,
		 * panel-left-close on hover when expanded; panel-left-open is shown
		 * via the absolutely positioned overlay when collapsed. */
		var b = document.createElement('button');
		b.type = 'button';
		b.className = 'swept-shell__toggle';
		b.setAttribute('aria-label', 'Toggle sidebar');
		b.setAttribute('title', 'Toggle sidebar');

		var rest = iconSvg('panel-left');
		rest.classList.add('swept-shell__toggle-icon', 'swept-shell__toggle-icon--rest');
		b.appendChild(rest);

		var hover = iconSvg('panel-left-close');
		hover.classList.add('swept-shell__toggle-icon', 'swept-shell__toggle-icon--hover');
		b.appendChild(hover);

		var open = iconSvg('panel-left-open');
		open.classList.add('swept-shell__toggle-icon', 'swept-shell__toggle-icon--open');
		b.appendChild(open);

		return b;
	}

	function applyCollapsed(aside, collapsed) {
		if (collapsed) {
			aside.setAttribute('data-sidebar-collapsed', 'true');
			document.documentElement.classList.add('swept-shell-collapsed');
		} else {
			aside.setAttribute('data-sidebar-collapsed', 'false');
			document.documentElement.classList.remove('swept-shell-collapsed');
		}
	}

	/* Defense-in-depth for sidebar links from Workbench: only same-origin
	 * paths (`/...`) and absolute URLs whose origin is in the allowlist
	 * pass through. The allowlist is `[workbench_url, cloud_lock_url]`
	 * (filtered to non-empty) — those are the only domains the shell
	 * should ever link to. Anything else (javascript:, data:, an
	 * arbitrary external host) returns null and the caller drops it.
	 *
	 * Match by origin prefix rather than string-startswith on the full
	 * URL so trailing-slash differences don't cause false negatives. */
	function safeHref(raw, allowedOrigins) {
		if (typeof raw !== 'string' || raw.length === 0) return null;
		/* Protocol-relative URLs ("//evil.example/x") are resolved by
		 * the browser as cross-origin navigation; reject them up front
		 * before the leading-slash fast-path. Same-origin paths still
		 * need to start with "/" but never "//". */
		if (raw.charAt(0) === '/' && raw.charAt(1) !== '/') return raw;
		try {
			var parsed = new URL(raw);
			if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
			for (var i = 0; i < allowedOrigins.length; i++) {
				if (parsed.origin === allowedOrigins[i]) return raw;
			}
		} catch (_e) {
			/* URL constructor throws for malformed input — treat as untrusted. */
		}
		return null;
	}

	/* Compute the origin of a base URL string for comparison in safeHref.
	 * Returns null for empty / malformed input so the caller can filter. */
	function originOf(urlStr) {
		if (typeof urlStr !== 'string' || urlStr.length === 0) return null;
		try {
			return new URL(urlStr).origin;
		} catch (_e) {
			return null;
		}
	}

	function hasHref(it) {
		return Boolean(it && it.href);
	}

	function buildShell(base, cloudLockUrl, sidebarData) {
		var nav;
		var bottom;
		/* sidebarData is the trimmed `sidebar` subtree from Workbench:
		 * `{main: [...], bottom: [...]}`. The /api/config endpoint
		 * forwards only this — siblings like user/company/features
		 * aren't included to keep the payload minimal. */
		var main = sidebarData && sidebarData.main;
		var bottomItems = sidebarData && sidebarData.bottom;

		/* Origins the shell is allowed to link to: Workbench itself
		 * and CloudLock (the "Private Cloud" target). Anything else
		 * returned by Workbench's sidebar endpoint is dropped by
		 * safeHref → null → hasHref filter. */
		var allowedOrigins = [originOf(base), originOf(cloudLockUrl)].filter(Boolean);

		/* Closure over allowedOrigins so itemFromWorkbench knows the
		 * allowlist without threading it through every call site. */
		function itemFromWorkbench(item) {
			var isChat = item.label === 'Chat';
			return {
				label: item.label,
				icon: item.icon,
				href: isChat ? '/' : safeHref(item.url, allowedOrigins),
				active: isChat
			};
		}

		/* Built-in nav used when Workbench doesn't provide one OR when
		 * everything Workbench provided got dropped by safeHref (a
		 * config mismatch — workbench_url / cloud_lock_url not aligned
		 * with what Workbench actually returns). Better to render a
		 * known-good shell than an empty rail. */
		function fallbackNav() {
			var n = [
				{ label: 'Chat', icon: 'message-square', href: '/', active: true },
				{ label: 'Governance', icon: 'shield-alert', href: base + '/governance/ai_applications' },
				{ label: 'Evaluations', icon: 'layout-dashboard', href: base + '/audits' },
				{ label: 'Supervision', icon: 'eye', href: base + '/supervision_policies' },
				{ label: 'Knowledge', icon: 'book-open', href: base + '/grounding_sets' }
			];
			if (cloudLockUrl) {
				n.push({ label: 'Private Cloud', icon: 'shield-check', href: cloudLockUrl });
			}
			return n;
		}
		function fallbackBottom() {
			return [{ label: 'Settings', icon: 'sliders-horizontal', href: base + '/settings' }];
		}

		if (Array.isArray(main)) {
			/* Use the entitlement-filtered list from Workbench. The
			 * user only sees nav items they're actually granted via
			 * FeatureAccessGrant (OIDC) or role-based can? (non-OIDC).
			 * Drop any item whose URL didn't pass safeHref so we never
			 * render a link with a missing/disallowed href. */
			nav = main.map(itemFromWorkbench).filter(hasHref);
			bottom = Array.isArray(bottomItems)
				? bottomItems.map(itemFromWorkbench).filter(hasHref)
				: [];

			/* If Workbench gave us items but safeHref dropped them all,
			 * that's a deployment config mismatch (mismatched origins).
			 * Workbench returning a legitimately empty entitlement is
			 * handled by the !main.length check — we don't override
			 * that. */
			if (main.length > 0 && nav.length === 0) {
				nav = fallbackNav();
				bottom = fallbackBottom();
			}
		} else {
			/* Fallback: Workbench endpoint not configured, the user
			 * isn't a member, or the fetch errored. Render the same
			 * built-in shell as before this PR so OWUI keeps working
			 * standalone. */
			nav = fallbackNav();
			bottom = fallbackBottom();
		}

		var aside = document.createElement('aside');
		aside.className = 'swept-shell';
		aside.id = 'swept-shell';

		/* Logo bar: wordmark when expanded, symbol when collapsed (with
		 * a hover-fade overlay revealing the toggle as a full-width click
		 * target — mirrors swept-workbench PR #655). */
		var logoBar = document.createElement('div');
		logoBar.className = 'swept-shell__logobar';

		var logo = document.createElement('a');
		logo.href = base || '/';
		logo.target = '_self';
		logo.className = 'swept-shell__logo';
		var wordmark = document.createElement('span');
		wordmark.className = 'swept-shell__wordmark';
		wordmark.innerHTML = WORDMARK_SVG;
		logo.appendChild(wordmark);
		var symbol = document.createElement('span');
		symbol.className = 'swept-shell__symbol';
		symbol.innerHTML = SYMBOL_SVG;
		logo.appendChild(symbol);
		logoBar.appendChild(logo);

		var btn = toggleButton();
		btn.addEventListener('click', function (e) {
			e.preventDefault();
			e.stopPropagation();
			var current = aside.getAttribute('data-sidebar-collapsed') === 'true';
			var next = !current;
			applyCollapsed(aside, next);
			writeCookie(next);
		});
		logoBar.appendChild(btn);

		aside.appendChild(logoBar);

		var nv = document.createElement('nav');
		nv.className = 'swept-shell__nav';
		nv.appendChild(listEl(nav));
		var spacer = document.createElement('div');
		spacer.className = 'swept-shell__spacer';
		nv.appendChild(spacer);
		nv.appendChild(listEl(bottom));
		aside.appendChild(nv);

		applyCollapsed(aside, initialCollapsed());

		return aside;
	}

	function ensureMounted(base, cloudLockUrl, sidebarData) {
		var existing = document.getElementById('swept-shell');
		if (existing) return existing;
		var shell = buildShell(base, cloudLockUrl, sidebarData);
		document.body.appendChild(shell);
		return shell;
	}

	/* Cross-app sync: when this tab regains focus (after the user toggled
	 * the sidebar in workbench / another chat tab), re-read the cookie and
	 * reapply. Mirrors the visibility/focus handler in src/routes/+layout.svelte
	 * for the inner Open WebUI sidebar. */
	function attachSync(getShell) {
		function reapply() {
			var shell = getShell();
			if (!shell) return;
			var cookie = readCookie();
			if (cookie === null) return;
			var current = shell.getAttribute('data-sidebar-collapsed') === 'true';
			if (current !== cookie) applyCollapsed(shell, cookie);
		}
		document.addEventListener('visibilitychange', function () {
			if (document.visibilityState === 'visible') reapply();
		});
		window.addEventListener('focus', reapply);
	}

	function preloadShellFonts() {
		/* Force-fetch Red Hat Text now so the shell paints in the right
		 * font on first frame instead of FOUT-swapping from system-ui. */
		if (!document.fonts || !document.fonts.load) {
			return Promise.resolve();
		}
		return Promise.all([
			document.fonts.load('400 14px "Red Hat Text"'),
			document.fonts.load('500 14px "Red Hat Text"'),
			document.fonts.load('700 14px "Red Hat Display"')
		]).catch(function () {
			/* font load failure shouldn't block the shell */
		});
	}

	function initShell() {
		fetch('/api/config', { credentials: 'include' })
			.then(function (r) {
				return r.ok ? r.json() : null;
			})
			.then(function (cfg) {
				var url = ((cfg && cfg.workbench_url) || '').replace(/\/$/, '');
				var cloudLockUrl = ((cfg && cfg.cloud_lock_url) || '').replace(/\/$/, '');
				/* Entitlement-filtered sidebar from Workbench (per-user
				 * nav list). Null when WORKBENCH_API_TOKEN/COMPANY_ID
				 * aren't set or the upstream call errored — buildShell
				 * falls back to its built-in nav in that case. */
				var sidebarData = (cfg && cfg.workbench_sidebar) || null;
				if (!url) return;
				return preloadShellFonts().then(function () {
					document.documentElement.classList.add('swept-shell-active');
					ensureMounted(url, cloudLockUrl, sidebarData);
					attachSync(function () {
						return document.getElementById('swept-shell');
					});
					/* SvelteKit doesn't replace document.body, so the shell
					 * survives hydration without any observer. We only need
					 * to react if something explicitly removes #swept-shell;
					 * scope the observer to that single removal signal so
					 * we're not running on every toast/modal mount. */
					new MutationObserver(function (mutations) {
						for (var i = 0; i < mutations.length; i++) {
							var removed = mutations[i].removedNodes;
							for (var j = 0; j < removed.length; j++) {
								if (removed[j].id === 'swept-shell') {
									ensureMounted(url, cloudLockUrl, sidebarData);
									return;
								}
							}
						}
					}).observe(document.body, { childList: true });
				});
			})
			.catch(function () {
				/* no-op */
			});
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', initShell);
	} else {
		initShell();
	}
})();
