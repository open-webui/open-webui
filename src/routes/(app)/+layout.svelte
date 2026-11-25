<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, tick, getContext, setContext } from 'svelte';
	import type { AppLayoutContext } from '$lib/types';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fade } from 'svelte/transition';

	import { getBackendConfig, getModels, getVersionUpdates } from '$lib/apis';
	import { getTools } from '$lib/apis/tools';
	import { getSkills } from '$lib/apis/skills';
	import { getFunctions } from '$lib/apis/functions';
	import { getFolders } from '$lib/apis/folders';
	import { getSessionUser } from '$lib/apis/auths';
	import { getBanners } from '$lib/apis/configs';
	import { getMachines } from '$lib/apis/machines';
	import { setAppFontFamily, setTextScale } from '$lib/utils/text-scale';

	import { WEBUI_VERSION, WEBUI_API_BASE_URL, WEBUI_BUILD_CHANNEL } from '$lib/constants';
	import { compareVersion } from '$lib/utils';

	import {
		config,
		user,
		settings,
		models,
		knowledge,
		tools,
		skills,
		socket,
		onSocketRestored,
		functions,
		tags,
		banners,
		showSettings,
		showChangelog,
		temporaryChat,
		machines,
		selectedMachineId,
		showSearch,
		showSidebar,
		showTabs,
		mobile,
		chatId,
		chats,
		folders,
		refreshRecentChats,
		refreshActiveFolders
	} from '$lib/stores';

	import Sidebar from '$lib/components/layout/Sidebar.svelte';
	import Chat from '$lib/components/chat/Chat.svelte';
	import { pageTabKey } from '$lib/components/chat/Tabs/tabs';
	import ChangelogModal from '$lib/components/ChangelogModal.svelte';
	import UserProfileModal from '$lib/components/UserProfileModal.svelte';
	import AccountPending from '$lib/components/layout/Overlay/AccountPending.svelte';
	import UpdateInfoToast from '$lib/components/layout/UpdateInfoToast.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import { loadKeybindings, matchKeybinding, Shortcut } from '$lib/shortcuts';
	import { canUseTemporaryChats } from '$lib/utils/settings-access';

	const i18n = getContext('i18n');
	const getUserSettings = getContext<(token: string) => Promise<any>>('getUserSettings');
	let profileUserId: string | null = null;
	const appLayout = setContext<AppLayoutContext>('appLayout', {
		openProfile: (userId) => (profileUserId = userId)
	});

	let loaded = false;
	// Settings (including the admin panels) load on first open, then stay mounted.
	let settingsRequested = false;
	$: if ($showSettings) settingsRequested = true;
	$: routeHasTabs = ['/(app)', '/(app)/c/[id]', '/(app)/folders/[folderId]'].includes(
		$page.route.id ?? ''
	);
	$: usePageTabs = !routeHasTabs && !!pageTabKey($page.url);

	let version;
	let handledSettingsUrl = '';

	const clearChatInputStorage = () => {
		const chatInputKeys = Object.keys(localStorage).filter((key) => key.startsWith('chat-input'));
		if (chatInputKeys.length > 0) {
			chatInputKeys.forEach((key) => {
				localStorage.removeItem(key);
			});
		}
	};

	const setUserSettings = async (cb?: () => Promise<void>) => {
		const userSettings = await getUserSettings(localStorage.token);

		if (userSettings?.ui) {
			settings.set(userSettings.ui);
		}
		loadKeybindings(userSettings?.keybindings);

		setTextScale($settings?.textScale ?? 1);
		setAppFontFamily($settings?.fontFamily ?? null);

		if (cb) {
			await cb();
		}
	};

	const setModels = async () => {
		models.set(await getModels(localStorage.token));
	};

	const refreshMachines = async () => {
		if (!$config?.features?.enable_tool_servers) {
			machines.set([]);
			return;
		}
		const userId = $user?.id;
		if (!userId || !localStorage.token) return;
		const systemMachines = await getMachines(localStorage.token);
		if ($user?.id !== userId || !$config?.features?.enable_tool_servers) return;
		machines.set(
			systemMachines.map((machine) => ({
				...machine,
				url: `${WEBUI_API_BASE_URL}/machines/${machine.id}`,
				key: localStorage.token
			}))
		);
	};

	const setBanners = async () => {
		const bannersData = await getBanners(localStorage.token);
		banners.set(bannersData);
	};

	const setTools = async () => {
		const toolsData = await getTools(localStorage.token);
		tools.set(toolsData);
	};

	const refreshAccess = async () => {
		if (!localStorage.token) return;
		try {
			user.set(await getSessionUser(localStorage.token));
			if (
				$user?.role !== 'admin' &&
				$user?.permissions?.chat?.temporary &&
				$user?.permissions?.chat?.temporary_enforced &&
				!$chatId
			) {
				temporaryChat.set(true);
			}
			const results = await Promise.allSettled([
				getBackendConfig().then((value) => config.set(value)),
				setModels(),
				setTools(),
				refreshMachines(),
				getSkills(localStorage.token).then((value) => skills.set(value)),
				getFolders(localStorage.token)
					.catch(() => [])
					.then((value) => folders.set(value))
			]);
			for (const result of results) {
				if (result.status === 'rejected') console.error('Unable to refresh access', result.reason);
			}
		} catch (error) {
			console.error('Unable to refresh permissions', error);
		}
	};

	onMount(() => {
		const socketInstance = $socket;
		const changed = () => {
			void refreshMachines().catch((error) => console.error('Unable to refresh terminals', error));
		};
		const eventHandler = (event: { data?: { type?: string } }) => {
			if (event?.data?.type === 'machines:changed') {
				changed();
				// Tether devices also bring the user's own models and tool servers.
				void setModels().catch((error) => console.error('Unable to refresh models', error));
				void setTools().catch((error) => console.error('Unable to refresh tools', error));
			} else if (event?.data?.type === 'access:updated') void refreshAccess();
		};
		socketInstance?.on('events', eventHandler);
		const unsubscribe = onSocketRestored(changed);
		return () => {
			socketInstance?.off('events', eventHandler);
			unsubscribe();
		};
	});

	const openSettingsFromUrl = async () => {
		const requestedSettings = $page.url.searchParams.get('settings');
		if (!requestedSettings) {
			// Param handled and stripped; allow the same deep link to be
			// handled again later in this session.
			handledSettingsUrl = '';
			return;
		}

		const urlKey = `${$page.url.pathname}${$page.url.search}${$page.url.hash}`;
		if (handledSettingsUrl === urlKey) {
			return;
		}
		handledSettingsUrl = urlKey;

		showSettings.set(
			requestedSettings.startsWith('admin:') && $user?.role !== 'admin'
				? 'general'
				: requestedSettings
		);

		const params = new URLSearchParams($page.url.searchParams);
		params.delete('settings');
		const query = params.toString();
		await goto(`${$page.url.pathname}${query ? `?${query}` : ''}${$page.url.hash}`, {
			replaceState: true,
			noScroll: true,
			keepFocus: true
		});
	};

	const gotoAuth = async () => {
		const currentUrl = `${$page.url.pathname}${$page.url.search}`;
		await goto(`/auth?redirect=${encodeURIComponent(currentUrl)}`);
	};

	// Chat shortcuts act on the chat that has focus, otherwise the main chat. Chat tabs sit
	// inside the main chat, so an element belongs to the nearest [data-chat] around it.
	const chatElements = <T extends HTMLElement = HTMLElement>(selector: string): T[] => {
		const chat =
			document.activeElement?.closest('[data-chat]') ??
			document.querySelector('[data-chat="main"]');
		if (chat?.querySelector('[data-main-chat-pane]')?.classList.contains('hidden')) return [];
		return [...document.querySelectorAll<T>(selector)].filter(
			(el) => !chat || el.closest('[data-chat]') === chat
		);
	};

	const chatInput = () => {
		const id = chatElements('[data-composer-id]')[0]?.dataset.composerId;
		return id ? document.getElementById(id) : null;
	};

	const navigateChat = async (direction: -1 | 1) => {
		if (!$chats?.length) return;

		const currentIndex = $chats.findIndex((chat) => chat.id === $chatId);
		const nextChat = currentIndex === -1 ? $chats[0] : $chats[currentIndex + direction];

		if (nextChat) {
			await goto(`/c/${nextChat.id}`);
		}
	};

	onMount(async () => {
		if ($user === undefined || $user === null) {
			await gotoAuth();
			return;
		}
		if (!['user', 'admin'].includes($user?.role)) {
			return;
		}

		clearChatInputStorage();
		// Requested beside settings. The page is drawn once settings are in;
		// each of these shows up when it arrives.
		void setBanners().catch((e) => console.error('Failed to load banners:', e));
		// The new-chat page lists these under the composer; started now so they're in before it draws.
		void refreshRecentChats(localStorage.token);
		void refreshActiveFolders(localStorage.token);
		const lists = Promise.all([
			setTools().catch((e) => console.error('Failed to load tools:', e)),
			refreshMachines().catch((e) => console.error('Failed to load machines:', e)),
			// The chat needs these to apply a model's defaults; without them here it
			// fetches them one after the other during set-up.
			getFunctions(localStorage.token)
				.then((value) => functions.set(value))
				.catch((e) => console.error('Failed to load functions:', e)),
			getSkills(localStorage.token)
				.then((value) => skills.set(value))
				.catch((e) => console.error('Failed to load skills:', e))
		]);
		const modelList = getModels(localStorage.token).catch((e) => {
			console.error('Failed to load models:', e);
			// Loaded, with nothing to list: null would mean the list is still on its way.
			return [];
		});
		try {
			await setUserSettings();
		} catch (e) {
			console.error('Failed to load user settings:', e);
			toast.error($i18n.t('Failed to load Interface settings'));
			return;
		}

		const setupKeyboardShortcuts = () => {
			document.addEventListener('keydown', async (event) => {
				if ($settings?.keyboardShortcuts === false) {
					return;
				}

				const shortcut = matchKeybinding(event);
				if (shortcut === Shortcut.SEARCH) {
					console.log('Shortcut triggered: SEARCH');
					event.preventDefault();
					showSearch.set(!$showSearch);
				} else if (shortcut === Shortcut.NEW_CHAT) {
					console.log('Shortcut triggered: NEW_CHAT');
					event.preventDefault();
					document.getElementById('sidebar-new-chat-button')?.click();
				} else if (shortcut === Shortcut.FOCUS_INPUT) {
					console.log('Shortcut triggered: FOCUS_INPUT');
					event.preventDefault();
					(
						chatElements('[data-composer-id]')
							.map((el) => document.getElementById(el.dataset.composerId ?? ''))
							.find((el) => el?.offsetParent) ?? chatInput()
					)?.focus();
				} else if (shortcut === Shortcut.COPY_LAST_CODE_BLOCK) {
					console.log('Shortcut triggered: COPY_LAST_CODE_BLOCK');
					event.preventDefault();
					chatElements('.copy-code-button').at(-1)?.click();
				} else if (shortcut === Shortcut.COPY_LAST_RESPONSE) {
					console.log('Shortcut triggered: COPY_LAST_RESPONSE');
					event.preventDefault();
					chatElements('.copy-response-button').at(-1)?.click();
				} else if (shortcut === Shortcut.TOGGLE_SIDEBAR) {
					console.log('Shortcut triggered: TOGGLE_SIDEBAR');
					event.preventDefault();
					showSidebar.set(!$showSidebar);
				} else if (shortcut === Shortcut.NAVIGATE_CHAT_UP) {
					console.log('Shortcut triggered: NAVIGATE_CHAT_UP');
					event.preventDefault();
					await navigateChat(-1);
				} else if (shortcut === Shortcut.NAVIGATE_CHAT_DOWN) {
					console.log('Shortcut triggered: NAVIGATE_CHAT_DOWN');
					event.preventDefault();
					await navigateChat(1);
				} else if (shortcut === Shortcut.TOGGLE_CONTROLS) {
					console.log('Shortcut triggered: TOGGLE_CONTROLS');
					event.preventDefault();
					showTabs.set(!$showTabs);
				} else if (shortcut === Shortcut.DELETE_CHAT) {
					console.log('Shortcut triggered: DELETE_CHAT');
					event.preventDefault();
					chatElements('#delete-chat-button')[0]?.click();
				} else if (shortcut === Shortcut.OPEN_SETTINGS) {
					console.log('Shortcut triggered: OPEN_SETTINGS');
					event.preventDefault();
					showSettings.set(!$showSettings);
				} else if (shortcut === Shortcut.SHOW_SHORTCUTS) {
					console.log('Shortcut triggered: SHOW_SHORTCUTS');
					event.preventDefault();
					showSettings.set('shortcuts');
				} else if (shortcut === Shortcut.OPEN_MODEL_SELECTOR) {
					console.log('Shortcut triggered: OPEN_MODEL_SELECTOR');
					event.preventDefault();
					chatElements('#model-selector-model-button')[0]?.click();
				} else if (shortcut === Shortcut.NEW_TEMPORARY_CHAT) {
					console.log('Shortcut triggered: NEW_TEMPORARY_CHAT');
					event.preventDefault();
					if (!canUseTemporaryChats({ user: $user, config: null })) {
						return;
					}
					const temporary = !$temporaryChat;
					await goto('/');
					setTimeout(() => appLayout.initNewChat?.({ temporary }), 0);
				} else if (shortcut === Shortcut.GENERATE_MESSAGE_PAIR) {
					console.log('Shortcut triggered: GENERATE_MESSAGE_PAIR');
					event.preventDefault();
					chatElements('.generate-message-pair-button')[0]?.click();
				} else if (shortcut === Shortcut.ALLOW_TOOL_CALL) {
					const button = chatElements<HTMLButtonElement>('.tool-call-allow-button')
						.reverse()
						.find((el) => !el.disabled);
					if (button) {
						console.log('Shortcut triggered: ALLOW_TOOL_CALL');
						event.preventDefault();
						button.click();
					}
				} else if (shortcut === Shortcut.DENY_TOOL_CALL) {
					const button = chatElements<HTMLButtonElement>('.tool-call-deny-button')
						.reverse()
						.find((el) => !el.disabled);
					if (button) {
						console.log('Shortcut triggered: DENY_TOOL_CALL');
						event.preventDefault();
						button.click();
					}
				} else if (
					shortcut === Shortcut.REGENERATE_RESPONSE &&
					document.activeElement === chatInput()
				) {
					console.log('Shortcut triggered: REGENERATE_RESPONSE');
					event.preventDefault();
					chatElements('.regenerate-response-button').at(-1)?.click();
				}
			});
		};
		setupKeyboardShortcuts();

		if ($user?.role === 'admin' && ($settings?.showChangelog ?? true)) {
			showChangelog.set($settings?.version !== $config.version);
		}

		// Check for version updates
		if (
			WEBUI_BUILD_CHANNEL === 'main' &&
			$user?.role === 'admin' &&
			$config?.features?.enable_version_update_check
		) {
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
		// Persist showTabs: track open/close state separately from saved size
		// chatControlsSize always retains the last width for openPane()
		await showTabs.set(!$mobile ? localStorage.showTabs === 'true' : false);
		showTabs.subscribe((value) => {
			localStorage.showTabs = value ? 'true' : 'false';
		});

		await tick();

		loaded = true;

		await lists;
		// selectedTerminalId is the former key.
		const storedMachineId = localStorage.selectedMachineId ?? localStorage.selectedTerminalId;
		delete localStorage.selectedTerminalId;
		if (storedMachineId) localStorage.selectedMachineId = storedMachineId;
		selectedMachineId.set(
			$config?.features?.enable_tool_servers ? (storedMachineId ?? null) : null
		);

		// Set last: the chat sets itself up once the model list is in, and that set-up
		// reads tools, machines and the selected machine as well.
		models.set(await modelList);
	});

	// `$page.url` must be referenced here: `$:` only tracks variables used in
	// the statement itself, and reads inside openSettingsFromUrl don't count —
	// without it, client-side navigations to `?settings=...` are never handled.
	$: if (loaded && $page.url) {
		void openSettingsFromUrl();
	}

	$: if (loaded && ($user === undefined || $user === null)) {
		void gotoAuth();
	}

	const checkForVersionUpdates = async () => {
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: null
			};
		});
	};
</script>

{#if settingsRequested}
	{#await import('$lib/components/chat/SettingsModal.svelte')}
		<Modal
			show={!!$showSettings}
			size="full"
			containerClassName="p-3 sm:p-4 lg:p-6"
			className="h-[calc(100dvh-1.5rem)] sm:h-[calc(100dvh-2rem)] lg:h-[calc(100dvh-3rem)] flex flex-col md:flex-row bg-base-0 dark:bg-base-900 rounded-4xl overflow-hidden"
			ariaLabel={$i18n.t('Settings')}
			onRequestClose={() => showSettings.set(false)}
		>
			<!-- Laid out like SettingsModal so the spinner stays in place when a panel takes over. -->
			<div
				class="shrink-0 border-b md:border-b-0 md:border-r border-base-100/30 dark:border-base-0/[0.02] md:w-[15rem]"
			>
				<div class="flex m-1 md:mb-0">
					<button
						type="button"
						class="flex flex-1 items-center gap-1.5 h-7 px-2 rounded-lg text-xs text-base-600 dark:text-base-500 hover:text-base-700 dark:hover:text-base-300 transition-colors duration-75"
						on:click={() => showSettings.set(false)}
					>
						<ChevronLeft className="size-3" strokeWidth="2" />
						<span>{$i18n.t('Back')}</span>
					</button>
				</div>
			</div>
			<div class="flex flex-1 items-center justify-center pb-4 pr-1.5">
				<Spinner className="size-6" />
			</div>
		</Modal>
	{:then { default: SettingsModal }}
		<SettingsModal bind:show={$showSettings} />
	{/await}
{/if}
<ChangelogModal bind:show={$showChangelog} />
<UserProfileModal bind:userId={profileUserId} />

{#if WEBUI_BUILD_CHANNEL === 'main' && version && compareVersion(version.latest, version.current) && ($settings?.showUpdateToast ?? true)}
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
			class=" text-base-700 dark:text-base-100 bg-base-0 dark:bg-base-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end"
		>
			{#if !['user', 'admin'].includes($user?.role)}
				<AccountPending />
			{:else}
				<Sidebar />

				{#if loaded}
					<main class="contents">
						<div id="main-content" tabindex="-1" class="sr-only left-0 top-0"></div>
						{#if routeHasTabs || usePageTabs}
							<Chat
								initialPage={usePageTabs
									? $page.url.pathname + $page.url.search + $page.url.hash
									: ''}
							/>
						{/if}
						{#if !usePageTabs}<slot />{/if}
					</main>
				{:else}
					<div
						class="w-full flex-1 h-full flex items-center justify-center {$showSidebar
							? '  md:max-w-[calc(100%-var(--sidebar-width))]'
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
		margin: 0.3125rem 0;
		padding: 1.75rem 0 1.75rem 1rem;
		border-radius: 0.625rem;
	}

	pre[class*='language-'] button {
		position: absolute;
		top: 0.3125rem;
		right: 0.3125rem;

		font-size: 0.9rem;
		padding: 0.15rem;
		background-color: #828282;

		border: ridge 1px #7b7b7c;
		border-radius: 0.3125rem;
		text-shadow: #c4c4c4 0 0 2px;
	}

	pre[class*='language-'] button:hover {
		cursor: pointer;
		background-color: #bcbabb;
	}
</style>
