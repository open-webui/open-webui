<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import {
		getDesktopStatus,
		startDesktop,
		stopDesktop,
		getDesktopViewerUrl,
		type DesktopStatus
	} from '$lib/apis/terminal';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let baseUrl: string;
	export let apiKey: string;
	export let overlay = false;

	let status: DesktopStatus | null = null;
	let loading = false;
	let starting = false;
	let iframeKey = 0;
	let iframeEl: HTMLIFrameElement | null = null;
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	$: isSystemTerminal = baseUrl.includes('/terminals/');
	$: serverId = extractServerId(baseUrl);
	$: novncPort = status?.novnc_port ?? 6080;
	$: viewerUrl = buildViewerUrl();
	$: connected = status?.running === true;

	function extractServerId(url: string): string | null {
		const match = url.match(/\/terminals\/([^/]+)/);
		return match ? match[1] : null;
	}

	function buildViewerUrl(): string {
		if (isSystemTerminal && serverId) {
			const base = `${WEBUI_API_BASE_URL}/terminals/${serverId}`;
			return `${base}/proxy/${novncPort}/vnc.html`;
		}
		return getDesktopViewerUrl(baseUrl, novncPort);
	}

	function buildWsPath(): string | null {
		if (!isSystemTerminal) return null;
		if (!serverId) return null;
		const token = localStorage.getItem('token') ?? '';
		return `/api/v1/terminals/${serverId}/desktop/ws?token=${encodeURIComponent(token)}`;
	}

	function getIframeSrc(): string {
		const url = viewerUrl;
		const params = new URLSearchParams({
			autoconnect: 'true',
			resize: 'scale'
		});
		const wsPath = buildWsPath();
		if (wsPath) {
			params.set('path', wsPath);
		}
		return `${url}?${params.toString()}`;
	}

	async function refreshStatus() {
		const result = await getDesktopStatus(baseUrl, apiKey);
		status = result;
	}

	async function ensureRunning() {
		if (status?.running) return;
		starting = true;
		const result = await startDesktop(baseUrl, apiKey);
		if (result) {
			status = result;
		} else {
			await refreshStatus();
		}
		starting = false;
	}

	async function toggleDesktop() {
		if (loading) return;
		loading = true;
		try {
			if (status?.running) {
				await stopDesktop(baseUrl, apiKey);
				status = { running: false };
			} else {
				await ensureRunning();
			}
		} finally {
			loading = false;
		}
	}

	function refresh() {
		iframeKey += 1;
	}

	function openExternal() {
		const url = buildExternalUrl();
		window.open(url, '_blank', 'noopener,noreferrer');
	}

	function buildExternalUrl(): string {
		if (isSystemTerminal && serverId) {
			const token = localStorage.getItem('token') ?? '';
			const base = `${WEBUI_API_BASE_URL}/terminals/${serverId}`;
			return `${base}/proxy/${novncPort}/vnc.html?autoconnect=true&resize=scale&path=/api/v1/terminals/${serverId}/desktop/ws?token=${encodeURIComponent(token)}`;
		}
		return `${getDesktopViewerUrl(baseUrl, novncPort)}?autoconnect=true&resize=scale`;
	}

	async function goFullscreen() {
		iframeEl?.requestFullscreen?.();
	}

	function startPolling() {
		stopPolling();
		pollTimer = setInterval(refreshStatus, 10000);
	}

	function stopPolling() {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
	}

	onMount(async () => {
		await refreshStatus();
		if (!status?.running) {
			await ensureRunning();
		}
		startPolling();
	});

	onDestroy(() => {
		stopPolling();
	});
</script>

<div class="flex flex-col h-full min-h-0">
	<!-- Toolbar -->
	<div
		class="flex items-center gap-1 px-1.5 py-1 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 shrink-0"
	>
		<!-- Status indicator -->
		<div class="flex items-center gap-1.5 px-1">
			<div
				class="w-1.5 h-1.5 rounded-full transition-colors {connected
					? 'bg-emerald-500'
					: starting
						? 'bg-yellow-500 animate-pulse'
						: 'bg-gray-400'}"
			></div>
			<span class="text-[11px] text-gray-500 dark:text-gray-400">
				{#if starting}
					{$i18n.t('Starting...')}
				{:else if connected}
					{$i18n.t('Connected')}
				{:else}
					{$i18n.t('Stopped')}
				{/if}
			</span>
		</div>

		<div class="flex-1"></div>

		<!-- Start/Stop -->
		<Tooltip content={connected ? $i18n.t('Stop desktop') : $i18n.t('Start desktop')}>
			<button
				class="p-1 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300 transition"
				on:click={toggleDesktop}
				disabled={loading}
				aria-label={connected ? $i18n.t('Stop desktop') : $i18n.t('Start desktop')}
			>
				{#if connected}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3.5"
					>
						<path
							fill-rule="evenodd"
							d="M4.5 2A1.5 1.5 0 0 0 3 3.5v13A1.5 1.5 0 0 0 4.5 18h11a1.5 1.5 0 0 0 1.5-1.5V7.621a1.5 1.5 0 0 0-.44-1.06l-4.12-4.122A1.5 1.5 0 0 0 11.378 2H4.5Zm2.25 8.5a.75.75 0 0 0 0 1.5h6.5a.75.75 0 0 0 0-1.5h-6.5Z"
							clip-rule="evenodd"
						/>
					</svg>
				{:else}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3.5"
					>
						<path
							d="M5.75 3a.75.75 0 0 0-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 0 0 .75-.75V3.75A.75.75 0 0 0 7.25 3h-1.5ZM12.75 3a.75.75 0 0 0-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 0 0 .75-.75V3.75a.75.75 0 0 0-.75-.75h-1.5Z"
						/>
					</svg>
				{/if}
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
				>
					<path
						fill-rule="evenodd"
						d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.451a.75.75 0 0 0 0-1.5H4.5a.75.75 0 0 0-.75.75v3.75a.75.75 0 0 0 1.5 0v-2.127l.13.13a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm-10.624-2.85a5.5 5.5 0 0 1 9.201-2.465l.312.31H11.75a.75.75 0 0 0 0 1.5h3.75a.75.75 0 0 0 .75-.75V3.42a.75.75 0 0 0-1.5 0v2.126l-.13-.129A7 7 0 0 0 3.239 8.555a.75.75 0 0 0 1.449.39Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</Tooltip>

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

		<!-- Fullscreen -->
		<Tooltip content={$i18n.t('Fullscreen')}>
			<button
				class="p-1 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-300 transition"
				on:click={goFullscreen}
				aria-label={$i18n.t('Fullscreen')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						d="M3.28 2.22a.75.75 0 0 0-1.06 1.06L5.44 6.5H2.75a.75.75 0 0 0 0 1.5h4.5a.75.75 0 0 0 .75-.75v-4.5a.75.75 0 0 0-1.5 0v2.69L3.28 2.22Zm13.44 0a.75.75 0 0 1 1.06 1.06L14.56 6.5h2.69a.75.75 0 0 1 0 1.5h-4.5a.75.75 0 0 1-.75-.75v-4.5a.75.75 0 0 1 1.5 0v2.69l2.97-2.97ZM3.28 17.78a.75.75 0 0 0 1.06 1.06L6.5 14.56v2.69a.75.75 0 0 0 1.5 0v-4.5a.75.75 0 0 0-.75-.75h-4.5a.75.75 0 0 0 0 1.5h2.69l-2.16 2.28Zm13.44 1.06a.75.75 0 0 0 1.06-1.06L14.56 14.56v2.69a.75.75 0 0 1-1.5 0v-4.5c0-.414.336-.75.75-.75h4.5a.75.75 0 0 1 0 1.5h-2.69l2.97 2.97a.75.75 0 0 1-.87 1.37Z"
					/>
				</svg>
			</button>
		</Tooltip>
	</div>

	<!-- Starting overlay -->
	{#if starting}
		<div class="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
			<div class="flex flex-col items-center gap-2 text-gray-500 dark:text-gray-400">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-5 animate-spin"
				>
					<path
						fill-rule="evenodd"
						d="M15.312 11.424a5.5 5.5 0 0 1-9.201 2.466l-.312-.311h2.451a.75.75 0 0 0 0-1.5H4.5a.75.75 0 0 0-.75.75v3.75a.75.75 0 0 0 1.5 0v-2.127l.13.13a7 7 0 0 0 11.712-3.138.75.75 0 0 0-1.449-.39Zm-10.624-2.85a5.5 5.5 0 0 1 9.201-2.465l.312.31H11.75a.75.75 0 0 0 0 1.5h3.75a.75.75 0 0 0 .75-.75V3.42a.75.75 0 0 0-1.5 0v2.126l-.13-.129A7 7 0 0 0 3.239 8.555a.75.75 0 0 0 1.449.39Z"
						clip-rule="evenodd"
					/>
				</svg>
				<span class="text-xs">{$i18n.t('Starting virtual desktop...')}</span>
			</div>
		</div>
	{:else if !connected}
		<!-- Stopped state -->
		<div class="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
			<button
				class="flex flex-col items-center gap-2 px-4 py-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
				on:click={toggleDesktop}
				disabled={loading}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="currentColor"
					class="size-6"
				>
					<path
						fill-rule="evenodd"
						d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z"
						clip-rule="evenodd"
					/>
				</svg>
				<span class="text-xs font-medium">{$i18n.t('Start Desktop')}</span>
			</button>
		</div>
	{:else}
		<!-- noVNC iframe -->
		<div class="flex-1 min-h-0 relative">
			{#if overlay}
				<div class="absolute inset-0 z-10"></div>
			{/if}
			{#key iframeKey}
				<iframe
					bind:this={iframeEl}
					src={getIframeSrc()}
					title="Remote Desktop"
					class="w-full h-full border-0 bg-black"
					sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads"
				></iframe>
			{/key}
		</div>
	{/if}
</div>
