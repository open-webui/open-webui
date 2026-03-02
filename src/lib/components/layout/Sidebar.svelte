<script lang="ts">
	import { toast } from 'svelte-sonner';
	// @ts-ignore
	import { v4 as uuidv4 } from 'uuid';
	// @ts-ignore
	import type { Folder as FolderType } from '$lib/apis/folders';

	import { goto } from '$app/navigation';
	import {
		user,
		chats,
		settings,
		showSettings,
		chatId,
		tags,
		showSidebar,
		mobile,
		showArchivedChats,
		pinnedChats,
		scrollPaginationEnabled,
		currentChatPage,
		temporaryChatEnabled,
		channels,
		socket,
		config,
		isApp
	} from '$lib/stores';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	const i18n = getContext('i18n') as any;

	import {
		deleteChatById,
		getChatList,
		getAllTags,
		getChatListBySearchText,
		createNewChat,
		getPinnedChatList,
		toggleChatPinnedStatusById,
		getChatPinnedStatusById,
		getChatById,
		updateChatFolderIdById,
		importChat
	} from '$lib/apis/chats';
	import { createNewFolder, getFolders, updateFolderParentIdById } from '$lib/apis/folders';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import ArchivedChatsModal from './Sidebar/ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import CreateProjectModal from './Sidebar/CreateProjectModal.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import AddFilesPlaceholder from '../AddFilesPlaceholder.svelte';
	import SearchInput from './Sidebar/SearchInput.svelte';
	import Folder from '../common/Folder.svelte';
	import Plus from '../icons/Plus.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Home from '../icons/Home.svelte';
	

	const BREAKPOINT = 768;

	let navElement: HTMLElement | undefined;
	let search = '';

	let shiftKey = false;

	let selectedChatId: string | null = null;
	let showDropdown = false;
	let showPinnedChat = true;

	let showCreateChannel = false;
	let showCreateProject = false;
	

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let folders: Record<string, any> = {};
	let newFolderId: string | null = null;

	const initFolders = async () => {
		const folderList = await getFolders(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return [];
		});

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
				folders[folder.parent_id].childrenIds.sort((a: string, b: string) => {
					return folders[b].updated_at - folders[a].updated_at;
				});
			}
		}
	};

	const createFolder = async (name = 'Untitled', category = '', description = '') => {
		if (name === '') {
			toast.error(i18n.t(`Folder name cannot be empty.`));
			return;
		}

		const rootFolders = Object.values(folders).filter((folder: any) => folder.parent_id === null);
		if (rootFolders.find((folder: any) => folder.name.toLowerCase() === name.toLowerCase())) {
			// If a folder with the same name already exists, append a number to the name
			let i = 1;
			while (
				rootFolders.find(
					(folder: any) => folder.name.toLowerCase() === `${name} ${i}`.toLowerCase()
				)
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
				category: category,
				description: description,
				created_at: Date.now(),
				updated_at: Date.now()
			}
		};

		const res = await createNewFolder(localStorage.token, name).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			newFolderId = res.id;
			await initFolders();
		}
	};

	const handleCreateProject = async (event: CustomEvent<{ name: string; category: string }>) => {
		const { name, category } = event.detail;
		await createFolder(name, category);
		toast.success(`Project "${name}" created successfully!`);
	};

	const initChannels = async () => {
		await channels.set(await getChannels(localStorage.token));
	};

	const initChatList = async () => {
		// Reset pagination variables
		tags.set(await getAllTags(localStorage.token));
		pinnedChats.set(await getPinnedChatList(localStorage.token));
		initFolders();

		currentChatPage.set(1);
		allChatsLoaded = false;

		if (search) {
			await chats.set(await getChatListBySearchText(localStorage.token, search, $currentChatPage));
		} else {
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
		}

		// Enable pagination
		scrollPaginationEnabled.set(true);
	};

	const loadMoreChats = async () => {
		chatListLoading = true;

		currentChatPage.set($currentChatPage + 1);

		let newChatList = [];

		if (search) {
			newChatList = await getChatListBySearchText(localStorage.token, search, $currentChatPage);
		} else {
			newChatList = await getChatList(localStorage.token, $currentChatPage);
		}

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;
		await chats.set([...($chats ?? []), ...newChatList] as any);

		chatListLoading = false;
	};

	let searchDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

	const searchDebounceHandler = async () => {
		console.log('search', search);
		chats.set(null);

		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		if (search === '') {
			await initChatList();
			return;
		} else {
			searchDebounceTimeout = setTimeout(async () => {
				allChatsLoaded = false;
				currentChatPage.set(1);
				await chats.set(await getChatListBySearchText(localStorage.token, search));

				if ((($chats as any) ?? []).length === 0) {
					tags.set(await getAllTags(localStorage.token));
				}
			}, 1000);
		}
	};

	const importChatHandler = async (
		items: any[],
		pinned = false,
		folderId: string | null = null
	) => {
		console.log('importChatHandler', items, pinned, folderId);
		for (const item of items) {
			console.log(item);
			if (item.chat) {
				await importChat(localStorage.token, item.chat, item?.meta ?? {}, pinned, folderId);
			}
		}

		initChatList();
	};

	const inputFilesHandler = async (files: File[] | FileList) => {
		console.log(files);

		for (const file of files) {
			const reader = new FileReader();
			reader.onload = async (e) => {
				const content = (e.target?.result as string) ?? '';

				try {
					const chatItems = JSON.parse(content);
					importChatHandler(chatItems);
				} catch {
					toast.error(i18n.t(`Invalid file format.`));
				}
			};

			reader.readAsText(file);
		}
	};

	const tagEventHandler = async (type: string, tagName: string, chatId: string) => {
		console.log(type, tagName, chatId);
		if (type === 'delete') {
			initChatList();
		} else if (type === 'add') {
			initChatList();
		}
	};

	let draggedOver = false;

	const onDragOver = (e: DragEvent) => {
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

	const onDrop = async (e: DragEvent) => {
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

	let touchstart: Touch | null = null;
	let touchend: Touch | null = null;

	function checkDirection() {
		if (!touchstart || !touchend) return;
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

	const onTouchStart = (e: TouchEvent) => {
		touchstart = e.changedTouches[0];
		console.log(touchstart?.clientX);
	};

	const handleChannelSubmit = async (data: { name: string; access_control: any }) => {
		const res = await createNewChannel(localStorage.token, {
			name: data.name,
			access_control: data.access_control
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			if ($socket) {
				$socket.emit('join-channels', { auth: { token: (localStorage as any).token } });
			}
			await initChannels();
			showCreateChannel = false;
		}
	};

	const handleProjectSubmit = async (event: CustomEvent) => {
		const { name, category, description } = event.detail;
		await createFolder(name, category, description);
		showCreateProject = false;
	};

	const onTouchEnd = (e: TouchEvent) => {
		touchend = e.changedTouches[0];
		checkDirection();
	};

	const onKeyDown = (e: KeyboardEvent) => {
		if (e.key === 'Shift') {
			shiftKey = true;
		}
	};

	const onKeyUp = (e: KeyboardEvent) => {
		if (e.key === 'Shift') {
			shiftKey = false;
		}
	};

	// Helper variables to avoid type assertion issues in templates
	// $: hasWorkspaceAccess = $user?.role === 'admin' || ($user as any)?.permissions;
	$: hasWorkspaceAccess = $user?.role === 'admin';
	$: hasChannelsEnabled = ($config as any)?.features?.enable_channels;
	$: chatList = ($chats as any) ?? [];
	$: pinnedChatList = ($pinnedChats as any) ?? [];
	$: renderChatList = chatList.map((c: any, idx: number) => ({
		id: c?.id,
		title: c?.title,
		time_range: c?.time_range,
		showTimeRange: idx === 0 || (idx > 0 && c?.time_range !== chatList[idx - 1]?.time_range)
	}));

	const onFocus = () => {};

	const onBlur = () => {
		shiftKey = false;
		selectedChatId = null;
	};

	onMount(async () => {
		showPinnedChat = localStorage?.showPinnedChat ? localStorage.showPinnedChat === 'true' : true;

		mobile.subscribe((value) => {
			if ($showSidebar && value) {
				showSidebar.set(false);
			}

			if ($showSidebar && !value) {
				const navElement = document.getElementsByTagName('nav')[0];
				if (navElement) {
					(navElement as any).style.webkitAppRegion = 'drag';
				}
			}

			if (!$showSidebar && !value) {
				showSidebar.set(true);
			}
		});

		showSidebar.set(!$mobile ? localStorage.sidebar === 'true' : false);
		showSidebar.subscribe((value) => {
			localStorage.sidebar = value;

			// nav element is not available on the first render
			const navElement = document.getElementsByTagName('nav')[0];

			if (navElement) {
				if ($mobile) {
					if (!value) {
						(navElement as any).style.webkitAppRegion = 'drag';
					} else {
						(navElement as any).style.webkitAppRegion = 'no-drag';
					}
				} else {
					(navElement as any).style.webkitAppRegion = 'drag';
				}
			}
		});

		await initChannels();
		await initChatList();

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);

		window.addEventListener('touchstart', onTouchStart);
		window.addEventListener('touchend', onTouchEnd);

		window.addEventListener('focus', onFocus);
		window.addEventListener('blur-sm', onBlur);

		const dropZone = document.getElementById('sidebar');

		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', onKeyDown);
		window.removeEventListener('keyup', onKeyUp);

		window.removeEventListener('touchstart', onTouchStart);
		window.removeEventListener('touchend', onTouchEnd);

		window.removeEventListener('focus', onFocus);
		window.removeEventListener('blur-sm', onBlur);

		const dropZone = document.getElementById('sidebar');

		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});
</script>

<CreateProjectModal bind:show={showCreateProject} on:submit={handleProjectSubmit} />

<ArchivedChatsModal
	bind:show={$showArchivedChats}
	on:change={async () => {
		await initChatList();
	}}
/>

<ChannelModal bind:show={showCreateChannel} onSubmit={handleChannelSubmit} />

<CreateProjectModal bind:show={showCreateProject} on:create={handleCreateProject} />

<!-- svelte-ignore a11y-no-static-element-interactions -->

{#if $showSidebar}
	<div
		class="sidebar-overlay {$isApp ? 'ml-[4.5rem] md:ml-0' : ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 backdrop-blur-md w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

<div
	bind:this={navElement}
	id="sidebar"
	class="sidebar-container h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
		? 'md:relative w-[280px] max-w-[280px] shadow-[0_8px_30px_rgb(0,0,0,0.12)] md:shadow-none'
		: '-translate-x-[280px] w-[0px]'} {$isApp
		? 'ml-[4.5rem] md:ml-0'
		: 'transition-all duration-300 ease-out'} shrink-0 bg-gradient-to-b from-white to-gray-50/50 dark:from-gray-900 dark:to-gray-950/80 text-gray-900 dark:text-gray-100 text-sm fixed z-50 top-0 left-0 overflow-x-hidden border-r border-gray-200/80 dark:border-gray-800/80"
	data-state={$showSidebar}
>

	<div
		class="py-3 my-auto flex flex-col justify-between h-screen max-h-[100dvh] w-[280px] overflow-x-hidden z-50 {$showSidebar
			? ''
			: 'invisible'}"
	>
		<!-- Enhanced Header with subtle gradient -->
		<div class="px-2.5 flex items-center gap-2">
			<button
				class="sidebar-toggle p-2.5 flex rounded-xl hover:bg-white/80 dark:hover:bg-gray-800/80 transition-all duration-200 active:scale-95 group border border-transparent hover:border-gray-200/50 dark:hover:border-gray-700/50 hover:shadow-sm"
				on:click={() => {
					showSidebar.set(!$showSidebar);
				}}
				aria-label="Toggle sidebar"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke-width="2.5"
					stroke="currentColor"
					class="size-5 text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors duration-200"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"
					/>
				</svg>
			</button>

			<a
				id="sidebar-new-chat-button"
				class="new-chat-button flex-1 flex items-center justify-between gap-2.5 rounded-xl px-3 py-2.5
       bg-white dark:bg-gray-800
       border border-gray-200 dark:border-gray-700
       hover:border-gray-300 dark:hover:border-gray-600
       hover:shadow-md dark:hover:shadow-gray-900/30
       transition-all duration-200 active:scale-[0.98]
       no-drag-region group"

				href="/"
				draggable="false"
				on:click={async () => {
					selectedChatId = null;
					await goto('/');
					const newChatButton = document.getElementById('new-chat-button');
					setTimeout(() => {
						newChatButton?.click();
						if ($mobile) {
							showSidebar.set(false);
						}
					}, 0);
				}}
			>
				<div class="flex items-center gap-2.5 min-w-0">
					<div class="flex-shrink-0 p-1.5 bg-gradient-to-br from-white to-gray-50 dark:from-gray-900/90 dark:to-gray-950/90 rounded-lg shadow-sm border border-gray-200/50 dark:border-gray-800/50">
						<img
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class="size-4 rounded"
							alt="logo"
						/>
					</div>
					<span class="font-semibold text-sm truncate text-gray-900 dark:text-gray-100"
						>{$i18n.t('New Chat')}</span
					>
				</div>

				<div class="flex-shrink-0 p-1 bg-gradient-to-br from-orange-50 to-orange-100/50 dark:from-orange-900/20 dark:to-orange-800/20 rounded-lg group-hover:from-orange-100 group-hover:to-orange-200/50 dark:group-hover:from-orange-900/30 dark:group-hover:to-orange-800/30 transition-all duration-200">
					<PencilSquare
						className="size-4 text-orange-600 dark:text-orange-400"
						strokeWidth="2.5"
					/>
				</div>
			</a>
		</div>

		<!-- Enhanced Workspace Link -->
		{#if hasWorkspaceAccess}
			<div class="px-2.5 mt-2.5">
				<a
					class="workspace-link flex items-center gap-2.5 rounded-xl px-3 py-2.5 
					hover:bg-gradient-to-r hover:from-white/90 hover:to-gray-50/90 
					dark:hover:from-gray-800/90 dark:hover:to-gray-900/80 
					transition-all duration-200 active:scale-[0.98] group 
					border border-transparent 
					hover:border-gray-200/60 dark:hover:border-gray-700/60
					hover:shadow-sm"
					href="/workspace"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
					draggable="false"
				>
					<div class="flex-shrink-0 p-1.5 bg-gradient-to-br from-gray-100 to-gray-50 dark:from-gray-900/40 dark:to-gray-950/40 rounded-lg group-hover:from-gray-200 group-hover:to-gray-100 dark:group-hover:from-gray-800/50 dark:group-hover:to-gray-900/50 transition-all duration-200 border border-gray-200/30 dark:border-gray-800/30">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2.5"
							stroke="currentColor"
							class="size-4 text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors duration-200"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 0 0 2.25-2.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v2.25A2.25 2.25 0 0 0 6 10.5Zm0 9.75h2.25A2.25 2.25 0 0 0 10.5 18v-2.25a2.25 2.25 0 0 0-2.25-2.25H6a2.25 2.25 0 0 0-2.25 2.25V18A2.25 2.25 0 0 0 6 20.25Zm9.75-9.75H18a2.25 2.25 0 0 0 2.25-2.25V6A2.25 2.25 0 0 0 18 3.75h-2.25A2.25 2.25 0 0 0 13.5 6v2.25a2.25 2.25 0 0 0 2.25 2.25Z"
							/>
						</svg>
					</div>
					<span class="font-semibold text-sm text-gray-700 dark:text-gray-200 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">{$i18n.t('Workspace')}</span>
				</a>
			</div>
		{/if}

		<!-- Enhanced Search Input with subtle border -->
		<div class="px-2.5 mt-3 relative {$temporaryChatEnabled ? 'opacity-30 pointer-events-none' : ''}">
			{#if $temporaryChatEnabled}
				<div class="absolute z-40 w-full h-full flex justify-center"></div>
			{/if}

			<div class="search-wrapper">
				<SearchInput
					bind:value={search}
					on:input={searchDebounceHandler}
					placeholder={$i18n.t('Search')}
					showClearButton={true}
				/>
			</div>
		</div>

		<!-- Enhanced Chat List with better spacing -->
		<div
			class="chat-list-container relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden mt-3 {$temporaryChatEnabled
				? 'opacity-30 pointer-events-none'
				: ''} enhanced-scrollbar"
		>
			{#if hasChannelsEnabled && ($user?.role === 'admin' || $channels.length > 0) && !search}
				<Folder
					className="px-2.5"
					name={$i18n.t('Channels')}
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

			<!-- ENHANCED PROJECTS SECTION -->
			{#if !search}
				<Folder
					collapsible={true}
					className="px-2.5 projects-section {hasChannelsEnabled &&
					($user?.role === 'admin' || $channels.length > 0)
						? 'mt-2.5'
						: ''}"
					name={$i18n.t('Projects')}
					onAdd={() => {
						showCreateProject = true;
					}}
					onAddLabel={$i18n.t('New Folder')}
					on:import={(e) => {
						importChatHandler(e.detail);
					}}
					on:drop={async (e) => {
						const { type, id, item } = e.detail;

						if (type === 'folder') {
							if (folders[id].parent_id === null) {
								return;
							}

							const res = await updateFolderParentIdById(localStorage.token, id, undefined).catch(
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
					{#if $temporaryChatEnabled}
						<div class="absolute z-40 w-full h-full flex justify-center"></div>
					{/if}

					{#if folders}
						<Folders
							{folders}
							on:import={(e) => {
								const { folderId, items } = e.detail;
								importChatHandler(items, false, folderId);
							}}
							on:update={async (e) => {
								initChatList();
							}}
							on:change={async () => {
								initChatList();
							}}
						/>
					{/if}
				</Folder>
			{/if}

			<!-- ENHANCED CHATS SECTION -->
			<Folder
				collapsible={!search}
				className="px-2.5 mt-0.5"
				name={$i18n.t('Chats')}
				dragAndDrop={true}
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
							chat = await importChat(localStorage.token, item.chat, item?.meta ?? {});
						}

						if (chat) {
							console.log(chat);
							if (chat.folder_id) {
								const res = await updateChatFolderIdById(
									localStorage.token,
									chat.id,
									undefined
								).catch((error) => {
									toast.error(`${error}`);
									return null;
								});
							}

							if (chat.pinned) {
								const res = await toggleChatPinnedStatusById(localStorage.token, chat.id);
							}

							initChatList();
						}
					}
				}}
			>
				{#if $temporaryChatEnabled}
					<div class="absolute z-40 w-full h-full flex justify-center"></div>
				{/if}

				{#if !search && $pinnedChats.length > 0}
					<div class="flex flex-col space-y-1">
						<Folder
							className=""
							bind:open={showPinnedChat}
							on:change={(e) => {
								localStorage.setItem('showPinnedChat', e.detail);
								console.log(e.detail);
							}}
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
										chat = await importChat(localStorage.token, item.chat, item?.meta ?? {});
									}

									if (chat) {
										console.log(chat);
										if (chat.folder_id) {
											const res = await updateChatFolderIdById(
												localStorage.token,
												chat.id,
												undefined
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
								class="ml-3 pl-1 mt-0.5 flex flex-col overflow-y-auto scrollbar-hidden border-s-2 border-blue-300/60 dark:border-blue-700/60"
							>
								{#each pinnedChatList as chat, idx}
									<ChatItem
										className=""
										id={chat.id ?? ''}
										title={chat.title ?? ''}
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
											tagEventHandler(type, name, chat.id ?? '');
										}}
									/>
								{/each}
							</div>
						</Folder>
					</div>
				{/if}

				<div class="flex-1 flex flex-col overflow-y-auto scrollbar-hidden">
					<div class="pt-1">
						{#if $chats}
							{#each renderChatList as chat, idx}
								{#if chat.showTimeRange}
									<div
										class="time-range-label w-full pl-3 text-[0.65rem] font-bold uppercase tracking-wider text-gray-500/90 dark:text-gray-500/80 {idx ===
										0
											? ''
											: 'pt-5'} pb-2"
									>
										{$i18n.t(chat.time_range)}
									</div>
								{/if}

								<ChatItem
									className=""
									id={chat.id ?? ''}
									title={chat.title ?? ''}
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
										tagEventHandler(type, name, chat.id ?? '');
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
										class="loading-indicator w-full flex justify-center py-4 text-xs text-gray-500/80 dark:text-gray-400/80 items-center gap-2"
									>
										<Spinner className="size-3.5" />
										<span class="font-medium">Loading more chats...</span>
									</div>
								</Loader>
							{/if}
						{:else}
							<div
								class="loading-indicator w-full flex justify-center py-6 text-xs text-gray-500/80 dark:text-gray-400/80 items-center gap-2"
							>
								<Spinner className="size-3.5" />
								<span class="font-medium">Loading chats...</span>
							</div>
						{/if}
					</div>
				</div>
			</Folder>
		</div>

		<!-- Enhanced User Menu with gradient border -->
		<div class="user-menu-container px-2.5 mt-2.5 border-t border-gray-200/60 dark:border-gray-800/60 pt-2.5">
			<div class="flex flex-col font-primary">
				{#if $user !== undefined && $user !== null}
					<UserMenu
						role={$user?.role}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<button
							class="user-profile-button flex items-center gap-2.5 rounded-xl py-2.5 px-3 w-full
							hover:bg-gradient-to-r hover:from-white/90 hover:to-gray-50/90 
							dark:hover:from-gray-800/90 dark:hover:to-gray-900/80 
							transition-all duration-200 active:scale-[0.98] group 
							border border-transparent 
							hover:border-gray-200/60 dark:hover:border-gray-700/60
							hover:shadow-sm"
						>
							<div class="relative flex-shrink-0">
								<img
									src={$user?.profile_image_url}
									class="w-9 h-9 object-cover rounded-full ring-2 ring-gray-200/60 dark:ring-gray-700/60 group-hover:ring-gray-300/80 dark:group-hover:ring-gray-600/80 transition-all duration-200"
									alt="User profile"
								/>
								<div class="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-white dark:border-gray-900 shadow-sm"></div>
							</div>

							<div class="font-semibold text-sm truncate flex-1 text-left text-gray-700 dark:text-gray-200 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
								{$user?.name}
							</div>

							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2.5"
								stroke="currentColor"
								class="ml-auto size-4 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-all group-hover:translate-x-0.5"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M9 18l6-6-6-6" />
							</svg>
						</button>
					</UserMenu>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	/* ===== Improve Folder Items Inside Projects ===== */

:global(.projects-section .folder-item),
:global(.projects-section .folder-row) {
	background: transparent !important;
	border-radius: 0.5rem;
	transition: background-color 0.2s ease, color 0.2s ease;
}

/* Folder text (light mode) */
:global(.projects-section .folder-item .folder-name),
:global(.projects-section .folder-row .folder-name) {
	color: rgb(31, 41, 55) !important; /* gray-800 */
	font-weight: 500;
}

/* Folder text (dark mode) */
:global(.dark .projects-section .folder-item .folder-name),
:global(.dark .projects-section .folder-row .folder-name) {
	color: rgb(229, 231, 235) !important; /* gray-200 */
}

/* Hover state */
:global(.projects-section .folder-item:hover),
:global(.projects-section .folder-row:hover) {
	background: rgba(243, 244, 246, 0.7) !important; /* gray-100 */
}

:global(.dark .projects-section .folder-item:hover),
:global(.dark .projects-section .folder-row:hover) {
	background: rgba(55, 65, 81, 0.5) !important; /* gray-700 */
}

/* Active / selected folder */
:global(.projects-section .folder-item.active),
:global(.projects-section .folder-row.active) {
	color: rgb(249, 115, 22) !important; /* orange-500 */
	font-weight: 600;
}

	/* Enhanced scrollbar with smoother appearance */
	.enhanced-scrollbar::-webkit-scrollbar {
		width: 5px;
	}

	.enhanced-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}

	.enhanced-scrollbar::-webkit-scrollbar-thumb {
		background: linear-gradient(to bottom, rgba(156, 163, 175, 0.2), rgba(156, 163, 175, 0.4));
		border-radius: 10px;
		transition: background 0.3s ease;
	}

	.enhanced-scrollbar::-webkit-scrollbar-thumb:hover {
		background: linear-gradient(to bottom, rgba(156, 163, 175, 0.4), rgba(156, 163, 175, 0.6));
	}

	:global(.dark) .enhanced-scrollbar::-webkit-scrollbar-thumb {
		background: linear-gradient(to bottom, rgba(75, 85, 99, 0.3), rgba(75, 85, 99, 0.5));
	}

	:global(.dark) .enhanced-scrollbar::-webkit-scrollbar-thumb:hover {
		background: linear-gradient(to bottom, rgba(75, 85, 99, 0.5), rgba(75, 85, 99, 0.7));
	}

	.scrollbar-hidden:active::-webkit-scrollbar-thumb,
	.scrollbar-hidden:focus::-webkit-scrollbar-thumb,
	.scrollbar-hidden:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	
	.scrollbar-hidden::-webkit-scrollbar-thumb {
		visibility: hidden;
	}

	/* Smooth fade-in animation for overlay */
	.sidebar-overlay {
		animation: overlayFadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	@keyframes overlayFadeIn {
		from {
			opacity: 0;
			backdrop-filter: blur(0px);
		}
		to {
			opacity: 1;
			backdrop-filter: blur(12px);
		}
	}

	/* Subtle scale animation for interactive elements */
	.sidebar-toggle,
	.new-chat-button,
	.workspace-link,
	.user-profile-button {
		transform-origin: center;
		will-change: transform;
	}

	/* Enhanced loading indicator with smoother pulse */
	.loading-indicator {
		animation: smoothPulse 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}

	@keyframes smoothPulse {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.6;
		}
	}

	/* Time range label with better typography */
	.time-range-label {
		letter-spacing: 0.06em;
		font-variant: small-caps;
	}

	/* Enhanced glassmorphism effect */
	.sidebar-container {
		backdrop-filter: blur(24px) saturate(180%);
		-webkit-backdrop-filter: blur(24px) saturate(180%);
	}

	/* Search wrapper subtle divider */
	.search-wrapper {
		position: relative;
	}

	.search-wrapper::after {
		content: '';
		position: absolute;
		bottom: -10px;
		left: 8px;
		right: 8px;
		height: 1px;
		background: linear-gradient(90deg, 
			transparent 0%, 
			rgba(229, 231, 235, 0.6) 15%, 
			rgba(229, 231, 235, 0.6) 85%, 
			transparent 100%);
		opacity: 0.5;
	}

	:global(.dark) .search-wrapper::after {
		background: linear-gradient(90deg, 
			transparent 0%, 
			rgba(55, 65, 81, 0.6) 15%, 
			rgba(55, 65, 81, 0.6) 85%, 
			transparent 100%);
		opacity: 0.4;
	}

	/* CLEAN PROJECTS SECTION - NO SPECIAL STYLING */
	:global(.projects-section) {
		position: relative;
	}

	:global(.projects-section .folder-header) {
		background: transparent !important;
		border: none !important;
		border-radius: 0 !important;
		padding: 0.5rem 0 !important;
		margin-bottom: 0.25rem !important;
		box-shadow: none !important;
		transition: none !important;
	}

	:global(.dark .projects-section .folder-header) {
		background: transparent !important;
		border: none !important;
		box-shadow: none !important;
	}

	:global(.projects-section .folder-header:hover) {
		background: transparent !important;
		border: none !important;
		box-shadow: none !important;
	}

	:global(.projects-section > *) {
		background: transparent !important;
		border: none !important;
		box-shadow: none !important;
	}

	:global(.projects-section .folder-name) {
		font-weight: 600;
		font-size: 0.875rem;
		letter-spacing: 0;
		color: rgb(55, 65, 81) !important;
		position: relative;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}

	:global(.dark .projects-section .folder-name) {
		color: rgb(209, 213, 219) !important;
	}

	:global(.projects-section .folder-name::before) {
		content: '';
		display: inline-block;
		width: 1.125rem;
		height: 1.125rem;
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke-width='2' stroke='rgb(75, 85, 99)'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z'/%3E%3C/svg%3E");
		background-size: contain;
		background-repeat: no-repeat;
		flex-shrink: 0;
	}

	:global(.dark .projects-section .folder-name::before) {
		background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke-width='2' stroke='rgb(156, 163, 175)'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z'/%3E%3C/svg%3E");
	}

	:global(.projects-section button.add-button) {
		background: transparent !important;
		border: none !important;
		border-radius: 0.375rem !important;
		padding: 0.25rem 0.5rem !important;
		color: rgb(75, 85, 99) !important;
		font-weight: 500 !important;
		font-size: 0.75rem !important;
		transition: background-color 0.2s, color 0.2s !important;
		box-shadow: none !important;
	}

	:global(.dark .projects-section button.add-button) {
		background: transparent !important;
		border: none !important;
		color: rgb(156, 163, 175) !important;
		box-shadow: none !important;
	}

	:global(.projects-section button.add-button:hover) {
		background: rgba(243, 244, 246, 0.8) !important;
		border: none !important;
		color: rgb(17, 24, 39) !important;
		transform: none !important;
		box-shadow: none !important;
	}

	:global(.dark .projects-section button.add-button:hover) {
		background: rgba(55, 65, 81, 0.5) !important;
		border: none !important;
		color: rgb(243, 244, 246) !important;
		box-shadow: none !important;
	}

	/* Micro-interactions */
	@keyframes subtle-bounce {
		0%, 100% {
			transform: translateY(0);
		}
		50% {
			transform: translateY(-2px);
		}
	}

	.new-chat-button:hover .flex-shrink-0:last-child {
		animation: subtle-bounce 0.6s ease-in-out;
	}
</style>