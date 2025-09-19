<script lang="ts">
	import { onDestroy, onMount, tick } from 'svelte';

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
	let iframeSrc: string | null = null;
	let iframeDoc: string | null = null;

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
	$: if (src) {
		setIframeSrc();
	}

	const setIframeSrc = async () => {
		await tick();
		if (isUrl) {
			iframeSrc = src as string;
			iframeDoc = null;
		} else {
			iframeDoc = await processHtmlForAlpine(src as string);
			iframeSrc = null;
		}
	};

	// Alpine directives detection
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

	async function processHtmlForAlpine(html: string): Promise<string> {
		if (!allowSameOrigin) return html;

		const hasAlpineDirectives = alpineDirectives.some((dir) => html.includes(dir));
		if (!hasAlpineDirectives) return html;

		try {
			// Import Alpine and get its source code
			// import alpineCode from './alpine.min.js?raw';
			const { default: alpineCode } = await import('alpinejs/dist/cdn.min.js?raw');
			const alpineBlob = new Blob([alpineCode], { type: 'text/javascript' });
			const alpineUrl = URL.createObjectURL(alpineBlob);

			// Create Alpine initialization script
			const alpineTag = `<script src="${alpineUrl}" defer><\/script>`;

			// Inject Alpine script at the beginning of head or body
			html = html.includes('</body>')
				? html.replace('</body>', alpineTag + '\n</body>')
				: `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>${html}\n${alpineTag}</body></html>`;

			return html;
		} catch (error) {
			console.error('Error processing Alpine for iframe:', error);
			return html;
		}
	}

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
