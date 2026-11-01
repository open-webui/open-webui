<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getPortProxyUrl } from '$lib/apis/terminal';
	import { settings } from '$lib/stores';
	import Icon from '../FileNav/Icon.svelte';
	import Tooltip from '../../common/Tooltip.svelte';

	const i18n = getContext<any>('i18n');
	export let baseUrl = '';
	export let initialUrl = '';
	export let overlay = false;
	export let onNavigate: (url: string, label: string) => void = () => {};
	export let onClose: (() => void) | null = null;
	let urlInput = initialUrl;
	let currentUrl = '';
	let frameUrl = '';
	let frameKey = 0;
	let iframe: HTMLIFrameElement;
	let addressInput: HTMLInputElement;
	let history: string[] = [];
	let historyIndex = -1;
	let error = '';
	let loading = false;
	$: canGoBack = historyIndex > 0;
	$: canGoForward = historyIndex < history.length - 1;

	const address = (value: string): URL => {
		const input = value.trim();
		const hasScheme = /^[a-z][a-z\d+.-]*:/i.test(input) && !/^[^/]+:\d+(?:[/?#]|$)/.test(input);
		const local = /^(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?=[:/?#]|$)/i.test(input);
		const url =
			/^[/?#]/.test(input) && currentUrl
				? new URL(input, currentUrl)
				: new URL(hasScheme ? input : `${local ? 'http' : 'https'}://${input}`);
		if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password)
			throw new Error($i18n.t('Enter an HTTP or HTTPS URL without credentials.'));
		return url;
	};
	const localPort = (url: URL) =>
		['localhost', '127.0.0.1', '0.0.0.0', '[::1]'].includes(url.hostname)
			? Number(url.port || (url.protocol === 'https:' ? 443 : 80))
			: null;
	const source = (url: URL) => {
		const port = localPort(url);
		if (port === null) return url.href;
		if (!baseUrl) throw new Error($i18n.t('Select a terminal to open localhost URLs.'));
		return getPortProxyUrl(baseUrl, port, url.pathname.slice(1) + url.search + url.hash);
	};
	const remember = (url: string) => {
		if (history[historyIndex] === url) return;
		history = [...history.slice(0, historyIndex + 1), url];
		historyIndex = history.length - 1;
	};
	const navigate = (value = urlInput, addHistory = true) => {
		if (!value.trim()) return;
		try {
			const url = address(value);
			const src = source(url);
			currentUrl = url.href;
			urlInput = url.href;
			if (addHistory) remember(url.href);
			frameUrl = src;
			frameKey++;
			loading = true;
			error = '';
			onNavigate(url.href, url.host);
		} catch (reason) {
			error = reason instanceof Error ? reason.message : String(reason);
		}
	};
	const move = (step: number) => {
		const next = historyIndex + step;
		if (next < 0 || next >= history.length) return;
		historyIndex = next;
		navigate(history[next], false);
	};
	const loaded = () => {
		loading = false;
		try {
			const location = iframe.contentWindow?.location;
			if (!location || location.href === 'about:blank') return;
			const url = new URL(currentUrl);
			const port = localPort(url);
			let next: URL;
			if (port !== null) {
				const prefix = new URL(getPortProxyUrl(baseUrl, port), window.location.origin);
				if (location.origin !== prefix.origin || !location.pathname.startsWith(prefix.pathname))
					return;
				next = new URL(
					location.pathname.slice(prefix.pathname.length) + location.search + location.hash,
					`${url.origin}/`
				);
			} else next = address(location.href);
			currentUrl = next.href;
			urlInput = next.href;
			remember(next.href);
			onNavigate(next.href, iframe.contentDocument?.title || next.host);
		} catch {
			/* Cross-origin pages do not expose their location or title. */
		}
	};
	const receiveNavigation = (event: MessageEvent) => {
		if (event.source !== iframe?.contentWindow || !baseUrl || !currentUrl) return;
		const expectedOrigin = new URL(frameUrl, window.location.origin).origin;
		if (event.origin !== 'null' && event.origin !== expectedOrigin) return;
		const data = event.data;
		if (!data || typeof data.url !== 'string') return;
		try {
			const url = address(data.url);
			if (data.type === 'terminal-browser-navigate') {
				if (data.replace && historyIndex >= 0) history[historyIndex] = url.href;
				navigate(url.href, !data.replace);
			} else if (data.type === 'terminal-browser-state') {
				if (url.origin !== new URL(currentUrl).origin) return;
				currentUrl = url.href;
				urlInput = url.href;
				remember(url.href);
				onNavigate(
					url.href,
					typeof data.title === 'string' && data.title.trim() ? data.title : url.host
				);
			}
		} catch {
			/* Ignore malformed messages from page content. */
		}
	};
	onMount(() => {
		window.addEventListener('message', receiveNavigation);
		if (initialUrl) navigate(initialUrl);
		else addressInput?.focus();
		return () => window.removeEventListener('message', receiveNavigation);
	});
</script>

<div class="flex h-full min-h-0 flex-col">
	<div class="flex shrink-0 items-center gap-1 px-2 pt-0 pb-1.5">
		{#each [{ name: 'Back', icon: 'chevron-left', disabled: !canGoBack, action: () => move(-1) }, { name: 'Forward', icon: 'chevron-right', disabled: !canGoForward, action: () => move(1) }, { name: 'Refresh', icon: 'refresh', disabled: !currentUrl, action: () => navigate(currentUrl, false) }] as button}
			<Tooltip content={$i18n.t(button.name)}
				><button
					type="button"
					class="flex size-5 shrink-0 items-center justify-center rounded text-gray-500 hover:text-gray-800 disabled:opacity-30 dark:text-gray-400 dark:hover:text-gray-200"
					disabled={button.disabled}
					aria-label={$i18n.t(button.name)}
					on:click={button.action}
					><Icon
						name={button.icon}
						size={11}
						strokeWidth={1.4}
						class={button.icon === 'refresh' && loading ? 'animate-spin' : ''}
					/></button
				></Tooltip
			>
		{/each}
		<form class="min-w-0 flex-1" on:submit|preventDefault={() => navigate()}>
			<input
				bind:this={addressInput}
				bind:value={urlInput}
				aria-label={$i18n.t('URL')}
				placeholder={$i18n.t('Enter URL')}
				spellcheck="false"
				class="h-6 w-full rounded-lg bg-gray-50 px-2 text-xs text-gray-700 outline-none dark:bg-gray-850 dark:text-gray-200"
			/>
		</form>
		<Tooltip content={$i18n.t('Open in new tab')}
			><button
				type="button"
				disabled={!frameUrl}
				aria-label={$i18n.t('Open in new tab')}
				class="flex size-5 shrink-0 items-center justify-center rounded text-gray-500 hover:text-gray-800 disabled:opacity-30 dark:text-gray-400 dark:hover:text-gray-200"
				on:click={() => window.open(frameUrl, '_blank', 'noopener,noreferrer')}
				><Icon name="external-link" size={11} strokeWidth={1.4} /></button
			></Tooltip
		>
		{#if onClose}<button
				type="button"
				aria-label={$i18n.t('Close')}
				class="flex size-5 shrink-0 items-center justify-center text-gray-500 dark:text-gray-400"
				on:click={onClose}><Icon name="xmark" size={11} /></button
			>{/if}
	</div>
	{#if error}<p role="alert" class="px-2 py-1 text-xs text-red-500">{error}</p>{/if}
	<div class="relative min-h-0 flex-1">
		{#if overlay}<div class="absolute inset-0 z-10"></div>{/if}
		{#if frameUrl}
			{#key frameKey}<iframe
					bind:this={iframe}
					src={frameUrl}
					title={$i18n.t('Browser')}
					class="h-full w-full border-0 bg-white"
					sandbox="allow-scripts{($settings?.terminalPreviewAllowSameOrigin ?? false)
						? ' allow-same-origin'
						: ''} allow-forms allow-popups allow-modals allow-downloads"
					on:load={loaded}
				></iframe>{/key}
		{:else}<div class="flex h-full items-center justify-center text-xs text-gray-400">
				{$i18n.t('Enter a URL to browse.')}
			</div>{/if}
	</div>
</div>
