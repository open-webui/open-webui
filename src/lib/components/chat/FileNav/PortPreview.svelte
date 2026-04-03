<script lang="ts">
	import { getContext } from 'svelte';
	import { getPortProxyUrl } from '$lib/apis/terminal';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let baseUrl: string;
	export let port: number;
	export let path: string = '';
	export let onClose: () => void = () => {};
	export let overlay = false;

	let iframeEl: HTMLIFrameElement;
	let urlInput: string = '';
	let iframeKey = 0;
	let isLoading = false;

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

	const goBack = () => {
		if (!canGoBack) return;
		historyIndex -= 1;
		path = history[historyIndex];
		syncUrlBar();
		iframeKey += 1;
	};

	const goForward = () => {
		if (!canGoForward) return;
		historyIndex += 1;
		path = history[historyIndex];
		syncUrlBar();
		iframeKey += 1;
	};

	// ── URLs ─────────────────────────────────────────────────────────────
	$: proxyUrl = getPortProxyUrl(baseUrl, port, path);

	$: proxyPathPrefix = (() => {
		try {
			return new URL(getPortProxyUrl(baseUrl, port, ''), window.location.origin).pathname;
		} catch {
			return `/proxy/${port}/`;
		}
	})();

	const makeDisplayUrl = (p: string) => `localhost:${port}${p ? '/' + p : ''}`;
	const syncUrlBar = () => {
		urlInput = makeDisplayUrl(path);
	};
	urlInput = makeDisplayUrl(path);

	const refresh = () => {
		iframeKey += 1;
	};

	const openExternal = () => {
		window.open(proxyUrl, '_blank', 'noopener,noreferrer');
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
		iframeKey += 1;
	};

	/**
	 * Read the iframe's current location and sync the URL bar.
	 * If the iframe escaped the proxy prefix, redirect it back.
	 */
	const onIframeLoad = () => {
		isLoading = false;
		if (!iframeEl) return;
		try {
			const loc = iframeEl.contentWindow?.location;
			if (!loc) return;
			const iframePath = loc.pathname ?? '';
			const iframeSearch = loc.search ?? '';
			const iframeHash = loc.hash ?? '';

			if (iframePath.startsWith(proxyPathPrefix)) {
				const relativePath = iframePath.slice(proxyPathPrefix.length) + iframeSearch + iframeHash;
				if (relativePath !== path) {
					path = relativePath;
					pushHistory(path);
					syncUrlBar();
				}
			}
		} catch {
			// Cross-origin — can't access
		}
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
				on:click={refresh}
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
				class="w-full text-[11px] font-mono bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full px-3 py-1 outline-none focus:border-blue-400 dark:focus:border-blue-500 focus:ring-1 focus:ring-blue-400/20 text-gray-600 dark:text-gray-300 transition"
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
		{#key iframeKey}
			<iframe
				bind:this={iframeEl}
				src={proxyUrl}
				title="Port {port} preview"
				class="w-full h-full border-0 bg-white"
				sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads"
				on:load={onIframeLoad}
			/>
		{/key}
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
