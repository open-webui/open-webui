<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';
	import { settings } from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';
	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';

	const i18n = getContext('i18n');

	export let title: string = 'widget';
	export let widgetCode: string = '';
	export let loadingMessages: string[] = [];

	let iframeElement: HTMLIFrameElement;
	let svgContainer: HTMLDivElement;
	let widgetHeight: number = 80; // initial height before ResizeObserver reports
	let messageIndex = 0;
	let messageInterval: ReturnType<typeof setInterval> | null = null;
	let widgetId = `data-viz-${Math.random().toString(36).slice(2, 10)}`;

	$: trimmedCode = (widgetCode ?? '').trimStart();
	$: isSvg = trimmedCode.startsWith('<svg');

	$: sandboxAttr = `allow-scripts allow-downloads${
		($settings?.iframeSandboxAllowForms ?? false) ? ' allow-forms' : ''
	}${($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}`;

	const themeVars = (dark: boolean) => {
		if (dark) {
			return `
				--color-text-primary: #e5e7eb;
				--color-text-secondary: #9ca3af;
				--color-text-tertiary: #6b7280;
				--color-bg-primary: transparent;
				--color-bg-secondary: rgba(255,255,255,0.04);
				--color-bg-tertiary: rgba(255,255,255,0.08);
				--color-border-primary: rgba(255,255,255,0.10);
				--color-border-secondary: rgba(255,255,255,0.06);
				--color-accent-primary: #60a5fa;
				--color-accent-secondary: #a78bfa;
				--color-success: #34d399;
				--color-warning: #fbbf24;
				--color-danger: #f87171;
				--border-radius-sm: 4px;
				--border-radius-md: 8px;
				--border-radius-lg: 12px;
			`;
		}
		return `
			--color-text-primary: #111827;
			--color-text-secondary: #4b5563;
			--color-text-tertiary: #6b7280;
			--color-bg-primary: transparent;
			--color-bg-secondary: rgba(0,0,0,0.04);
			--color-bg-tertiary: rgba(0,0,0,0.08);
			--color-border-primary: rgba(0,0,0,0.10);
			--color-border-secondary: rgba(0,0,0,0.06);
			--color-accent-primary: #2563eb;
			--color-accent-secondary: #7c3aed;
			--color-success: #059669;
			--color-warning: #d97706;
			--color-danger: #dc2626;
			--border-radius-sm: 4px;
			--border-radius-md: 8px;
			--border-radius-lg: 12px;
		`;
	};

	const buildIframeDoc = (fragment: string): string => {
		const dark =
			typeof document !== 'undefined' &&
			document.documentElement.classList.contains('dark');
		const css = `:root { ${themeVars(dark)} }
html, body {
	margin: 0;
	padding: 0;
	background: transparent;
	color: var(--color-text-primary);
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
body { overflow: hidden; }`;

		const heightScript = `(function () {
	const post = () => {
		const h = Math.max(
			document.documentElement.scrollHeight,
			document.body.scrollHeight
		);
		parent.postMessage({ __dataViz: true, id: ${JSON.stringify(widgetId)}, height: h }, '*');
	};
	const ro = new ResizeObserver(post);
	ro.observe(document.documentElement);
	ro.observe(document.body);
	window.addEventListener('load', post);
	setTimeout(post, 50);
	setTimeout(post, 250);
})();`;

		// Hide the inline <style> and <script> tags from the Svelte preprocessor
		// by reassembling them at runtime with `<${''}tag>`.
		return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<${''}style>${css}</${''}style>
</head>
<body>
${fragment}
<${''}script>${heightScript}</${''}script>
</body>
</html>`;
	};

	// Note: `done` is the "tool callable returned" flag. The args (and thus
	// widget_code) are already complete by the time the <details> block is
	// emitted, so we render whenever trimmedCode is present. This also makes
	// persistence robust to streams that crashed before the done="true" rewrite.
	$: iframeDoc = !isSvg && trimmedCode ? buildIframeDoc(trimmedCode) : '';

	const handleMessage = (event: MessageEvent) => {
		const data = event.data;
		if (!data || typeof data !== 'object') return;
		if (!data.__dataViz || data.id !== widgetId) return;
		if (typeof data.height === 'number' && data.height > 0) {
			widgetHeight = Math.min(Math.max(data.height + 8, 60), 4000);
		}
	};

	const cycleLoadingMessages = () => {
		if (messageInterval) clearInterval(messageInterval);
		if (!loadingMessages || loadingMessages.length <= 1) return;
		messageInterval = setInterval(() => {
			messageIndex = (messageIndex + 1) % loadingMessages.length;
		}, 2000);
	};

	const handleCopy = async () => {
		const ok = await copyToClipboard(widgetCode);
		if (ok) toast.success($i18n.t('Copying to clipboard was successful!'));
	};

	const handleDownload = () => {
		const ext = isSvg ? 'svg' : 'html';
		const content = isSvg ? widgetCode : iframeDoc;
		const blob = new Blob([content], {
			type: isSvg ? 'image/svg+xml' : 'text/html'
		});
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `${title || 'widget'}.${ext}`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	};

	const handleFullscreen = () => {
		const target = isSvg ? svgContainer : iframeElement;
		if (!target) return;
		if (target.requestFullscreen) target.requestFullscreen();
		// @ts-ignore
		else if (target.webkitRequestFullscreen) target.webkitRequestFullscreen();
	};

	onMount(() => {
		window.addEventListener('message', handleMessage);
		cycleLoadingMessages();
	});

	onDestroy(() => {
		window.removeEventListener('message', handleMessage);
		if (messageInterval) clearInterval(messageInterval);
	});

	$: if (loadingMessages) cycleLoadingMessages();
</script>

<div class="group relative w-full my-2">
	{#if isSvg && trimmedCode}
		<div
			bind:this={svgContainer}
			class="w-full overflow-hidden [&>svg]:w-full [&>svg]:h-auto [&>svg]:max-w-full"
		>
			{@html widgetCode}
		</div>
	{:else if !isSvg && trimmedCode}
		<iframe
			bind:this={iframeElement}
			title={title}
			srcdoc={iframeDoc}
			class="w-full block"
			style="border:0; height:{widgetHeight}px; background:transparent;"
			sandbox={sandboxAttr}
			referrerpolicy="strict-origin-when-cross-origin"
		></iframe>
	{:else if loadingMessages.length > 0}
		<div class="text-xs text-gray-500 dark:text-gray-400 italic select-none">
			{loadingMessages[messageIndex]}
		</div>
	{/if}

	{#if trimmedCode}
		<div
			class="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none"
		>
			<Tooltip content={$i18n.t('Copy')}>
				<button
					on:click={handleCopy}
					type="button"
					class="pointer-events-auto bg-white/80 dark:bg-gray-900/80 hover:bg-white dark:hover:bg-gray-900 text-gray-700 dark:text-gray-200 rounded-md p-1 backdrop-blur-sm"
					aria-label={$i18n.t('Copy')}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.75"
						class="size-3.5"
					>
						<path
							d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2"
						/>
					</svg>
				</button>
			</Tooltip>
			<Tooltip content={$i18n.t('Download')}>
				<button
					on:click={handleDownload}
					type="button"
					class="pointer-events-auto bg-white/80 dark:bg-gray-900/80 hover:bg-white dark:hover:bg-gray-900 text-gray-700 dark:text-gray-200 rounded-md p-1 backdrop-blur-sm"
					aria-label={$i18n.t('Download')}
				>
					<Download className="size-3.5" />
				</button>
			</Tooltip>
			<Tooltip content={$i18n.t('Open in full screen')}>
				<button
					on:click={handleFullscreen}
					type="button"
					class="pointer-events-auto bg-white/80 dark:bg-gray-900/80 hover:bg-white dark:hover:bg-gray-900 text-gray-700 dark:text-gray-200 rounded-md p-1 backdrop-blur-sm"
					aria-label={$i18n.t('Open in full screen')}
				>
					<ArrowsPointingOut className="size-3.5" />
				</button>
			</Tooltip>
		</div>
	{/if}
</div>
