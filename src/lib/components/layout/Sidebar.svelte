<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import Sortable from 'sortablejs';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import {
		user,
		chats,
		settings,
		chatId,
		tags,
		folders as _folders,
		showSidebar,
		showSearch,
		mobile,
		pinnedChats,
		pinnedNotes,
		temporaryChatEnabled,
		channels,
		socket,
		config,
		isApp,
		visiblePinnedModels,
		selectedFolder,
		WEBUI_NAME,
		sidebarWidth
	} from '$lib/stores';
	import {
		loadNextChatListPage,
		refreshChatList,
		registerFolderRefreshHandler,
		setAllChatsRead,
		setChatActive,
		setChatReadAt
	} from '$lib/stores/chatList';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	$: canImportChats = $user?.role === 'admin' || ($user?.permissions?.chat?.import ?? true);

	import {
		getAllTags,
		toggleChatPinnedStatusById,
		getChatById,
		updateChatFolderIdById,
		importChats,
		deleteAllChats,
		getChatListBySearchText,
		markChatsRead
	} from '$lib/apis/chats';
	import {
		createNewFolder,
		getFolders,
		getSharedFolders,
		updateFolderParentIdById
	} from '$lib/apis/folders';
	import { createNewNote, getPinnedNoteList, toggleNotePinnedStatusById } from '$lib/apis/notes';
	import { updateUserSettings } from '$lib/apis/users';
	import { createNoteHandler } from '$lib/components/notes/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import Folder from '../common/Folder.svelte';
	import SidebarSection from './Sidebar/Section.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import SharedFolderItem from './Sidebar/SharedFolderItem.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import SearchModal from './SearchModal.svelte';
	import FolderModal from './Sidebar/Folders/FolderModal.svelte';
	import PinnedModelList from './Sidebar/PinnedModelList.svelte';
	import PinnedNoteList from './Sidebar/PinnedNoteList.svelte';
	import CalendarIcon from './Sidebar/icons/Calendar.svelte';
	import ClockIcon from './Sidebar/icons/Clock.svelte';
	import CodeIcon from './Sidebar/icons/Code.svelte';
	import EditPencilIcon from './Sidebar/icons/EditPencil.svelte';
	import NotesIcon from './Sidebar/icons/Notes.svelte';
	import SearchIcon from './Sidebar/icons/Search.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import WorkspaceIcon from './Sidebar/icons/Workspace.svelte';
	import HotkeyHint from '../common/HotkeyHint.svelte';
	import Dropdown from '../common/Dropdown.svelte';
	import DropdownMenu from '../common/DropdownMenu.svelte';
	import CheckIcon from '../icons/Check.svelte';
	import MoreHorizontalIcon from './Sidebar/icons/MoreHorizontal.svelte';
	import MobileSwipePanel from '../common/MobileSwipePanel.svelte';

	const BREAKPOINT = 768;
	const DEFAULT_PINNED_ITEMS = ['notes', 'workspace'];

	let scrollTop = 0;

	let navElement;
	let shiftKey = false;

	let selectedChatId = null;

	// Keep the optimistic sidebar highlight in sync with the active chat. Leaving the
	// chat view (e.g. navigating to an admin page) clears chatId, and programmatic
	// navigation such as cloning moves chatId to a different chat — in both cases the
	// previously-selected item must not stay highlighted. The optimistic on-click
	// highlight is preserved because a click sets selectedChatId without changing
	// chatId, so this reactive only re-runs once chatId catches up to the same value.
	$: selectedChatId = $chatId || null;

	let showCreateChannel = false;

	// Pagination variables
	let chatListLoading = false;
	let chatListReady = false;
	let allChatsLoaded = false;

	let showCreateFolderModal = false;

	let showPinnedModels = true;
	let showPinnedNotes = false;
	let showChannels = false;
	let showFolders = false;
	let showSharedFolders = false;
	let showChatsMenu = false;

	let folders = {};
	type SelectedSidebarFolder = { id: string } | null;
	let folderRegistry: Record<
		string,
		{
			setFolderItems?: () => unknown;
			upsertChat?: (chat: Record<string, unknown>) => unknown;
			setChatActive?: (chatId: string, active: boolean) => boolean;
			setChatReadAt?: (chatId: string, lastReadAt: number) => boolean;
			setAllChatsRead?: () => unknown;
		}
	> = {};

	let newFolderId = null;

	let sharedFolders: any[] = [];

	const initSelectedFolderChats = (folder: SelectedSidebarFolder) => {
		if (!folder?.id) {
			return;
		}

		folderRegistry[folder.id]?.setFolderItems?.();
	};

	$: pinnedItems = $settings?.pinnedMenuItems ?? DEFAULT_PINNED_ITEMS;

	const isMenuItemVisible = (id) => {
		switch (id) {
			case 'notes':
				return (
					($config?.features?.enable_notes ?? false) &&
					($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
				);
			case 'workspace':
				return (
					$user?.role === 'admin' ||
					$user?.permissions?.workspace?.models ||
					$user?.permissions?.workspace?.knowledge ||
					$user?.permissions?.workspace?.prompts ||
					$user?.permissions?.workspace?.tools ||
					$user?.permissions?.workspace?.skills
				);
			case 'automations':
				return (
					$config?.features?.enable_automations &&
					($user?.role === 'admin' || $user?.permissions?.features?.automations)
				);
			case 'calendar':
				return (
					$config?.features?.enable_calendar &&
					($user?.role === 'admin' || $user?.permissions?.features?.calendar)
				);
			case 'playground':
				return $user?.role === 'admin';
			default:
				return false;
		}
	};

	const getMenuItemMeta = (id) => {
		const items = {
			notes: { label: 'Notes', href: '/notes', iconType: 'note' },
			workspace: { label: 'Workspace', href: '/workspace', iconType: 'workspace' },
			automations: { label: 'Automations', href: '/automations', iconType: 'automations' },
			calendar: { label: 'Calendar', href: '/calendar', iconType: 'calendar' },
			playground: { label: 'Playground', href: '/playground', iconType: 'playground' }
		};
		return items[id];
	};

	const menuItemPathPrefixes = {
		notes: '/notes',
		workspace: '/workspace',
		calendar: '/calendar',
		automations: '/automations',
		playground: '/playground'
	};

	const getActiveMenuItemId = (pathname) => {
		for (const [id, pathPrefix] of Object.entries(menuItemPathPrefixes)) {
			if (pathname === pathPrefix || pathname.startsWith(`${pathPrefix}/`)) {
				return id;
			}
		}

		return null;
	};

	$: activeMenuItemId = getActiveMenuItemId($page.url.pathname);

	const initPinnedMenuSortable = () => {
		const el = document.getElementById('pinned-menu-items-list');
		if (el && !$mobile) {
			new Sortable(el, {
				animation: 150,
				onUpdate: async (event) => {
					const itemId = event.item.dataset.id;
					const newIndex = event.newIndex;
					const current = [...pinnedItems];
					const oldIndex = current.indexOf(itemId);
					current.splice(oldIndex, 1);
					current.splice(newIndex, 0, itemId);
					settings.set({ ...$settings, pinnedMenuItems: current });
					await updateUserSettings(localStorage.token, { ui: $settings });
				}
			});
		}
	};

	$: initSelectedFolderChats($selectedFolder as SelectedSidebarFolder);

	const initFolders = async () => {
		if ($config?.features?.enable_folders === false) {
			return;
		}

		const [folderList, sharedFolderList] = await Promise.all([
			getFolders(localStorage.token).catch((error) => {
				return [];
			}),
			getSharedFolders(localStorage.token).catch((error) => {
				return [];
			})
		]);
		_folders.set(folderList.sort((a, b) => b.updated_at - a.updated_at));

		sharedFolders = sharedFolderList;
		const folderMap: Record<string, any> = {};

		// First pass: Initialize all folder entries
		for (const folder of folderList) {
			// Ensure folder is added to folders with its data
			folderMap[folder.id] = { ...(folderMap[folder.id] || {}), ...folder };

			if (newFolderId && folder.id === newFolderId) {
				folderMap[folder.id].new = true;
				newFolderId = null;
			}
		}

		// Second pass: Tie child folders to their parents
		for (const folder of folderList) {
			if (folder.parent_id) {
				// Ensure the parent folder is initialized if it doesn't exist
				if (!folderMap[folder.parent_id]) {
					folderMap[folder.parent_id] = {}; // Create a placeholder if not already present
				}

				// Initialize childrenIds array if it doesn't exist and add the current folder id
				folderMap[folder.parent_id].childrenIds = folderMap[folder.parent_id].childrenIds
					? [...folderMap[folder.parent_id].childrenIds, folder.id]
					: [folder.id];

				// Sort the children by updated_at field
				folderMap[folder.parent_id].childrenIds.sort((a, b) => {
					return folderMap[b].updated_at - folderMap[a].updated_at;
				});
			}
		}

		// Merge shared folders into the same structure
		for (const sf of sharedFolders) {
			if (folderMap[sf.id]) continue; // Already owned by user
			folderMap[sf.id] = { ...sf, shared: true };
		}

		// Build parent-child relationships for shared folders
		for (const sf of sharedFolders) {
			if (folderMap[sf.id]?.shared && sf.parent_id && folderMap[sf.parent_id]) {
				folderMap[sf.parent_id].childrenIds = folderMap[sf.parent_id].childrenIds
					? [...new Set([...folderMap[sf.parent_id].childrenIds, sf.id])]
					: [sf.id];
			}
		}

		folders = folderMap;
	};

	const createFolder = async ({ name, data, parent_id }) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		// Check for duplicate names in the same parent
		const siblings = Object.values(folders).filter((folder) => folder.parent_id === parent_id);
		if (siblings.find((folder) => folder.name.toLowerCase() === name.toLowerCase())) {
			// If a folder with the same name already exists, append a number to the name
			let i = 1;
			while (
				siblings.find((folder) => folder.name.toLowerCase() === `${name} ${i}`.toLowerCase())
			) {
				i++;
			}

			name = `${name} ${i}`;
		}

		// Add a dummy folder to the list to show the user that the folder is being created
		const tempId = uuidv4();
		folders = {
			...folders,
			[tempId]: {
				id: tempId,
				name: name,
				parent_id: parent_id,
				created_at: Date.now(),
				updated_at: Date.now()
			}
		};

		const res = await createNewFolder(localStorage.token, {
			name,
			data,
			parent_id
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// newFolderId = res.id;
			await initFolders();
			showFolders = true;
		}
	};

	const initChannels = async () => {
		// default (none), group, dm type
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
		// Reset pagination variables
		console.log('initChatList');
		allChatsLoaded = false;
		chatListReady = false;

		await Promise.all([
			(async () => {
				console.log('Init tags');
				const _tags = await getAllTags(localStorage.token);
				tags.set(_tags);
			})(),
			(async () => {
				if (
					$config?.features?.enable_notes &&
					($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
				) {
					console.log('Init pinned notes');
					const _pinnedNotes = await getPinnedNoteList(localStorage.token).catch(() => []);
					pinnedNotes.set(_pinnedNotes);
				}
			})(),
			(async () => {
				console.log('Init chat list');
				await refreshChatRows();
			})()
		]);
	};

	const initSidebarData = async () => {
		// Only fetch channels if the feature is enabled and user has permission
		if (
			$config?.features?.enable_channels &&
			($user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true))
		) {
			await initChannels();
		}

		await initChatList();
	};

	const refreshChatRows = async () => {
		const result = await refreshChatList(localStorage.token, { refreshPinned: true });
		if (result.accepted) {
			await initFolders();
			await Promise.all(Object.values(folderRegistry).map((folder) => folder?.setFolderItems?.()));
			allChatsLoaded = result.allLoaded;
			chatListReady = true;
		}
	};

	const loadMoreChats = async () => {
		if (chatListLoading || allChatsLoaded || !$showSidebar) {
			return;
		}

		chatListLoading = true;

		const result = await loadNextChatListPage(localStorage.token);
		allChatsLoaded = result.allLoaded;

		chatListLoading = false;
	};

	const applyFolderUnreadCounts = (folderUnreadCounts: Record<string, number>) => {
		folders = Object.fromEntries(
			Object.entries(folders).map(([id, folder]) => [
				id,
				id in folderUnreadCounts ? { ...folder, unread_count: folderUnreadCounts[id] } : folder
			])
		);
		_folders.update((folderList) =>
			folderList.map((folder) =>
				folder.id in folderUnreadCounts
					? { ...folder, unread_count: folderUnreadCounts[folder.id] }
					: folder
			)
		);
	};

	const applyChatReadState = (data) => {
		if (data?.folder_unread_counts) {
			applyFolderUnreadCounts(data.folder_unread_counts);
		}

		if (data?.chat_id && typeof data?.last_read_at === 'number') {
			setChatReadAt(data.chat_id, data.last_read_at);
			for (const folder of Object.values(folderRegistry)) {
				folder?.setChatReadAt?.(data.chat_id, data.last_read_at);
			}
		}
	};

	const markAllChatsReadHandler = async () => {
		const res = await markChatsRead(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!res) return;

		showChatsMenu = false;
		if (res.folder_unread_counts) {
			applyFolderUnreadCounts(res.folder_unread_counts);
		}
		setAllChatsRead();
		for (const folder of Object.values(folderRegistry)) {
			folder?.setAllChatsRead?.();
		}
	};

	const importChatHandler = async (items, pinned = false, folderId = null) => {
		if (!canImportChats) {
			toast.error($i18n.t('Access prohibited'));
			return;
		}

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

		// Check if a file is being draggedOver.
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
		console.log(e); // Log the drop event

		// Perform file drop check and handle it accordingly
		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);

			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles); // Log the dropped files
				inputFilesHandler(inputFiles); // Handle the dropped files
			}
		}

		draggedOver = false; // Reset draggedOver status after drop
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

	const closeMobileSidebar = () => {
		if ($mobile) {
			showSidebar.set(false);
		}
	};

	const MIN_WIDTH = 220;
	const MAX_WIDTH = 480;

	let isResizing = false;
	let activePointerId: number | null = null;
	let activeResizer: HTMLElement | null = null;

	let startWidth = 0;
	let startClientX = 0;

	const resizeStartHandler = (e: PointerEvent) => {
		if ($mobile) return;

		e.preventDefault();
		isResizing = true;
		activePointerId = e.pointerId;
		activeResizer = e.currentTarget as HTMLElement;
		activeResizer.setPointerCapture?.(e.pointerId);

		startClientX = e.clientX;
		startWidth = $sidebarWidth ?? 245;

		document.body.style.userSelect = 'none';
	};

	const resizeEndHandler = (e?: PointerEvent) => {
		if (!isResizing) return;
		if (e && activePointerId !== null && e.pointerId !== activePointerId) return;

		isResizing = false;

		if (activePointerId !== null && activeResizer?.hasPointerCapture?.(activePointerId)) {
			activeResizer.releasePointerCapture(activePointerId);
		}
		activePointerId = null;
		activeResizer = null;

		document.body.style.userSelect = '';
		localStorage.setItem('sidebarWidth', String($sidebarWidth));
	};

	const resizeSidebarHandler = (endClientX: number) => {
		const dx = endClientX - startClientX;
		const newSidebarWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + dx));

		sidebarWidth.set(newSidebarWidth);
		document.documentElement.style.setProperty('--sidebar-width', `${newSidebarWidth}px`);
	};

	onDestroy(() => {
		if (isResizing) {
			document.body.style.userSelect = '';
		}
	});

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

		showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);

		const unsubscribers = [
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
				localStorage.sidebar = value;

				// nav element is not available on the first render
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
			})
		];

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur', onBlur);

		const dropZone = document.getElementById('sidebar');
		if (dropZone) {
			dropZone.addEventListener('dragover', onDragOver);
			dropZone.addEventListener('drop', onDrop);
			dropZone.addEventListener('dragleave', onDragLeave);
		}

		const socketInstance = $socket;
		socketInstance?.on('events', chatActiveEventHandler);
		socketInstance?.on('connect', refreshChatRows);

		const unregisterFolderRefreshHandler = registerFolderRefreshHandler(async (folderId, chat) => {
			// null refreshes the folder tree; undefined refreshes all folder chat lists.
			if (folderId === null) {
				return initFolders();
			}

			if (folderId) {
				if (chat) {
					return folderRegistry[folderId]?.upsertChat?.(chat);
				}

				return folderRegistry[folderId]?.setFolderItems?.();
			}

			return Promise.all(Object.values(folderRegistry).map((folder) => folder?.setFolderItems?.()));
		});

		await tick();
		await initSidebarData();
		initPinnedMenuSortable();

		return () => {
			unsubscribers.forEach((unsubscriber) => unsubscriber());

			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);

			window.removeEventListener('focus', onFocus);
			window.removeEventListener('blur', onBlur);

			if (dropZone) {
				dropZone.removeEventListener('dragover', onDragOver);
				dropZone.removeEventListener('drop', onDrop);
				dropZone.removeEventListener('dragleave', onDragLeave);
			}

			socketInstance?.off('events', chatActiveEventHandler);
			socketInstance?.off('connect', refreshChatRows);

			unregisterFolderRefreshHandler();
		};
	});

	// Handler for chat events (defined outside onMount for proper cleanup)
	const chatActiveEventHandler = async (event: {
		chat_id: string;
		message_id: string;
		data: {
			type: string;
			data: {
				active?: boolean;
				folder_id?: string | null;
				last_read_at?: number;
				folder_unread_counts?: Record<string, number>;
			};
		};
	}) => {
		if (event.data?.type === 'chat:active') {
			const eventData = event.data.data ?? {};
			const active = eventData.active ?? false;
			const found = setChatActive(event.chat_id, active);
			let foundInFolder = false;
			for (const folder of Object.values(folderRegistry)) {
				foundInFolder = folder?.setChatActive?.(event.chat_id, active) || foundInFolder;
			}
			if (!foundInFolder && active && eventData.folder_id) {
				await folderRegistry[eventData.folder_id]?.setFolderItems?.();
			}
			if (!found && active) {
				await refreshChatRows();
			}
		} else if (event.data?.type === 'chat:list') {
			const eventData = event.data.data ?? {};
			const folderUnreadCounts = eventData.folder_unread_counts;
			if (folderUnreadCounts) {
				applyFolderUnreadCounts(folderUnreadCounts);
			}

			if (typeof eventData.last_read_at === 'number') {
				setChatReadAt(event.chat_id, eventData.last_read_at);
				for (const folder of Object.values(folderRegistry)) {
					folder?.setChatReadAt?.(event.chat_id, eventData.last_read_at);
				}
				return;
			}

			await refreshChatRows();
			if (eventData.folder_id) {
				await folderRegistry[eventData.folder_id]?.setFolderItems?.();
			}
		}
	};

	const newChatHandler = async () => {
		selectedChatId = null;
		selectedFolder.set(null);
		closeMobileSidebar();

		if ($user?.role !== 'admin' && $user?.permissions?.chat?.temporary_enforced) {
			await temporaryChatEnabled.set(true);
		} else {
			await temporaryChatEnabled.set(false);
		}
	};

	const itemClickHandler = async () => {
		selectedChatId = null;
		chatId.set('');

		closeMobileSidebar();

		await tick();
	};

	const isWindows = /Windows/i.test(navigator.userAgent);
</script>

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

<svelte:window
	on:pointermove={(e) => {
		if (!isResizing) return;
		if (activePointerId !== null && e.pointerId !== activePointerId) return;
		resizeSidebarHandler(e.clientX);
	}}
	on:pointerup={resizeEndHandler}
	on:pointercancel={resizeEndHandler}
/>

<MobileSwipePanel
	open={$showSidebar}
	enabled={$mobile}
	width={$sidebarWidth}
	onOpenChange={(open) => showSidebar.set(open)}
	let:visible
	let:progress
	let:panelStyle
	let:backdropStyle
>
	<!-- svelte-ignore a11y-no-static-element-interactions -->

	{#if visible}
		<div
			class=" {$isApp
				? ' ml-[4.5rem] md:ml-0'
				: ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain {progress >
			0.02
				? ''
				: 'pointer-events-none'}"
			style={backdropStyle}
			on:mousedown={() => {
				showSidebar.set(false);
			}}
		></div>
	{/if}

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

	{#if !$mobile && !$showSidebar}
		<div
			class="w-[calc(42px*var(--app-text-scale,1))] shrink-0 py-[calc(0.25rem*var(--app-text-scale,1))] px-[calc(0.25rem*var(--app-text-scale,1))] flex flex-col justify-between text-gray-700 dark:text-gray-300 hover:bg-gray-50/30 dark:hover:bg-gray-800/30 h-full z-10 transition-all border-e-[0.5px] border-gray-50 dark:border-gray-850/30"
			id="sidebar"
			role="navigation"
			aria-label={$i18n.t('Chat history')}
		>
			<button
				class="flex flex-col flex-1 {isWindows ? 'cursor-pointer' : 'cursor-[e-resize]'}"
				on:click={async () => {
					showSidebar.set(!$showSidebar);
				}}
			>
				<div class="pb-1">
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						placement="right"
					>
						<button
							class="flex size-8.5 items-center justify-center transition group {isWindows
								? 'cursor-pointer'
								: 'cursor-[e-resize]'}"
							aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						>
							<div
								class="self-center flex size-[calc(30px*var(--app-text-scale,1))] items-center justify-center rounded-lg transition group-hover:bg-gray-100 dark:group-hover:bg-gray-900"
							>
								<!-- LICENSE covers this Open WebUI sidebar logo.
							Do not alter, remove, obscure, or replace it except as LICENSE permits:
							https://docs.openwebui.com/license. -->
								<img
									src="{WEBUI_BASE_URL}/static/favicon.png"
									class="sidebar-new-chat-icon size-5 rounded-full group-hover:hidden"
									alt=""
								/>

								<Sidebar className="size-4 hidden group-hover:flex" />
							</div>
						</button>
					</Tooltip>
				</div>

				<div class="-gap-0.5">
					<div class="">
						<Tooltip content={$i18n.t('New Chat')} placement="right">
							<a
								class=" cursor-pointer flex size-8 items-center justify-center transition group"
								href="/"
								draggable="false"
								on:click={async (e) => {
									e.stopImmediatePropagation();
									e.preventDefault();

									goto('/');
									newChatHandler();
								}}
								aria-label={$i18n.t('New Chat')}
							>
								<div
									class="self-center flex size-[calc(30px*var(--app-text-scale,1))] items-center justify-center rounded-lg transition group-hover:bg-gray-100 dark:group-hover:bg-gray-900"
								>
									<EditPencilIcon className="size-4" strokeWidth="1.5" />
								</div>
							</a>
						</Tooltip>
					</div>

					<div>
						<Tooltip content={$i18n.t('Search')} placement="right">
							<button
								class=" cursor-pointer flex size-8 items-center justify-center transition group"
								on:click={(e) => {
									e.stopImmediatePropagation();
									e.preventDefault();

									showSearch.set(true);
								}}
								draggable="false"
								aria-label={$i18n.t('Search')}
							>
								<div
									class="self-center flex size-[calc(30px*var(--app-text-scale,1))] items-center justify-center rounded-lg transition group-hover:bg-gray-100 dark:group-hover:bg-gray-900"
								>
									<SearchIcon className="size-4" strokeWidth="1.5" />
								</div>
							</button>
						</Tooltip>
					</div>

					{#each pinnedItems as itemId (itemId)}
						{@const meta = getMenuItemMeta(itemId)}
						{#if meta && isMenuItemVisible(itemId)}
							<div class="">
								<Tooltip content={$i18n.t(meta.label)} placement="right">
									<a
										class=" cursor-pointer flex size-8 items-center justify-center transition group"
										href={meta.href}
										on:click={async (e) => {
											e.stopImmediatePropagation();
											e.preventDefault();
											goto(meta.href);
											itemClickHandler();
										}}
										draggable="false"
										aria-label={$i18n.t(meta.label)}
									>
										<div
											class="self-center flex size-[calc(30px*var(--app-text-scale,1))] items-center justify-center rounded-lg transition {itemId ===
											activeMenuItemId
												? ($settings?.highContrastMode ?? false)
													? 'bg-black/[0.035] dark:bg-white/[0.06]'
													: 'bg-black/[0.035] dark:bg-white/[0.045]'
												: 'group-hover:bg-gray-100 dark:group-hover:bg-gray-900'}"
										>
											{#if itemId === 'notes'}
												<NotesIcon className="size-4" strokeWidth="1.5" />
											{:else if itemId === 'workspace'}
												<WorkspaceIcon className="size-4" strokeWidth="1.5" />
											{:else if itemId === 'automations'}
												<ClockIcon className="size-4" strokeWidth="1.5" />
											{:else if itemId === 'calendar'}
												<CalendarIcon className="size-4" strokeWidth="1.5" />
											{:else if itemId === 'playground'}
												<CodeIcon className="size-4" strokeWidth="1.5" />
											{/if}
										</div>
									</a>
								</Tooltip>
							</div>
						{/if}
					{/each}
				</div>
			</button>

			<div>
				<div>
					<div class=" flex justify-center items-center">
						{#if $user !== undefined && $user !== null}
							<UserMenu role={$user?.role} profile={$config?.features?.enable_user_status ?? true}>
								<button
									type="button"
									class=" cursor-pointer flex size-8.5 items-center justify-center transition group"
									aria-label={$i18n.t('User menu')}
								>
									<div
										class="self-center relative flex size-[calc(30px*var(--app-text-scale,1))] items-center justify-center rounded-lg transition group-hover:bg-gray-100 dark:group-hover:bg-gray-900"
									>
										<img
											src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
											class="size-5.5 object-cover rounded-full"
											alt={$i18n.t('Open User Profile Menu')}
											aria-label={$i18n.t('Open User Profile Menu')}
										/>

										{#if $config?.features?.enable_user_status}
											<div class="absolute -bottom-0.5 -right-0.5">
												<span class="relative flex size-2.5">
													<span
														class="relative inline-flex size-2.5 rounded-full {true
															? 'bg-green-500'
															: 'bg-gray-300 dark:bg-gray-700'} border-2 border-white dark:border-gray-900"
													></span>
												</span>
											</div>
										{/if}
									</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- {$i18n.t('New Folder')} -->
	<!-- {$i18n.t('Pinned')} -->

	{#if visible || !$mobile}
		<div
			bind:this={navElement}
			id={visible ? 'sidebar' : undefined}
			role="navigation"
			aria-label={$i18n.t('Chat history')}
			aria-hidden={!$showSidebar}
			inert={!$showSidebar}
			class="h-screen max-h-[100dvh] min-h-screen select-none {$mobile
				? visible
					? 'bg-gray-50 dark:bg-gray-950 z-50'
					: 'bg-transparent z-0 pointer-events-none'
				: `bg-gray-50 dark:bg-gray-950 z-50 ${$showSidebar ? '' : 'pointer-events-none'}`} {$isApp
				? `ml-[4.5rem] md:ml-0 `
				: $mobile
					? ''
					: ''} shrink-0 text-gray-700 dark:text-gray-300 text-[0.8125rem] leading-5 fixed top-0 left-0 overflow-x-hidden
        "
			style={$mobile
				? panelStyle
				: `width: ${$showSidebar ? 'var(--sidebar-width)' : '0'}; transition: width 250ms cubic-bezier(0.22, 1, 0.36, 1);`}
			data-state={$showSidebar}
		>
			<div
				class=" my-auto flex flex-col justify-between h-screen max-h-[100dvh] w-[var(--sidebar-width)] overflow-x-hidden scrollbar-hidden z-50 border-e border-gray-50 dark:border-gray-850/30"
			>
				<div
					class="sidebar px-1 pt-1.5 pb-1 flex justify-between space-x-1 text-gray-600 dark:text-gray-400 sticky top-0 z-10 -mb-2"
				>
					<a
						class="flex items-center rounded-xl size-8.5 h-full justify-center hover:bg-gray-100 dark:hover:bg-gray-900 transition no-drag-region"
						href="/"
						draggable="false"
						on:click={newChatHandler}
					>
						<!-- LICENSE covers this Open WebUI sidebar logo.
					Do not alter, remove, obscure, or replace it except as LICENSE permits:
					https://docs.openwebui.com/license. -->
						<img
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class="sidebar-new-chat-icon size-5 rounded-full"
							alt=""
						/>
					</a>

					<a href="/" class="flex flex-1 px-0.5" on:click={newChatHandler}>
						<!-- LICENSE covers this Open WebUI sidebar name.
					Do not alter, remove, obscure, or replace it except as LICENSE permits:
					https://docs.openwebui.com/license. -->
						<div
							id="sidebar-webui-name"
							class=" self-center font-normal text-gray-700 dark:text-gray-200"
						>
							{$WEBUI_NAME}
						</div>
					</a>
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						placement="bottom"
					>
						<button
							class="flex size-[1.875rem] justify-center items-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900 transition {isWindows
								? 'cursor-pointer'
								: 'cursor-[w-resize]'}"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
							aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						>
							<div class=" self-center">
								<Sidebar className="size-4" />
							</div>
						</button>
					</Tooltip>

					<div
						class="{scrollTop > 0
							? 'visible'
							: 'invisible'} sidebar-bg-gradient-to-b bg-linear-to-b from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mb-6"
					></div>
				</div>

				<div
					class="relative flex flex-col flex-1 overflow-y-auto scrollbar-hidden space-y-1.5 pt-2.5 pb-2.5"
					on:scroll={(e) => {
						if (e.target.scrollTop === 0) {
							scrollTop = 0;
						} else {
							scrollTop = e.target.scrollTop;
						}
					}}
				>
					<div class="pb-1">
						<div class="px-1 flex justify-center text-gray-700 dark:text-gray-300">
							<a
								id="sidebar-new-chat-button"
								class="group grow flex items-center space-x-2 rounded-xl px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
								href="/"
								draggable="false"
								on:click={newChatHandler}
								aria-label={$i18n.t('New Chat')}
							>
								<div class="self-center flex size-4 shrink-0 items-center justify-center">
									<EditPencilIcon className=" size-4" strokeWidth="1.5" />
								</div>

								<div class="flex flex-1 self-center translate-y-[0.5px]">
									<div class=" self-center text-[0.8125rem] leading-5">{$i18n.t('New Chat')}</div>
								</div>

								<HotkeyHint name="newChat" className=" hover-reveal " />
							</a>
						</div>

						<div class="px-1 flex justify-center text-gray-700 dark:text-gray-300">
							<button
								id="sidebar-search-button"
								class="group grow flex items-center space-x-2 rounded-xl px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
								on:click={() => {
									showSearch.set(true);
								}}
								draggable="false"
								aria-label={$i18n.t('Search')}
							>
								<div class="self-center flex size-4 shrink-0 items-center justify-center">
									<SearchIcon strokeWidth="1.5" className="size-4" />
								</div>

								<div class="flex flex-1 self-center translate-y-[0.5px]">
									<div class=" self-center text-[0.8125rem] leading-5">{$i18n.t('Search')}</div>
								</div>
								<HotkeyHint name="search" className=" hover-reveal " />
							</button>
						</div>

						<div id="pinned-menu-items-list">
							{#each pinnedItems as itemId (itemId)}
								{@const meta = getMenuItemMeta(itemId)}
								{#if meta && isMenuItemVisible(itemId)}
									<div
										class="px-1 flex justify-center text-gray-700 dark:text-gray-300"
										data-id={itemId}
									>
										<a
											id="sidebar-{itemId}-button"
											class="grow flex items-center space-x-2 rounded-xl px-2 py-1.5 transition {itemId ===
											activeMenuItemId
												? ($settings?.highContrastMode ?? false)
													? 'bg-black/[0.035] dark:bg-white/[0.06]'
													: 'bg-black/[0.035] dark:bg-white/[0.045]'
												: 'hover:bg-gray-100 dark:hover:bg-gray-900'}"
											href={meta.href}
											on:click={itemClickHandler}
											draggable="false"
											aria-label={$i18n.t(meta.label)}
										>
											<div class="self-center flex size-4 shrink-0 items-center justify-center">
												{#if itemId === 'notes'}
													<NotesIcon className="size-4" strokeWidth="1.5" />
												{:else if itemId === 'workspace'}
													<WorkspaceIcon className="size-4" strokeWidth="1.5" />
												{:else if itemId === 'automations'}
													<ClockIcon className="size-4" strokeWidth="1.5" />
												{:else if itemId === 'calendar'}
													<CalendarIcon className="size-4" strokeWidth="1.5" />
												{:else if itemId === 'playground'}
													<CodeIcon className="size-4" strokeWidth="1.5" />
												{/if}
											</div>

											<div class="flex self-center translate-y-[0.5px]">
												<div class=" self-center text-[0.8125rem] leading-5">
													{$i18n.t(meta.label)}
												</div>
											</div>
										</a>
									</div>
								{/if}
							{/each}
						</div>
					</div>

					{#if $visiblePinnedModels.length > 0}
						<SidebarSection
							id="sidebar-models"
							bind:open={showPinnedModels}
							name={$i18n.t('Models')}
							dragAndDrop={false}
						>
							<PinnedModelList bind:selectedChatId {shiftKey} />
						</SidebarSection>
					{/if}

					{#if ($config?.features?.enable_notes ?? false) && ($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true)) && $pinnedNotes.length > 0}
						<SidebarSection
							id="sidebar-pinned-notes"
							bind:open={showPinnedNotes}
							name={$i18n.t('Notes')}
							dragAndDrop={false}
							onAdd={async () => {
								const note = await createNoteHandler('New Note');
								if (note) {
									goto(`/notes/${note.id}`);
								}
							}}
							onAddLabel={$i18n.t('New Note')}
						>
							<PinnedNoteList bind:selectedChatId />
						</SidebarSection>
					{/if}

					{#if $config?.features?.enable_channels && ($user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true))}
						<SidebarSection
							id="sidebar-channels"
							bind:open={showChannels}
							name={$i18n.t('Channels')}
							dragAndDrop={false}
							onAdd={$user?.role === 'admin' || ($user?.permissions?.features?.channels ?? true)
								? async () => {
										await tick();

										setTimeout(() => {
											showCreateChannel = true;
										}, 0);
									}
								: null}
							onAddLabel={$i18n.t('Create Channel')}
						>
							{#each $channels as channel, channelIdx (`${channel?.id}`)}
								<ChannelItem
									{channel}
									onUpdate={async () => {
										await initChannels();
									}}
								/>

								{#if channelIdx < $channels.length - 1 && channel.type !== $channels[channelIdx + 1]?.type}<hr
										class=" border-gray-100/40 dark:border-gray-800/10 my-1.5 w-full"
									/>
								{/if}
							{/each}
						</SidebarSection>
					{/if}

					{#if $config?.features?.enable_folders && ($user?.role === 'admin' || ($user?.permissions?.features?.folders ?? true))}
						<SidebarSection
							id="sidebar-folders"
							bind:open={showFolders}
							name={$i18n.t('Folders')}
							onAdd={() => {
								showCreateFolderModal = true;
							}}
							onAddLabel={$i18n.t('New Folder')}
							on:drop={async (e) => {
								const { type, id, item } = e.detail;

								if (type === 'folder') {
									if (folders[id].parent_id === null) {
										return;
									}

									const res = await updateFolderParentIdById(localStorage.token, id, null).catch(
										(error) => {
											toast.error(`${error}`);
											return null;
										}
									);

									if (res) {
										await initFolders();
									}
								}
							}}
						>
							<Folders
								bind:folderRegistry
								{folders}
								{shiftKey}
								onFolderUnreadCounts={applyFolderUnreadCounts}
								onDelete={(folderId) => {
									selectedFolder.set(null);
									initChatList();
								}}
								on:update={() => {
									initChatList();
								}}
								on:import={(e) => {
									const { folderId, items } = e.detail;
									importChatHandler(items, false, folderId);
								}}
								on:change={async () => {
									initChatList();
								}}
							/>
						</SidebarSection>
					{/if}

					<SidebarSection
						id="sidebar-chats"
						name={$i18n.t('Chats')}
						on:change={async (e) => {
							selectedFolder.set(null);
						}}
						on:import={(e) => {
							importChatHandler(e.detail);
						}}
						on:drop={async (e) => {
							const { type, id, item } = e.detail;

							if (type === 'chat') {
								let chat = await getChatById(localStorage.token, id).catch((error) => {
									return null;
								});
								if (!chat && item) {
									if (!canImportChats) {
										toast.error($i18n.t('Access prohibited'));
										return;
									}

									chat = await importChats(localStorage.token, [
										{
											chat: item.chat,
											meta: item?.meta ?? {},
											pinned: false,
											folder_id: null,
											created_at: item?.created_at ?? null,
											updated_at: item?.updated_at ?? null
										}
									]);
								}

								if (chat) {
									console.log(chat);
									if (!chat.folder_id && !chat.pinned) {
										return;
									}

									if (chat.folder_id) {
										const res = await updateChatFolderIdById(
											localStorage.token,
											chat.id,
											null
										).catch((error) => {
											toast.error(`${error}`);
											return null;
										});

										folderRegistry[chat.folder_id]?.setFolderItems();
									}

									if (chat.pinned) {
										const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
									}

									initChatList();
								}
							} else if (type === 'folder') {
								if (folders[id].parent_id === null) {
									return;
								}

								const res = await updateFolderParentIdById(localStorage.token, id, null).catch(
									(error) => {
										toast.error(`${error}`);
										return null;
									}
								);

								if (res) {
									await initFolders();
								}
							}
						}}
					>
						<svelte:fragment slot="action">
							<Dropdown bind:show={showChatsMenu} align="end">
								<Tooltip content={$i18n.t('More')}>
									<button
										type="button"
										class="flex items-center justify-center w-7 h-7 rounded-lg text-gray-300 hover:text-gray-500 dark:text-gray-600 dark:hover:text-gray-400 transition-colors duration-100"
										aria-label={$i18n.t('More')}
									>
										<MoreHorizontalIcon className="size-3.5" strokeWidth="2" />
									</button>
								</Tooltip>

								<div slot="content">
									<DropdownMenu className="min-w-[10.625rem]">
										<button
											class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] select-none cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-900"
											on:click={markAllChatsReadHandler}
										>
											<CheckIcon className="size-3.5" />
											<div class="flex items-center">{$i18n.t('Mark all as read')}</div>
										</button>
									</DropdownMenu>
								</div>
							</Dropdown>
						</svelte:fragment>

						{#if $pinnedChats.length > 0}
							<div class="mb-1">
								<div class="flex flex-col space-y-1 rounded-xl">
									<Folder
										id="sidebar-pinned-chats"
										buttonClassName=" text-gray-500"
										on:import={(e) => {
											importChatHandler(e.detail, true);
										}}
										on:drop={async (e) => {
											const { type, id, item } = e.detail;

											if (type === 'chat') {
												let chat = await getChatById(localStorage.token, id).catch((error) => {
													return null;
												});
												if (!chat && item) {
													if (!canImportChats) {
														toast.error($i18n.t('Access prohibited'));
														return;
													}

													chat = await importChats(localStorage.token, [
														{
															chat: item.chat,
															meta: item?.meta ?? {},
															pinned: false,
															folder_id: null,
															created_at: item?.created_at ?? null,
															updated_at: item?.updated_at ?? null
														}
													]);
												}

												if (chat) {
													console.log(chat);
													if (chat.folder_id) {
														const res = await updateChatFolderIdById(
															localStorage.token,
															chat.id,
															null
														).catch((error) => {
															toast.error(`${error}`);
															return null;
														});
													}

													if (!chat.pinned) {
														const res = await toggleChatPinnedStatusById(
															localStorage.token,
															chat.id
														);
													}

													initChatList();
												}
											}
										}}
										name={$i18n.t('Pinned')}
									>
										<div
											class="ml-3 pl-1 mt-[0.0625rem] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900 text-gray-700 dark:text-gray-300"
										>
											{#each $pinnedChats as chat, idx (`pinned-chat-${chat?.id ?? idx}`)}
												<ChatItem
													className=""
													id={chat.id}
													title={chat.title}
													createdAt={chat.created_at}
													updatedAt={chat.updated_at}
													lastReadAt={chat.last_read_at}
													active={chat.active ?? false}
													{shiftKey}
													selected={selectedChatId === chat.id}
													on:select={() => {
														selectedChatId = chat.id;
													}}
													on:unselect={() => {
														selectedChatId = null;
													}}
													on:change={async () => {
														initChatList();
													}}
													onReadStateChange={applyChatReadState}
													on:tag={(e) => {
														const { type, name } = e.detail;
														tagEventHandler(type, name, chat.id);
													}}
												/>
											{/each}
										</div>
									</Folder>
								</div>
							</div>
						{/if}

						<div class=" flex-1 flex flex-col overflow-y-auto scrollbar-hidden">
							<div class="pt-1.5">
								{#if $chats}
									{#each $chats as chat, idx (`chat-${chat?.id ?? idx}`)}
										{#if idx === 0 || (idx > 0 && chat.time_range !== $chats[idx - 1].time_range)}
											<div
												class="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-normal {idx ===
												0
													? ''
													: 'pt-4'} pb-1"
											>
												{$i18n.t(chat.time_range)}
												<!-- localisation keys for time_range to be recognized from the i18next parser (so they don't get automatically removed):
							{$i18n.t('Today')}
							{$i18n.t('Yesterday')}
							{$i18n.t('Previous 7 days')}
							{$i18n.t('Previous 30 days')}
							{$i18n.t('January')}
							{$i18n.t('February')}
							{$i18n.t('March')}
							{$i18n.t('April')}
							{$i18n.t('May')}
							{$i18n.t('June')}
							{$i18n.t('July')}
							{$i18n.t('August')}
							{$i18n.t('September')}
							{$i18n.t('October')}
							{$i18n.t('November')}
							{$i18n.t('December')}
							-->
											</div>
										{/if}

										<ChatItem
											className=""
											id={chat.id}
											title={chat.title}
											createdAt={chat.created_at}
											updatedAt={chat.updated_at}
											lastReadAt={chat.last_read_at}
											active={chat.active ?? false}
											{shiftKey}
											selected={selectedChatId === chat.id}
											on:select={() => {
												selectedChatId = chat.id;
											}}
											on:unselect={() => {
												selectedChatId = null;
											}}
											on:change={async () => {
												initChatList();
											}}
											onReadStateChange={applyChatReadState}
											on:tag={(e) => {
												const { type, name } = e.detail;
												tagEventHandler(type, name, chat.id);
											}}
										/>
									{/each}

									{#if chatListReady && !allChatsLoaded}
										<Loader
											on:visible={(e) => {
												if (!chatListLoading) {
													loadMoreChats();
												}
											}}
										>
											<div
												class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
											>
												<Spinner className=" size-4" />
												<div class=" ">{$i18n.t('Loading...')}</div>
											</div>
										</Loader>
									{/if}
								{:else}
									<div
										class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
									>
										<Spinner className=" size-4" />
										<div class=" ">{$i18n.t('Loading...')}</div>
									</div>
								{/if}
							</div>
						</div>
					</SidebarSection>
				</div>

				<div class="px-1 pt-1 pb-1.5 sticky bottom-0 z-10 -mt-2 sidebar">
					<div
						class=" sidebar-bg-gradient-to-t bg-linear-to-t from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mt-6"
					></div>
					<div class="flex flex-col">
						{#if $user !== undefined && $user !== null}
							<UserMenu
								role={$user?.role}
								profile={$config?.features?.enable_user_status ?? true}
								className="w-[calc(var(--sidebar-width)-1rem)]"
							>
								<button
									type="button"
									class=" flex items-center rounded-xl py-1.5 px-1.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
									aria-label={$i18n.t('User menu')}
								>
									<div class=" self-center mr-3 relative flex-shrink-0">
										<img
											src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
											class="size-5.5 object-cover rounded-full"
											alt={$i18n.t('Open User Profile Menu')}
											aria-label={$i18n.t('Open User Profile Menu')}
										/>

										{#if $config?.features?.enable_user_status}
											<div class="absolute -bottom-0.5 -right-0.5">
												<span class="relative flex size-2.5">
													<span
														class="relative inline-flex size-2.5 rounded-full {true
															? 'bg-green-500'
															: 'bg-gray-300 dark:bg-gray-700'} border-2 border-white dark:border-gray-900"
													></span>
												</span>
											</div>
										{/if}
									</div>
									<div class=" self-center font-normal truncate">{$user?.name}</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>
		</div>

		{#if !$mobile && visible}
			<div
				class="relative flex items-center justify-center group border-r border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800 transition z-20 bg-transparent p-0 appearance-none"
				id="sidebar-resizer"
				on:pointerdown={resizeStartHandler}
				role="separator"
			>
				<div
					class=" absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"
					style="touch-action: none;"
				></div>
			</div>
		{/if}
	{/if}
</MobileSwipePanel>

<style>
	@media (max-width: 767px) {
		#sidebar {
			will-change: transform;
			touch-action: pan-y;
		}
	}
</style>
