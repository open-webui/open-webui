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
