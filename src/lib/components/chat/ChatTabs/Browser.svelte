<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import Dropdown from '../../common/Dropdown.svelte';
	import DropdownMenu from '../../common/DropdownMenu.svelte';
	import Switch from '../../common/Switch.svelte';
	import ChromeBrowser from './ChromeBrowser.svelte';
	import {
		createBrowserSession,
		updateBrowserSession,
		closeBrowserSession,
		browserViewUrl,
		browserFrameUrl,
		type BrowserSession
	} from '$lib/apis/terminal/browser';
	import { getPortProxyUrl, type TerminalConnection } from '$lib/apis/terminal';
	import PortList from '../FileNav/PortList.svelte';
	import { settings } from '$lib/stores';
	import Icon from '../FileNav/Icon.svelte';
	import Tooltip from '../../common/Tooltip.svelte';

	const i18n = getContext<any>('i18n');
	export let baseUrl = '';
	export let connection: TerminalConnection | null = null;
	export let chatId: string | null = null;
	export let active = true;
	export let initialUrl = '';
	export let overlay = false;
	export let onNavigate: (url: string, label: string) => void = () => {};
	export let onOpenBrowser: (url: string) => void = () => {};
	export let onClose: (() => void) | null = null;
	let session: BrowserSession | null = null;
	let sessionChatId = chatId;
	let sessionConnection = connection;
	let chrome: ChromeBrowser;
	let switching = false;
	let deviceMode: 'desktop' | 'mobile' = 'desktop';
	let optionsOpen = false;
	let quality: 'low' | 'balanced' | 'crisp' = 'balanced';
	let chromeBack = false;
	let chromeForward = false;
	let frameReady = false;
	$: viewUrl = session && sessionConnection ? browserViewUrl(sessionConnection, session) : '';
	$: if (session && sessionConnection) {
		void updateBrowserSession(sessionConnection, sessionChatId, session.id, { active }).catch(
			() => {}
		);
	}
	$: if (session && sessionConnection && chatId && !sessionChatId) {
		const savedChatId = chatId;
		void updateBrowserSession(sessionConnection, sessionChatId, session.id, {
			chat_id: savedChatId
		})
			.then(() => (sessionChatId = savedChatId))
			.catch(() => {});
	}
	const persist = (url: string, title: string) => {
		if (session && sessionConnection)
			void updateBrowserSession(sessionConnection, sessionChatId, session.id, { url, title }).catch(
				() => {}
			);
	};
	const switchMode = async (mode: 'proxy' | 'chrome', remember = true) => {
		if (!session || !sessionConnection || switching || session.mode === mode) return;
		switching = true;
		try {
			session = await updateBrowserSession(sessionConnection, sessionChatId, session.id, {
				mode,
				url: currentUrl
			});
			frameReady = false;
			if (session.mode === 'proxy') {
				history = [];
				historyIndex = -1;
				if (currentUrl)
					frameUrl = browserFrameUrl(browserViewUrl(sessionConnection, session), currentUrl);
			}
			error = '';
			if (remember) localStorage.setItem('browserMode', mode);
		} catch (reason) {
			error = reason instanceof Error ? reason.message : String(reason);
		} finally {
			switching = false;
		}
	};
	const frameCommand = (command: string, url?: string) =>
		iframe?.contentWindow?.postMessage({ type: 'terminal-browser-command', command, url }, '*');
	const reload = () =>
		session?.mode === 'chrome'
			? chrome?.command('reload')
			: session
				? frameCommand('reload')
				: navigate(currentUrl, false);
	let urlInput = initialUrl;
	let currentUrl = '';
	let frameUrl = '';
	let frameKey = 0;
	let iframe: HTMLIFrameElement;
	let addressInput: HTMLInputElement;
	let history: string[] = [];
	let historyIndex = -1;
	let replaceHistory = false;
	let error = '';
	let connectionStatus = '';
	let loading = false;
	$: canGoBack = session?.mode === 'chrome' ? chromeBack : historyIndex > 0;
	$: canGoForward = session?.mode === 'chrome' ? chromeForward : historyIndex < history.length - 1;

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
		if (session && sessionConnection)
			return browserFrameUrl(browserViewUrl(sessionConnection, session), url.href);
		const port = localPort(url);
		if (port === null) return url.href;
		if (!baseUrl) throw new Error($i18n.t('Select a terminal to open localhost URLs.'));
		return getPortProxyUrl(baseUrl, port, url.pathname.slice(1) + url.search + url.hash);
	};
	const remember = (url: string, replace = false) => {
		if (replace && historyIndex >= 0) {
			history[historyIndex] = url;
			return;
		}
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
			if (!session && addHistory) remember(url.href);
			if (session?.mode === 'proxy') replaceHistory = !addHistory;
			if (session?.mode === 'chrome') chrome?.command('navigate', { url: url.href });
			else if (session && frameReady) frameCommand(addHistory ? 'navigate' : 'replace', url.href);
			else {
				frameUrl = src;
				frameKey++;
			}
			persist(url.href, url.host);
			loading = true;
			error = '';
			onNavigate(url.href, url.host);
		} catch (reason) {
			error = reason instanceof Error ? reason.message : String(reason);
		}
	};
	const move = (step: number) => {
		if (session?.mode === 'chrome') {
			chrome?.command(step < 0 ? 'back' : 'forward');
			return;
		}
		const next = historyIndex + step;
		if (next < 0 || next >= history.length) return;
		if (session) {
			historyIndex = next;
			frameCommand(step < 0 ? 'back' : 'forward');
			return;
		}
		historyIndex = next;
		navigate(history[next], false);
	};
	const loaded = () => {
		loading = false;
		frameReady = true;
		if (session) return;
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
		if (event.source !== iframe?.contentWindow || !currentUrl) return;
		const expectedOrigin = new URL(frameUrl, window.location.origin).origin;
		if (event.origin !== 'null' && event.origin !== expectedOrigin) return;
		const data = event.data;
		if (!data || typeof data.url !== 'string') return;
		try {
			const url = address(data.url);
			if (data.type === 'terminal-browser-popup') {
				onOpenBrowser(url.href);
				return;
			}
			if (data.type === 'terminal-browser-navigate') {
				navigate(url.href, !data.replace);
			} else if (data.type === 'terminal-browser-state') {
				if (!session && url.origin !== new URL(currentUrl).origin) return;
				if (currentUrl !== url.href || document.activeElement !== addressInput) urlInput = url.href;
				currentUrl = url.href;
				remember(url.href, replaceHistory || data.replace === true);
				replaceHistory = false;
				persist(url.href, typeof data.title === 'string' ? data.title : url.host);
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
		let disposed = false;
		const release = () => {
			if (session && sessionConnection)
				void closeBrowserSession(sessionConnection, sessionChatId, session.id).catch(() => {});
		};
		const heartbeat = setInterval(() => {
			if (session && sessionConnection)
				void updateBrowserSession(sessionConnection, sessionChatId, session.id, {}).catch(() => {});
		}, 60_000);
		window.addEventListener('message', receiveNavigation);
		window.addEventListener('pagehide', release);
		void (async () => {
			if (sessionConnection) {
				try {
					const created = await createBrowserSession(sessionConnection, sessionChatId, initialUrl);
					if (disposed) {
						await closeBrowserSession(sessionConnection, sessionChatId, created.id);
						return;
					}
					session = created;
					currentUrl = created.url || initialUrl;
					const savedMode = localStorage.getItem('browserMode');
					const mode =
						savedMode === 'proxy' || savedMode === 'chrome'
							? savedMode
							: created.chrome_available
								? 'chrome'
								: 'proxy';
					if (mode !== 'chrome' || created.chrome_available) {
						await switchMode(mode, false);
					}
					if (disposed) {
						release();
						return;
					}
					await tick();
				} catch (reason) {
					error = 'Browser sessions unavailable. Update Open Terminal. ' + String(reason);
					return;
				}
			}
			if (initialUrl) navigate(initialUrl);
			else addressInput?.focus();
		})();
		return () => {
			disposed = true;
			window.removeEventListener('message', receiveNavigation);
			window.removeEventListener('pagehide', release);
			clearInterval(heartbeat);
			release();
		};
	});
</script>

<div class="flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
	<div class="flex min-w-0 shrink-0 items-center gap-1 px-1.5 py-[3px] sm:px-2">
		{#each [{ name: 'Back', icon: 'chevron-left', disabled: !canGoBack, action: () => move(-1) }, { name: 'Forward', icon: 'chevron-right', disabled: !canGoForward, action: () => move(1) }, { name: 'Refresh', icon: 'refresh', disabled: !currentUrl, action: reload }] as button}
			<Tooltip content={$i18n.t(button.name)}
				><button
					type="button"
					class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 disabled:pointer-events-none disabled:opacity-35 dark:hover:bg-white/6 dark:hover:text-gray-300"
					disabled={button.disabled}
					aria-label={$i18n.t(button.name)}
					on:click={button.action}
					><Icon
						name={button.icon}
						size={12}
						class={button.icon === 'refresh' && loading ? 'animate-spin' : ''}
					/></button
				></Tooltip
			>
		{/each}
		<form class="relative min-w-0 flex-1" on:submit|preventDefault={() => navigate()}>
			<input
				bind:this={addressInput}
				bind:value={urlInput}
				on:click={() => addressInput.select()}
				aria-label={$i18n.t('URL')}
				placeholder="https://example.com"
				spellcheck="false"
				class="h-7 w-full min-w-0 rounded-full bg-transparent py-1 pr-8 pl-3 text-left text-xs font-normal text-gray-700 outline-none transition-colors hover:bg-gray-100/60 focus:bg-gray-100 sm:px-8 sm:text-center dark:text-gray-300 dark:hover:bg-white/5 dark:focus:bg-white/8"
			/>
			<Tooltip content={$i18n.t('Open in new tab')}
				><button
					type="button"
					disabled={!currentUrl && !frameUrl}
					aria-label={$i18n.t('Open in new tab')}
					class="absolute top-1/2 right-1 z-10 grid h-5 w-5 -translate-y-1/2 place-items-center rounded-full text-xs text-gray-500 hover:bg-gray-200/60 disabled:pointer-events-none disabled:opacity-35 dark:hover:bg-white/8"
					on:click={() =>
						window.open(
							session
								? localPort(new URL(currentUrl)) !== null
									? browserFrameUrl(viewUrl, currentUrl)
									: currentUrl
								: frameUrl,
							'_blank',
							'noopener,noreferrer'
						)}>↗</button
				></Tooltip
			>
		</form>
		{#if session}
			<Dropdown align="end" bind:show={optionsOpen}>
				<button
					type="button"
					aria-label={$i18n.t('Browser options')}
					class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 disabled:pointer-events-none disabled:opacity-35 dark:hover:bg-white/6 dark:hover:text-gray-300"
					><Icon name="three-dots" size={12} /></button
				>
				<div slot="content">
					<DropdownMenu className="w-48 font-normal">
						{#each session.chrome_available ? ['proxy', 'chrome'] : ['proxy'] as mode}
							<button
								type="button"
								role="menuitemradio"
								aria-checked={session.mode === mode}
								disabled={switching}
								on:click={() => {
									optionsOpen = false;
									void switchMode(mode as 'proxy' | 'chrome');
								}}
								class="font-normal disabled:opacity-40"
							>
								<span class="flex-1 text-left"
									>{mode === 'chrome' ? 'Chrome' : $i18n.t('Proxy')}</span
								>
								{#if session.mode === mode}<Icon name="check" size={12} />{/if}
							</button>
						{/each}
						{#if session.mode === 'chrome'}
							<hr class="border-gray-100 dark:border-gray-800" />
							{#each [{ value: 'low', label: 'Low' }, { value: 'balanced', label: 'Balanced' }, { value: 'crisp', label: 'Crisp' }] as item}
								<button
									type="button"
									role="menuitemradio"
									aria-checked={quality === item.value}
									on:click={() => {
										quality = item.value as typeof quality;
										optionsOpen = false;
									}}
									class="font-normal"
								>
									<span class="flex-1 text-left">{$i18n.t(item.label)}</span>
									{#if quality === item.value}<Icon name="check" size={12} />{/if}
								</button>
							{/each}
							<hr class="border-gray-100 dark:border-gray-800" />
							<button
								type="button"
								role="menuitemcheckbox"
								aria-checked={deviceMode === 'mobile'}
								class="font-normal"
								on:click={() => (deviceMode = deviceMode === 'mobile' ? 'desktop' : 'mobile')}
							>
								<span class="flex-1 whitespace-nowrap text-left">{$i18n.t('Mobile view')}</span>
								<div class="shrink-0" inert>
									<Switch state={deviceMode === 'mobile'} />
								</div>
							</button>
						{/if}
					</DropdownMenu>
				</div>
			</Dropdown>
		{/if}

		{#if onClose}<button
				type="button"
				aria-label={$i18n.t('Close')}
				class="flex size-5 shrink-0 items-center justify-center text-gray-500 dark:text-gray-400"
				on:click={onClose}><Icon name="xmark" size={11} /></button
			>{/if}
	</div>
	{#if error}
		<p role="alert" class="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">{error}</p>
	{:else if connectionStatus}
		<p role="status" class="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t(connectionStatus)}
		</p>
	{/if}
	<div class="relative min-h-0 flex-1">
		{#if overlay}<div class="absolute inset-0 z-10"></div>{/if}
		{#if session?.mode === 'chrome'}
			<div class="h-full" class:hidden={!currentUrl}>
				<ChromeBrowser
					bind:this={chrome}
					streamUrl={`${viewUrl}/stream`}
					{active}
					mobile={deviceMode === 'mobile'}
					{quality}
					onError={(message) => (error = message)}
					onStatus={(message) => (connectionStatus = message)}
					onState={(state) => {
						if (!state.url) return;
						if (currentUrl !== state.url || document.activeElement !== addressInput)
							urlInput = state.url;
						currentUrl = state.url;
						chromeBack = state.canGoBack;
						chromeForward = state.canGoForward;
						loading = false;
						onNavigate(state.url, state.title.trim() || new URL(state.url).host);
					}}
				/>
			</div>
		{:else if frameUrl}
			{#key frameKey}<iframe
					bind:this={iframe}
					src={frameUrl}
					title={$i18n.t('Browser')}
					class="block h-full w-full border-0 bg-white"
					sandbox="allow-scripts{!session && ($settings?.terminalPreviewAllowSameOrigin ?? false)
						? ' allow-same-origin'
						: ''} allow-forms allow-popups allow-modals allow-downloads"
					on:load={loaded}
				></iframe>{/key}
		{/if}
		{#if !currentUrl && !frameUrl}<div class="flex h-full overflow-y-auto px-6 pt-8 pb-20">
				<div class="m-auto w-full max-w-xs">
					<div class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
						<Icon name="browser" size={18} strokeWidth={1.4} class="text-gray-400" />
						{$i18n.t('Browser')}
					</div>
					{#if connection}
						<div class="mt-3">
							<PortList
								baseUrl={connection.baseUrl}
								previewBaseUrl={baseUrl}
								apiKey={connection.key}
								{chatId}
								{active}
								on:previewPort={(event) => navigate(`http://localhost:${event.detail}/`)}
							/>
						</div>
					{/if}
				</div>
			</div>{/if}
	</div>
</div>
