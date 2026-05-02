<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';
	import { settings } from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';
	import { toast } from 'svelte-sonner';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';

	const i18n = getContext('i18n');

	export let title: string = 'widget';
	export let widgetCode: string = '';
	export let loadingMessages: string[] = [];
	export let chatId: string = '';
	export let messageId: string = '';

	let iframeElement: HTMLIFrameElement;
	let svgContainer: HTMLDivElement;
	let widgetHeight: number = 80; // initial height before ResizeObserver reports
	let messageIndex = 0;
	let messageInterval: ReturnType<typeof setInterval> | null = null;
	let widgetId = `data-viz-${Math.random().toString(36).slice(2, 10)}`;

	// Auto-repair state. Starts idle, transitions to 'repairing' on first error,
	// then 'fixed' (briefly, with chip) or 'failed'. Resets on widgetCode prop
	// changes from upstream (new tool call).
	type RepairState = 'idle' | 'repairing' | 'fixed' | 'failed';
	let repairState: RepairState = 'idle';
	let attemptsUsed = 0;
	let lastError: { msg: string; stack?: string } | null = null;
	let abortController: AbortController | null = null;
	let firstErrorTimer: ReturnType<typeof setTimeout> | null = null;
	let repairFlashTimer: ReturnType<typeof setTimeout> | null = null;
	let lastRenderedCode = widgetCode;
	const MAX_ATTEMPTS_HARDCAP = 5; // server enforces too; this is a UI safety net

	$: if (widgetCode !== lastRenderedCode) {
		// Upstream pushed a new widget — cancel any in-flight repair, reset state.
		lastRenderedCode = widgetCode;
		abortController?.abort();
		abortController = null;
		if (firstErrorTimer) {
			clearTimeout(firstErrorTimer);
			firstErrorTimer = null;
		}
		if (repairFlashTimer) {
			clearTimeout(repairFlashTimer);
			repairFlashTimer = null;
		}
		attemptsUsed = 0;
		repairState = 'idle';
		lastError = null;
	}

	$: trimmedCode = (widgetCode ?? '').trimStart();
	$: isSvg = trimmedCode.startsWith('<svg');

	$: sandboxAttr = `allow-scripts allow-downloads${
		($settings?.iframeSandboxAllowForms ?? false) ? ' allow-forms' : ''
	}${($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}`;

	const themeVars = (dark: boolean) => {
		// Shared across modes (typography + radii — values don't depend on theme)
		const shared = `
			--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
			--font-serif: Georgia, 'Times New Roman', serif;
			--font-mono: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
			--border-radius-sm: 4px;
			--border-radius-md: 8px;
			--border-radius-lg: 12px;
			--border-radius-xl: 16px;
		`;

		if (dark) {
			return `
				${shared}

				/* Text */
				--color-text-primary: #F0F0EB;
				--color-text-secondary: #BFBFBA;
				--color-text-tertiary: #91918D;
				--color-text-info: #A4B5D6;
				--color-text-danger: #D88577;
				--color-text-success: #9CB07F;
				--color-text-warning: #E2B873;

				/* Backgrounds (short names — back-compat) */
				--color-bg-primary: transparent;
				--color-bg-secondary: rgba(255,255,255,0.04);
				--color-bg-tertiary: rgba(255,255,255,0.08);

				/* Backgrounds (full namespace — what the prompt advertises) */
				--color-background-primary: transparent;
				--color-background-secondary: rgba(255,255,255,0.04);
				--color-background-tertiary: rgba(255,255,255,0.08);
				--color-background-info: rgba(164,181,214,0.12);
				--color-background-danger: rgba(216,133,119,0.12);
				--color-background-success: rgba(156,176,127,0.12);
				--color-background-warning: rgba(226,184,115,0.12);

				/* Borders */
				--color-border-primary: rgba(255,255,255,0.10);
				--color-border-secondary: rgba(255,255,255,0.06);
				--color-border-tertiary: rgba(255,255,255,0.03);
				--color-border-info: rgba(164,181,214,0.30);
				--color-border-danger: rgba(216,133,119,0.30);
				--color-border-success: rgba(156,176,127,0.30);
				--color-border-warning: rgba(226,184,115,0.30);

				/* Accents (Book Cloth + Kraft, hex-stable across modes) */
				--color-accent-primary: #CC785C;
				--color-accent-secondary: #D4A27F;

				/* Status (use as text/icon/border, not as solid backgrounds) */
				--color-success: #9CB07F;
				--color-warning: #E2B873;
				--color-danger: #D88577;

				/* SVG short aliases (diagram / art modules) */
				--p: #F0F0EB;
				--s: #BFBFBA;
				--t: #91918D;
				--bg2: rgba(255,255,255,0.04);
				--b: rgba(255,255,255,0.10);
			`;
		}
		return `
			${shared}

			/* Text */
			--color-text-primary: #191919;
			--color-text-secondary: #666663;
			--color-text-tertiary: #91918D;
			--color-text-info: #5A6B8A;
			--color-text-danger: #BF4D43;
			--color-text-success: #5C7048;
			--color-text-warning: #A8783E;

			/* Backgrounds (short names — back-compat) */
			--color-bg-primary: transparent;
			--color-bg-secondary: rgba(0,0,0,0.04);
			--color-bg-tertiary: rgba(0,0,0,0.08);

			/* Backgrounds (full namespace — what the prompt advertises) */
			--color-background-primary: transparent;
			--color-background-secondary: rgba(0,0,0,0.04);
			--color-background-tertiary: rgba(0,0,0,0.08);
			--color-background-info: rgba(90,107,138,0.12);
			--color-background-danger: rgba(191,77,67,0.10);
			--color-background-success: rgba(92,112,72,0.10);
			--color-background-warning: rgba(168,120,62,0.10);

			/* Borders */
			--color-border-primary: rgba(0,0,0,0.10);
			--color-border-secondary: rgba(0,0,0,0.06);
			--color-border-tertiary: rgba(0,0,0,0.03);
			--color-border-info: rgba(90,107,138,0.30);
			--color-border-danger: rgba(191,77,67,0.30);
			--color-border-success: rgba(92,112,72,0.30);
			--color-border-warning: rgba(168,120,62,0.30);

			/* Accents (Book Cloth + Kraft) */
			--color-accent-primary: #CC785C;
			--color-accent-secondary: #D4A27F;

			/* Status */
			--color-success: #5C7048;
			--color-warning: #A8783E;
			--color-danger: #BF4D43;

			/* SVG short aliases */
			--p: #191919;
			--s: #666663;
			--t: #91918D;
			--bg2: rgba(0,0,0,0.04);
			--b: rgba(0,0,0,0.10);
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

		const errorScript = `(function () {
	const ID = ${JSON.stringify(widgetId)};
	const truncate = (s, n) => {
		try { s = String(s == null ? '' : s); } catch (e) { s = ''; }
		return s.length > n ? s.slice(0, n) : s;
	};
	const topFrames = (stack) => {
		try {
			return String(stack || '').split('\\n').slice(0, 8).join('\\n');
		} catch (e) { return ''; }
	};
	let posted = false;
	const send = (payload) => {
		if (posted) return;
		posted = true;
		try { parent.postMessage(payload, '*'); } catch (e) {}
	};
	window.addEventListener('error', function (e) {
		send({
			__dataVizError: true,
			id: ID,
			msg: truncate((e && e.message) || 'Error', 500),
			line: e && e.lineno,
			col: e && e.colno,
			stack: topFrames(e && e.error && e.error.stack)
		});
	}, true);
	window.addEventListener('unhandledrejection', function (e) {
		const reason = e && e.reason;
		const msg = (reason && reason.message) || (typeof reason === 'string' ? reason : 'Unhandled rejection');
		send({
			__dataVizError: true,
			id: ID,
			msg: 'Unhandled rejection: ' + truncate(msg, 460),
			stack: topFrames(reason && reason.stack)
		});
	});
})();`;

		// Hide the inline <style> and <script> tags from the Svelte preprocessor
		// by reassembling them at runtime with `<${''}tag>`.
		return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<${''}script>${errorScript}</${''}script>
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
		if (!data || typeof data !== 'object' || data.id !== widgetId) return;
		if (data.__dataVizError) {
			handleIframeError(data);
			return;
		}
		if (!data.__dataViz) return;
		if (typeof data.height === 'number' && data.height > 0) {
			widgetHeight = Math.min(Math.max(data.height + 8, 60), 4000);
		}
	};

	const handleIframeError = (data: { msg: string; stack?: string }) => {
		// Don't pile on if we're already repairing or just succeeded.
		if (repairState === 'repairing' || repairState === 'fixed') return;
		if (attemptsUsed >= MAX_ATTEMPTS_HARDCAP) return;
		// Debounce rapid chained errors during initial load — first one wins.
		if (firstErrorTimer) return;
		lastError = { msg: String(data.msg ?? 'Unknown error'), stack: data.stack };
		firstErrorTimer = setTimeout(() => {
			firstErrorTimer = null;
			triggerRepair();
		}, 250);
	};

	const triggerRepair = async () => {
		if (!lastError || !widgetCode) return;
		abortController?.abort();
		abortController = new AbortController();
		attemptsUsed += 1;
		repairState = 'repairing';

		const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/data_viz/repair`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(token ? { Authorization: `Bearer ${token}` } : {})
				},
				signal: abortController.signal,
				body: JSON.stringify({
					chat_id: chatId || null,
					message_id: messageId || null,
					title,
					widget_code: widgetCode,
					error_message: lastError.msg,
					error_stack: lastError.stack ?? null,
					attempt: attemptsUsed
				})
			});
			if (!res.ok) {
				repairState = 'failed';
				return;
			}
			const body = await res.json();
			if (body?.success && typeof body.widget_code === 'string') {
				lastRenderedCode = body.widget_code; // suppress reactive reset
				widgetCode = body.widget_code;
				lastError = null;
				repairState = 'fixed';
				clearTimeout(repairFlashTimer);
				repairFlashTimer = setTimeout(() => {
					if (repairState === 'fixed') repairState = 'idle';
				}, 3000);
			} else {
				repairState = 'failed';
			}
		} catch (err: any) {
			if (err?.name === 'AbortError') return;
			repairState = 'failed';
			console.warn('data_viz repair failed', err);
		}
	};

	const manualRetry = () => {
		if (!lastError) return;
		// Don't bypass the hardcap; the server also enforces it.
		if (attemptsUsed >= MAX_ATTEMPTS_HARDCAP) return;
		repairState = 'idle';
		triggerRepair();
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
		if (firstErrorTimer) clearTimeout(firstErrorTimer);
		if (repairFlashTimer) clearTimeout(repairFlashTimer);
		abortController?.abort();
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

	{#if trimmedCode && repairState !== 'idle'}
		<div
			class="absolute top-1 left-1 z-10 flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium border-hairline bg-manilla/60 dark:bg-manilla-dark border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 backdrop-blur-sm"
		>
			{#if repairState === 'repairing'}
				<span
					class="inline-block w-1.5 h-1.5 rounded-full bg-book-cloth animate-pulse"
					aria-hidden="true"
				></span>
				<span>{$i18n.t('Auto-fixing widget…')}</span>
			{:else if repairState === 'fixed'}
				<span class="text-book-cloth" aria-hidden="true">✓</span>
				<span>{$i18n.t('Auto-fixed')}</span>
			{:else if repairState === 'failed'}
				<Tooltip content={lastError?.msg ?? ''}>
					<span class="text-gray-600 dark:text-gray-400">{$i18n.t("Couldn't auto-fix")}</span>
				</Tooltip>
				{#if attemptsUsed < MAX_ATTEMPTS_HARDCAP}
					<button
						on:click={manualRetry}
						class="ml-1 underline text-gray-700 dark:text-gray-200 hover:text-book-cloth transition-colors duration-200 ease-paper"
						type="button"
					>
						{$i18n.t('Retry')}
					</button>
				{/if}
			{/if}
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
