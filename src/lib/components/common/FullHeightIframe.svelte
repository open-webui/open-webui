<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	// Props
	export let src: string | null = null; // URL or raw HTML (auto-detected)
	export let title = 'Embedded Content';
	export let initialHeight = 400; // fallback height if we can't measure
	export let allowScripts = true;
	export let allowForms = false;

	export let allowSameOrigin = false; // set to true only when you trust the content
	export let allowPopups = false;
	export let allowDownloads = true;

	export let referrerPolicy: HTMLIFrameElement['referrerPolicy'] =
		'strict-origin-when-cross-origin';
	export let allowFullscreen = true;

	let iframe: HTMLIFrameElement | null = null;

	// Derived: build sandbox attribute from flags
	$: sandbox =
		[
			allowScripts && 'allow-scripts',
			allowForms && 'allow-forms',
			allowSameOrigin && 'allow-same-origin',
			allowPopups && 'allow-popups',
			allowDownloads && 'allow-downloads'
		]
			.filter(Boolean)
			.join(' ') || undefined;

	// Detect URL vs raw HTML and prep src/srcdoc
	$: isUrl = typeof src === 'string' && /^(https?:)?\/\//i.test(src);
	$: iframeSrc = isUrl ? (src as string) : null;
	$: iframeDoc = !isUrl && src ? ensureAutosizer(src) : null;

	// Try to measure same-origin content safely
	function resizeSameOrigin() {
		if (!iframe) return;
		try {
			const doc = iframe.contentDocument || iframe.contentWindow?.document;
			if (!doc) return;
			const h = Math.max(doc.documentElement?.scrollHeight ?? 0, doc.body?.scrollHeight ?? 0);
			if (h > 0) iframe.style.height = h + 20 + 'px';
		} catch {
			// Cross-origin → rely on postMessage from inside the iframe
		}
	}

	// Handle height messages from the iframe (we also verify the sender)
	function onMessage(e: MessageEvent) {
		if (!iframe || e.source !== iframe.contentWindow) return;
		const data = e.data as { type?: string; height?: number };
		if (data?.type === 'iframe:height' && typeof data.height === 'number') {
			iframe.style.height = Math.max(0, data.height) + 'px';
		}
	}

	// Ensure event listener bound only while component lives
	onMount(() => {
		window.addEventListener('message', onMessage);
	});

	onDestroy(() => {
		window.removeEventListener('message', onMessage);
	});

	// When the iframe loads, try same-origin resize (cross-origin will noop)
	function onLoad() {
		// schedule after layout
		requestAnimationFrame(resizeSameOrigin);
	}

	/**
	 * If user passes raw HTML, we inject a tiny autosizer that posts height.
	 * This helps both same-origin and "about:srcdoc" cases.
	 * (No effect if the caller already includes their own autosizer.)
	 */
	function ensureAutosizer(html: string): string {
		const hasOurHook = /iframe:height/.test(html) || /postMessage\(.+height/i.test(html);
		if (hasOurHook) return html;

		// This script uses ResizeObserver to post the document height
		const autosizer = `
<script>
(function () {
  function send() {
    try {
      var h = Math.max(
        document.documentElement.scrollHeight || 0,
        document.body ? document.body.scrollHeight : 0
      );
      parent.postMessage({ type: 'iframe:height', height: h + 20 }, '*');
    } catch (e) {}
  }
  var ro = new ResizeObserver(function(){ send(); });
  ro.observe(document.documentElement);
  window.addEventListener('load', send);
  // Also observe body if present
  if (document.body) ro.observe(document.body);
  // Periodic guard in case of late content
  setTimeout(send, 0);
  setTimeout(send, 250);
  setTimeout(send, 1000);
})();
<\/script>`;
		// inject before </body> if present, else append
		return (
			html.replace(/<\/body\s*>/i, autosizer + '</body>') +
			(/<\/body\s*>/i.test(html) ? '' : autosizer)
		);
	}
</script>

{#if iframeDoc}
	<iframe
		bind:this={iframe}
		srcdoc={iframeDoc}
		{title}
		class="w-full rounded-xl"
		style={`height:${initialHeight}px;`}
		width="100%"
		frameborder="0"
		{sandbox}
		referrerpolicy={referrerPolicy}
		{allowFullscreen}
		on:load={onLoad}
	/>
{:else if iframeSrc}
	<iframe
		bind:this={iframe}
		src={iframeSrc}
		{title}
		class="w-full rounded-xl"
		style={`height:${initialHeight}px;`}
		width="100%"
		frameborder="0"
		{sandbox}
		referrerpolicy={referrerPolicy}
		{allowFullscreen}
		on:load={onLoad}
	/>
{/if}
