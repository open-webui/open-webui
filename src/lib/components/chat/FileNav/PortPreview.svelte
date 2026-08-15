<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { createPortPreviewToken, getPortPreviewUrl, isSystemTerminal } from '$lib/apis/terminal';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let baseUrl: string;
	export let apiKey: string = '';
	export let port: number;
	export let path: string = '';
	export let onClose: () => void = () => {};
	export let overlay = false;

	let urlInput: string = '';
	let iframeKey = 0;
	let isLoading = false;
	let previewToken: string | null = null;
	let tokenReady = false;
	let tokenError = false;

	// ── Navigation history ──────────────────────────────────────────────
	let history: string[] = [path];
	let historyIndex = 0;

	$: canGoBack = historyIndex > 0;
	$: canGoForward = historyIndex < history.length - 1;

	const pushHistory = (newPath: string) => {
		if (historyIndex < history.length - 1) {
			history = history.slice(0, historyIndex + 1);
		}
		history = [...history, newPath];
		historyIndex = history.length - 1;
	};

	const reloadFrame = () => {
		// Drop the cached key so an expired credential is re-minted rather than reloaded into a 403.
		tokenKey = '';
		ensurePreviewToken(baseUrl, port);
		isLoading = true;
		iframeKey += 1;
	};

	const goBack = () => {
		if (!canGoBack) return;
		historyIndex -= 1;
		path = history[historyIndex];
		syncUrlBar();
		reloadFrame();
	};

	const goForward = () => {
		if (!canGoForward) return;
		historyIndex += 1;
		path = history[historyIndex];
		syncUrlBar();
		reloadFrame();
	};

	// ── URLs ─────────────────────────────────────────────────────────────
	// A system terminal's preview comes from the application's own origin, so it must be denied that
	// origin. A user's own terminal server is a separate origin already and keeps its own.
	$: iframeSandbox = isSystemTerminal(baseUrl)
		? 'allow-scripts allow-forms allow-popups allow-modals allow-downloads'
		: 'allow-scripts allow-forms allow-popups allow-modals allow-downloads allow-same-origin';

	// Denied that origin, the preview's own requests cannot carry the session cookie and are
	// authorised by the token in the path instead. Wait for it before pointing the iframe anywhere,
	// and keep it across unrelated prop reassignments so the frame is not torn down mid-load.
	$: ensurePreviewToken(baseUrl, port);

	let tokenKey = '';
	let latestRequest = 0;
	const ensurePreviewToken = async (terminalUrl: string, previewPort: number) => {
		const key = `${terminalUrl}|${previewPort}`;
		if (key === tokenKey) return;
		tokenKey = key;
		const request = ++latestRequest;
		tokenReady = false;
		tokenError = false;
		previewToken = null;
		isLoading = true;

		if (!isSystemTerminal(terminalUrl)) {
			tokenReady = true;
			return;
		}
		const token = await createPortPreviewToken(terminalUrl, apiKey, previewPort);
		// A newer request took over while this one was in flight.
		if (request !== latestRequest) return;
		previewToken = token;
		tokenError = token === null;
		if (tokenError) isLoading = false;
		tokenReady = true;
	};

	$: previewUrl = getPortPreviewUrl(baseUrl, port, previewToken, path);

	const makeDisplayUrl = (p: string) => `localhost:${port}${p ? '/' + p : ''}`;
	const syncUrlBar = () => {
		urlInput = makeDisplayUrl(path);
	};
	urlInput = makeDisplayUrl(path);

	const openExternal = () => {
		if (!tokenReady || tokenError) {
			toast.error($i18n.t('Failed to open port {{port}}', { port }));
			return;
		}
		window.open(previewUrl, '_blank', 'noopener,noreferrer');
	};

	const navigateUrl = () => {
		const localhostPrefix = `localhost:${port}`;
		const stripped = urlInput.trim();
		let newPath = '';

		if (stripped.startsWith(localhostPrefix)) {
			newPath = stripped.slice(localhostPrefix.length).replace(/^\//, '');
		} else if (stripped.startsWith('/') || !stripped.includes(':')) {
			newPath = stripped.replace(/^\//, '');
		}

		if (newPath !== path) {
			path = newPath;
			pushHistory(path);
		}
		syncUrlBar();
		reloadFrame();
	};

	// The sandboxed frame is opaque-origin, so its location is unreadable and the URL bar only
	// reflects paths entered here.
	const onIframeLoad = () => {
		isLoading = false;
	};
</script>

<div class="flex flex-col h-full min-h-0">
	<!-- Browser chrome -->
	<div
		class="flex items-center gap-1 px-1.5 py-1 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 shrink-0"
	>
		<!-- Back -->
		<Tooltip content={$i18n.t('Back')}>
			<button
				class="p-1 rounded transition {canGoBack
					? 'text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300'
					: 'text-gray-300 dark:text-gray-700 cursor-default'}"
				on:click={goBack}
				disabled={!canGoBack}
				aria-label={$i18n.t('Back')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M11.78 5.22a.75.75 0 0 1 0 1.06L8.06 10l3.72 3.72a.75.75 0 1 1-1.06 1.06l-4.25-4.25a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</Tooltip>

		<!-- Forward -->
		<Tooltip content={$i18n.t('Forward')}>
			<button
				class="p-1 rounded transition {canGoForward
					? 'text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300'
					: 'text-gray-300 dark:text-gray-700 cursor-default'}"
				on:click={goForward}
				disabled={!canGoForward}
				aria-label={$i18n.t('Forward')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 1 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</Tooltip>

		<!-- Refresh -->
		<Tooltip content={$i18n.t('Refresh')}>
			<button
				class="p-1 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300 transition"
				on:click={reloadFrame}
				aria-label={$i18n.t('Refresh')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
					class:animate-spin={isLoading}
				>
					<path
						fill-rule="evenodd"
						d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.451a.75.75 0 0 0 0-1.5H4.5a.75.75 0 0 0-.75.75v3.75a.75.75 0 0 0 1.5 0v-2.127l.13.13a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm-10.624-2.85a5.5 5.5 0 0 1 9.201-2.465l.312.31H11.75a.75.75 0 0 0 0 1.5h3.75a.75.75 0 0 0 .75-.75V3.42a.75.75 0 0 0-1.5 0v2.126l-.13-.129A7 7 0 0 0 3.239 8.555a.75.75 0 0 0 1.449.39Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</Tooltip>

		<!-- URL bar -->
		<form class="flex-1 min-w-0" on:submit|preventDefault={navigateUrl}>
			<input
				type="text"
				bind:value={urlInput}
				class="w-full text-[0.6875rem] font-mono bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full px-3 py-1 outline-none focus:border-blue-400 dark:focus:border-blue-500 focus:ring-1 focus:ring-blue-400/20 text-gray-600 dark:text-gray-300 transition"
				placeholder="localhost:{port}"
			/>
		</form>

		<!-- Open in new tab -->
		<Tooltip content={$i18n.t('Open in new tab')}>
			<button
				class="p-1 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300 transition"
				on:click={openExternal}
				aria-label={$i18n.t('Open in new tab')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M4.25 5.5a.75.75 0 0 0-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 0 0 .75-.75v-4a.75.75 0 0 1 1.5 0v4A2.25 2.25 0 0 1 12.75 17h-8.5A2.25 2.25 0 0 1 2 14.75v-8.5A2.25 2.25 0 0 1 4.25 4h5a.75.75 0 0 1 0 1.5h-5Zm7.5-3.5a.75.75 0 0 0 0 1.5h2.69l-4.72 4.72a.75.75 0 0 0 1.06 1.06l4.72-4.72v2.69a.75.75 0 0 0 1.5 0v-5.25a.75.75 0 0 0-.75-.75h-5.25Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</Tooltip>

		<!-- Close -->
		<Tooltip content={$i18n.t('Close')}>
			<button
				class="p-1 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300 transition"
				on:click={onClose}
				aria-label={$i18n.t('Close')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
					/>
				</svg>
			</button>
		</Tooltip>
	</div>

	<!-- Loading bar -->
	{#if isLoading}
		<div class="h-0.5 bg-gray-100 dark:bg-gray-800 shrink-0 overflow-hidden">
			<div class="h-full bg-blue-500 animate-loading-bar rounded-full" />
		</div>
	{/if}

	<!-- Iframe -->
	<div class="flex-1 min-h-0 relative">
		{#if overlay}
			<div class="absolute inset-0 z-10"></div>
		{/if}
		{#if tokenError}
			<div class="flex h-full items-center justify-center px-4 text-xs text-gray-500">
				{$i18n.t('Failed to open port {{port}}', { port })}
			</div>
		{:else if tokenReady}
			{#key iframeKey}
				<iframe
					src={previewUrl}
					title="Port {port} preview"
					class="w-full h-full border-0 bg-white"
					sandbox={iframeSandbox}
					on:load={onIframeLoad}
				/>
			{/key}
		{/if}
	</div>
</div>

<style>
	@keyframes loading-bar {
		0% {
			width: 0;
			margin-left: 0;
		}
		50% {
			width: 60%;
			margin-left: 20%;
		}
		100% {
			width: 0;
			margin-left: 100%;
		}
	}
	.animate-loading-bar {
		animation: loading-bar 1.5s ease-in-out infinite;
	}
</style>
