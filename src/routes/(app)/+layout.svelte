<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { openDB, deleteDB } from 'idb';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fade } from 'svelte/transition';

	import { getModels, getVersionUpdates } from '$lib/apis';
	import { getTools } from '$lib/apis/tools';
	import { getBanners } from '$lib/apis/configs';
	import { getUserSettings } from '$lib/apis/users';

	import { WEBUI_VERSION } from '$lib/constants';
	import type { Banner } from '$lib/types';
	import { readLocalStorageCache, writeLocalStorageCache } from '$lib/utils/cache';
	import { loadToolServers } from '$lib/utils/toolServers';
	import { compareVersion } from '$lib/utils';

	import {
		config,
		user,
		settings,
		models,
		modelsLoaded,
		tools,
		banners,
		showSettings,
		showShortcuts,
		showChangelog,
		temporaryChatEnabled,
		toolServers,
		toolServersLoaded,
		showSearch,
		showSidebar
	} from '$lib/stores';

	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	const SettingsModal = () => import('$lib/components/chat/SettingsModal.svelte');
	const ChangelogModal = () => import('$lib/components/ChangelogModal.svelte');
	import AccountPending from '$lib/components/layout/Overlay/AccountPending.svelte';
	import UpdateInfoToast from '$lib/components/layout/UpdateInfoToast.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	let loaded = false;
	let DB = null;
	let localDBChats = [];

	let version;
	const MODELS_CACHE_KEY = 'models';
	const STARTUP_CACHE_VERSION = 1;
	const STARTUP_BANNERS_CACHE_KEY = 'startup:banners';
	const STARTUP_TOOLS_CACHE_KEY = 'startup:tools';
	const LEGACY_CHAT_DB_EMPTY_KEY = 'legacy-chat-db-empty';
	const BANNERS_CACHE_TTL = 5 * 60 * 1000;
	const TOOLS_CACHE_TTL = 60 * 1000;
	let toolServersLoadScheduled = false;

	type DirectConnections = {
		OPENAI_API_BASE_URLS?: string[];
		OPENAI_API_KEYS?: string[];
		OPENAI_API_CONFIGS?: Record<
			string,
			{
				enable?: boolean;
				model_ids?: string[];
				prefix_id?: string;
				tags?: { name: string }[];
			}
		>;
	};

	const getUserCacheKey = (name: string) =>
		JSON.stringify({
			version: STARTUP_CACHE_VERSION,
			userId: $user?.id ?? null,
			name
		});

	const clearChatInputStorage = () => {
		const chatInputKeys = Object.keys(localStorage).filter((key) => key.startsWith('chat-input'));
		if (chatInputKeys.length > 0) {
			chatInputKeys.forEach((key) => {
				localStorage.removeItem(key);
			});
		}
	};

	const getLegacyChatDBCheckCacheKey = () => getUserCacheKey('legacy-chat-db-empty');

	const markLegacyChatDBEmptyChecked = () => {
		localStorage.setItem(LEGACY_CHAT_DB_EMPTY_KEY, getLegacyChatDBCheckCacheKey());
	};

	const checkLocalDBChats = async () => {
		if (localStorage.getItem(LEGACY_CHAT_DB_EMPTY_KEY) === getLegacyChatDBCheckCacheKey()) {
			return;
		}

		try {
			// Check if IndexedDB exists
			DB = await openDB('Chats', 1);

			if (!DB) {
				markLegacyChatDBEmptyChecked();
				return;
			}

			const chats = await DB.getAllFromIndex('chats', 'timestamp');
			localDBChats = chats.map((item, idx) => chats[chats.length - 1 - idx]);

			if (localDBChats.length === 0) {
				await deleteDB('Chats');
				markLegacyChatDBEmptyChecked();
			}
		} catch (error) {
			if (error instanceof DOMException && error.name === 'NotFoundError') {
				await deleteDB('Chats').catch((e) => {
					console.error('Failed to delete empty legacy Chats DB', e);
				});
				markLegacyChatDBEmptyChecked();
				return;
			}

			console.error('Failed to check legacy local DB chats', error);
		}
	};

	const getModelRequestDirectConnections = (): DirectConnections | null =>
		$config?.features?.enable_direct_connections
			? (($settings?.directConnections as DirectConnections | null) ?? null)
			: null;

	const getDirectConnectionsCacheKey = (directConnections: DirectConnections | null) => {
		if (!directConnections) {
			return null;
		}

		return {
			OPENAI_API_BASE_URLS: directConnections.OPENAI_API_BASE_URLS ?? [],
			OPENAI_API_CONFIGS: directConnections.OPENAI_API_CONFIGS ?? {},
			OPENAI_API_KEYS: (directConnections.OPENAI_API_KEYS ?? []).map((key) => Boolean(key))
		};
	};

	const getModelsCacheKey = (
		directConnections: DirectConnections | null = getModelRequestDirectConnections()
	) =>
		JSON.stringify({
			version: 1,
			userId: $user?.id ?? null,
			directConnections: getDirectConnectionsCacheKey(directConnections)
		});

	const hydrateModelsFromCache = () => {
		try {
			const cachedModels = JSON.parse(localStorage.getItem(MODELS_CACHE_KEY) ?? 'null');
			if (cachedModels?.cacheKey === getModelsCacheKey() && Array.isArray(cachedModels?.models)) {
				models.set(cachedModels.models);
				modelsLoaded.set(true);
			}
		} catch (e) {
			console.error('Failed to parse cached models', e);
			localStorage.removeItem(MODELS_CACHE_KEY);
		}
	};

	const hydrateStartupDataFromCache = () => {
		const cachedBanners = readLocalStorageCache<Banner[]>(
			STARTUP_BANNERS_CACHE_KEY,
			getUserCacheKey('banners')
		);
		if (Array.isArray(cachedBanners)) {
			banners.set(cachedBanners);
		}

		const cachedTools = readLocalStorageCache<any[]>(
			STARTUP_TOOLS_CACHE_KEY,
			getUserCacheKey('tools')
		);
		if (Array.isArray(cachedTools)) {
			tools.set(cachedTools);
		}
	};

	const setModels = async () => {
		const directConnections = getModelRequestDirectConnections();
		const cacheKey = getModelsCacheKey(directConnections);

		try {
			const modelData = await getModels(localStorage.token, directConnections);

			models.set(modelData);
			try {
				localStorage.setItem(
					MODELS_CACHE_KEY,
					JSON.stringify({
						cacheKey,
						models: modelData
					})
				);
			} catch (e) {
				console.error('Failed to cache models', e);
			}
		} catch (e) {
			console.error('Failed to fetch models', e);
		} finally {
			modelsLoaded.set(true);
		}
	};

	const setBanners = async () => {
		try {
			const bannersData = await getBanners(localStorage.token);
			banners.set(bannersData);
			writeLocalStorageCache(
				STARTUP_BANNERS_CACHE_KEY,
				getUserCacheKey('banners'),
				bannersData,
				BANNERS_CACHE_TTL
			);
		} catch (e) {
			console.error('Failed to fetch banners', e);
		}
	};

	const scheduleToolServersLoad = () => {
		if (toolServersLoadScheduled) {
			return;
		}

		toolServersLoadScheduled = true;
		const load = () => {
			toolServersLoadScheduled = false;
			loadToolServers().catch((e) => {
				console.error('Failed to load tool servers', e);
			});
		};

		if ('requestIdleCallback' in window) {
			(window as any).requestIdleCallback(load, { timeout: 2000 });
		} else {
			setTimeout(load, 250);
		}
	};

	const setTools = async () => {
		try {
			const toolsData = await getTools(localStorage.token);
			tools.set(toolsData);
			writeLocalStorageCache(
				STARTUP_TOOLS_CACHE_KEY,
				getUserCacheKey('tools'),
				toolsData,
				TOOLS_CACHE_TTL
			);
		} catch (e) {
			console.error('Failed to fetch tools', e);
		}
	};

	onMount(async () => {
		if ($user === undefined || $user === null) {
			await goto('/auth');
			return;
		}
		if (!['user', 'admin'].includes($user?.role)) {
			return;
		}

		clearChatInputStorage();
		models.set([]);
		modelsLoaded.set(false);
		tools.set(null);
		banners.set([]);
		toolServers.set([]);
		toolServersLoaded.set(false);

		// SWR: Apply cached settings immediately so <slot/> renders without delay
		try {
			const cachedSettings = JSON.parse(localStorage.getItem('settings') ?? '{}');
			if (cachedSettings?.ui) {
				settings.set(cachedSettings.ui);
			}
		} catch (e) {}

		hydrateStartupDataFromCache();
		hydrateModelsFromCache();

		loaded = true;

		// Background: fetch fresh settings + everything else in parallel
		Promise.all([
			getUserSettings(localStorage.token)
				.then((userSettings) => {
					if (userSettings?.ui) {
						settings.set(userSettings.ui);
						localStorage.setItem('settings', JSON.stringify(userSettings));
						scheduleToolServersLoad();
					}
				})
				.catch((e) => console.error('Failed to fetch user settings', e)),
			checkLocalDBChats(),
			setBanners(),
			setTools(),
			setModels()
		]);

		const setupKeyboardShortcuts = () => {
			document.addEventListener('keydown', async function (event) {
				const isCtrlPressed = event.ctrlKey || event.metaKey; // metaKey is for Cmd key on Mac
				// Check if the Shift key is pressed
				const isShiftPressed = event.shiftKey;

				// Check if Ctrl  + K is pressed
				if (isCtrlPressed && event.key.toLowerCase() === 'k') {
					event.preventDefault();
					console.log('search');
					showSearch.set(!$showSearch);
				}

				// Check if Ctrl + Shift + O is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 'o') {
					event.preventDefault();
					console.log('newChat');
					document.getElementById('sidebar-new-chat-button')?.click();
				}

				// Check if Shift + Esc is pressed
				if (isShiftPressed && event.key === 'Escape') {
					event.preventDefault();
					console.log('focusInput');
					document.getElementById('chat-input')?.focus();
				}

				// Check if Ctrl + Shift + ; is pressed
				if (isCtrlPressed && isShiftPressed && event.key === ';') {
					event.preventDefault();
					console.log('copyLastCodeBlock');
					const button = [...document.getElementsByClassName('copy-code-button')]?.at(-1);
					button?.click();
				}

				// Check if Ctrl + Shift + C is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 'c') {
					event.preventDefault();
					console.log('copyLastResponse');
					const button = [...document.getElementsByClassName('copy-response-button')]?.at(-1);
					console.log(button);
					button?.click();
				}

				// Check if Ctrl + Shift + S is pressed
				if (isCtrlPressed && isShiftPressed && event.key.toLowerCase() === 's') {
					event.preventDefault();
					console.log('toggleSidebar');
					document.getElementById('sidebar-toggle-button')?.click();
				}

				// Check if Ctrl + Shift + Backspace is pressed
				if (
					isCtrlPressed &&
					isShiftPressed &&
					(event.key === 'Backspace' || event.key === 'Delete')
				) {
					event.preventDefault();
					console.log('deleteChat');
					document.getElementById('delete-chat-button')?.click();
				}

				// Check if Ctrl + . is pressed
				if (isCtrlPressed && event.key === '.') {
					event.preventDefault();
					console.log('openSettings');
					showSettings.set(!$showSettings);
				}

				// Check if Ctrl + / is pressed
				if (isCtrlPressed && event.key === '/') {
					event.preventDefault();

					showShortcuts.set(!$showShortcuts);
				}

				// Check if Ctrl + Shift + ' is pressed
				if (
					isCtrlPressed &&
					isShiftPressed &&
					(event.key.toLowerCase() === `'` || event.key.toLowerCase() === `"`)
				) {
					event.preventDefault();
					console.log('temporaryChat');

					if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
						temporaryChatEnabled.set(true);
					} else {
						temporaryChatEnabled.set(!$temporaryChatEnabled);
					}

					await goto('/');
					const newChatButton = document.getElementById('new-chat-button');
					setTimeout(() => {
						newChatButton?.click();
					}, 0);
				}
			});
		};
		setupKeyboardShortcuts();

		if ($user?.role === 'admin' && ($settings?.showChangelog ?? true)) {
			showChangelog.set($settings?.version !== $config.version);
		}

		if ($user?.role === 'admin' || ($user?.permissions?.chat?.temporary ?? true)) {
			if ($page.url.searchParams.get('temporary-chat') === 'true') {
				temporaryChatEnabled.set(true);
			}

			if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
				temporaryChatEnabled.set(true);
			}
		}

		// Check for version updates
		if ($user?.role === 'admin' && $config?.features?.enable_version_update_check) {
			// Check if the user has dismissed the update toast in the last 24 hours
			if (localStorage.dismissedUpdateToast) {
				const dismissedUpdateToast = new Date(Number(localStorage.dismissedUpdateToast));
				const now = new Date();

				if (now - dismissedUpdateToast > 24 * 60 * 60 * 1000) {
					checkForVersionUpdates();
				}
			} else {
				checkForVersionUpdates();
			}
		}
		await tick();
	});

	const checkForVersionUpdates = async () => {
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});
	};
</script>

{#if $showSettings}
	{#await SettingsModal() then Module}
		<svelte:component this={Module.default} bind:show={$showSettings} />
	{/await}
{/if}

{#if $showChangelog}
	{#await ChangelogModal() then Module}
		<svelte:component this={Module.default} bind:show={$showChangelog} />
	{/await}
{/if}

{#if version && compareVersion(version.latest, version.current) && ($settings?.showUpdateToast ?? true)}
	<div class=" absolute bottom-8 right-8 z-50" in:fade={{ duration: 100 }}>
		<UpdateInfoToast
			{version}
			on:close={() => {
				localStorage.setItem('dismissedUpdateToast', Date.now().toString());
				version = null;
			}}
		/>
	</div>
{/if}

{#if $user}
	<div class="app relative">
		<div
			class=" text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end"
		>
			{#if !['user', 'admin'].includes($user?.role)}
				<AccountPending />
			{:else}
				{#if localDBChats.length > 0}
					<div class="fixed w-full h-full flex z-50">
						<div
							class="absolute w-full h-full backdrop-blur-md bg-white/20 dark:bg-gray-900/50 flex justify-center"
						>
							<div class="m-auto pb-44 flex flex-col justify-center">
								<div class="max-w-md">
									<div class="text-center dark:text-white text-2xl font-medium z-50">
										{$i18n.t('Important Update')}<br />
										{$i18n.t('Action Required for Chat Log Storage')}
									</div>

									<div class=" mt-4 text-center text-sm dark:text-gray-200 w-full">
										{$i18n.t(
											"Saving chat logs directly to your browser's storage is no longer supported. Please take a moment to download and delete your chat logs by clicking the button below. Don't worry, you can easily re-import your chat logs to the backend through"
										)}
										<span class="font-semibold dark:text-white"
											>{$i18n.t('Settings')} > {$i18n.t('Chats')} > {$i18n.t('Import Chats')}</span
										>. {$i18n.t(
											'This ensures that your valuable conversations are securely saved to your backend database. Thank you!'
										)}
									</div>

									<div class=" mt-6 mx-auto relative group w-fit">
										<button
											class="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 transition font-medium text-sm"
											on:click={async () => {
												let blob = new Blob([JSON.stringify(localDBChats)], {
													type: 'application/json'
												});
												saveAs(blob, `chat-export-${Date.now()}.json`);

												const tx = DB.transaction('chats', 'readwrite');
												await Promise.all([tx.store.clear(), tx.done]);
												await deleteDB('Chats');
												markLegacyChatDBEmptyChecked();

												localDBChats = [];
											}}
										>
											{$i18n.t('Download & Delete')}
										</button>

										<button
											class="text-xs text-center w-full mt-2 text-gray-400 underline"
											on:click={async () => {
												localDBChats = [];
											}}>{$i18n.t('Close')}</button
										>
									</div>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<Sidebar />

				{#if loaded}
					<slot />
				{:else}
					<div
						class="w-full flex-1 h-full flex items-center justify-center {$showSidebar
							? '  md:max-w-[calc(100%-260px)]'
							: ' '}"
					>
						<Spinner className="size-5" />
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}

<style>
	.loading {
		display: inline-block;
		clip-path: inset(0 1ch 0 0);
		animation: l 1s steps(3) infinite;
		letter-spacing: -0.5px;
	}

	@keyframes l {
		to {
			clip-path: inset(0 -1ch 0 0);
		}
	}

	pre[class*='language-'] {
		position: relative;
		overflow: auto;

		/* make space  */
		margin: 5px 0;
		padding: 1.75rem 0 1.75rem 1rem;
		border-radius: 10px;
	}

	pre[class*='language-'] button {
		position: absolute;
		top: 5px;
		right: 5px;

		font-size: 0.9rem;
		padding: 0.15rem;
		background-color: #828282;

		border: ridge 1px #7b7b7c;
		border-radius: 5px;
		text-shadow: #c4c4c4 0 0 2px;
	}

	@media (hover: hover) and (pointer: fine) {
		pre[class*='language-'] button:hover {
			cursor: pointer;
			background-color: #bcbabb;
		}
	}
</style>
