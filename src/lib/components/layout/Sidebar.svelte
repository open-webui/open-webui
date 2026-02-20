<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import {
		user,
		chats,
		settings,
		showSettings,
		chatId,
		tags,
		folders as _folders,
		showSidebar,
		showSearch,
		mobile,
		showArchivedChats,
		pinnedChats,
		scrollPaginationEnabled,
		currentChatPage,
		temporaryChatEnabled,
		channels,
		socket,
		config,
		isApp,
		models,
		selectedFolder,
		WEBUI_NAME,
		sidebarWidth,
		sidebarPinned,
		activeChatIds,
		brandingConfig
	} from '$lib/stores';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	import {
		getChatList,
		getAllTags,
		getPinnedChatList,
		toggleChatPinnedStatusById,
		getChatById,
		updateChatFolderIdById,
		importChats
	} from '$lib/apis/chats';
	import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
	import { checkActiveChats } from '$lib/apis/tasks';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import ArchivedChatsModal from './ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import Folder from '../common/Folder.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import SpaceSettingsModal from './Sidebar/SpaceSettingsModal.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Search from '../icons/Search.svelte';
	import SearchModal from './SearchModal.svelte';
	import FolderModal from './Sidebar/Folders/FolderModal.svelte';
	import SidebarIcon from '../icons/Sidebar.svelte';
	import PinnedModelList from './Sidebar/PinnedModelList.svelte';
	import Note from '../icons/Note.svelte';
	import SpaceItem from './Sidebar/SpaceItem.svelte';
	import { getSpaces, getPinnedSpaces, getBookmarkedSpaces, type Space } from '$lib/apis/spaces';

	import { fly } from 'svelte/transition';
	import HotkeyHint from '../common/HotkeyHint.svelte';

	const BREAKPOINT = 768;

	let scrollTop = 0;

	let navElement: HTMLElement | null = null;
	let shiftKey = false;

	let selectedChatId: string | null = null;
	let showCreateChannel = false;

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let showCreateFolderModal = false;

	let pinnedModels: string[] = [];

	let showPinnedModels = false;
	let showChannels = false;
	let showCreateSpace = false;
	let showFolders = false;

	const SIDEBAR_ENTER_DELAY = 500;
	const SIDEBAR_LEAVE_DELAY = 200;
	const RAIL_WIDTH = 52;
	const MAX_SIDEBAR_CHATS = 15;

	let sidebarEnterTimer: ReturnType<typeof setTimeout> | null = null;
	let sidebarLeaveTimer: ReturnType<typeof setTimeout> | null = null;
	let sidebarHoverOpen = false;
	let sidebarDataLoaded = false;

	// ── Submenu hover state (Perplexity-style with named timers) ──────────
	type SubmenuId = 'history' | 'spaces' | 'more' | null;
	let activeSubmenu: SubmenuId = null;

	// Separate named timers (like Perplexity)
	const submenuTimers: Record<string, ReturnType<typeof setTimeout> | null> = {
		enterIcon: null,
		leaveIcon: null,
		leavePanel: null
	};

	const SUBMENU_ENTER_DELAY = 150; // Wait before showing (prevents accidental hovers)
	const SUBMENU_LEAVE_DELAY = 100; // Wait before hiding (allows transition to panel)

	// Spaces data for submenu
	let spacesPrivate: Space[] = [];
	let spacesShared: Space[] = [];
	let spacesPinned: Space[] = [];
	let spacesBookmarked: Space[] = [];
	let spacesLoading = false;
	let spacesLoaded = false;

	const loadSpacesForSubmenu = async () => {
		if (spacesLoaded || spacesLoading) return;
		spacesLoading = true;
		try {
			const [priv, shared, pinned, bookmarked] = await Promise.all([
				getSpaces(localStorage.token, null, 'private'),
				getSpaces(localStorage.token, null, 'shared'),
				getPinnedSpaces(localStorage.token).catch(() => []),
				getBookmarkedSpaces(localStorage.token).catch(() => [])
			]);
			spacesPrivate = priv?.items ?? [];
			spacesShared = shared?.items ?? [];
			spacesPinned = pinned ?? [];
			spacesBookmarked = bookmarked ?? [];
			spacesLoaded = true;
		} catch {
			spacesPrivate = [];
			spacesShared = [];
			spacesPinned = [];
			spacesBookmarked = [];
		}
		spacesLoading = false;
	};

	// Helper: clear multiple timers
	const clearTimers = (...names: string[]) => {
		for (const name of names) {
			if (submenuTimers[name]) {
				clearTimeout(submenuTimers[name]!);
				submenuTimers[name] = null;
			}
		}
	};

	// Helper: set a timer (auto-clears previous)
	const setTimer = (name: string, fn: () => void, delay: number) => {
		clearTimers(name);
		submenuTimers[name] = setTimeout(fn, delay);
	};

	// Trigger data loading for a submenu
	const triggerSubmenuDataLoad = (id: SubmenuId) => {
		if (id === 'history' && !sidebarDataLoaded) {
			sidebarDataLoaded = true;
			initChatList();
			if (
				$config?.features?.enable_channels &&
				($user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true))
			) {
				initChannels();
			}
		}
		// Load spaces for both history (SHARED section) and spaces submenus
		if (id === 'history' || id === 'spaces') {
			loadSpacesForSubmenu();
		}
	};

	// Icon hover: wait before showing, clear all leave timers
	const onSubmenuEnter = (id: SubmenuId) => {
		// Clear all leave timers (we're entering something)
		clearTimers('leaveIcon', 'leavePanel');

		// Set enter timer - wait before showing submenu
		setTimer(
			'enterIcon',
			() => {
				activeSubmenu = id;
				triggerSubmenuDataLoad(id);
			},
			SUBMENU_ENTER_DELAY
		);
	};

	// Icon leave: clear enter timer, start leave timer
	const onSubmenuLeave = () => {
		// Clear enter timer (we left before it fired)
		clearTimers('enterIcon');

		// Start leave timer
		setTimer(
			'leaveIcon',
			() => {
				activeSubmenu = null;
			},
			SUBMENU_LEAVE_DELAY
		);
	};

	// Panel enter: clear all leave timers (we're still in the submenu area)
	const onSubmenuPanelEnter = () => {
		clearTimers('leaveIcon', 'leavePanel', 'enterIcon');
	};

	// Panel leave: start leave timer
	const onSubmenuPanelLeave = () => {
		setTimer(
			'leavePanel',
			() => {
				activeSubmenu = null;
			},
			SUBMENU_LEAVE_DELAY
		);
	};

	const clearSidebarTimers = () => {
		if (sidebarEnterTimer) {
			clearTimeout(sidebarEnterTimer);
			sidebarEnterTimer = null;
		}
		if (sidebarLeaveTimer) {
			clearTimeout(sidebarLeaveTimer);
			sidebarLeaveTimer = null;
		}
	};

	const isInSidebarZone = (x: number): boolean => {
		if (x <= RAIL_WIDTH) return true;
		if ($showSidebar && navElement) {
			const rect = navElement.getBoundingClientRect();
			if (x <= rect.right + 8) return true;
		}
		return false;
	};

	const onPointerMove = (e: PointerEvent | MouseEvent) => {
		if ($mobile) return;
		if ($sidebarPinned) return;

		const inZone = isInSidebarZone(e.clientX);

		if (inZone) {
			if (sidebarLeaveTimer) {
				clearTimeout(sidebarLeaveTimer);
				sidebarLeaveTimer = null;
			}

			if (!$showSidebar && !sidebarEnterTimer) {
				sidebarEnterTimer = setTimeout(() => {
					sidebarEnterTimer = null;
					sidebarHoverOpen = true;
					showSidebar.set(true);
				}, SIDEBAR_ENTER_DELAY);
			}
		} else {
			if (sidebarEnterTimer) {
				clearTimeout(sidebarEnterTimer);
				sidebarEnterTimer = null;
			}

			if (sidebarHoverOpen && !sidebarLeaveTimer) {
				sidebarLeaveTimer = setTimeout(() => {
					sidebarLeaveTimer = null;
					sidebarHoverOpen = false;
					showSidebar.set(false);
				}, SIDEBAR_LEAVE_DELAY);
			}
		}
	};

	let sidebarProfileImageFailed = false;
	$: if ($user?.id) sidebarProfileImageFailed = false;

	const SIDEBAR_AVATAR_COLORS = [
		'#E67E22',
		'#3498DB',
		'#2ECC71',
		'#9B59B6',
		'#1ABC9C',
		'#E74C3C',
		'#F39C12',
		'#2980B9',
		'#27AE60',
		'#8E44AD',
		'#16A085',
		'#C0392B',
		'#D35400',
		'#7F8C8D',
		'#2C3E50'
	];
	function getSidebarUserColor(userId: string): string {
		let hash = 0;
		for (let i = 0; i < userId.length; i++) {
			hash = ((hash << 5) - hash + userId.charCodeAt(i)) | 0;
		}
		return SIDEBAR_AVATAR_COLORS[Math.abs(hash) % SIDEBAR_AVATAR_COLORS.length];
	}
	$: sidebarUserInitials = $user?.name
		? $user.name
				.split(' ')
				.map((w: string) => w[0])
				.filter(Boolean)
				.slice(0, 2)
				.join('')
				.toUpperCase()
		: '';
	$: sidebarUserColor = $user?.id ? getSidebarUserColor($user.id) : '#E67E22';

	let folders = {};
	let folderRegistry = {};

	let newFolderId = null;

	$: if ($selectedFolder) {
		initFolders();
	}

	const initFolders = async () => {
		if ($config?.features?.enable_folders === false) {
			return;
		}

		const folderList = await getFolders(localStorage.token).catch((error) => {
			return [];
		});
		_folders.set(folderList.sort((a, b) => b.updated_at - a.updated_at));

		folders = {};

		for (const folder of folderList) {
			folders[folder.id] = { ...(folders[folder.id] || {}), ...folder };

			if (newFolderId && folder.id === newFolderId) {
				folders[folder.id].new = true;
				newFolderId = null;
			}
		}

		for (const folder of folderList) {
			if (folder.parent_id) {
				if (!folders[folder.parent_id]) {
					folders[folder.parent_id] = {};
				}

				folders[folder.parent_id].childrenIds = folders[folder.parent_id].childrenIds
					? [...folders[folder.parent_id].childrenIds, folder.id]
					: [folder.id];

				folders[folder.parent_id].childrenIds.sort((a, b) => {
					return folders[b].updated_at - folders[a].updated_at;
				});
			}
		}
	};

	const createFolder = async ({ name, data }) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const rootFolders = Object.values(folders).filter((folder) => folder.parent_id === null);
		if (rootFolders.find((folder) => folder.name.toLowerCase() === name.toLowerCase())) {
			let i = 1;
			while (
				rootFolders.find((folder) => folder.name.toLowerCase() === `${name} ${i}`.toLowerCase())
			) {
				i++;
			}

			name = `${name} ${i}`;
		}

		const tempId = uuidv4();
		folders = {
			...folders,
			tempId: {
				id: tempId,
				name: name,
				created_at: Date.now(),
				updated_at: Date.now()
			}
		};

		const res = await createNewFolder(localStorage.token, {
			name,
			data
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			await initFolders();
			showFolders = true;
		}
	};

	const initChannels = async () => {
		const res = await getChannels(localStorage.token).catch((error) => {
			return null;
		});

		if (res) {
			await channels.set(
				res.sort(
					(a, b) =>
						['', null, 'group', 'dm'].indexOf(a.type) - ['', null, 'group', 'dm'].indexOf(b.type)
				)
			);
		}
	};

	const initChatList = async () => {
		console.log('initChatList');
		currentChatPage.set(1);
		allChatsLoaded = false;
		scrollPaginationEnabled.set(false);

		initFolders();
		await Promise.all([
			await (async () => {
				console.log('Init tags');
				const _tags = await getAllTags(localStorage.token);
				tags.set(_tags);
			})(),
			await (async () => {
				console.log('Init pinned chats');
				const _pinnedChats = await getPinnedChatList(localStorage.token);
				pinnedChats.set(_pinnedChats);
			})(),
			await (async () => {
				console.log('Init chat list');
				const _chats = await getChatList(localStorage.token, $currentChatPage);
				await chats.set(_chats);
			})()
		]);

		scrollPaginationEnabled.set(true);
	};

	const loadMoreChats = async () => {
		chatListLoading = true;
		currentChatPage.set($currentChatPage + 1);
		let newChatList = [];
		newChatList = await getChatList(localStorage.token, $currentChatPage);
		allChatsLoaded = newChatList.length === 0;
		await chats.set([...($chats ? $chats : []), ...newChatList]);
		chatListLoading = false;
	};

	const importChatHandler = async (items, pinned = false, folderId = null) => {
		console.log('importChatHandler', items, pinned, folderId);
		for (const item of items) {
			console.log(item);
			if (item.chat) {
				await importChats(localStorage.token, [
					{
						chat: item.chat,
						meta: item?.meta ?? {},
						pinned: pinned,
						folder_id: folderId,
						created_at: item?.created_at ?? null,
						updated_at: item?.updated_at ?? null
					}
				]);
			}
		}

		initChatList();
	};

	const inputFilesHandler = async (files) => {
		console.log(files);

		for (const file of files) {
			const reader = new FileReader();
			reader.onload = async (e) => {
				const content = e.target.result;

				try {
					const chatItems = JSON.parse(content);
					importChatHandler(chatItems);
				} catch {
					toast.error($i18n.t(`Invalid file format.`));
				}
			};

			reader.readAsText(file);
		}
	};

	const tagEventHandler = async (type, tagName, chatId) => {
		console.log(type, tagName, chatId);
		if (type === 'delete') {
			initChatList();
		} else if (type === 'add') {
			initChatList();
		}
	};

	let draggedOver = false;

	const onDragOver = (e) => {
		e.preventDefault();
		if (e.dataTransfer?.types?.includes('Files')) {
			draggedOver = true;
		} else {
			draggedOver = false;
		}
	};

	const onDragLeave = () => {
		draggedOver = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		console.log(e);

		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);

			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles);
				inputFilesHandler(inputFiles);
			}
		}

		draggedOver = false;
	};

	let touchstart;
	let touchend;

	function checkDirection() {
		const screenWidth = window.innerWidth;
		const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);
		if (touchstart.clientX < 40 && swipeDistance >= screenWidth / 8) {
			if (touchend.screenX < touchstart.screenX) {
				showSidebar.set(false);
			}
			if (touchend.screenX > touchstart.screenX) {
				showSidebar.set(true);
			}
		}
	}

	const onTouchStart = (e) => {
		touchstart = e.changedTouches[0];
		console.log(touchstart.clientX);
	};

	const onTouchEnd = (e) => {
		touchend = e.changedTouches[0];
		checkDirection();
	};

	const onKeyDown = (e) => {
		if (e.key === 'Shift') {
			shiftKey = true;
		}
	};

	const onKeyUp = (e) => {
		if (e.key === 'Shift') {
			shiftKey = false;
		}
	};

	const onFocus = () => {};

	const onBlur = () => {
		shiftKey = false;
		selectedChatId = null;
	};

	const MIN_WIDTH = 220;
	const MAX_WIDTH = 480;

	let isResizing = false;
	let startWidth = 0;
	let startClientX = 0;

	const resizeStartHandler = (e: MouseEvent) => {
		if ($mobile) return;
		isResizing = true;
		startClientX = e.clientX;
		startWidth = $sidebarWidth ?? 260;
		document.body.style.userSelect = 'none';
	};

	const resizeEndHandler = () => {
		if (!isResizing) return;
		isResizing = false;
		document.body.style.userSelect = '';
		localStorage.setItem('sidebarWidth', String($sidebarWidth));
	};

	const resizeSidebarHandler = (endClientX) => {
		const dx = endClientX - startClientX;
		const newSidebarWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + dx));
		sidebarWidth.set(newSidebarWidth);
		document.documentElement.style.setProperty('--sidebar-width', `${newSidebarWidth}px`);
	};

	let unsubscribers = [];

	onMount(async () => {
		try {
			const width = Number(localStorage.getItem('sidebarWidth'));
			if (!Number.isNaN(width) && width >= MIN_WIDTH && width <= MAX_WIDTH) {
				sidebarWidth.set(width);
			}
		} catch {}

		document.documentElement.style.setProperty('--sidebar-width', `${$sidebarWidth}px`);
		sidebarWidth.subscribe((w) => {
			document.documentElement.style.setProperty('--sidebar-width', `${w}px`);
		});

		sidebarPinned.set(false);
		await showSidebar.set(false);

		unsubscribers = [
			mobile.subscribe((value) => {
				if ($showSidebar && value) {
					showSidebar.set(false);
				}

				if ($showSidebar && !value) {
					const navElement = document.getElementsByTagName('nav')[0];
					if (navElement) {
						navElement.style['-webkit-app-region'] = 'drag';
					}
				}
			}),
			showSidebar.subscribe(async (value) => {
				const navElement = document.getElementsByTagName('nav')[0];

				if (navElement) {
					if ($mobile) {
						if (!value) {
							navElement.style['-webkit-app-region'] = 'drag';
						} else {
							navElement.style['-webkit-app-region'] = 'no-drag';
						}
					} else {
						navElement.style['-webkit-app-region'] = 'drag';
					}
				}

				if (value && !sidebarDataLoaded) {
					sidebarDataLoaded = true;
					if (
						$config?.features?.enable_channels &&
						($user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true))
					) {
						await initChannels();
					}
					await initChatList();

					// Check which chats have active tasks
					const allChatIds = [...$chats.map((c) => c.id), ...$pinnedChats.map((c) => c.id)];
					if (allChatIds.length > 0) {
						try {
							const res = await checkActiveChats(localStorage.token, allChatIds);
							activeChatIds.set(new Set(res.active_chat_ids || []));
						} catch (e) {
							console.debug('Failed to check active chats:', e);
						}
					}
				}
			}),
			settings.subscribe((value) => {
				if (pinnedModels != value?.pinnedModels ?? []) {
					pinnedModels = value?.pinnedModels ?? [];
					showPinnedModels = pinnedModels.length > 0;
				}
			})
		];

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		document.addEventListener('pointermove', onPointerMove);

		const dropZone = document.getElementById('sidebar');

		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);

		// Listen for real-time chat:active events via the events channel
		$socket?.off('events', chatActiveEventHandler);
		$socket?.on('events', chatActiveEventHandler);
	});

	// Handler for chat:active events (defined outside onMount for proper cleanup)
	const chatActiveEventHandler = (event: {
		chat_id: string;
		message_id: string;
		data: { type: string; data: any };
	}) => {
		if (event.data?.type === 'chat:active') {
			const { active } = event.data.data;
			activeChatIds.update((ids) => {
				const newSet = new Set(ids);
				if (active) {
					newSet.add(event.chat_id);
				} else {
					newSet.delete(event.chat_id);
				}
				return newSet;
			});
		}
	};

	onDestroy(() => {
		if (unsubscribers && unsubscribers.length > 0) {
			unsubscribers.forEach((unsubscriber) => {
				if (unsubscriber) {
					unsubscriber();
				}
			});
		}

		window.removeEventListener('keydown', onKeyDown);
		window.removeEventListener('keyup', onKeyUp);

		window.removeEventListener('touchstart', onTouchStart);
		window.removeEventListener('touchend', onTouchEnd);

		window.removeEventListener('focus', onFocus);
		window.removeEventListener('blur', onBlur);

		document.removeEventListener('pointermove', onPointerMove);
		clearSidebarTimers();
		clearSubmenuTimers();

		const dropZone = document.getElementById('sidebar');

		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);

		// Clean up socket listener
		$socket?.off('events', chatActiveEventHandler);
	});

	const newChatHandler = async () => {
		selectedChatId = null;
		selectedFolder.set(null);

		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		} else {
			await temporaryChatEnabled.set(false);
		}

		setTimeout(() => {
			if ($mobile) {
				showSidebar.set(false);
			}
		}, 0);
	};

	const itemClickHandler = async () => {
		selectedChatId = null;
		chatId.set('');

		if ($mobile) {
			showSidebar.set(false);
		}

		await tick();
	};

	const isWindows = /Windows/i.test(navigator.userAgent);
</script>

<!-- Mobile overlay backdrop -->
{#if $mobile && $showSidebar}
	<div
		class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity"
		on:click={() => showSidebar.set(false)}
		on:keydown={(e) => e.key === 'Escape' && showSidebar.set(false)}
		role="button"
		tabindex="-1"
		aria-label="Close sidebar"
		transition:fly={{ duration: 200, opacity: 0 }}
	/>
{/if}

<!-- ═══════════════════════════════════════════════════════════════════
     MOBILE: Keep existing slide-out panel behavior
     ═══════════════════════════════════════════════════════════════════ -->
{#if $mobile && $showSidebar}
	<div id="sidebar" class="fixed left-0 top-0 z-50 flex h-full">
		<nav
			bind:this={navElement}
			class="sidebar-panel pointer-events-auto flex h-full flex-col bg-gray-50 shadow-xl dark:bg-gray-900 mobile-panel"
			style="width: 100vw;"
			transition:fly={{ x: -300, duration: 200, opacity: 1 }}
			on:dragover={onDragOver}
			on:dragleave={onDragLeave}
			on:drop={onDrop}
		>
			<!-- Panel header -->
			<div
				class="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 px-3 dark:border-gray-700/50"
			>
				<div class="flex items-center gap-2">
					<a
						href="/"
						class="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white"
						on:click={itemClickHandler}
					>
						<img
							src={$brandingConfig?.favicon_data ||
								$brandingConfig?.favicon_url ||
								`${WEBUI_BASE_URL}/static/favicon.png`}
							class="size-6 rounded"
							alt="logo"
						/>
						<span class="truncate">{$WEBUI_NAME}</span>
					</a>
				</div>
				<button
					class="flex size-8 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-800"
					on:click={() => showSidebar.set(false)}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-5"
					>
						<path
							d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
						/>
					</svg>
				</button>
			</div>

			<!-- Mobile panel content (scrollable) -->
			<div
				class="flex-1 overflow-y-auto overflow-x-hidden"
				on:scroll={(e) => {
					scrollTop = e.target.scrollTop;
					if (
						$scrollPaginationEnabled &&
						!allChatsLoaded &&
						!chatListLoading &&
						e.target.scrollHeight - e.target.scrollTop <= e.target.clientHeight + 50
					) {
						loadMoreChats();
					}
				}}
			>
				{#if pinnedModels.length > 0}
					<div class="px-2 pt-2">
						<button
							class="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
							on:click={() => (showPinnedModels = !showPinnedModels)}
						>
							<span>{$i18n.t('Pinned Models')}</span>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-4 transition-transform"
								class:rotate-180={showPinnedModels}
							>
								<path
									fill-rule="evenodd"
									d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						{#if showPinnedModels}
							<div class="mt-1" transition:fly={{ y: -10, duration: 150 }}>
								<PinnedModelList {pinnedModels} />
							</div>
						{/if}
					</div>
				{/if}

				{#if $config?.features?.enable_channels && ($user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true))}
					<div class="px-2 pt-2">
						<div
							class="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
						>
							<button class="flex-1 text-left" on:click={() => (showChannels = !showChannels)}>
								{$i18n.t('Channels')}
							</button>
							<div class="flex items-center gap-1">
								{#if $user?.role === 'admin'}
									<button
										class="rounded p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700"
										on:click={() => (showCreateChannel = true)}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="size-3.5"
										>
											<path
												d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
											/>
										</svg>
									</button>
								{/if}
								<button on:click={() => (showChannels = !showChannels)}>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-4 transition-transform"
										class:rotate-180={showChannels}
									>
										<path
											fill-rule="evenodd"
											d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</div>
						</div>
						{#if showChannels && $channels}
							<div class="mt-1 space-y-0.5" transition:fly={{ y: -10, duration: 150 }}>
								{#each $channels as channel (channel.id)}
									<ChannelItem {channel} onUpdate={initChannels} />
								{/each}
							</div>
						{/if}
					</div>
				{/if}

				{#if $config?.features?.enable_folders !== false}
					<div class="px-2 pt-2">
						<div
							class="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
						>
							<button class="flex-1 text-left" on:click={() => (showFolders = !showFolders)}>
								{$i18n.t('Folders')}
							</button>
							<div class="flex items-center gap-1">
								<button
									class="rounded p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700"
									on:click={() => (showCreateFolderModal = true)}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-3.5"
									>
										<path
											d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
										/>
									</svg>
								</button>
								<button on:click={() => (showFolders = !showFolders)}>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-4 transition-transform"
										class:rotate-180={showFolders}
									>
										<path
											fill-rule="evenodd"
											d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>
							</div>
						</div>
						{#if showFolders}
							<div class="mt-1" transition:fly={{ y: -10, duration: 150 }}>
								<Folders
									{folders}
									on:import={(e) => importChatHandler(e.detail, false, e.detail.folderId)}
									on:update={initFolders}
									on:change={itemClickHandler}
								/>
							</div>
						{/if}
					</div>
				{/if}

				{#if $pinnedChats && $pinnedChats.length > 0}
					<div class="px-2 pt-3">
						<div class="px-2 pb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
							{$i18n.t('Pinned')}
						</div>
						<div class="space-y-0.5">
							{#each $pinnedChats as chat (chat.id)}
								<ChatItem
									id={chat.id}
									title={chat.title}
									selected={$chatId === chat.id}
									{shiftKey}
									on:select={() => {
										selectedChatId = chat.id;
									}}
									on:unselect={() => {
										selectedChatId = null;
									}}
									on:change={itemClickHandler}
									on:tag={tagEventHandler}
									on:update={initChatList}
								/>
							{/each}
						</div>
					</div>
				{/if}

				<div class="px-2 pt-3">
					<div class="px-2 pb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
						{$i18n.t('Chats')}
					</div>
					{#if $chats}
						{@const filteredChats = $chats.filter((c) => !$pinnedChats?.some((p) => p.id === c.id))}
						{@const displayedChats = filteredChats.slice(0, MAX_SIDEBAR_CHATS)}
						{@const hasMoreChats = filteredChats.length > MAX_SIDEBAR_CHATS}
						<div class="space-y-0.5">
							{#each displayedChats as chat (chat.id)}
								<ChatItem
									id={chat.id}
									title={chat.title}
									selected={$chatId === chat.id}
									{shiftKey}
									on:select={() => {
										selectedChatId = chat.id;
									}}
									on:unselect={() => {
										selectedChatId = null;
									}}
									on:change={itemClickHandler}
									on:tag={tagEventHandler}
									on:update={initChatList}
								/>
							{/each}
						</div>
						{#if hasMoreChats}
							<button
								class="mt-2 w-full rounded-lg px-3 py-2 text-center text-xs font-medium text-accent-500 transition-colors hover:bg-gray-100 hover:text-accent-600 dark:text-accent-400 dark:hover:bg-gray-800 dark:hover:text-accent-300"
								on:click={() => showSearch.set(true)}
							>
								{$i18n.t('View All')} ({filteredChats.length})
							</button>
						{/if}
						{#if chatListLoading}
							<div class="flex justify-center py-4">
								<Spinner className="size-4" />
							</div>
						{/if}
					{:else}
						<div class="flex justify-center py-8">
							<Loader />
						</div>
					{/if}
				</div>
			</div>

			<!-- Mobile panel footer -->
			<div class="shrink-0 border-t border-gray-200 p-2 dark:border-gray-700/50">
				<UserMenu
					on:show={(e) => {
						if (e.detail === 'archived-chats') {
							showArchivedChats.set(true);
						}
					}}
				>
					<button
						class="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
					>
						{#if !sidebarProfileImageFailed && $user?.profile_image_url}
							<img
								src={$user.profile_image_url}
								class="size-8 shrink-0 rounded-full object-cover"
								alt={$user.name}
								on:error={() => (sidebarProfileImageFailed = true)}
							/>
						{:else}
							<div
								class="flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
								style="background-color: {sidebarUserColor};"
							>
								{sidebarUserInitials}
							</div>
						{/if}
						<div class="min-w-0 flex-1">
							<div class="truncate text-sm font-medium text-gray-900 dark:text-white">
								{$user?.name ?? ''}
							</div>
							<div class="truncate text-xs text-gray-500 dark:text-gray-400">
								{$user?.email ?? ''}
							</div>
						</div>
					</button>
				</UserMenu>
			</div>

			{#if draggedOver}
				<div
					class="absolute inset-0 flex items-center justify-center bg-gray-900/80 backdrop-blur-sm"
					transition:fly={{ duration: 150 }}
				>
					<div class="text-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="currentColor"
							class="mx-auto size-12 text-white"
						>
							<path
								fill-rule="evenodd"
								d="M10.5 3.75a6 6 0 0 0-5.98 6.496A5.25 5.25 0 0 0 6.75 20.25H18a4.5 4.5 0 0 0 2.206-8.423 3.75 3.75 0 0 0-4.133-4.303A6.001 6.001 0 0 0 10.5 3.75Zm2.03 5.47a.75.75 0 0 0-1.06 0l-3 3a.75.75 0 1 0 1.06 1.06l1.72-1.72v4.94a.75.75 0 0 0 1.5 0v-4.94l1.72 1.72a.75.75 0 1 0 1.06-1.06l-3-3Z"
								clip-rule="evenodd"
							/>
						</svg>
						<p class="mt-2 text-sm font-medium text-white">
							{$i18n.t('Drop files to import chats')}
						</p>
					</div>
				</div>
			{/if}
		</nav>
	</div>
{/if}

<!-- ═══════════════════════════════════════════════════════════════════
     DESKTOP: Icon rail + hover submenus (Perplexity-style)
     ═══════════════════════════════════════════════════════════════════ -->
{#if !$mobile}
	<div
		id="sidebar"
		class="fixed left-0 top-0 z-50 flex h-full"
		class:pointer-events-none={!activeSubmenu}
	>
		<!-- Icon rail (always visible) -->
		<div
			class="icon-rail pointer-events-auto relative z-10 flex h-full flex-col items-center bg-gray-100/80 py-2 backdrop-blur-sm dark:bg-gray-850/80"
			style="width: {RAIL_WIDTH}px;"
		>
			<!-- Logo -->
			<a
				href="/"
				class="mb-2 flex size-10 items-center justify-center rounded-xl transition-transform hover:scale-105 active:scale-95"
				on:click={itemClickHandler}
			>
				<img
					src={$brandingConfig?.favicon_data ||
						$brandingConfig?.favicon_url ||
						`${WEBUI_BASE_URL}/static/favicon.png`}
					class="size-7 rounded"
					alt="logo"
				/>
			</a>

			<!-- New chat -->
			<Tooltip content={$i18n.t('New Chat')} placement="right">
				<a
					href="/"
					class="flex size-10 items-center justify-center rounded-xl text-accent-500 transition-colors hover:bg-gray-200 hover:text-accent-600 dark:text-accent-400 dark:hover:bg-gray-700 dark:hover:text-accent-300"
					on:click={newChatHandler}
				>
					<PencilSquare className="size-5" />
				</a>
			</Tooltip>

			<!-- Search -->
			<Tooltip content={$i18n.t('Search')} placement="right">
				<button
					class="flex size-10 items-center justify-center rounded-xl text-accent-500 transition-colors hover:bg-gray-200 hover:text-accent-600 dark:text-accent-400 dark:hover:bg-gray-700 dark:hover:text-accent-300"
					on:click={() => showSearch.set(true)}
				>
					<Search className="size-5" />
				</button>
			</Tooltip>

			<!-- ── History icon (hover submenu trigger) ── -->
			<button
				class="rail-icon flex size-10 items-center justify-center rounded-xl text-accent-500 transition-all hover:bg-gray-200 hover:text-accent-600 dark:text-accent-400 dark:hover:bg-gray-700 dark:hover:text-accent-300"
				class:bg-gray-200={activeSubmenu === 'history'}
				class:dark:bg-gray-700={activeSubmenu === 'history'}
				class:text-accent-600={activeSubmenu === 'history'}
				class:dark:text-accent-300={activeSubmenu === 'history'}
				on:mouseenter={() => onSubmenuEnter('history')}
				on:mouseleave={onSubmenuLeave}
			>
				<!-- Clock / history icon -->
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="1.8"
					stroke="currentColor"
					class="size-5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
					/>
				</svg>
			</button>

			<!-- ── Spaces icon (direct link) ── -->
			<a
				href="/spaces"
				class="rail-icon flex size-10 items-center justify-center rounded-xl text-accent-500 transition-all hover:bg-gray-200 hover:text-accent-600 dark:text-accent-400 dark:hover:bg-gray-700 dark:hover:text-accent-300"
				class:bg-gray-200={$page.url.pathname.startsWith('/spaces')}
				class:dark:bg-gray-700={$page.url.pathname.startsWith('/spaces')}
				class:text-accent-600={$page.url.pathname.startsWith('/spaces')}
				class:dark:text-accent-300={$page.url.pathname.startsWith('/spaces')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2"
					stroke="currentColor"
					class="size-5"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"
					/>
				</svg>
			</a>

			<!-- Spacer -->
			<div class="flex-1" />

			<!-- ── More icon (hover submenu trigger) ── -->
			<button
				class="rail-icon flex size-10 items-center justify-center rounded-xl text-accent-500 transition-all hover:bg-gray-200 hover:text-accent-600 dark:text-accent-400 dark:hover:bg-gray-700 dark:hover:text-accent-300"
				class:bg-gray-200={activeSubmenu === 'more'}
				class:dark:bg-gray-700={activeSubmenu === 'more'}
				class:text-accent-600={activeSubmenu === 'more'}
				class:dark:text-accent-300={activeSubmenu === 'more'}
				on:mouseenter={() => onSubmenuEnter('more')}
				on:mouseleave={onSubmenuLeave}
			>
				<!-- Ellipsis horizontal -->
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="currentColor"
					class="size-5"
				>
					<path
						fill-rule="evenodd"
						d="M4.5 12a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0Zm6 0a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0Zm6 0a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>

			<!-- User avatar (always visible at bottom) -->
			<UserMenu
				on:show={(e) => {
					if (e.detail === 'archived-chats') {
						showArchivedChats.set(true);
					}
				}}
			>
				<button class="mt-1 flex size-10 items-center justify-center">
					{#if !sidebarProfileImageFailed && $user?.profile_image_url}
						<img
							src={$user.profile_image_url}
							class="size-8 rounded-full object-cover ring-2 ring-gray-200 transition-shadow hover:ring-gray-300 dark:ring-gray-700 dark:hover:ring-gray-600"
							alt={$user.name}
							on:error={() => (sidebarProfileImageFailed = true)}
						/>
					{:else}
						<div
							class="flex size-8 items-center justify-center rounded-full text-xs font-semibold text-white ring-2 ring-gray-200 transition-shadow hover:ring-gray-300 dark:ring-gray-700 dark:hover:ring-gray-600"
							style="background-color: {sidebarUserColor};"
						>
							{sidebarUserInitials}
						</div>
					{/if}
				</button>
			</UserMenu>
		</div>

		<!-- ── Submenu panels (slide out from rail) ── -->

		<!-- HISTORY SUBMENU -->
		{#if activeSubmenu === 'history'}
			<div
				class="submenu-panel pointer-events-auto flex h-full flex-col border-r border-gray-200/60 bg-gray-50/95 shadow-lg backdrop-blur-md dark:border-gray-700/40 dark:bg-gray-900/95"
				style="width: {$sidebarWidth}px;"
				transition:fly={{ x: -20, duration: 180, opacity: 0 }}
				on:mouseenter={onSubmenuPanelEnter}
				on:mouseleave={onSubmenuPanelLeave}
				on:dragover={onDragOver}
				on:dragleave={onDragLeave}
				on:drop={onDrop}
			>
				<!-- Header -->
				<div class="flex h-12 shrink-0 items-center justify-between px-4">
					<h2 class="text-sm font-semibold tracking-tight text-gray-900 dark:text-gray-100">
						{$i18n.t('History')}
					</h2>
					<button
						class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
						on:click={() => showSearch.set(true)}
					>
						<Search className="size-3.5" />
					</button>
				</div>

				<!-- Scrollable content -->
				<div
					class="flex-1 overflow-y-auto overflow-x-hidden px-2 pb-2"
					on:scroll={(e) => {
						scrollTop = e.target.scrollTop;
						if (
							$scrollPaginationEnabled &&
							!allChatsLoaded &&
							!chatListLoading &&
							e.target.scrollHeight - e.target.scrollTop <= e.target.clientHeight + 50
						) {
							loadMoreChats();
						}
					}}
				>
					<!-- Pinned Models -->
					{#if pinnedModels.length > 0}
						<div class="mb-1">
							<button
								class="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
								on:click={() => (showPinnedModels = !showPinnedModels)}
							>
								<span>{$i18n.t('Pinned Models')}</span>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="size-3.5 transition-transform"
									class:rotate-180={showPinnedModels}
								>
									<path
										fill-rule="evenodd"
										d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
							{#if showPinnedModels}
								<div class="mt-1" transition:fly={{ y: -10, duration: 150 }}>
									<PinnedModelList {pinnedModels} />
								</div>
							{/if}
						</div>
					{/if}

					<!-- Channels -->
					{#if $config?.features?.enable_channels && ($user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true))}
						<div class="mb-1">
							<div
								class="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
							>
								<button class="flex-1 text-left" on:click={() => (showChannels = !showChannels)}>
									{$i18n.t('Channels')}
								</button>
								<div class="flex items-center gap-1">
									{#if $user?.role === 'admin'}
										<button
											class="rounded p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700"
											on:click={() => (showCreateChannel = true)}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="size-3.5"
											>
												<path
													d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
												/>
											</svg>
										</button>
									{/if}
									<button on:click={() => (showChannels = !showChannels)}>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="size-3.5 transition-transform"
											class:rotate-180={showChannels}
										>
											<path
												fill-rule="evenodd"
												d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							</div>
							{#if showChannels && $channels}
								<div class="mt-1 space-y-0.5" transition:fly={{ y: -10, duration: 150 }}>
									{#each $channels as channel (channel.id)}
										<ChannelItem {channel} onUpdate={initChannels} />
									{/each}
								</div>
							{/if}
						</div>
					{/if}

					<!-- Pinned Chats -->
					{#if $pinnedChats && $pinnedChats.length > 0}
						<div class="mb-1">
							<div
								class="px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400"
							>
								{$i18n.t('Pinned')}
							</div>
							<div class="space-y-0.5">
								{#each $pinnedChats as chat (chat.id)}
									<ChatItem
										id={chat.id}
										title={chat.title}
										selected={$chatId === chat.id}
										{shiftKey}
										on:select={() => {
											selectedChatId = chat.id;
										}}
										on:unselect={() => {
											selectedChatId = null;
										}}
										on:change={itemClickHandler}
										on:tag={tagEventHandler}
										on:update={initChatList}
									/>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Private Chats -->
					<div>
						<div
							class="flex items-center gap-1.5 px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-2.5"
							>
								<path
									fill-rule="evenodd"
									d="M8 1a3.5 3.5 0 0 0-3.5 3.5V7A1.5 1.5 0 0 0 3 8.5v5A1.5 1.5 0 0 0 4.5 15h7a1.5 1.5 0 0 0 1.5-1.5v-5A1.5 1.5 0 0 0 11.5 7V4.5A3.5 3.5 0 0 0 8 1Zm2 6V4.5a2 2 0 1 0-4 0V7h4Z"
									clip-rule="evenodd"
								/>
							</svg>
							{$i18n.t('Private')}
						</div>
						{#if $chats}
							{@const filteredChats = $chats.filter(
								(c) => !$pinnedChats?.some((p) => p.id === c.id) && !c.space_id
							)}
							{@const displayedChats = filteredChats.slice(0, MAX_SIDEBAR_CHATS)}
							{@const hasMoreChats = filteredChats.length > MAX_SIDEBAR_CHATS}
							<div class="space-y-0.5">
								{#each displayedChats as chat (chat.id)}
									<ChatItem
										id={chat.id}
										title={chat.title}
										selected={$chatId === chat.id}
										{shiftKey}
										on:select={() => {
											selectedChatId = chat.id;
										}}
										on:unselect={() => {
											selectedChatId = null;
										}}
										on:change={itemClickHandler}
										on:tag={tagEventHandler}
										on:update={initChatList}
									/>
								{/each}
							</div>
							{#if hasMoreChats}
								<button
									class="mt-2 w-full rounded-lg px-3 py-1.5 text-center text-xs font-medium text-accent-500 transition-colors hover:bg-gray-100 hover:text-accent-600 dark:text-accent-400 dark:hover:bg-gray-800 dark:hover:text-accent-300"
									on:click={() => showSearch.set(true)}
								>
									{$i18n.t('View All')} ({filteredChats.length})
								</button>
							{/if}
							{#if chatListLoading}
								<div class="flex justify-center py-4">
									<Spinner className="size-4" />
								</div>
							{/if}
						{:else}
							<div class="flex justify-center py-6">
								<Loader />
							</div>
						{/if}
					</div>

					{#if spacesShared.length > 0}
						<div class="mt-3">
							<div
								class="flex items-center gap-1.5 px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="size-2.5"
								>
									<path
										d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM12.735 14c.618 0 1.093-.561.872-1.139a6.002 6.002 0 0 0-11.215 0c-.22.578.254 1.139.872 1.139h9.47Z"
									/>
								</svg>
								{$i18n.t('Shared Spaces')}
							</div>
							{#each spacesShared as space (space.id)}
								<SpaceItem {space} variant="shared" {shiftKey} />
							{/each}
						</div>
					{/if}

					{#if spacesPrivate.length > 0}
						<div class="mt-3">
							<div
								class="flex items-center gap-1.5 px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="size-2.5"
								>
									<path
										fill-rule="evenodd"
										d="M8 1a3.5 3.5 0 0 0-3.5 3.5V7A1.5 1.5 0 0 0 3 8.5v5A1.5 1.5 0 0 0 4.5 15h7a1.5 1.5 0 0 0 1.5-1.5v-5A1.5 1.5 0 0 0 11.5 7V4.5A3.5 3.5 0 0 0 8 1Zm2 6V4.5a2 2 0 1 0-4 0V7h4Z"
										clip-rule="evenodd"
									/>
								</svg>
								{$i18n.t('Private Spaces')}
							</div>
							{#each spacesPrivate as space (space.id)}
								<SpaceItem {space} variant="private" {shiftKey} />
							{/each}
						</div>
					{/if}
				</div>

				<!-- Footer: Archived link -->
				<div class="shrink-0 border-t border-gray-200/60 px-2 py-2 dark:border-gray-700/40">
					<button
						class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
						on:click={() => showArchivedChats.set(true)}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z"
							/>
						</svg>
						{$i18n.t('Archived Chats')}
					</button>
				</div>

				{#if draggedOver}
					<div
						class="absolute inset-0 flex items-center justify-center rounded-r-xl bg-gray-900/80 backdrop-blur-sm"
						transition:fly={{ duration: 150 }}
					>
						<div class="text-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								fill="currentColor"
								class="mx-auto size-10 text-white"
							>
								<path
									fill-rule="evenodd"
									d="M10.5 3.75a6 6 0 0 0-5.98 6.496A5.25 5.25 0 0 0 6.75 20.25H18a4.5 4.5 0 0 0 2.206-8.423 3.75 3.75 0 0 0-4.133-4.303A6.001 6.001 0 0 0 10.5 3.75Zm2.03 5.47a.75.75 0 0 0-1.06 0l-3 3a.75.75 0 1 0 1.06 1.06l1.72-1.72v4.94a.75.75 0 0 0 1.5 0v-4.94l1.72 1.72a.75.75 0 1 0 1.06-1.06l-3-3Z"
									clip-rule="evenodd"
								/>
							</svg>
							<p class="mt-1 text-xs font-medium text-white">
								{$i18n.t('Drop files to import chats')}
							</p>
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- SPACES SUBMENU -->
		{#if activeSubmenu === 'spaces'}
			<div
				class="submenu-panel pointer-events-auto flex h-full flex-col border-r border-gray-200/60 bg-gray-50/95 shadow-lg backdrop-blur-md dark:border-gray-700/40 dark:bg-gray-900/95"
				style="width: {$sidebarWidth}px;"
				transition:fly={{ x: -20, duration: 180, opacity: 0 }}
				on:mouseenter={onSubmenuPanelEnter}
				on:mouseleave={onSubmenuPanelLeave}
			>
				<!-- Header -->
				<div class="flex h-12 shrink-0 items-center justify-between px-4">
					<h2 class="text-sm font-semibold tracking-tight text-gray-900 dark:text-gray-100">
						{$i18n.t('Spaces')}
					</h2>
					<button
						class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
						on:click={() => (showCreateSpace = true)}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="size-3.5"
						>
							<path
								d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
							/>
						</svg>
					</button>
				</div>

				<!-- Scrollable content -->
				<div class="flex-1 overflow-y-auto overflow-x-hidden px-2 pb-2">
					{#if spacesLoading}
						<div class="flex justify-center py-6">
							<Spinner className="size-4" />
						</div>
					{:else if !spacesPrivate.length && !spacesShared.length && !spacesPinned.length && !spacesBookmarked.length}
						<div class="px-2 py-6 text-center text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('No spaces yet. Create one to get started!')}
						</div>
					{:else}
						{#if spacesPinned.length > 0}
							<div class="mb-2">
								<div
									class="flex items-center gap-1.5 px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="size-2.5"
									>
										<path
											d="M8.074.334a.75.75 0 0 0-1.148 0L4.203 3.57a.75.75 0 0 0 .722 1.212l.336-.034.067.067-.067 3.281a.75.75 0 0 0 .467.713l2.022.808a.75.75 0 0 0 .5 0l2.022-.808a.75.75 0 0 0 .467-.713L10.672 4.815l.067-.067.336.034a.75.75 0 0 0 .722-1.212L8.074.334Z"
										/>
										<path d="M6.428 9.628 8 12.236l1.572-2.608L8 10.256l-1.572-.628Z" />
										<path
											fill-rule="evenodd"
											d="M3.5 13.5c0 .643.224 1.005.44 1.184.224.186.537.265.804.28a7.634 7.634 0 0 0 3.256-.378 7.634 7.634 0 0 0 3.256.378c.267-.015.58-.094.804-.28.216-.179.44-.541.44-1.184a3 3 0 0 0-1.605-2.656l-.29-.155-.776 1.29-.057.095a.75.75 0 0 1-.578.426H6.806a.75.75 0 0 1-.578-.426l-.057-.095-.776-1.29-.29.155A3 3 0 0 0 3.5 13.5Z"
											clip-rule="evenodd"
										/>
									</svg>
									{$i18n.t('Pinned')}
								</div>
								{#each spacesPinned as space (space.id)}
									<SpaceItem {space} variant="pinned" {shiftKey} />
								{/each}
							</div>
						{/if}

						{#if spacesBookmarked.length > 0}
							<div class="mb-2">
								<div
									class="flex items-center gap-1.5 px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="size-2.5"
									>
										<path
											fill-rule="evenodd"
											d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z"
											clip-rule="evenodd"
										/>
									</svg>
									{$i18n.t('Bookmarked')}
								</div>
								{#each spacesBookmarked as space (space.id)}
									<SpaceItem {space} variant="bookmarked" {shiftKey} />
								{/each}
							</div>
						{/if}

						{#if spacesPrivate.length > 0}
							<div class="mb-2">
								<div
									class="flex items-center gap-1.5 px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="size-2.5"
									>
										<path
											fill-rule="evenodd"
											d="M8 1a3.5 3.5 0 0 0-3.5 3.5V7A1.5 1.5 0 0 0 3 8.5v5A1.5 1.5 0 0 0 4.5 15h7a1.5 1.5 0 0 0 1.5-1.5v-5A1.5 1.5 0 0 0 11.5 7V4.5A3.5 3.5 0 0 0 8 1Zm2 6V4.5a2 2 0 1 0-4 0V7h4Z"
											clip-rule="evenodd"
										/>
									</svg>
									{$i18n.t('Private')}
								</div>
								{#each spacesPrivate as space (space.id)}
									<SpaceItem {space} variant="private" {shiftKey} />
								{/each}
							</div>
						{/if}

						{#if spacesShared.length > 0}
							<div class="mb-2">
								<div
									class="flex items-center gap-1.5 px-2 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-wider text-accent-500 dark:text-accent-400"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="size-2.5"
									>
										<path
											d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM12.735 14c.618 0 1.093-.561.872-1.139a6.002 6.002 0 0 0-11.215 0c-.22.578.254 1.139.872 1.139h9.47Z"
										/>
									</svg>
									{$i18n.t('Shared')}
								</div>
								{#each spacesShared as space (space.id)}
									<SpaceItem {space} variant="shared" {shiftKey} />
								{/each}
							</div>
						{/if}
					{/if}
				</div>

				<!-- Footer -->
				<div class="shrink-0 border-t border-gray-200/60 px-2 py-2 dark:border-gray-700/40">
					<a
						href="/spaces"
						class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3"
							/>
						</svg>
						{$i18n.t('View all spaces')}
					</a>
				</div>
			</div>
		{/if}

		<!-- MORE SUBMENU -->
		{#if activeSubmenu === 'more'}
			<div
				class="submenu-panel pointer-events-auto flex h-full flex-col border-r border-gray-200/60 bg-gray-50/95 shadow-lg backdrop-blur-md dark:border-gray-700/40 dark:bg-gray-900/95"
				style="width: {$sidebarWidth}px;"
				transition:fly={{ x: -20, duration: 180, opacity: 0 }}
				on:mouseenter={onSubmenuPanelEnter}
				on:mouseleave={onSubmenuPanelLeave}
			>
				<!-- Header -->
				<div class="flex h-12 shrink-0 items-center px-4">
					<h2 class="text-sm font-semibold tracking-tight text-gray-900 dark:text-gray-100">
						{$i18n.t('More')}
					</h2>
				</div>

				<!-- Content -->
				<div class="flex-1 overflow-y-auto overflow-x-hidden px-2 pb-2">
					<!-- Folders section -->
					{#if $config?.features?.enable_folders !== false}
						<div class="mb-2">
							<div
								class="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
							>
								<button class="flex-1 text-left" on:click={() => (showFolders = !showFolders)}>
									{$i18n.t('Folders')}
								</button>
								<div class="flex items-center gap-1">
									<button
										class="rounded p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700"
										on:click={() => (showCreateFolderModal = true)}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="size-3.5"
										>
											<path
												d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
											/>
										</svg>
									</button>
									<button on:click={() => (showFolders = !showFolders)}>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="size-3.5 transition-transform"
											class:rotate-180={showFolders}
										>
											<path
												fill-rule="evenodd"
												d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							</div>
							{#if showFolders}
								<div class="mt-1" transition:fly={{ y: -10, duration: 150 }}>
									<Folders
										{folders}
										on:import={(e) => importChatHandler(e.detail, false, e.detail.folderId)}
										on:update={initFolders}
										on:change={itemClickHandler}
									/>
								</div>
							{/if}
						</div>
					{/if}

					<!-- Quick links -->
					<div class="space-y-0.5">
						<button
							class="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
							on:click={() => showSettings.set(true)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-4 text-gray-500 dark:text-gray-400"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
								/>
							</svg>
							{$i18n.t('Settings')}
						</button>

						<a
							href="/oversight"
							class="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-4 text-gray-500 dark:text-gray-400"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
								/>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
								/>
							</svg>
							{$i18n.t('Oversight')}
						</a>

						{#if $user?.role === 'admin'}
							<a
								href="/admin"
								class="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									class="size-4 text-gray-500 dark:text-gray-400"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75"
									/>
								</svg>
								{$i18n.t('Admin Panel')}
							</a>
						{/if}

						<button
							class="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
							on:click={() => showArchivedChats.set(true)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-4 text-gray-500 dark:text-gray-400"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m20.25 7.5-.625 10.632a2.25 2.25 0 0 1-2.247 2.118H6.622a2.25 2.25 0 0 1-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125Z"
								/>
							</svg>
							{$i18n.t('Archived Chats')}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}

<!-- Global mouse move handler for resize -->
<svelte:window
	on:mousemove={(e) => {
		if (isResizing) {
			resizeSidebarHandler(e.clientX);
		}
	}}
	on:mouseup={resizeEndHandler}
/>

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	onUpdate={async () => {
		await initChatList();
	}}
/>

<ChannelModal
	bind:show={showCreateChannel}
	onSubmit={async (payload: any) => {
		let { type, name, is_private, access_grants, group_ids, user_ids } = payload ?? {};
		name = name?.trim();

		if (type === 'dm') {
			if (!user_ids || user_ids.length === 0) {
				toast.error($i18n.t('Please select at least one user for Direct Message channel.'));
				return;
			}
		} else {
			if (!name) {
				toast.error($i18n.t('Channel name cannot be empty.'));
				return;
			}
		}

		const res = await createNewChannel(localStorage.token, {
			type: type,
			name: name,
			is_private: is_private,
			access_grants: access_grants,
			group_ids: group_ids,
			user_ids: user_ids
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			$socket.emit('join-channels', { auth: { token: $user?.token } });
			await initChannels();
			showCreateChannel = false;
			showChannels = true;
			goto(`/channels/${res.id}`);
		}
	}}
/>

<FolderModal
	bind:show={showCreateFolderModal}
	onSubmit={async (folder) => {
		await createFolder(folder);
		showCreateFolderModal = false;
	}}
/>

<SpaceSettingsModal
	bind:show={showCreateSpace}
	onSubmit={async (space) => {
		showCreateSpace = false;
		goto(`/spaces/${space.slug}`);
	}}
/>

<SearchModal
	bind:show={$showSearch}
	onClose={() => {
		if ($mobile) {
			showSidebar.set(false);
		}
	}}
/>

<button
	id="sidebar-new-chat-button"
	class="hidden"
	on:click={() => {
		goto('/');
		newChatHandler();
	}}
/>

<style>
	.submenu-panel {
		position: relative;
	}

	.icon-rail {
		border-right: 1px solid rgba(0, 0, 0, 0.06);
	}

	:global(.dark) .icon-rail {
		border-right-color: rgba(255, 255, 255, 0.06);
	}
</style>
