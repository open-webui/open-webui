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
		showSidebar,
		showSearch,
		mobile,
		showArchivedChats,
		pinnedChats,
		scrollPaginationEnabled,
		currentChatPage,
		temporaryChatEnabled,
		clearMessageInput,
		channels,
		socket,
		config,
		isApp,
		models
	} from '$lib/stores';
	import { onMount, getContext, tick, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

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

	import ArchivedChatsModal from './ArchivedChatsModal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import ChatItem from './Sidebar/ChatItem.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Loader from '../common/Loader.svelte';
	import AddFilesPlaceholder from '../AddFilesPlaceholder.svelte';
	import Folder from '../common/Folder.svelte';
	import MaterialIcon from '../common/MaterialIcon.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import GenerateText from '../icons/GenerateText.svelte';
	import Logout from '../icons/Logout.svelte';
	import Admin from '../icons/Admin.svelte';
	import Chat2 from '../icons/Chat2.svelte';
	import Setting from '../icons/Setting.svelte';
	import AIFolder from '../icons/AIFolder.svelte';
	import Content from '../icons/Content.svelte';
	import SearchNew from '../icons/SearchNew.svelte';
	import NewChat from '../icons/NewChat.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import ChevronLeft from '../icons/ChevronLeft.svelte';
	import Home from '../icons/Home.svelte';
	import MagnifyingGlass from '../icons/MagnifyingGlass.svelte';
	import LogoText from '../icons/LogoText.svelte';
	import Toggle from '../icons/Toggle.svelte';
	import SearchModal from './SearchModal.svelte';
	import { isRTL } from '$lib/i18n';

	const BREAKPOINT = 768;

	let navElement;
	let shiftKey = false;

	let selectedChatId = null;
	let showDropdown = false;
	let showPinnedChat = true;

	let showCreateChannel = false;

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let folders = {};
	let newFolderId = null;

	// Hover functionality variables
	let isHovered = false;
	let wasOpenedByClick = false;
	let hoverTimeout: number | null = null;

	function openSidebarOnAction() {
		if (!$showSidebar) {
			showSidebar.set(true);
		}
		wasOpenedByClick = true;
	}

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
				folders[folder.parent_id].childrenIds.sort((a, b) => {
					return folders[b].updated_at - folders[a].updated_at;
				});
			}
		}
	};

	const createFolder = async (name = 'Untitled') => {
		if (name === '') {
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

		const res = await createNewFolder(localStorage.token, name).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			newFolderId = res.id;
			await initFolders();
		}
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

		await chats.set(await getChatList(localStorage.token, $currentChatPage));

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
				await importChat(localStorage.token, item.chat, item?.meta ?? {}, pinned, folderId);
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

	// Hover functionality handlers
	const onMouseEnter = () => {
		isHovered = true;
		// Clear any existing timeout
		if (hoverTimeout) {
			clearTimeout(hoverTimeout);
			hoverTimeout = null;
		}

		// Only open sidebar on hover if it wasn't opened by click
		if (!$showSidebar && !wasOpenedByClick) {
			showSidebar.set(true);
		}
	};

	const onMouseLeave = () => {
		isHovered = false;

		// Only close sidebar on hover out if it wasn't opened by click
		if ($showSidebar && !wasOpenedByClick) {
			// Add a small delay to prevent accidental closing
			hoverTimeout = setTimeout(() => {
				if (!isHovered && !wasOpenedByClick) {
					showSidebar.set(false);
				}
			}, 300);
		}
	};

	const onSidebarClick = (e: any) => {
		e.stopPropagation();

		const willBeOpen = !$showSidebar;

		// Mark that sidebar was opened by click if we're opening it
		if (willBeOpen) {
			wasOpenedByClick = true;
		} else {
			// If we're closing the sidebar, reset the flag
			wasOpenedByClick = false;
		}

		showSidebar.set(willBeOpen);

		// Clear any existing timeout
		if (hoverTimeout) {
			clearTimeout(hoverTimeout);
			hoverTimeout = null;
		}
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
					navElement.style['-webkit-app-region'] = 'drag';
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
						navElement.style['-webkit-app-region'] = 'drag';
					} else {
						navElement.style['-webkit-app-region'] = 'no-drag';
					}
				} else {
					navElement.style['-webkit-app-region'] = 'drag';
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
		window.addEventListener('blur', onBlur);

		const dropZone = document.getElementById('sidebar');

		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
		// dropZone?.addEventListener('click', openSidebarOnAction);
	});

	onDestroy(() => {
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
		// dropZone?.removeEventListener('click', openSidebarOnAction);

		// Clean up hover timeout
		if (hoverTimeout) {
			clearTimeout(hoverTimeout);
		}
	});
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

<!-- svelte-ignore a11y-no-static-element-interactions -->

<SearchModal
	bind:show={$showSearch}
	onClose={() => {
		if ($mobile) {
			showSidebar.set(false);
		}
	}}
/>
{#if $showSidebar}
	<div
		on:click={onSidebarClick}
		class="block md:hidden fixed z-[40] w-full h-full bg-[#32404D] opacity-50"
	></div>
{/if}
<div
	bind:this={navElement}
	id="sidebar"
	role="navigation"
	class=" h-screen max-h-[100dvh] min-h-screen select-none shadown-none border-0 {$showSidebar
		? `md:relative w-[300px] max-w-[300px] ${$mobile ? 'w-[0px]' : ''}`
		: $mobile
			? 'w-[0px] absolute'
			: ''} {$isApp
		? `ml-[4.5rem] md:ml-0`
		: 'transition-width duration-200 ease-in-out'} shadow-md shrink-0 text-sm z-50 top-0 left-0
	}
        "
	data-state={$showSidebar}
>
	<div
		class="flex flex-col justify-between max-h-[100dvh] overflow-x-hidden z-50 bg-light-bg shadow-[0px_48px_96px_0px_rgba(0,0,0,0.08)] dark:shadow-none"
	>
		<div class="px-[8px] py-[24px] sidebar__top h-[calc(100vh-58px)] overflow-y-auto">
			{#if $mobile}
				<div class="sidebar__mobile">
					<div
						class="mb-[30px] px-[16px] search_new-chat flex justify-center text-gray-800 dark:text-gray-200"
					>
						<a
							id="sidebar-new-chat-button"
							class="p-[8px] flex-1 items-center rounded-[8px] h-full bg-gradient-bg-2"
							class:justify-center={!$showSidebar}
							href="/"
							draggable="false"
							on:click={() => {
								showSearch.set(true);
							}}
						>
							<div class="flex gap-[8px] items-center">
								<MaterialIcon name="search" size="1.1rem" />

								<!-- Label -->
								<div
									class="self-center font-medium text-typography-disabled text-[16px] leading-[22px] transition-all duration-300 ease-in-out"
									class:hidden={!$showSidebar}
								>
									{$i18n.t('Search')}
								</div>
							</div>
						</a>
						<a
							id="sidebar-new-chat-button"
							class="pl-[10px] py-[8px] flex items-center rounded-lg h-full text-right hover:bg-gradient-bg-2 dark:hover:bg-gray-900 transition-all duration-300 ease-in-out no-drag-region"
							class:justify-center={!$showSidebar}
							href="/"
							draggable="false"
							on:click={async () => {
								selectedChatId = null;

								await temporaryChatEnabled.set(false);
								setTimeout(() => {
									if ($mobile) {
										showSidebar.set(false);
									}
								}, 0);
							}}
						>
							<NewChat />
						</a>
					</div>
					<a
						id="sidebar-new-chat-button"
						class="px-[16px] py-[8px] flex items-center flex-1 rounded-lg h-full text-right hover:bg-gradient-bg-2 dark:hover:bg-gray-900 transition-all duration-300 ease-in-out no-drag-region"
						href="/"
					>
						<div class="flex gap-[8px] items-center">
							<!-- Icon -->
							<div class="flex items-center self-center transition-all duration-300 ease-in-out">
								<img
									src="/logov4.png"
									alt="GovGPT Logo"
									class="w-[17px] h-[17px] filter dark:invert dark:brightness-0 dark:contrast-200"
								/>
							</div>

							<!-- Label -->
							<div
								class="self-center link-style text-typography-titles transition-all duration-300 ease-in-out"
							>
								{$i18n.t('GovGPT')}
							</div>
						</div></a
					>
				</div>
			{/if}
			{#if !$mobile}
				<div
					class="mb-[24px] flex justify-between items-center text-gray-600 dark:text-gray-400"
					class:justify-center={!$showSidebar}
				>
					<!-- Menu Icon behaves like other sidebar buttons -->

					<a
						class="p-[10px] hover:bg-gradient-bg-2 flex items-center rounded-lg transition-all duration-300 ease-in-out"
						class:justify-center={!$showSidebar}
						href="#"
						on:click={onSidebarClick}
					>
						<MaterialIcon name="menu" size="1.1rem" />
					</a>

					<!-- Search icon only when sidebar is expanded, right aligned -->
					{#if $showSidebar}
						<div class="flex-1 flex justify-end transition-all duration-300 ease-in-out">
							<button
								class="flex items-center outline-none rounded-lg transition-all duration-300 ease-in-out"
								on:click={() => {
									showSearch.set(true);
								}}
								draggable="false"
							>
								<MaterialIcon name="search" size="1.1rem" />
							</button>
						</div>
					{/if}
				</div>
			{/if}
			{#if false && $user?.role === 'admin'}
				<div class="px-[16px] py-[8px] flex justify-center text-gray-800 dark:text-gray-200">
					<a
						class="grow flex items-center rounded-lg px-2 py-[7px] hover:bg-gray-100 dark:hover:bg-gray-900 transition-all duration-300 ease-in-out"
						class:justify-center={!$showSidebar}
						href="/home"
						on:click={() => {
							selectedChatId = null;
							chatId.set('');

							if ($mobile) {
								showSidebar.set(false);
							}
						}}
						draggable="false"
					>
						<!-- Icon -->
						<div
							class="self-center transition-all duration-300 ease-in-out"
							class:mr-[15px]={$showSidebar}
						>
							<MaterialIcon name="home" size="1.1rem" />
						</div>

						<!-- Label -->
						<div
							class="self-center font-medium text-sm text-gray-850 dark:text-white leading-[22px] transition-all duration-300 ease-in-out"
							class:hidden={!$showSidebar}
						>
							{$i18n.t('Home')}
						</div>
					</a>
				</div>
			{/if}
			{#if !$mobile}
				<div class="flex justify-center text-gray-800 dark:text-gray-200">
					<a
						id="sidebar-new-chat-button"
						class="px-[16px] py-[8px] flex items-center flex-1 rounded-lg h-full text-right hover:bg-gradient-bg-2 dark:hover:bg-gray-900 transition-all duration-300 ease-in-out no-drag-region"
						class:justify-center={!$showSidebar}
						href="/"
						draggable="false"
						on:click={async () => {
							selectedChatId = null;

							// Trigger clearing of message input
							clearMessageInput.set(true);

							await temporaryChatEnabled.set(false);
							setTimeout(() => {
								if ($mobile) {
									showSidebar.set(false);
								}
							}, 0);
						}}
					>
						<div class="flex items-center">
							<!-- Icon -->
							<div
								class="flex items-center self-center transition-all duration-300 ease-in-out"
								class:me-[8px]={$showSidebar}
							>
								<NewChat />
							</div>

							<!-- Label -->
							<div
								class="self-center link-style text-typography-titles transition-all duration-300 ease-in-out"
								class:hidden={!$showSidebar}
							>
								{$i18n.t('New Chat')}
							</div>
						</div>
					</a>
				</div>
			{/if}

			{#if $user?.role === 'admin' && ($config?.features?.enable_notes ?? false) && ($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))}
				<div class="flex justify-center text-gray-800 dark:text-gray-200">
					<a
						class="px-[16px] py-[8px] grow flex items-center rounded-lg hover:bg-gradient-bg-2 dark:hover:bg-gray-900 transition-all duration-300 ease-in-out"
						class:justify-center={!$showSidebar}
						href="/notes"
						on:click={() => {
							selectedChatId = null;
							chatId.set('');

							if ($mobile) {
								showSidebar.set(false);
							}
						}}
						draggable="false"
					>
						<!-- Icon -->
						<div
							class="flex items-center self-center transition-all duration-300 ease-in-out"
							class:me-[8px]={$showSidebar}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								width="20"
								height="20"
								viewBox="0 0 20 20"
								fill="none"
							>
								<mask
									id="mask0_293_12936"
									style="mask-type:alpha"
									maskUnits="userSpaceOnUse"
									x="0"
									y="0"
									width="20"
									height="20"
								>
									<rect width="20" height="20" fill="#D9D9D9" />
								</mask>
								<g mask="url(#mask0_293_12936)">
									<path
										d="M4.42443 17.0833C4.00887 17.0833 3.65387 16.9362 3.35943 16.6419C3.06512 16.3474 2.91797 15.9924 2.91797 15.5769V4.42313C2.91797 4.00757 3.06512 3.65257 3.35943 3.35813C3.65387 3.06382 4.00887 2.91667 4.42443 2.91667H8.13276C8.18512 2.45403 8.38707 2.06062 8.73859 1.73646C9.08998 1.41215 9.51089 1.25 10.0013 1.25C10.497 1.25 10.9206 1.41215 11.2721 1.73646C11.6237 2.06062 11.8229 2.45403 11.8698 2.91667H15.5782C15.9937 2.91667 16.3487 3.06382 16.6432 3.35813C16.9375 3.65257 17.0846 4.00757 17.0846 4.42313V15.5769C17.0846 15.9924 16.9375 16.3474 16.6432 16.6419C16.3487 16.9362 15.9937 17.0833 15.5782 17.0833H4.42443ZM4.42443 15.8333H15.5782C15.6423 15.8333 15.7011 15.8066 15.7544 15.7531C15.8079 15.6998 15.8346 15.641 15.8346 15.5769V4.42313C15.8346 4.35896 15.8079 4.30021 15.7544 4.24687C15.7011 4.1934 15.6423 4.16667 15.5782 4.16667H4.42443C4.36026 4.16667 4.30151 4.1934 4.24818 4.24687C4.19471 4.30021 4.16797 4.35896 4.16797 4.42313V15.5769C4.16797 15.641 4.19471 15.6998 4.24818 15.7531C4.30151 15.8066 4.36026 15.8333 4.42443 15.8333ZM6.04297 13.8621H11.4596V12.6123H6.04297V13.8621ZM6.04297 10.625H13.9596V9.375H6.04297V10.625ZM6.04297 7.38771H13.9596V6.13792H6.04297V7.38771ZM10.0013 3.62187C10.1819 3.62187 10.3312 3.56285 10.4492 3.44479C10.5673 3.32674 10.6263 3.17743 10.6263 2.99687C10.6263 2.81632 10.5673 2.66701 10.4492 2.54896C10.3312 2.4309 10.1819 2.37187 10.0013 2.37187C9.82075 2.37187 9.67144 2.4309 9.55339 2.54896C9.43533 2.66701 9.3763 2.81632 9.3763 2.99687C9.3763 3.17743 9.43533 3.32674 9.55339 3.44479C9.67144 3.56285 9.82075 3.62187 10.0013 3.62187Z"
										fill="currentColor"
									/>
								</g>
							</svg>
						</div>

						<!-- Label -->
						<div
							class="self-center translate-y-[0.5px] transition-all duration-300 ease-in-out"
							class:hidden={!$showSidebar}
						>
							<div class="self-center link-style text-typography-titles">
								{$i18n.t('Notes')}
							</div>
						</div>
					</a>
				</div>
			{/if}

			{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models || $user?.permissions?.workspace?.knowledge || $user?.permissions?.workspace?.prompts || $user?.permissions?.workspace?.tools}
				<div class="flex justify-center text-gray-800 dark:text-gray-200">
					<a
						class="px-[16px] py-[8px] grow flex items-center rounded-lg hover:bg-gradient-bg-2 dark:hover:bg-gray-900 transition-all duration-300 ease-in-out"
						class:justify-center={!$showSidebar}
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
						<!-- Icon -->
						<div
							class="flex items-center self-center transition-all duration-300 ease-in-out"
							class:me-[8px]={$showSidebar}
						>
							<MaterialIcon name="workspaces" size="1.1rem" />
						</div>

						<!-- Label -->
						<div
							class="self-center translate-y-[0.5px] transition-all duration-300 ease-in-out"
							class:hidden={!$showSidebar}
						>
							<div class="self-center link-style text-typography-titles">
								{$i18n.t('Workspace')}
							</div>
						</div>
					</a>
				</div>
			{/if}

			<div class="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
				{#if false && ($models ?? []).length > 0 && ($settings?.pinnedModels ?? []).length > 0}
					<div class="mt-0.5">
						{#each $settings.pinnedModels as modelId (modelId)}
							{@const model = $models.find((model) => model.id === modelId)}
							{#if model}
								<div class="p-[14px] flex justify-center text-gray-800 dark:text-gray-200">
									<a
										class="grow flex items-center space-x-2.5 rounded-lg px-2 py-[7px] hover:bg-gray-100 dark:hover:bg-gray-900 transition"
										href="/?model={modelId}"
										on:click={() => {
											selectedChatId = null;
											chatId.set('');

											if ($mobile) {
												showSidebar.set(false);
											}
										}}
										draggable="false"
									>
										<div class="self-center shrink-0">
											<img
												crossorigin="anonymous"
												src={model?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
												class=" size-5 rounded-full -translate-x-[0.5px]"
												alt="logo"
											/>
										</div>

										<div class="self-center translate-y-[0.5px] {$showSidebar ? '' : 'hidden'}">
											<div class=" self-center link-style text-typography-titles line-clamp-1">
												{model?.name ?? modelId}
											</div>
										</div>
									</a>
								</div>
							{/if}
						{/each}
					</div>
				{/if}

				{#if $config?.features?.enable_channels && ($user?.role === 'admin' || $channels.length > 0)}
					<Folder
						className=" mt-0.5"
						name={$i18n.t('Channels')}
						dragAndDrop={false}
						showSidebar={$showSidebar}
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

				{#if $user?.role === 'admin'}
				<Folder
					className=""
					name={$i18n.t('Folders')}
					onAdd={() => {
						createFolder();
					}}
					onAddLabel={$i18n.t('New Folder')}
					showSidebar={$showSidebar}
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
									const res = await updateChatFolderIdById(localStorage.token, chat.id, null).catch(
										(error) => {
											toast.error(`${error}`);
											return null;
										}
									);
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

				{#if false && $pinnedChats.length > 0}
					<div class="flex flex-col space-y-1 rounded-xl">
						<Folder
							className="px-2"
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
								class="ml-3 pl-1 mt-[1px] flex flex-col overflow-y-auto scrollbar-hidden border-s border-gray-100 dark:border-gray-900"
							>
								{#each $pinnedChats as chat, idx (`pinned-chat-${chat?.id ?? idx}`)}
									<ChatItem
										className=""
										id={chat.id}
										title={chat.title}
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
				{/if}

				{#if $showSidebar && $pinnedChats.length > 0}
					<div class="flex flex-col space-y-1 rounded-xl">
						<div
							class="px-[16px] py-[8px] pt-[20px] mt-[12px] text-[12px] sm:text-[14px] leading-[22px] text-typography-secondary-body-text font-medium"
						>
							{$i18n.t('Pinned Chats')}
						</div>
						<div class="flex flex-col space-y-1 rounded-xl">
							{#each $pinnedChats as chat, idx (`pinned-chat-${chat?.id ?? idx}`)}
								<ChatItem
											className=""
											id={chat.id}
											title={chat.title}
											{shiftKey}
											selected={selectedChatId === chat.id}
											
											on:change={async () => {
												initChatList();
											}}
											
										/>
							{/each}
						</div>
					</div>
				{/if}

				<div class="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
					{#if $showSidebar}
						<div class=" flex-1 flex flex-col overflow-y-auto scrollbar-hidden">
							<div class="py-1.5">
								{#if $chats}
									{#each $chats as chat, idx (`chat-${chat?.id ?? idx}`)}
										{#if idx === 0 || (idx > 0 && chat.time_range !== $chats[idx - 1].time_range)}
											<div
												class="w-full px-[16px] py-[8px] pt-[20px] mt-[12px] text-[12px] sm:text-[14px] leading-[22px] text-typography-secondary-body-text font-medium border-t border-gray-100 dark:border-gray-900 {idx ===
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
												<div class=" ">{$i18n.t('Loading')}</div>
											</div>
										</Loader>
									{/if}
								{:else}
									<div
										class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2"
									>
										<Spinner className=" size-4" />
										<div class=" ">{$i18n.t('Loading')}</div>
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
		<div class="p-[8px] pb-[24px] sidebar__bottom">
			<div class="w-full flex flex-col left-[20px] bottom-[20px] dark:border-gray-900">
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
							class="px-[12px] py-[8px] flex items-center justify-between cursor-pointer rounded-xl w-full hover:bg-gradient-bg-2 dark:hover:bg-gray-900 {$showSidebar
								? ''
								: 'justify-center'}"
							on:click={() => {
								showDropdown = !showDropdown;
							}}
						>
							<div class="flex">
								<div class=" self-center {$showSidebar ? 'me-[8px]' : ''}">
									<img
										src={$user?.profile_image_url}
										class=" max-w-[30px] object-cover rounded-full"
										alt="User profile"
									/>
								</div>
								<div
									class="self-center link-style text-typography-titles {$showSidebar
										? ''
										: 'hidden'}"
								>
									{$user?.name}
								</div>
							</div>
							{#if $showSidebar}
								<div>
									{#if $isRTL}
										<ChevronLeft />
									{:else}
										<ChevronRight />
									{/if}
								</div>
							{/if}
						</button>
					</UserMenu>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.scrollbar-hidden:active::-webkit-scrollbar-thumb,
	.scrollbar-hidden:focus::-webkit-scrollbar-thumb,
	.scrollbar-hidden:hover::-webkit-scrollbar-thumb {
		visibility: visible;
	}
	.scrollbar-hidden::-webkit-scrollbar-thumb {
		visibility: hidden;
	}
</style>
