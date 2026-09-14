<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import Sortable from 'sortablejs';

	import { goto } from '$app/navigation';
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
		pinnedNotes,
		scrollPaginationEnabled,
		currentChatPage,
		temporaryChatEnabled,
		socket,
		config,
		isApp,
		models,
		selectedFolder,
		WEBUI_NAME,
		sidebarWidth,
		activeChatIds,
		chatCount,
		showChatLimitModal
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
		deleteAllChats,
		getChatListBySearchText,
		getChatCount
	} from '$lib/apis/chats';
	import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
	import { createNewNote, getPinnedNoteList, toggleNotePinnedStatusById } from '$lib/apis/notes';
	import { updateUserSettings } from '$lib/apis/users';
	import { checkActiveChats } from '$lib/apis/tasks';
	import { createNoteHandler } from '$lib/components/notes/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import ArchivedChatsModal from './ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import TenantSwitcher from './Sidebar/TenantSwitcher.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import RetentionNotice from '../common/RetentionNotice.svelte';
	import ChatLimitModal from '../common/ChatLimitModal.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import Folder from '../common/Folder.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Search from '../icons/Search.svelte';
	import SearchModal from './SearchModal.svelte';
	import FolderModal from './Sidebar/Folders/FolderModal.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import PinnedModelList from './Sidebar/PinnedModelList.svelte';
	import Note from '../icons/Note.svelte';
	import Code from '../icons/Code.svelte';
	import ArrowLeft from '../icons/ArrowLeft.svelte';
	import QuestionMarkCircle from '../icons/QuestionMarkCircle.svelte';
	import HelpCenterModal from './HelpCenterModal.svelte';

	let showHelpCenter = false;
	import { slide } from 'svelte/transition';
	import HotkeyHint from '../common/HotkeyHint.svelte';

	const BREAKPOINT = 768;
	const DEFAULT_PINNED_ITEMS = ['notes', 'workspace'];

	let scrollTop = 0;

	let navElement;
	let shiftKey = false;

	let selectedChatId = null;

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let showCreateFolderModal = false;

	let pinnedModels = [];

	let showPinnedModels = false;
	let showPinnedNotes = false;

	// Live per-user chat count for the retention cap display. Refreshes whenever
	// the chat list store changes (create / delete / load). Published to the `chatCount`
	// store so the cap can also be pre-flighted from the chat view (see Chat.svelte).
	$: if (typeof localStorage !== 'undefined' && localStorage.token && $chats) {
		getChatCount(localStorage.token)
			.then((c) => {
				if (typeof c === 'number') chatCount.set(c);
			})
			.catch(() => {});
	}
	let showFolders = false;

	let folders = {};
	let folderRegistry = {};

	let newFolderId = null;

	$: pinnedItems = $settings?.pinnedMenuItems ?? DEFAULT_PINNED_ITEMS;

	const isMenuItemVisible = (id) => {
		switch (id) {
			case 'notes':
				return (
					($config?.features?.enable_notes ?? false) &&
					($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
				);
			case 'workspace':
				// Sunway: Knowledge is the only workspace section left -- Models, Prompts, Skills are
				// hidden and Tools is deleted -- so this entry is gated on workspace.knowledge alone.
				// Upstream OR-ed all five, which on an existing DB (USER_PERMISSIONS is
				// PersistentConfig, so a stored value beats the env default) could show a user the
				// "Knowledge Base" entry off the back of, say, workspace.prompts, and then bounce
				// them straight back to / from the route guard, because that guard checks
				// workspace.knowledge. A visible link to nowhere.
				return $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge;
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
				// Sunway: Playground deferred, hidden for everyone incl. admins — this also drops
				// any previously pinned sidebar shortcut. Original gate: user.role === 'admin'
				return false;
			default:
				return false;
		}
	};

	const getMenuItemMeta = (id) => {
		const items = {
			notes: { label: 'Notes', href: '/notes', iconType: 'note' },
			// Sunway: reads "Knowledge Space" in the UI, not "Workspace". The key stays
			// 'Workspace' and the three shipped locales translate it (en-GB/ms-MY/zh-CN
			// translation.json), which also renames the user-menu entry and the page title
			// in one place. Knowledge is the only section left in the workspace. "Knowledge
			// Space" is the container of every Knowledge Base; each individual KB keeps the
			// "Knowledge Base" name (see workspace/Knowledge.svelte and its "Knowledge Space" H1).
			workspace: { label: 'Workspace', href: '/workspace', iconType: 'workspace' },
			automations: { label: 'Automations', href: '/automations', iconType: 'automations' },
			calendar: { label: 'Calendar', href: '/calendar', iconType: 'calendar' },
			playground: { label: 'Playground', href: '/playground', iconType: 'playground' }
		};
		return items[id];
	};

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

		// First pass: Initialize all folder entries
		for (const folder of folderList) {
			// Ensure folder is added to folders with its data
			folders[folder.id] = { ...(folders[folder.id] || {}), ...folder };

			if (newFolderId && folder.id === newFolderId) {
				folders[folder.id].new = true;
				newFolderId = null;
			}
		}

		// Second pass: Tie child folders to their parents
		for (const folder of folderList) {
			if (folder.parent_id) {
				// Ensure the parent folder is initialized if it doesn't exist
				if (!folders[folder.parent_id]) {
					folders[folder.parent_id] = {}; // Create a placeholder if not already present
				}

				// Initialize childrenIds array if it doesn't exist and add the current folder id
				folders[folder.parent_id].childrenIds = folders[folder.parent_id].childrenIds
					? [...folders[folder.parent_id].childrenIds, folder.id]
					: [folder.id];

				// Sort the children by updated_at field
				folders[folder.parent_id].childrenIds.sort((a, b) => {
					return folders[b].updated_at - folders[a].updated_at;
				});
			}
		}
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

	const initChatList = async () => {
		// Reset pagination variables
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
				if (
					$config?.features?.enable_notes &&
					($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
				) {
					console.log('Init pinned notes');
					const _pinnedNotes = await getPinnedNoteList(localStorage.token).catch(() => []);
					pinnedNotes.set(_pinnedNotes);
				}
			})(),
			await (async () => {
				console.log('Init chat list');
				const _chats = await getChatList(localStorage.token, $currentChatPage);
				await chats.set(_chats);
			})()
		]);

		// Enable pagination
		scrollPaginationEnabled.set(true);
	};

	const loadMoreChats = async () => {
		chatListLoading = true;

		currentChatPage.set($currentChatPage + 1);

		let newChatList = [];

		newChatList = await getChatList(localStorage.token, $currentChatPage);

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;
		const existingIds = new Set(($chats ?? []).map((c) => c.id));
		const uniqueNewChats = newChatList.filter((c) => !existingIds.has(c.id));
		await chats.set([...($chats ? $chats : []), ...uniqueNewChats]);

		chatListLoading = false;
	};

	// Sunway: importChatHandler() was removed here (hardening plan). It called the deleted
	// POST /chats/import for chats dragged in from another schat instance.

	// Sunway: inputFilesHandler() was removed here (hardening plan). Its only job was to parse a
	// dropped JSON file and feed it to the deleted chat-import endpoint.

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

		// Sunway: the dropped-file branch was removed here (hardening plan) -- dropping a chat
		// export onto the sidebar imported it, bypassing the 30-chat cap. Dragging chats WITHIN
		// the app is unaffected; that path uses getChatById, not import.

		draggedOver = false; // Reset draggedOver status after drop
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

		// Sunway: default the sidebar OPEN on desktop for a user's first-ever visit (no stored
		// preference yet) -- upstream defaults closed here, which meant every new schat user's
		// first impression was a hidden sidebar. Once a user explicitly opens/closes it, that
		// choice is what persists (see the `showSidebar.subscribe` below), so this only changes
		// the very first render, not returning users' preferences.
		showSidebar.set(
			!$mobile
				? localStorage.sidebar === undefined
					? true
					: localStorage.sidebar === 'true'
				: false
		);

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

				if (value) {
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

		const dropZone = document.getElementById('sidebar');
		if (dropZone) {
			dropZone.addEventListener('dragover', onDragOver);
			dropZone.addEventListener('drop', onDrop);
			dropZone.addEventListener('dragleave', onDragLeave);
		}

		const socketInstance = $socket;
		socketInstance?.on('events', chatActiveEventHandler);

		await tick();
		initPinnedMenuSortable();

		return () => {
			unsubscribers.forEach((unsubscriber) => unsubscriber());

			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);

			window.removeEventListener('touchstart', onTouchStart);
			window.removeEventListener('touchend', onTouchEnd);

			window.removeEventListener('focus', onFocus);
			window.removeEventListener('blur', onBlur);

			if (dropZone) {
				dropZone.removeEventListener('dragover', onDragOver);
				dropZone.removeEventListener('drop', onDrop);
				dropZone.removeEventListener('dragleave', onDragLeave);
			}

			socketInstance?.off('events', chatActiveEventHandler);
		};
	});

	// Handler for chat events (defined outside onMount for proper cleanup)
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
		} else if (event.data?.type === 'chat:list') {
			initChatList();
		}
	};

	const newChatHandler = async (e) => {
		// Sunway retention cap: at the limit, block the new chat and open the
		// chat-management modal instead of routing to a fresh chat. The backend
		// enforces the cap independently — this is the UX layer. Applies to all roles.
		const maxChats = $config?.retention?.max_chats_per_user ?? 0;
		if (maxChats > 0 && $chatCount >= maxChats) {
			e?.preventDefault?.();
			showChatLimitModal.set(true);
			return;
		}

		selectedChatId = null;
		selectedFolder.set(null);

		// Sunway: Temporary Chat hidden for the rollout (honor enable_temporary_chat; see CLAUDE.md)
		if (
			($config?.enable_temporary_chat ?? false) &&
			$user?.role !== 'admin' &&
			$user?.permissions?.chat?.temporary_enforced
		) {
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

<ChatLimitModal
	bind:show={$showChatLimitModal}
	maxChats={$config?.retention?.max_chats_per_user ?? 0}
	onUpdate={async () => {
		await initChatList();
		if (localStorage.token) {
			getChatCount(localStorage.token)
				.then((c) => {
					if (typeof c === 'number') chatCount.set(c);
				})
				.catch(() => {});
		}
	}}
/>

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	onUpdate={async () => {
		await initChatList();
	}}
	onDelete={(id) => {
		if ($chatId === id) {
			goto('/');
			chatId.set('');
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

<!-- svelte-ignore a11y-no-static-element-interactions -->

{#if $showSidebar}
	<div
		class=" {$isApp
			? ' ml-[4.5rem] md:ml-0'
			: ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

<SearchModal
	bind:show={$showSearch}
	onClose={() => {
		if ($mobile) {
			showSidebar.set(false);
		}
	}}
/>

<!-- Sunway: Help Center. Rendered once here rather than inside either sidebar variant, because
     both the expanded footer row and the collapsed rail button open the same instance. -->
<HelpCenterModal bind:show={showHelpCenter} />

<button
	id="sidebar-new-chat-button"
	class="hidden"
	on:click={() => {
		goto('/');
		newChatHandler();
	}}
/>

<svelte:window
	on:mousemove={(e) => {
		if (!isResizing) return;
		resizeSidebarHandler(e.clientX);
	}}
	on:mouseup={() => {
		resizeEndHandler();
	}}
/>

{#if !$mobile && !$showSidebar}
	<div
		class=" pt-[7px] pb-2 px-2 flex flex-col justify-between text-black dark:text-white brand-nav-item h-full z-10 transition-all border-e-[0.5px] border-gray-50 dark:border-gray-850/30"
		id="sidebar"
	>
		<button
			class="flex flex-col flex-1 {isWindows ? 'cursor-pointer' : 'cursor-[e-resize]'}"
			on:click={async () => {
				showSidebar.set(!$showSidebar);
			}}
		>
			<div class="pb-1.5">
				<Tooltip
					content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					placement="right"
				>
					<button
						class="flex rounded-xl brand-nav-item transition {isWindows
							? 'cursor-pointer'
							: 'cursor-[e-resize]'}"
						aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					>
						<!-- Sunway: collapsed-rail toggle uses the plain sidebar icon, same as the
						     expanded footer's toggle button below — no brand mark (the red S) here. -->
						<div class=" self-center flex items-center justify-center size-9">
							<Sidebar className="size-5" />
						</div>
					</button>
				</Tooltip>
			</div>

			<!-- Sunway: platform-home link, promoted from the bottom user menu to the top of
			     the sidebar -- primary "go home" navigation belongs beside the app's own
			     identity, not buried in the account menu, which stays reserved for profile/
			     sign-out actions (matching how Google Workspace's app-switcher sits top-level
			     next to the product logo rather than inside the avatar menu). "Landing Page"
			     wording (not a logo) matches the labelled row in the expanded sidebar's New
			     Chat/Search list and sdeck's equivalent -- one term for employees to learn
			     across both apps, and no brand asset means no compliance surface. Left-arrow
			     rather than a Home icon: SCore.ai is the umbrella portal schat is nested
			     inside, so "back to" framing fits better than "teleport home". The labelled
			     SCore.ai entry in the user menu (UserMenu.svelte) is left in place as a
			     secondary path. -->
			<div class="pb-1.5">
				<Tooltip content={$i18n.t('Landing Page')} placement="right">
					<a
						class=" cursor-pointer flex rounded-xl brand-nav-item transition group"
						href={$config?.features?.landing_page_url ?? '/'}
						draggable="false"
						on:click={(e) => {
							e.stopImmediatePropagation();
						}}
						aria-label={$i18n.t('Landing Page')}
					>
						<div class=" self-center flex items-center justify-center size-9">
							<ArrowLeft className="size-4.5" strokeWidth="1.5" />
						</div>
					</a>
				</Tooltip>
			</div>

			<div class="-mt-[0.5px]">
				<div class="">
					<Tooltip content={$i18n.t('New Chat')} placement="right">
						<a
							class=" cursor-pointer flex rounded-xl brand-nav-item transition group"
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
							<div class=" self-center flex items-center justify-center size-9">
								<PencilSquare className="size-4.5" />
							</div>
						</a>
					</Tooltip>
				</div>

				<div>
					<Tooltip content={$i18n.t('Search')} placement="right">
						<button
							class=" cursor-pointer flex rounded-xl brand-nav-item transition group"
							on:click={(e) => {
								e.stopImmediatePropagation();
								e.preventDefault();

								showSearch.set(true);
							}}
							draggable="false"
							aria-label={$i18n.t('Search')}
						>
							<div class=" self-center flex items-center justify-center size-9">
								<Search className="size-4.5" />
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
									class=" cursor-pointer flex rounded-xl brand-nav-item transition group"
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
									<div class=" self-center flex items-center justify-center size-9">
										{#if itemId === 'notes'}
											<Note className="size-4.5" />
										{:else if itemId === 'workspace'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-4.5"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
												/>
											</svg>
										{:else if itemId === 'automations'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-4.5"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
												/>
											</svg>
										{:else if itemId === 'calendar'}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-4.5"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5"
												/>
											</svg>
										{:else if itemId === 'playground'}
											<Code className="size-4.5" />
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
				<!-- Sunway: the collapsed rail's counterpart to the Help row in the expanded footer.
				     Both are needed: the rail is a distinct render, not the same markup at a narrower
				     width, so a row added only to the expanded sidebar disappears entirely for anyone
				     who works with the sidebar collapsed. -->
				<div class=" py-1 flex justify-center items-center">
					<Tooltip content={$i18n.t('Help')} placement="right">
						<button
							type="button"
							class=" cursor-pointer flex rounded-xl brand-nav-item transition group text-gray-600 dark:text-gray-400"
							draggable="false"
							aria-label={$i18n.t('Help')}
							on:click={() => {
								showHelpCenter = true;
							}}
						>
							<div class=" self-center flex items-center justify-center size-9">
								<QuestionMarkCircle className="size-4.5" strokeWidth="1.5" />
							</div>
						</button>
					</Tooltip>
				</div>

				<div class=" py-2 flex justify-center items-center">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							role={$user?.role}
							profile={$config?.features?.enable_user_status ?? false}
							showActiveUsers={false}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<button
								type="button"
								class=" cursor-pointer flex rounded-xl brand-nav-item transition group"
								aria-label={$i18n.t('User menu')}
							>
								<div class="self-center relative">
									<img
										src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
										class=" size-7 object-cover rounded-full"
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

{#if $showSidebar}
	<div
		bind:this={navElement}
		id="sidebar"
		class="h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
			? `${$mobile ? 'bg-gray-50 dark:bg-gray-950' : 'bg-gray-50/70 dark:bg-gray-950/70'} z-50`
			: ' bg-transparent z-0 '} {$isApp
			? `ml-[4.5rem] md:ml-0 `
			: ' transition-all duration-300 '} shrink-0 text-gray-900 dark:text-gray-200 text-sm fixed top-0 left-0 overflow-x-hidden
        "
		transition:slide={{ duration: 250, axis: 'x' }}
		data-state={$showSidebar}
	>
		<div
			class=" my-auto flex flex-col justify-between h-screen max-h-[100dvh] w-[var(--sidebar-width)] overflow-x-hidden scrollbar-hidden z-50 {$showSidebar
				? ''
				: 'invisible'}"
		>
			<div
				class="sidebar px-[0.5625rem] pt-2 pb-1.5 flex justify-between space-x-1 text-gray-600 dark:text-gray-400 sticky top-0 z-10 -mb-3"
			>
				<a href="/" class="flex flex-1 px-0.5" on:click={newChatHandler}>
					<div
						id="sidebar-webui-name"
						class=" self-center font-medium text-gray-850 dark:text-white font-primary"
					>
						<img
							src="{WEBUI_BASE_URL}/static/schat-wordmark.svg"
							class="h-6 w-auto dark:hidden"
							alt={$WEBUI_NAME}
						/><img
							src="{WEBUI_BASE_URL}/static/schat-wordmark-dark.svg"
							class="h-6 w-auto hidden dark:block"
							alt={$WEBUI_NAME}
						/>
					</div>
				</a>
				<Tooltip
					content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					placement="bottom"
				>
					<button
						class="flex rounded-xl size-8.5 justify-center items-center brand-nav-item transition {isWindows
							? 'cursor-pointer'
							: 'cursor-[w-resize]'}"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
					>
						<div class=" self-center p-1.5">
							<Sidebar />
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
				class="relative flex flex-col flex-1 overflow-y-auto scrollbar-hidden pt-3 pb-3"
				on:scroll={(e) => {
					if (e.target.scrollTop === 0) {
						scrollTop = 0;
					} else {
						scrollTop = e.target.scrollTop;
					}
				}}
			>
				<div class="pb-1.5">
					<!-- Multi-tenancy: workspace switcher (renders only when tenants are loaded) -->
					<TenantSwitcher />

					<!-- Sunway: platform-home link, labelled to match New Chat/Search below rather
					     than living icon-only in the tight top identity row (see the collapsed
					     rail's copy above for the full "why here, why this wording" rationale).
					     Reuses the exact New Chat/Search row markup so it reads as part of the same
					     list, not a visually distinct nav element. -->
					<div class="px-[0.4375rem] flex justify-center text-gray-800 dark:text-gray-200">
						<a
							id="sidebar-landing-page-button"
							class="group grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 brand-nav-item transition outline-none"
							href={$config?.features?.landing_page_url ?? '/'}
							draggable="false"
							aria-label={$i18n.t('Landing Page')}
						>
							<div class="self-center">
								<ArrowLeft className=" size-4.5" strokeWidth="2" />
							</div>

							<div class="flex flex-1 self-center translate-y-[0.5px]">
								<div class=" self-center text-sm font-primary">{$i18n.t('Landing Page')}</div>
							</div>
						</a>
					</div>

					<div class="px-[0.4375rem] flex justify-center text-gray-800 dark:text-gray-200">
						<a
							id="sidebar-new-chat-button"
							class="group grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 brand-nav-item transition outline-none"
							href="/"
							draggable="false"
							on:click={newChatHandler}
							aria-label={$i18n.t('New Chat')}
						>
							<div class="self-center">
								<PencilSquare className=" size-4.5" strokeWidth="2" />
							</div>

							<div class="flex flex-1 self-center translate-y-[0.5px]">
								<div class=" self-center text-sm font-primary">{$i18n.t('New Chat')}</div>
							</div>

							<HotkeyHint name="newChat" className=" group-hover:visible invisible" />
						</a>
					</div>

					<div class="px-[0.4375rem] flex justify-center text-gray-800 dark:text-gray-200">
						<button
							id="sidebar-search-button"
							class="group grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 brand-nav-item transition outline-none"
							on:click={() => {
								showSearch.set(true);
							}}
							draggable="false"
							aria-label={$i18n.t('Search')}
						>
							<div class="self-center">
								<Search strokeWidth="2" className="size-4.5" />
							</div>

							<div class="flex flex-1 self-center translate-y-[0.5px]">
								<div class=" self-center text-sm font-primary">{$i18n.t('Search')}</div>
							</div>
							<HotkeyHint name="search" className=" group-hover:visible invisible" />
						</button>
					</div>

					<div id="pinned-menu-items-list">
						{#each pinnedItems as itemId (itemId)}
							{@const meta = getMenuItemMeta(itemId)}
							{#if meta && isMenuItemVisible(itemId)}
								<div
									class="px-[0.4375rem] flex justify-center text-gray-800 dark:text-gray-200"
									data-id={itemId}
								>
									<a
										id="sidebar-{itemId}-button"
										class="grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 brand-nav-item transition"
										href={meta.href}
										on:click={itemClickHandler}
										draggable="false"
										aria-label={$i18n.t(meta.label)}
									>
										<div class="self-center">
											{#if itemId === 'notes'}
												<Note className="size-4.5" strokeWidth="2" />
											{:else if itemId === 'workspace'}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
													stroke="currentColor"
													class="size-4.5"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
													/>
												</svg>
											{:else if itemId === 'automations'}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
													stroke="currentColor"
													class="size-4.5"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
													/>
												</svg>
											{:else if itemId === 'calendar'}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
													stroke="currentColor"
													class="size-4.5"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5"
													/>
												</svg>
											{:else if itemId === 'playground'}
												<Code className="size-4.5" strokeWidth="2" />
											{/if}
										</div>

										<div class="flex self-center translate-y-[0.5px]">
											<div class=" self-center text-sm font-primary">{$i18n.t(meta.label)}</div>
										</div>
									</a>
								</div>
							{/if}
						{/each}
					</div>
				</div>

				{#if ($models ?? []).length > 0 && (($settings?.pinnedModels ?? []).length > 0 || $config?.default_pinned_models)}
					<Folder
						id="sidebar-models"
						bind:open={showPinnedModels}
						className="px-2 mt-0.5"
						name={$i18n.t('Models')}
						chevron={false}
						dragAndDrop={false}
					>
						<PinnedModelList bind:selectedChatId {shiftKey} />
					</Folder>
				{/if}

				{#if ($config?.features?.enable_notes ?? false) && ($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true)) && $pinnedNotes.length > 0}
					<Folder
						id="sidebar-pinned-notes"
						bind:open={showPinnedNotes}
						className="px-2 mt-0.5"
						name={$i18n.t('Notes')}
						chevron={false}
						dragAndDrop={false}
						onAdd={async () => {
							const note = await createNoteHandler('New Note');
							if (note) {
								goto(`/notes/${note.id}`);
							}
						}}
						onAddLabel={$i18n.t('New Note')}
					>
						<div class="mt-0.5 pb-1.5">
							{#each $pinnedNotes as note (note.id)}
								<a
									class="w-full flex items-center gap-2.5 rounded-xl px-2.5 py-1.5 brand-nav-item transition group text-sm"
									href={`/notes/${note.id}`}
									on:click={() => {
										itemClickHandler();
									}}
									draggable="false"
								>
									<div class="self-center">
										<Note className="size-4" strokeWidth="2" />
									</div>
									<div class="flex-1 text-ellipsis line-clamp-1">
										{note.title}
									</div>
									<button
										class="invisible group-hover:visible self-center p-0.5 brand-nav-item rounded-lg transition"
										on:click|preventDefault|stopPropagation={async () => {
											await toggleNotePinnedStatusById(localStorage.token, note.id);
											const _pinnedNotes = await getPinnedNoteList(localStorage.token).catch(
												() => []
											);
											pinnedNotes.set(_pinnedNotes);
										}}
										aria-label={$i18n.t('Unpin')}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="2"
											stroke="currentColor"
											class="size-3.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M6 18 18 6M6 6l12 12"
											/>
										</svg>
									</button>
								</a>
							{/each}
						</div>
					</Folder>
				{/if}

				<!-- Sunway: the Channels sidebar section was deleted here (hardening plan Item 6). -->

				{#if $config?.features?.enable_folders && ($user?.role === 'admin' || ($user?.permissions?.features?.folders ?? true))}
					<Folder
						id="sidebar-folders"
						bind:open={showFolders}
						className="px-2 mt-0.5"
						name={$i18n.t('Folders')}
						chevron={false}
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
							onDelete={(folderId) => {
								selectedFolder.set(null);
								initChatList();
							}}
							on:update={() => {
								initChatList();
							}}
							on:change={async () => {
								initChatList();
							}}
						/>
					</Folder>
				{/if}

				{#if ($config?.retention?.chat_retention_days ?? 0) > 0 || ($config?.retention?.max_chats_per_user ?? 0) > 0}
					<div class="px-2 mt-0.5 space-y-1">
						<RetentionNotice variant="banner" />
						{#if ($config?.retention?.max_chats_per_user ?? 0) > 0}
							<div class="flex justify-end pr-1">
								<RetentionNotice variant="counter" chatCount={$chatCount} />
							</div>
						{/if}
					</div>
				{/if}

				<Folder
					id="sidebar-chats"
					className="px-2 mt-0.5"
					name={$i18n.t('Chats')}
					chevron={false}
					on:change={async (e) => {
						selectedFolder.set(null);
					}}
					on:drop={async (e) => {
						const { type, id, item } = e.detail;

						if (type === 'chat') {
							let chat = await getChatById(localStorage.token, id).catch((error) => {
								return null;
							});
							// Sunway: the cross-instance import fallback was removed here (hardening plan).

							if (chat) {
								console.log(chat);
								if (chat.folder_id) {
									const res = await updateChatFolderIdById(localStorage.token, chat.id, null).catch(
										(error) => {
											toast.error(`${error}`);
											return null;
										}
									);

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
					{#if $pinnedChats.length > 0}
						<div class="mb-1">
							<div class="flex flex-col space-y-1 rounded-xl">
								<Folder
									id="sidebar-pinned-chats"
									buttonClassName=" text-gray-500"
									on:drop={async (e) => {
										const { type, id, item } = e.detail;

										if (type === 'chat') {
											let chat = await getChatById(localStorage.token, id).catch((error) => {
												return null;
											});
											// Sunway: the cross-instance import fallback was removed here (hardening plan).

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
													const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
												}

												initChatList();
											}
										}
									}}
									name={$i18n.t('Pinned')}
								>
									<div
										class="ml-3 pl-1 mt-[1px] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900 text-gray-900 dark:text-gray-200"
									>
										{#each $pinnedChats as chat, idx (`pinned-chat-${chat?.id ?? idx}`)}
											<ChatItem
												className=""
												id={chat.id}
												title={chat.title}
												createdAt={chat.created_at}
												updatedAt={chat.updated_at}
												lastReadAt={chat.last_read_at}
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
											class="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-medium {idx ===
											0
												? ''
												: 'pt-5'} pb-1.5"
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
										on:tag={(e) => {
											const { type, name } = e.detail;
											tagEventHandler(type, name, chat.id);
										}}
									/>
								{/each}

								{#if $scrollPaginationEnabled && !allChatsLoaded}
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
				</Folder>
			</div>

			<div class="px-1.5 pt-1.5 pb-2 sticky bottom-0 z-10 -mt-3 sidebar">
				<div
					class=" sidebar-bg-gradient-to-t bg-linear-to-t from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mt-6"
				></div>
				<div class="flex flex-col font-primary">
					<!-- Sunway: Help Center entry point, modelled on sdeck's. Deliberately a sibling of
					     the profile row inside the STICKY footer, not an item in the chat list. The list
					     above scrolls and is capped at MAX_CHATS_PER_USER, so anything placed in it would
					     compete with the user's own chats and scroll out of reach; here it is one fixed
					     row that is always on screen.

					     The feedback form lives in the modal's footer rather than being linked directly
					     from here: a bare "Feedback" link invites reports of things that are documented
					     answers, so the FAQ goes first and the form is what you reach past it. -->
					<button
						type="button"
						class="flex items-center rounded-2xl py-2 px-1.5 w-full brand-nav-item transition text-gray-600 dark:text-gray-400"
						aria-label={$i18n.t('Help')}
						on:click={() => {
							showHelpCenter = true;
						}}
					>
						<div class="self-center mr-3 flex-shrink-0 size-7 flex items-center justify-center">
							<QuestionMarkCircle className="size-5" strokeWidth="1.5" />
						</div>
						<div class="self-center text-sm truncate">{$i18n.t('Help')}</div>
					</button>

					{#if $user !== undefined && $user !== null}
						<UserMenu
							role={$user?.role}
							profile={$config?.features?.enable_user_status ?? false}
							showActiveUsers={false}
							className="w-[calc(var(--sidebar-width)-1rem)]"
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<button
								type="button"
								class=" flex items-center rounded-2xl py-2 px-1.5 w-full brand-nav-item transition"
								aria-label={$i18n.t('User menu')}
							>
								<div class=" self-center mr-3 relative flex-shrink-0">
									<img
										src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
										class=" size-7 object-cover rounded-full"
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
								<div class=" self-center font-medium truncate">{$user?.name}</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if !$mobile}
		<div
			class="relative flex items-center justify-center group border-l border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800 transition z-20"
			id="sidebar-resizer"
			on:mousedown={resizeStartHandler}
			role="separator"
		>
			<div
				class=" absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"
			/>
		</div>
	{/if}
{/if}
