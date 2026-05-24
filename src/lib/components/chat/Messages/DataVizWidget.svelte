<script lang="ts">
	import { onDestroy, onMount, getContext, tick } from 'svelte';
	import { settings } from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';
	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';

	import {
		registerWidgetHandler,
		type WidgetRenderRequest,
		type WidgetRenderResponse
	} from '$lib/utils/dataVizRegistry';

	const i18n = getContext('i18n');

	export let title: string = 'widget';
	export let widgetCode: string = '';
	export let loadingMessages: string[] = [];
	export let chatId: string = '';
	export let messageId: string = '';

	/**
	 * Reload-time persisted overrides from the message: if the original
	 * widget_code (the model's emission) errored at runtime and was
	 * auto-repaired, the backend stored {hash(original_widget_code): final_code}
	 * on the message. We hash our incoming widgetCode and look it up here.
	 */
	export let dataVizOverrides: Record<string, string> = {};

	let iframeElement: HTMLIFrameElement;
	let svgContainer: HTMLDivElement;
	let widgetHeight: number = 80;
	let messageIndex = 0;
	let messageInterval: ReturnType<typeof setInterval> | null = null;
	let widgetId = `data-viz-${Math.random().toString(36).slice(2, 10)}`;

	// Hash of the ORIGINAL widget_code (matches backend's _override_key). Used
	// both for live registry lookup and reload-time override application.
	// Async-computed in onMount, so the iframe waits one tick to render.
	let overrideKey = '';
	let unregister: (() => void) | null = null;

	// What's actually displayed in the iframe right now. Mirrors widgetCode by
	// default, but the live render handler can swap it in (during a backend
	// tool roundtrip), and reload override can preempt it on first mount.
	let displayedCode = widgetCode;
	let lastPropCode = widgetCode;

	type RenderState = 'idle' | 'live' | 'repairing' | 'fixed' | 'failed';
	let renderState: RenderState = 'idle';
	let attemptsSeen = 0;
	let lastErrorMessage = '';
	let fixedFlashTimer: ReturnType<typeof setTimeout> | null = null;

	// In-flight render promise machinery. `pendingResolve` is set when the
	// backend asks us to render+report; it gets called either by the iframe
	// load+grace timer (success) or by handleIframeError (failure).
	let pendingResolve: ((res: WidgetRenderResponse) => void) | null = null;
	let pendingHardTimeout: ReturnType<typeof setTimeout> | null = null;
	let loadGraceTimer: ReturnType<typeof setTimeout> | null = null;
	let rAFGraceId: number | null = null;
	let rAFGraceTimeout: ReturnType<typeof setTimeout> | null = null;
	const HARD_TIMEOUT_MS = 12_000; // upper bound; longer than typical repair latency

	// When the parent passes a different widgetCode (e.g., new tool call in a
	// fresh assistant turn), reset state and re-apply any persisted override.
	$: if (widgetCode !== lastPropCode) {
		lastPropCode = widgetCode;

		// Drop any in-flight pending resolver — it belongs to a previous render
		// request and is no longer relevant.
		clearPending('ok');

		const override = overrideKey ? dataVizOverrides?.[overrideKey] : null;
		displayedCode = override ?? widgetCode;
		renderState = 'idle';
		attemptsSeen = 0;
		lastErrorMessage = '';
		if (fixedFlashTimer) {
			clearTimeout(fixedFlashTimer);
			fixedFlashTimer = null;
		}
	}

	// When dataVizOverrides arrives or updates AFTER mount (typical case: the
	// backend's auto-repair persisted a fix, the socket event reaches the
	// frontend after this widget already mounted with the broken code), pick
	// up the override and swap the iframe to render the working version.
	$: if (overrideKey && dataVizOverrides && typeof dataVizOverrides[overrideKey] === 'string') {
		const o = dataVizOverrides[overrideKey];
		if (o && o !== displayedCode) {
			lastPropCode = widgetCode; // suppress the prop-watcher's reset path
			displayedCode = o;
			// The previously-rendered iframe may have set renderState='failed';
			// we just swapped to the corrected code, so clear that state.
			if (renderState === 'failed') {
				renderState = 'idle';
				lastErrorMessage = '';
			}
		}
	}

	$: trimmedCode = (displayedCode ?? '').trimStart();
	$: isSvg = trimmedCode.startsWith('<svg');

	$: sandboxAttr = `allow-scripts allow-downloads${
		($settings?.iframeSandboxAllowForms ?? false) ? ' allow-forms' : ''
	}${($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}`;

	const themeVars = (dark: boolean) => {
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

				--color-text-primary: #F0F0EB;
				--color-text-secondary: #BFBFBA;
				--color-text-tertiary: #91918D;
				--color-text-info: #A4B5D6;
				--color-text-danger: #D88577;
				--color-text-success: #9CB07F;
				--color-text-warning: #E2B873;

				--color-bg-primary: transparent;
				--color-bg-secondary: rgba(255,255,255,0.04);
				--color-bg-tertiary: rgba(255,255,255,0.08);

				--color-background-primary: transparent;
				--color-background-secondary: rgba(255,255,255,0.04);
				--color-background-tertiary: rgba(255,255,255,0.08);
				--color-background-info: rgba(164,181,214,0.12);
				--color-background-danger: rgba(216,133,119,0.12);
				--color-background-success: rgba(156,176,127,0.12);
				--color-background-warning: rgba(226,184,115,0.12);

				--color-border-primary: rgba(255,255,255,0.10);
				--color-border-secondary: rgba(255,255,255,0.06);
				--color-border-tertiary: rgba(255,255,255,0.03);
				--color-border-info: rgba(164,181,214,0.30);
				--color-border-danger: rgba(216,133,119,0.30);
				--color-border-success: rgba(156,176,127,0.30);
				--color-border-warning: rgba(226,184,115,0.30);

				--color-accent-primary: #CC785C;
				--color-accent-secondary: #D4A27F;

				--color-success: #9CB07F;
				--color-warning: #E2B873;
				--color-danger: #D88577;

				--p: #F0F0EB;
				--s: #BFBFBA;
				--t: #91918D;
				--bg2: rgba(255,255,255,0.04);
				--b: rgba(255,255,255,0.10);
			`;
		}
		return `
			${shared}

			--color-text-primary: #191919;
			--color-text-secondary: #666663;
			--color-text-tertiary: #91918D;
			--color-text-info: #5A6B8A;
			--color-text-danger: #BF4D43;
			--color-text-success: #5C7048;
			--color-text-warning: #A8783E;

			--color-bg-primary: transparent;
			--color-bg-secondary: rgba(0,0,0,0.04);
			--color-bg-tertiary: rgba(0,0,0,0.08);

			--color-background-primary: transparent;
			--color-background-secondary: rgba(0,0,0,0.04);
			--color-background-tertiary: rgba(0,0,0,0.08);
			--color-background-info: rgba(90,107,138,0.12);
			--color-background-danger: rgba(191,77,67,0.10);
			--color-background-success: rgba(92,112,72,0.10);
			--color-background-warning: rgba(168,120,62,0.10);

			--color-border-primary: rgba(0,0,0,0.10);
			--color-border-secondary: rgba(0,0,0,0.06);
			--color-border-tertiary: rgba(0,0,0,0.03);
			--color-border-info: rgba(90,107,138,0.30);
			--color-border-danger: rgba(191,77,67,0.30);
			--color-border-success: rgba(92,112,72,0.30);
			--color-border-warning: rgba(168,120,62,0.30);

			--color-accent-primary: #CC785C;
			--color-accent-secondary: #D4A27F;

			--color-success: #5C7048;
			--color-warning: #A8783E;
			--color-danger: #BF4D43;

			--p: #191919;
			--s: #666663;
			--t: #91918D;
			--bg2: rgba(0,0,0,0.04);
			--b: rgba(0,0,0,0.10);
		`;
	};

	const buildIframeDoc = (fragment: string): string => {
		const dark =
			typeof document !== 'undefined' && document.documentElement.classList.contains('dark');
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

		// Captures the FIRST runtime error (sync throws + unhandled rejections)
		// and reports back to the parent. Once posted, further errors in the same
		// frame load are dropped — the first one is enough.
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

	$: iframeDoc = !isSvg && trimmedCode ? buildIframeDoc(trimmedCode) : '';

	// ───── Live render machinery ──────────────────────────────────────────────

	const clearPending = (defaultStatus: 'ok' | 'error' = 'ok') => {
		if (pendingHardTimeout) {
			clearTimeout(pendingHardTimeout);
			pendingHardTimeout = null;
		}
		if (loadGraceTimer) {
			clearTimeout(loadGraceTimer);
			loadGraceTimer = null;
		}
		if (rAFGraceId) {
			cancelAnimationFrame(rAFGraceId);
			rAFGraceId = null;
		}
		if (rAFGraceTimeout) {
			clearTimeout(rAFGraceTimeout);
			rAFGraceTimeout = null;
		}
		if (pendingResolve) {
			const r = pendingResolve;
			pendingResolve = null;
			r({ status: defaultStatus });
		}
	};

	const renderHandler = async (req: WidgetRenderRequest): Promise<WidgetRenderResponse> => {
		// A new request supersedes anything in flight.
		clearPending('ok');

		attemptsSeen = req.attempt;
		renderState = req.is_repair ? 'repairing' : 'live';
		lastErrorMessage = '';

		// Force an iframe re-render even if widget_code is identical to what's
		// already shown (rare but possible: same widget asked for re-confirmation).
		if (displayedCode === req.widget_code) {
			displayedCode = '';
			await tick();
		}
		// Suppress the prop-watcher's reset path — this update is internal.
		lastPropCode = widgetCode;
		displayedCode = req.widget_code;

		return new Promise<WidgetRenderResponse>((resolve) => {
			pendingResolve = (res: WidgetRenderResponse) => {
				resolve(res);
				pendingResolve = null;
				if (pendingHardTimeout) {
					clearTimeout(pendingHardTimeout);
					pendingHardTimeout = null;
				}
				if (loadGraceTimer) {
					clearTimeout(loadGraceTimer);
					loadGraceTimer = null;
				}

				if (res.status === 'ok') {
					if (req.is_repair) {
						renderState = 'fixed';
						if (fixedFlashTimer) clearTimeout(fixedFlashTimer);
						fixedFlashTimer = setTimeout(() => {
							if (renderState === 'fixed') renderState = 'idle';
						}, 3000);
					} else {
						renderState = 'idle';
					}
				} else {
					renderState = 'failed';
					lastErrorMessage = (res.error_message ?? '').slice(0, 240);
				}
			};

			// Fail-soft hard timeout. If neither load nor error arrives, assume
			// rendered so the model can move on.
			pendingHardTimeout = setTimeout(() => {
				if (pendingResolve) {
					const r = pendingResolve;
					pendingResolve = null;
					r({ status: 'ok' });
				}
			}, HARD_TIMEOUT_MS);
		});
	};

	const handleIframeLoad = () => {
		if (!pendingResolve) return;

		// Wait for the browser to complete rendering by counting consecutive
		// animation frames. Chart.js, D3, etc. schedule their first paint via
		// rAF or ResizeObserver (which fires before rAF). After 5 stable
		// frames the browser has fully painted; then add a short grace window
		// for any async errors to surface via postMessage.
		const RENDER_FRAMES = 5;
		let stableFrames = 0;
		let rafId: number | null = null;
		let rafTimeout: ReturnType<typeof setTimeout> | null = null;

		const checkFrame = () => {
			if (!pendingResolve) {
				if (rafId) cancelAnimationFrame(rafId);
				if (rafTimeout) clearTimeout(rafTimeout);
				return;
			}
			stableFrames++;
			if (stableFrames >= RENDER_FRAMES) {
				if (loadGraceTimer) clearTimeout(loadGraceTimer);
				loadGraceTimer = setTimeout(() => {
					loadGraceTimer = null;
					if (pendingResolve) {
						const r = pendingResolve;
						pendingResolve = null;
						r({ status: 'ok' });
					}
				}, 500);
			} else {
				rafId = requestAnimationFrame(checkFrame);
			}
		};
		rafId = requestAnimationFrame(checkFrame);

		// Safety: if rAF is throttled (e.g. hidden tab at 1fps),
		// don't wait forever. Fall through to the grace window.
		rafTimeout = setTimeout(() => {
			if (!pendingResolve || stableFrames >= RENDER_FRAMES) return;
			if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
			if (loadGraceTimer) clearTimeout(loadGraceTimer);
			loadGraceTimer = setTimeout(() => {
				loadGraceTimer = null;
				if (pendingResolve) {
					const r = pendingResolve;
					pendingResolve = null;
					r({ status: 'ok' });
				}
			}, 500);
		}, 5000);
	};

	const handleIframeError = (data: { msg: string; stack?: string }) => {
		if (loadGraceTimer) {
			clearTimeout(loadGraceTimer);
			loadGraceTimer = null;
		}
		if (pendingResolve) {
			const r = pendingResolve;
			pendingResolve = null;
			r({
				status: 'error',
				error_message: String(data.msg ?? '').slice(0, 500),
				error_stack: data.stack ?? undefined
			});
			return;
		}
		// No active resolver — this is a reload-time render error. The tool
		// already finished long ago; just surface a small "render error" chip
		// so the user has context.
		renderState = 'failed';
		lastErrorMessage = String(data.msg ?? '').slice(0, 240);
	};

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

	// ───── Hash + override registration ───────────────────────────────────────

	const computeOverrideKey = async (code: string): Promise<string> => {
		try {
			const enc = new TextEncoder();
			const buf = await crypto.subtle.digest('SHA-256', enc.encode(code));
			return Array.from(new Uint8Array(buf))
				.map((b) => b.toString(16).padStart(2, '0'))
				.join('')
				.slice(0, 16);
		} catch {
			return '';
		}
	};

	// ───── Misc UI ────────────────────────────────────────────────────────────

	const cycleLoadingMessages = () => {
		if (messageInterval) clearInterval(messageInterval);
		if (!loadingMessages || loadingMessages.length <= 1) return;
		messageInterval = setInterval(() => {
			messageIndex = (messageIndex + 1) % loadingMessages.length;
		}, 2000);
	};

	const handleCopy = async () => {
		const ok = await copyToClipboard(displayedCode || widgetCode);
		if (ok) toast.success($i18n.t('Copying to clipboard was successful!'));
	};

	const handleDownload = () => {
		const ext = isSvg ? 'svg' : 'html';
		const content = isSvg ? displayedCode : iframeDoc;
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

	onMount(async () => {
		window.addEventListener('message', handleMessage);
		cycleLoadingMessages();

		// Compute override key from the original widgetCode and apply persisted
		// override (if any) before the first paint.
		overrideKey = await computeOverrideKey(widgetCode);
		if (overrideKey) {
			const override = dataVizOverrides?.[overrideKey];
			if (override && override !== widgetCode) {
				lastPropCode = widgetCode; // suppress reactive reset
				displayedCode = override;
			}
			// Register with the registry so backend live-render calls find us.
			if (messageId) {
				unregister = registerWidgetHandler(messageId, overrideKey, renderHandler);
			}
		}
	});

	onDestroy(() => {
		window.removeEventListener('message', handleMessage);
		if (messageInterval) clearInterval(messageInterval);
		if (loadGraceTimer) clearTimeout(loadGraceTimer);
		if (pendingHardTimeout) clearTimeout(pendingHardTimeout);
		if (fixedFlashTimer) clearTimeout(fixedFlashTimer);
		clearPending('ok');
		if (unregister) unregister();
	});

	$: if (loadingMessages) cycleLoadingMessages();
</script>

<div class="group relative w-full my-2">
	{#if isSvg && trimmedCode}
		<div
			bind:this={svgContainer}
			class="w-full overflow-hidden [&>svg]:w-full [&>svg]:h-auto [&>svg]:max-w-full"
		>
			{@html displayedCode}
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
			on:load={handleIframeLoad}
		></iframe>
	{:else if loadingMessages.length > 0}
		<div class="text-xs text-gray-500 dark:text-gray-400 italic select-none">
			{loadingMessages[messageIndex]}
		</div>
	{/if}

	{#if trimmedCode && renderState !== 'idle' && renderState !== 'live'}
		<div
			class="absolute top-1 left-1 z-10 flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium border-hairline bg-manilla/60 dark:bg-manilla-dark border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 backdrop-blur-sm"
		>
			{#if renderState === 'repairing'}
				<span
					class="inline-block w-1.5 h-1.5 rounded-full bg-book-cloth animate-pulse"
					aria-hidden="true"
				></span>
				<span>{$i18n.t('Auto-fixing widget…')}</span>
			{:else if renderState === 'fixed'}
				<span class="text-book-cloth" aria-hidden="true">✓</span>
				<span>{$i18n.t('Auto-fixed')}</span>
			{:else if renderState === 'failed'}
				<Tooltip content={lastErrorMessage}>
					<span class="text-gray-600 dark:text-gray-400">{$i18n.t('Render error')}</span>
				</Tooltip>
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
