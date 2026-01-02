<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';

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
		isInstructor,
		selectedTextbookSection
	} from '$lib/stores';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	import {
		getChatList,
		getAllTags,
		getPinnedChatList,
		toggleChatPinnedStatusById,
		getChatById,
		updateChatById,
		updateChatFolderIdById,
		importChats
	} from '$lib/apis/chats';
	import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL, SIDEBAR_WIDTH } from '$lib/constants';

	import ArchivedChatsModal from './ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import Folder from '../common/Folder.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import HYULogo36 from '../icons/HYULogo36.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Search from '../icons/Search.svelte';
	import DashboardToggleSwitch from '../dashboard/DashboardToggleSwitch.svelte';
	import SearchModal from './SearchModal.svelte';
	import FolderModal from './Sidebar/Folders/FolderModal.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import PinnedModelList from './Sidebar/PinnedModelList.svelte';
	import Note from '../icons/Note.svelte';
	import { slide, fly } from 'svelte/transition';
	import HotkeyHint from '../common/HotkeyHint.svelte';
	import Bookmark from '../icons/Bookmark.svelte';
	import BookmarkSolid from '../icons/BookmarkSolid.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import TextbookInfo from './Sidebar/TextbookInfo.svelte';

	const BREAKPOINT = 768;

	let scrollTop = 0;

	let navElement;
	let shiftKey = false;

	let selectedChatId = null;
	let showCreateChannel = false;

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let showCreateFolderModal = false;

	// History section states
	let showHistorySearch = false;
	let historySearchQuery = '';
	let showBookmarkedOnly = false;
	let historyExpanded = true;

	// Dummy bookmark data (chat ID -> bookmarked status)
	let chatBookmarks = {};

	// Textbook section states
	let currentChapterId = '';
	let currentTextbookTitle = '';
	let currentTextbookSubtitle = '';

	// Tab states
	let activeTab = 'textbook'; // 'textbook' or 'history'

	let folders = {};
	let folderRegistry = {};

	let newFolderId = null;

	$: if ($selectedFolder) {
		initFolders();
	}

	const initFolders = async () => {
		const folderList = await getFolders(localStorage.token).catch((error) => {
			toast.error(`${error}`);
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

	const createFolder = async ({ name, data }) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Folder name cannot be empty.'));
			return;
		}

		const rootFolders = Object.values(folders).filter((folder) => folder.parent_id === null);
		if (rootFolders.find((folder) => folder.name.toLowerCase() === name.toLowerCase())) {
			// If a folder with the same name already exists, append a number to the name
			let i = 1;
			while (
				rootFolders.find((folder) => folder.name.toLowerCase() === `${name} ${i}`.toLowerCase())
			) {
				i++;
			}

			name = `${name} ${i}`;
		}

		// Add a dummy folder to the list to show the user that the folder is being created
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
			// newFolderId = res.id;
			await initFolders();
		}
	};

	const initChannels = async () => {
		await channels.set(await getChannels(localStorage.token));
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

	let touchstart;
	let touchend;

	function checkDirection() {
		const screenWidth = window.innerWidth;
		const swipeDistance = Math.abs(touchend.screenX - touchstart.screenX);

		// 오른쪽 가장자리에서 시작하는 스와이프 (열기)
		if (touchstart.clientX > screenWidth - 40 && swipeDistance >= screenWidth / 8) {
			if (touchend.screenX < touchstart.screenX) {
				showSidebar.set(true); // 왼쪽으로 스와이프하면 열기
			}
		}

		// 사이드바가 열려있을 때 오른쪽으로 스와이프하면 닫기
		if ($showSidebar && swipeDistance >= screenWidth / 8) {
			if (touchend.screenX > touchstart.screenX) {
				showSidebar.set(false);
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

	let unsubscribers = [];
	onMount(async () => {
		await showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);

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
					await initChannels();
					await initChatList();
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

		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

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

		const dropZone = document.getElementById('sidebar');

		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});

	const newChatHandler = async () => {
		selectedChatId = null;
		selectedFolder.set(null);
		selectedTextbookSection.set(null);  // 새 채팅 시 챕터 선택 초기화

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

	// Dummy bookmark toggle function
	const toggleChatBookmark = (chatId) => {
		chatBookmarks[chatId] = !chatBookmarks[chatId];
		chatBookmarks = { ...chatBookmarks };
	};

	// Filter chats based on search and bookmark filter
	$: filteredChats =
		$chats?.filter((chat) => {
			const matchesSearch = historySearchQuery
				? chat.title?.toLowerCase().includes(historySearchQuery.toLowerCase())
				: true;
			const matchesBookmark = showBookmarkedOnly ? chatBookmarks[chat.id] : true;
			return matchesSearch && matchesBookmark;
		}) || [];

	// Handle textbook subsection selection
	const handleSubsectionSelect = async (event) => {
		currentChapterId = event.detail.id;
		currentTextbookTitle = event.detail.title;
		currentTextbookSubtitle = event.detail.subtitle;

		// Update store for ChatToolbar
		selectedTextbookSection.set({
			id: event.detail.id,
			title: event.detail.title,
			subtitle: event.detail.subtitle
		});

		// Update current chat with selected textbook section
		if ($chatId) {
			try {
				await updateChatById(localStorage.token, $chatId, {
					chapter_id: event.detail.id,
					chapter: event.detail.title,
					subtitle: event.detail.subtitle
				});
				console.log('Updated chat with subsection:', event.detail);
			} catch (error) {
				toast.error('Failed to update chat with textbook section');
				console.error('Error updating chat:', error);
			}
		}
	};

	// Handle textbook section clear (when clicking textbook card)
	const handleSectionClear = async () => {
		currentChapterId = '';
		currentTextbookTitle = '';
		currentTextbookSubtitle = '';

		// Clear store for ChatToolbar
		selectedTextbookSection.set(null);

		// Update current chat to clear chapter info
		if ($chatId) {
			try {
				await updateChatById(localStorage.token, $chatId, {
					chapter_id: null,
					chapter: null,
					subtitle: null
				});
				console.log('Cleared chat chapter info');
			} catch (error) {
				toast.error('Failed to clear chat chapter info');
				console.error('Error clearing chat chapter:', error);
			}
		}
	};
</script>

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	onUpdate={async () => {
		await initChatList();
	}}
/>

<ChannelModal
	bind:show={showCreateChannel}
	onSubmit={async ({ name, access_control }) => {
		name = name?.trim();
		if (!name) {
			toast.error($i18n.t('Channel name cannot be empty.'));
			return;
		}

		const res = await createNewChannel(localStorage.token, {
			name: name,
			access_control: access_control
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			$socket.emit('join-channels', { auth: { token: $user?.token } });
			await initChannels();
			showCreateChannel = false;
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

<!-- Mobile Top Nav Bar (when sidebar closed) -->
{#if $mobile && !$showSidebar}
	<div
		class="fixed top-0 left-0 right-0 h-[60px] z-40 flex items-center justify-between px-4
			bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl
			border-b border-gray-200/50 dark:border-gray-800/50"
	>
		<!-- Logo + Title -->
		<a
			href="/"
			class="flex items-center gap-2"
			on:click={newChatHandler}
		>
			<HYULogo36 />
			<span class="text-sm font-medium text-gray-900 dark:text-white font-primary">HYU AI Tutoring Assistant</span>
		</a>
		<!-- Menu Button -->
		<button
			on:click={() => showSidebar.set(true)}
			class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-700 dark:text-gray-300"
			aria-label="Open menu"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="1.5"
				stroke="currentColor"
				class="size-6"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
			</svg>
		</button>
	</div>
{/if}

{#if $showSidebar}
	<div
		class=" {$isApp
			? ' ml-[4.5rem] md:ml-0'
			: ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-white/30 dark:bg-gray-900/30 backdrop-blur-md w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
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
		class="px-4 pt-4 pb-2 flex flex-col justify-between bg-gray-50/70 text-gray-900 dark:text-gray-50 h-full z-10 transition-all dark:bg-gray-900/50"
		id="sidebar"
	>
		<!-- Top: HYU Logo -->
		<div>
			<a
				class="flex items-center rounded-xl size-8.5 h-full justify-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition"
				href="https://hanyang.ac.kr/"
				draggable="false"
				on:click={newChatHandler}
			>
				<HYULogo36 />
			</a>
		</div>

		<!-- Bottom: Sidebar Toggle + User Profile -->
		<div class="flex flex-col gap-2">
			<!-- Sidebar Open Button -->
			<Tooltip
				content={$i18n.t('Open Sidebar')}
				placement="right"
			>
				<button
					class="flex rounded-xl size-8.5 justify-center items-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition {isWindows
						? 'cursor-pointer'
						: 'cursor-[e-resize]'} text-gray-900 dark:text-gray-50"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label={$i18n.t('Open Sidebar')}
				>
					<div class="self-center p-1.5">
						<Sidebar />
					</div>
				</button>
			</Tooltip>

			<!-- User Profile (Collapsed Sidebar - Figma: 40x40 frame, 36x36 image) -->
			{#if $user !== undefined && $user !== null}
				<UserMenu
					role={$user?.role}
					on:show={(e) => {
						if (e.detail === 'archived-chat') {
							showArchivedChats.set(true);
						}
					}}
				>
					<div
						class="cursor-pointer flex rounded-xl hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition group mb-1"
					>
						<div class="self-center flex items-center justify-center size-10">
							<img
								src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
								class="size-9 object-cover rounded-full bg-primary-500"
								alt={$i18n.t('Open User Profile Menu')}
								aria-label={$i18n.t('Open User Profile Menu')}
							/>
						</div>
					</div>
				</UserMenu>
			{/if}
		</div>
	</div>
{/if}

{#if $showSidebar}
	<div
		bind:this={navElement}
		id="sidebar"
		class="h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
			? `${$mobile ? 'bg-gray-50 dark:bg-gray-950' : 'bg-gray-50 dark:bg-gray-950' } z-50`
			: ' bg-transparent z-0 '} {$isApp
			? `ml-[4.5rem] md:ml-0 `
			: ' transition-all duration-300 '} shrink-0 text-gray-50 text-sm fixed top-0 {$mobile ? 'right-0' : 'left-0'} overflow-x-hidden
        "
		transition:fly={{ duration: 250, x: $mobile ? SIDEBAR_WIDTH : -SIDEBAR_WIDTH }}
		data-state={$showSidebar}
	>
		<div
			class=" my-auto flex flex-col justify-between h-screen max-h-[100dvh] overflow-x-hidden scrollbar-none bg-gray-50 dark:bg-gray-950 z-50 {$showSidebar
				? ''
				: 'invisible'}"
			style="width: {SIDEBAR_WIDTH}px;"
		>
			<div
				class="sidebar px-4 pt-4 pb-1.5 flex flex-col gap-3 text-gray-600 dark:text-gray-400 sticky top-0 z-10"
			>
				<!-- Header Row -->
				<div class="flex items-center space-x-1">
					<a
						class="flex items-center rounded-xl size-8.5 h-full justify-center hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition no-drag-region"
						href="https://hanyang.ac.kr/"
						draggable="false"
					>
						<HYULogo36 />
					</a>

					<div
						id="sidebar-webui-name"
						class="flex flex-1 px-1.5 self-center font-medium text-gray-900 dark:text-white font-primary"
					>
						HYU AI Tutoring Assistant
					</div>
				</div>

				<!-- New Chat Button -->
				<a
					href="/"
					class="flex flex-row justify-center items-center py-1 pl-5 pr-7 gap-2
						w-full h-[35px] bg-[#076EF4] rounded-full
						hover:bg-[#0558c7] transition-colors duration-200 no-drag-region"
					draggable="false"
					on:click={newChatHandler}
				>
					<svg
						width="24"
						height="24"
						viewBox="0 0 24 24"
						fill="none"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							d="M12 5V19M5 12H19"
							stroke="#FDFEFE"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						/>
					</svg>
					<span class="text-body-3 text-[#FDFEFE]">
						새 채팅
					</span>
				</a>

				<div
					class="{scrollTop > 0
						? 'visible'
						: 'invisible'} sidebar-bg-gradient-to-b bg-linear-to-b from-gray-50 dark:from-gray-950 to-transparent from-50% pointer-events-none absolute inset-0 -z-10 -mb-6"
				></div>
			</div>

			<div
				class="relative flex flex-col flex-1 overflow-y-auto scrollbar-none pt-3 pb-3"
				on:scroll={(e) => {
					if (e.target.scrollTop === 0) {
						scrollTop = 0;
					} else {
						scrollTop = e.target.scrollTop;
					}
				}}
			>
				<!-- <div class="pb-1.5">
					<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
						<a
							id="sidebar-new-chat-button"
							class="group grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
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

					<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
						<button
							id="sidebar-search-button"
							class="group grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
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

					{#if ($config?.features?.enable_notes ?? false) && ($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))}
						<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
							<a
								id="sidebar-notes-button"
								class="grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
								href="/notes"
								on:click={itemClickHandler}
								draggable="false"
								aria-label={$i18n.t('Notes')}
							>
								<div class="self-center">
									<Note className="size-4.5" strokeWidth="2" />
								</div>

								<div class="flex self-center translate-y-[0.5px]">
									<div class=" self-center text-sm font-primary">{$i18n.t('Notes')}</div>
								</div>
							</a>
						</div>
					{/if}

					
				</div> -->
				<!-- {#if $user?.role === 'admin' || $user?.permissions?.workspace?.models || $user?.permissions?.workspace?.knowledge || $user?.permissions?.workspace?.prompts || $user?.permissions?.workspace?.tools}
						<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200 ">
							<a
								id="sidebar-workspace-button"
								class="grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition"
								href="/workspace"
								on:click={itemClickHandler}
								draggable="false"
								aria-label={$i18n.t('Workspace')}
							>
								<div class="self-center ">
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
								</div>

								<div class="flex self-center translate-y-[0.5px]">
									<div class=" self-center text-sm font-primary">{$i18n.t('Workspace')}</div>
								</div>
							</a>
						</div>
					{/if} -->

				<!-- {#if ($models ?? []).length > 0 && (($settings?.pinnedModels ?? []).length > 0 || $config?.default_pinned_models)}
					<Folder
						id="sidebar-models"
						className="px-2 mt-0.5"
						name={$i18n.t('Models')}
						chevron={false}
						dragAndDrop={false}
					>
						<PinnedModelList bind:selectedChatId {shiftKey} />
					</Folder>
				{/if} -->

				<!-- {#if $config?.features?.enable_channels && ($user?.role === 'admin' || $channels.length > 0)}
					<Folder
						id="sidebar-channels"
						className="px-2 mt-0.5"
						name={$i18n.t('Channels')}
						chevron={false}
						dragAndDrop={false}
						onAdd={async () => {
							if ($user?.role === 'admin') {
								await tick();

								setTimeout(() => {
									showCreateChannel = true;
								}, 0);
							}
						}}
						onAddLabel={$i18n.t('Create Channel')}
					>
						{#each $channels as channel}
							<ChannelItem
								{channel}
								onUpdate={async () => {
									await initChannels();
								}}
							/>
						{/each}
					</Folder>
				{/if}

				{#if folders}
					<Folder
						id="sidebar-folders"
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
							on:import={(e) => {
								const { folderId, items } = e.detail;
								importChatHandler(items, false, folderId);
							}}
							on:change={async () => {
								initChatList();
							}}
						/>
					</Folder>
				{/if} -->

				<!-- Separator Line -->
				<div class="px-5">
					<div class="w-full h-0 border-t border-gray-200/20 dark:border-gray-600/30"></div>
				</div>

				<!-- Tab Navigation -->
				<div class="px-5 mt-5">
					<div class="flex flex-row justify-center items-center w-full h-7
						shadow-[inset_2px_2px_10px_rgba(255,255,255,0.05),inset_2px_2px_16px_rgba(206,212,229,0.12)]
						drop-shadow-[4px_4px_20px_rgba(0,0,0,0.1)]
						backdrop-blur-sm
						rounded-full">
						<!-- Textbook Tab -->
						<button
							class="flex flex-row justify-center items-center py-2 px-3 gap-1 flex-1 h-9 transition
								{activeTab === 'textbook'
									? 'text-gray-950 dark:text-white'
									: 'text-gray-500 dark:text-gray-600'}"
							on:click={() => {
								activeTab = 'textbook';
							}}
							aria-label="교재 정보"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
								/>
							</svg>
							<span class="text-body-4">교재 정보</span>
						</button>

						<!-- History Tab -->
						<button
							class="flex flex-row justify-center items-center py-2 px-3 gap-1 flex-1 h-9 transition
								{activeTab === 'history'
									? 'text-gray-950 dark:text-white'
									: 'text-gray-500 dark:text-gray-600'}"
							on:click={() => {
								activeTab = 'history';
							}}
							aria-label="히스토리"
						>
							<svg
								width="20"
								height="20"
								viewBox="0 0 20 20"
								fill="none"
								xmlns="http://www.w3.org/2000/svg"
								class="size-5"
							>
								<mask
									id="mask0_191_446_tab"
									style="mask-type:alpha"
									maskUnits="userSpaceOnUse"
									x="0"
									y="0"
									width="20"
									height="20"
								>
									<rect width="20" height="20" fill="#D9D9D9" />
								</mask>
								<g mask="url(#mask0_191_446_tab)">
									<path
										d="M5 15L3.27333 16.7267C3.03556 16.9644 2.76389 17.018 2.45833 16.8873C2.15278 16.7567 2 16.5235 2 16.1875V3.5C2 3.0875 2.14688 2.73438 2.44063 2.44063C2.73438 2.14688 3.0875 2 3.5 2H16.5C16.9125 2 17.2656 2.14688 17.5594 2.44063C17.8531 2.73438 18 3.0875 18 3.5V13.5C18 13.9125 17.8531 14.2656 17.5594 14.5594C17.2656 14.8531 16.9125 15 16.5 15H5ZM4.375 13.5H16.5V3.5H3.5V14.375L4.375 13.5ZM5.75 12H11.25C11.4625 12 11.6406 11.9285 11.7844 11.7856C11.9281 11.6427 12 11.4656 12 11.2544C12 11.0431 11.9281 10.8646 11.7844 10.7188C11.6406 10.5729 11.4625 10.5 11.25 10.5H5.75C5.5375 10.5 5.35938 10.5715 5.21563 10.7144C5.07188 10.8573 5 11.0344 5 11.2456C5 11.4569 5.07188 11.6354 5.21563 11.7812C5.35938 11.9271 5.5375 12 5.75 12ZM5.75 9.25H14.25C14.4625 9.25 14.6406 9.17854 14.7844 9.03563C14.9281 8.89271 15 8.71563 15 8.50438C15 8.29313 14.9281 8.11458 14.7844 7.96875C14.6406 7.82292 14.4625 7.75 14.25 7.75H5.75C5.5375 7.75 5.35938 7.82146 5.21563 7.96437C5.07188 8.10729 5 8.28437 5 8.49562C5 8.70687 5.07188 8.88542 5.21563 9.03125C5.35938 9.17708 5.5375 9.25 5.75 9.25ZM5.75 6.5H14.25C14.4625 6.5 14.6406 6.42854 14.7844 6.28563C14.9281 6.14271 15 5.96563 15 5.75438C15 5.54313 14.9281 5.36458 14.7844 5.21875C14.6406 5.07292 14.4625 5 14.25 5H5.75C5.5375 5 5.35938 5.07146 5.21563 5.21437C5.07188 5.35729 5 5.53437 5 5.74562C5 5.95687 5.07188 6.13542 5.21563 6.28125C5.35938 6.42708 5.5375 6.5 5.75 6.5Z"
										fill="currentColor"
									/>
								</g>
							</svg>
							<span class="text-body-4">히스토리</span>
						</button>
					</div>
				</div>

				<!-- Tab Content -->
				{#if activeTab === 'textbook'}
					<!-- Textbook Info Section -->
					<TextbookInfo on:subsection-select={handleSubsectionSelect} on:section-clear={handleSectionClear} />
				{:else}
					<!-- History Section -->
					<div class="px-5 mt-5">
						<!-- Search Input - Always Visible with Glass Effect -->
						<div class="relative">
							<input
								type="text"
								bind:value={historySearchQuery}
								placeholder="채팅 검색"
								class="w-full px-4 py-3 rounded-full
									bg-gray-100/50 dark:bg-gray-900/20
									shadow-[4px_4px_20px_rgba(0,0,0,0.1),inset_2px_2px_10px_rgba(255,255,255,0.05),inset_2px_2px_16px_rgba(206,212,229,0.12)]
									backdrop-blur-sm
									text-body-4 text-gray-950 dark:text-white
									placeholder-gray-500 dark:placeholder-gray-500
									border-none focus:outline-none focus:ring-1 focus:ring-primary-500/50"
							/>
							<div class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 dark:text-gray-400">
								<Search className="size-4" strokeWidth="1.5" />
							</div>
						</div>

						<!-- Bookmark Filter Row -->
						<div class="flex items-center justify-end mt-3">
							<button
								class="flex items-center gap-1.5 px-2 py-1 rounded-lg
									hover:bg-gray-200/30 dark:hover:bg-gray-800/30 transition
									{showBookmarkedOnly
										? 'text-primary-500'
										: 'text-gray-500 dark:text-gray-500'}"
								on:click={() => {
									showBookmarkedOnly = !showBookmarkedOnly;
								}}
								aria-label="북마크만 보기"
							>
								<span class="text-caption">북마크 필터</span>
								{#if showBookmarkedOnly}
									<BookmarkSolid className="size-4" />
								{:else}
									<Bookmark className="size-4" strokeWidth="1.5" />
								{/if}
							</button>
						</div>

						<!-- Chat List -->
						{#if historyExpanded}
							<div class="mt-3 flex flex-col gap-1" transition:slide={{ duration: 200 }}>
								{#if filteredChats && filteredChats.length > 0}
									{#each filteredChats as chat, idx (`chat-${chat?.id ?? idx}`)}
										<ChatItem
											className=""
											id={chat.id}
											title={chat.title}
											{shiftKey}
											bookmarked={chatBookmarks[chat.id] || false}
											selected={selectedChatId === chat.id}
											on:select={() => {
												selectedChatId = chat.id;
											}}
											on:unselect={() => {
												selectedChatId = null;
											}}
											on:bookmark-toggle={() => {
												toggleChatBookmark(chat.id);
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
								{:else if historySearchQuery || showBookmarkedOnly}
									<div class="py-4 text-center text-body-4 text-gray-500 dark:text-gray-500">
										검색 결과가 없습니다
									</div>
								{:else}
									<div
										class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
									>
										<Spinner className=" size-4" />
										<div class=" ">{$i18n.t('Loading...')}</div>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Profile Section (Figma: h-80px, padding 20px, gap 20px) -->
			<div class="sticky bottom-0 z-10 sidebar flex flex-row justify-between items-center p-5 gap-5 h-20">
				<!-- User Section (Figma: gap 12px, h-40px) -->
				<div class="flex flex-row items-center gap-3 flex-1 h-10">
					{#if $user !== undefined && $user !== null}
						<UserMenu
							role={$user?.role}
							on:show={(e) => {
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
							}}
						>
							<div class="flex flex-row items-center gap-3 rounded-xl hover:bg-gray-100/50 dark:hover:bg-gray-850/50 transition cursor-pointer py-1 px-1 -mx-1">
								<!-- Profile Image Frame (Figma: 40x40) -->
								<div class="flex items-center justify-center size-10 shrink-0">
									<img
										src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
										class="size-9 object-cover rounded-full bg-primary-500"
										alt={$i18n.t('Open User Profile Menu')}
										aria-label={$i18n.t('Open User Profile Menu')}
									/>
								</div>
								<!-- User Info (Figma: name 14px/500, role 12px/400) -->
								<div class="flex flex-col justify-center items-start">
									<div class="text-sm font-medium leading-[21px] text-gray-900 dark:text-white truncate max-w-[140px]">
										{$user?.name}
									</div>
									<div class="text-xs font-normal leading-[18px] text-[#B4BCD0]">
										{$i18n.t($user?.role)}
									</div>
								</div>
							</div>
						</UserMenu>
					{/if}
				</div>

				<!-- Right Side Controls -->
				<div class="flex items-center gap-2">
					<!-- Admin Buttons (Online Knowledge, Online Chapter) -->
					{#if $user?.role === 'admin'}
						<Tooltip content="온라인 지식기반" placement="top">
							<a
								href="/workspace/online-knowledge"
								class="flex rounded-lg size-5 justify-center items-center hover:opacity-70 transition text-gray-900 dark:text-white"
								on:click={() => {
									if ($mobile) {
										showSidebar.set(false);
									}
								}}
								aria-label="온라인 지식기반"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									class="size-5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
									/>
								</svg>
							</a>
						</Tooltip>

						<Tooltip content="온라인 챕터" placement="top">
							<a
								href="/workspace/online-chapter"
								class="flex rounded-lg size-5 justify-center items-center hover:opacity-70 transition text-gray-900 dark:text-white"
								on:click={() => {
									if ($mobile) {
										showSidebar.set(false);
									}
								}}
								aria-label="온라인 챕터"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									class="size-5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"
									/>
								</svg>
							</a>
						</Tooltip>
					{/if}

					<!-- Sidebar Toggle (Figma: 20x20) -->
					<Tooltip
						content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						placement="top"
					>
						<button
							class="flex size-5 justify-center items-center hover:opacity-70 transition text-gray-900 dark:text-white {isWindows
								? 'cursor-pointer'
								: 'cursor-[w-resize]'}"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
							aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						>
							<Sidebar />
						</button>
					</Tooltip>
				</div>
			</div>
			<!-- Dashboard Toggle Switch (Instructor/Admin only) -->
					{#if $user && isInstructor($user)}
						<div class="px-3 pb-2 pt-2 w-full flex items-center justify-center">
							<DashboardToggleSwitch activeMode="chat" />
						</div>
					{/if}
		</div>
	</div>
{/if}
