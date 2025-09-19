<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	// Props
	export let src: string | null = null; // URL or raw HTML (auto-detected)
	export let title = 'Embedded Content';
	export let initialHeight: number | null = null; // initial height in px, null = auto

	export let args = null;

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
	$: iframeDoc = !isUrl ? src : null;

	// Try to measure same-origin content safely
	function resizeSameOrigin() {
		if (!iframe) return;
		try {
			const doc = iframe.contentDocument || iframe.contentWindow?.document;
			console.log('iframe doc:', doc);
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

	// When the iframe loads, try same-origin resize (cross-origin will noop)
	const onLoad = async () => {
		requestAnimationFrame(resizeSameOrigin);

		// if arguments are provided, inject them into the iframe window
		if (args && iframe?.contentWindow) {
			(iframe.contentWindow as any).args = args;
		}

		// If we're injecting Alpine into srcdoc iframe and sameOrigin allowed
		if (iframeDoc && allowSameOrigin && iframe?.contentWindow) {
			const alpineDirectives = [
				'x-data',
				'x-init',
				'x-show',
				'x-bind',
				'x-on',
				'x-text',
				'x-html',
				'x-model',
				'x-modelable',
				'x-ref',
				'x-for',
				'x-if',
				'x-effect',
				'x-transition',
				'x-cloak',
				'x-ignore',
				'x-teleport',
				'x-id'
			];

			const isAlpine = alpineDirectives.some((dir) => iframeDoc?.includes(dir));

			if (isAlpine) {
				const { default: Alpine } = await import('alpinejs');
				const win = iframe.contentWindow as Window & { Alpine?: typeof Alpine };

				// Assign Alpine
				win.Alpine = Alpine;

				// Initialize inside iframe DOM
				try {
					Alpine.start();
				} catch (e) {
					console.error('Error starting Alpine inside iframe:', e);
				}
			}
		}
	};

	// Ensure event listener bound only while component lives
	onMount(() => {
		window.addEventListener('message', onMessage);
	});

	onDestroy(() => {
		window.removeEventListener('message', onMessage);
	});
</script>

{#if iframeDoc}
	<iframe
		bind:this={iframe}
		srcdoc={iframeDoc}
		{title}
		class="w-full rounded-2xl"
		style={`${initialHeight ? `height:${initialHeight}px;` : ''}`}
		width="100%"
		frameborder="0"
		{sandbox}
		{allowFullscreen}
		on:load={onLoad}
	/>
{:else if iframeSrc}
	<iframe
		bind:this={iframe}
		src={iframeSrc}
		{title}
		class="w-full rounded-2xl"
		style={`${initialHeight ? `height:${initialHeight}px;` : ''}`}
		width="100%"
		frameborder="0"
		{sandbox}
		referrerpolicy={referrerPolicy}
		{allowFullscreen}
		on:load={onLoad}
	/>
{/if}
