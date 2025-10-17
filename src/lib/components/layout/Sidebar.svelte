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
	import Plus from '../icons/Plus.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Folders from './Sidebar/Folders.svelte';
	import { getChannels, createNewChannel } from '$lib/apis/channels';
	import ChannelModal from './Sidebar/ChannelModal.svelte';
	import ChannelItem from './Sidebar/ChannelItem.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import Home from '../icons/Home.svelte';
	import MagnifyingGlass from '../icons/MagnifyingGlass.svelte';
	import SearchModal from './SearchModal.svelte';
	import PersonalStore from '../personas/PersonalStore.svelte';
	import { childProfileSync } from '$lib/services/childProfileSync';
	import type { ChildProfile } from '$lib/apis/child-profiles';

	const BREAKPOINT = 768;

	let navElement;
	let shiftKey = false;

	let selectedChatId = null;
	let showDropdown = false;
	let showPinnedChat = true;

	let showCreateChannel = false;
	let showPersonalStore = false;
	let currentPersonal = null;

	// Pagination variables
	let chatListLoading = false;
	let allChatsLoaded = false;

	let folders = {};
	let newFolderId = null;

	// Child profile state
	let childProfiles: ChildProfile[] = [];
	let currentChild: ChildProfile | null = null;
	let selectedChildIndex: number = 0;

	// Assignment workflow state
	let assignmentStep: number = 1; // 1: child-profile, 2: moderation-scenario, 3: exit-survey
	let showAssignmentSetup: boolean = false;
	let assignmentCompleted: boolean = false;
	let moderationScenariosAccessed: boolean = false; // Track if user has accessed moderation scenarios

	// Make assignmentStep reactive to localStorage changes
	$: if (typeof window !== 'undefined') {
		const storedStep = localStorage.getItem('assignmentStep');
		if (storedStep) {
			assignmentStep = parseInt(storedStep);
		}
		const moderationAccessed = localStorage.getItem('moderationScenariosAccessed');
		moderationScenariosAccessed = moderationAccessed === 'true';
	}

	// Listen for localStorage changes from other tabs/windows
	onMount(() => {
		// Check assignment step on mount
		const storedStep = localStorage.getItem('assignmentStep');
		if (storedStep) {
			assignmentStep = parseInt(storedStep);
		}
		
		// Check moderation scenarios access on mount
		const moderationAccessed = localStorage.getItem('moderationScenariosAccessed');
		moderationScenariosAccessed = moderationAccessed === 'true';
		
		const handleStorageChange = (e) => {
			if (e.key === 'assignmentStep' && e.newValue) {
				assignmentStep = parseInt(e.newValue);
			}
			if (e.key === 'moderationScenariosAccessed' && e.newValue) {
				moderationScenariosAccessed = e.newValue === 'true';
			}
		};
		
		window.addEventListener('storage', handleStorageChange);
		
		return () => {
			window.removeEventListener('storage', handleStorageChange);
		};
	});

	// 加载当前选择的personal
	const loadCurrentPersonal = () => {
		const selectedId = localStorage.getItem('selectedPersonalId');
		if (selectedId) {
			const personals = JSON.parse(localStorage.getItem('personals') || '[]');
			currentPersonal = personals.find(p => p.id === selectedId) || null;
		}
	};

	const handlePersonalSelected = (event) => {
		currentPersonal = event.detail;
	};

	// Child profile functions
	const loadChildProfiles = async () => {
		try {
			console.log('Loading child profiles in sidebar...');
			childProfiles = await childProfileSync.getChildProfiles();
			// Ensure childProfiles is always an array
			if (!childProfiles || !Array.isArray(childProfiles)) {
				console.warn('Child profiles returned invalid value, defaulting to empty array');
				childProfiles = [];
			}
			console.log('Loaded child profiles:', childProfiles);
			const currentChildId = childProfileSync.getCurrentChildId();
			console.log('Current child ID:', currentChildId);
				
				if (currentChildId && childProfiles.length > 0) {
					const index = childProfiles.findIndex(child => child.id === currentChildId);
					if (index !== -1) {
						selectedChildIndex = index;
						currentChild = childProfiles[index];
						console.log('Selected child:', currentChild);
					} else {
						selectedChildIndex = 0;
						currentChild = childProfiles[0];
						console.log('Using first child as default:', currentChild);
					}
				} else if (childProfiles.length > 0) {
					// No current child selected, use the first one
					selectedChildIndex = 0;
					currentChild = childProfiles[0];
					console.log('No current child, using first:', currentChild);
				}
		} catch (error) {
			console.error('Failed to load child profiles:', error);
			childProfiles = [];
			currentChild = null;
		}
	};


	// Track the current role to avoid infinite loops
	let lastKnownRole: string | null = '';
	
	// Reactive statement to reload child profiles when role changes
	$: if (typeof window !== 'undefined') {
		const currentRole = localStorage.getItem('selectedRole');
		if (currentRole !== lastKnownRole) {
			lastKnownRole = currentRole;
			if (currentRole === 'kids') {
				loadChildProfiles();
				// Check if we need to show assignment setup
				checkAssignmentSetup();
			} else {
				childProfiles = [];
				currentChild = null;
				selectedChildIndex = 0;
			}
		}
	}

	// Assignment workflow functions
	function checkAssignmentSetup() {
		// Check if user has completed child profile setup
		const hasChildProfile = localStorage.getItem('assignmentStep') !== null;
		const currentStep = localStorage.getItem('assignmentStep');
		
		if (!hasChildProfile || !currentStep) {
			showAssignmentSetup = true;
			assignmentStep = 1;
		} else {
			assignmentStep = parseInt(currentStep) || 1;
		}
	}

	function proceedToNextStep() {
		if (assignmentStep < 3) {
			assignmentStep++;
			localStorage.setItem('assignmentStep', assignmentStep.toString());
		} else {
			assignmentCompleted = true;
			localStorage.setItem('assignmentCompleted', 'true');
		}
	}

	function goToStep(step: number) {
		// Only allow going to previous steps or current step
		const currentStep = parseInt(localStorage.getItem('assignmentStep') || '1');
		if (step <= currentStep) {
			assignmentStep = step;
			goto(getStepRoute(step));
		}
	}

	function getStepRoute(step: number): string {
		switch (step) {
			case 1: return '/kids/profile';
			case 2: return '/moderation-scenario';
			case 3: return '/exit-survey';
			case 4: return '/completion';
			default: return '/kids/profile';
		}
	}

	function startAssignment() {
		showAssignmentSetup = false;
		localStorage.setItem('assignmentStep', '1');
		assignmentStep = 1;
		goto('/kids/profile');
	}

	// Function to update assignment step when user completes tasks
	function updateAssignmentStep(step: number) {
		localStorage.setItem('assignmentStep', step.toString());
		assignmentStep = step;
	}

	// Listen for navigation events to update assignment progress
	$: if (typeof window !== 'undefined') {
		const currentPath = window.location.pathname;
		if (currentPath === '/kids/profile' && assignmentStep < 2) {
			updateAssignmentStep(1);
		} else if (currentPath === '/moderation-scenario' && assignmentStep < 3) {
			updateAssignmentStep(2);
		} else if (currentPath === '/exit-survey' && assignmentStep < 4) {
			updateAssignmentStep(3);
		} else if (currentPath === '/completion') {
			updateAssignmentStep(4);
			assignmentCompleted = true;
		}
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

		loadCurrentPersonal();
		await loadChildProfiles();
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

<PersonalStore 
	bind:open={showPersonalStore} 
	on:personalSelected={handlePersonalSelected}
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


<!-- Assignment Overview Popup -->
{#if showAssignmentSetup}
<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
	<div class="bg-white dark:bg-gray-800 rounded-xl p-8 max-w-2xl w-full mx-4 shadow-2xl">
		<div class="text-center mb-6">
			<h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">
				Welcome to the AI Moderation Assignment
			</h2>
			<p class="text-gray-600 dark:text-gray-300 mb-6">
				You'll be completing a 3-step assignment to help us understand how AI moderation works with children's conversations.
			</p>
		</div>

		<div class="space-y-4 mb-8">
			<div class="flex items-center space-x-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
				<div class="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">1</div>
				<div>
					<h3 class="font-semibold text-gray-900 dark:text-white">Child Profile Setup</h3>
					<p class="text-sm text-gray-600 dark:text-gray-300">Create and select a child profile for the assignment</p>
				</div>
			</div>
			
			<div class="flex items-center space-x-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
				<div class="w-8 h-8 bg-purple-500 text-white rounded-full flex items-center justify-center font-bold">2</div>
				<div>
					<h3 class="font-semibold text-gray-900 dark:text-white">Moderation Scenarios</h3>
					<p class="text-sm text-gray-600 dark:text-gray-300">Review and moderate AI responses to children's questions</p>
				</div>
			</div>
			
			<div class="flex items-center space-x-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
				<div class="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center font-bold">3</div>
				<div>
					<h3 class="font-semibold text-gray-900 dark:text-white">Exit Survey</h3>
					<p class="text-sm text-gray-600 dark:text-gray-300">Provide feedback on your moderation experience</p>
				</div>
			</div>
		</div>

		<div class="text-center">
			<button
				on:click={startAssignment}
				class="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white px-8 py-3 rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
			>
				Start Assignment - Step 1
			</button>
		</div>
	</div>
</div>
{/if}

<div
	bind:this={navElement}
	id="sidebar"
	class="h-screen max-h-[100dvh] min-h-screen select-none {$showSidebar
		? 'md:relative w-[260px] max-w-[260px]'
		: '-translate-x-[260px] w-[0px]'} {$isApp
		? `ml-[4.5rem] md:ml-0 `
		: 'transition-width duration-200 ease-in-out'}  shrink-0 bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-200 text-sm fixed z-50 top-0 left-0 overflow-x-hidden
        "
	data-state={$showSidebar}
>
	<div
		class="py-2 flex flex-col justify-start h-screen max-h-[100dvh] w-[260px] overflow-x-hidden z-50 {$showSidebar
			? ''
			: 'invisible'}"
	>
		<!-- Top element with hamburger menu, title, and fill space -->
	<div class="px-1.5 flex justify-between space-x-1 text-gray-600 dark:text-gray-400">
		<button
			class="cursor-pointer p-[7px] flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-900 transition"
			on:click={() => {
				showSidebar.set(!$showSidebar);
			}}
		>
			<div class="m-auto self-center">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"></path>
				</svg>
			</div>
		</button>
		<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide flex items-center">
			Assignment Steps
		</h3>
		<div class="flex-1 min-h-0"></div>
	</div>

			<!-- Hidden New Chat button -->
			<!--
			<a
				id="sidebar-new-chat-button"
				class="flex justify-between items-center flex-1 rounded-lg px-2 py-1 h-full text-right hover:bg-gray-100 dark:hover:bg-gray-900 transition no-drag-region"
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
				<div class="flex items-center">
					<div class="self-center mx-1.5">
						<img
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class="sidebar-new-chat-icon size-5 -translate-x-1.5 rounded-full"
							alt="logo"
						/>
					</div>
					<div class=" self-center font-medium text-sm text-gray-850 dark:text-white font-primary">
						{$i18n.t('New Chat')}
					</div>
				</div>

				<div>
					<PencilSquare className=" size-5" strokeWidth="2" />
				</div>
			</a>
			-->


		<!-- Hidden pinned models section -->
		<!--
		<div class="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
			{#if ($models ?? []).length > 0 && ($settings?.pinnedModels ?? []).length > 0}
				<div class="mt-0.5">
					{#each $settings.pinnedModels as modelId (modelId)}
						{@const model = $models.find((model) => model.id === modelId)}
						{#if model}
							<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
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

									<div class="flex self-center translate-y-[0.5px]">
										<div class=" self-center font-medium text-sm font-primary line-clamp-1">
											{model?.name ?? modelId}
										</div>
									</div>
								</a>
							</div>
						{/if}
					{/each}
				</div>
			{/if}
		-->

		<!-- Hidden channels section -->
		<!--
			{#if $config?.features?.enable_channels && ($user?.role === 'admin' || $channels.length > 0)}
				<Folder
					className="px-2 mt-0.5"
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
		-->

		<!-- Hidden chat history section -->
		{#if false}
			<Folder
				className="px-2 mt-0.5"
				name={$i18n.t('Chats')}
				onAdd={() => {
					createFolder();
				}}
				onAddLabel={$i18n.t('New Folder')}
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
				{#if $pinnedChats.length > 0}
					<div class="flex flex-col space-y-1 rounded-xl">
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
										<div class=" ">Loading...</div>
									</div>
								</Loader>
							{/if}
						{:else}
							<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
								<Spinner className=" size-4" />
								<div class=" ">Loading...</div>
							</div>
						{/if}
					</div>
				</div>
			</Folder>
		{/if}

		<div class="px-2">
			<div class="flex flex-col font-primary">
			<!-- Assignment Navigation - moved to bottom -->
			{#if true}

					<!-- Grey divider above instructions -->
					<div class="px-4 py-2">
						<div class="border-b border-gray-200 dark:border-gray-700"></div>
					</div>

					<!-- Instructions Tab -->
					<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
						<a
							href="/assignment-instructions"
							class="grow flex items-center space-x-3 rounded-lg px-2 py-[7px] hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => {
								selectedChatId = null;
								chatId.set('');

								if ($mobile) {
									showSidebar.set(false);
								}
							}}
						>
							<div class="self-center">
								<div class="w-6 h-6 rounded-full flex items-center justify-center bg-gray-500 text-white">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
									</svg>
								</div>
							</div>
							<div class="flex self-center translate-y-[0.5px]">
								<div class="font-medium text-sm font-primary">Instructions</div>
							</div>
						</a>
					</div>

					<!-- Grey divider below instructions and above assignment steps -->
					<div class="px-4 py-2">
						<div class="border-b border-gray-200 dark:border-gray-700"></div>
					</div>

					<!-- Step 1: Child Profile -->
					<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
						<div class="grow flex items-center space-x-3 rounded-lg px-2 py-[7px] transition {assignmentStep >= 1 ? 'hover:bg-gray-100 dark:hover:bg-gray-900' : 'opacity-50 cursor-not-allowed'}">
							<button
								class="flex items-center space-x-3 flex-1"
								on:click={() => goto('/kids/profile')}
								disabled={assignmentStep < 1}
							>
								<div class="self-center">
									<div class="w-6 h-6 rounded-full flex items-center justify-center {assignmentStep >= 1 ? 'bg-blue-500 text-white' : 'bg-gray-300 dark:bg-gray-600 text-gray-500'}">
										{#if assignmentStep > 1}
											<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
											</svg>
										{:else}
											<span class="text-xs font-bold">1</span>
										{/if}
									</div>
								</div>
								<div class="flex self-center translate-y-[0.5px]">
									<div class="font-medium text-sm font-primary">Child Profile</div>
								</div>
							</button>
							
							<!-- Hidden Edit button -->
							<!--
							<div class="flex space-x-1 ml-auto">
								<a
									href="/kids/profile"
									on:click={() => {
										selectedChatId = null;
										chatId.set('');

										if ($mobile) {
											showSidebar.set(false);
										}
									}}
									class="bg-gradient-to-r from-blue-500 to-purple-600 text-white text-xs font-medium px-2 py-1 rounded hover:from-blue-600 hover:to-purple-700 transition-all duration-200"
									title="Edit Profile"
								>
									Edit
								</a>
							</div>
							-->
						</div>
					</div>

					<!-- Step 2: Moderation Scenarios -->
					<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
						<button
							class="grow flex items-center space-x-3 rounded-lg px-2 py-[7px] transition {assignmentStep >= 2 ? 'hover:bg-gray-100 dark:hover:bg-gray-900' : 'opacity-50 cursor-not-allowed'}"
							on:click={() => {
								if (assignmentStep >= 2) {
									localStorage.setItem('moderationScenariosAccessed', 'true');
									goto('/moderation-scenario');
								}
							}}
							disabled={assignmentStep < 2}
						>
							<div class="self-center">
								<div class="w-6 h-6 rounded-full flex items-center justify-center {assignmentStep >= 2 ? 'bg-purple-500 text-white' : 'bg-gray-300 dark:bg-gray-600 text-gray-500'}">
									{#if assignmentStep > 2}
										<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
										</svg>
									{:else}
										<span class="text-xs font-bold">2</span>
									{/if}
								</div>
							</div>
							<div class="flex self-center translate-y-[0.5px]">
								<div class="font-medium text-sm font-primary">Moderation Scenarios</div>
							</div>
						</button>
					</div>

					<!-- Step 3: Exit Survey -->
					<div class="px-1.5 flex justify-center text-gray-800 dark:text-gray-200">
						<button
							class="grow flex items-center space-x-3 rounded-lg px-2 py-[7px] transition {assignmentStep >= 3 && moderationScenariosAccessed ? 'hover:bg-gray-100 dark:hover:bg-gray-900' : 'opacity-50 cursor-not-allowed'}"
							on:click={() => goToStep(3)}
							disabled={assignmentStep < 3 || !moderationScenariosAccessed}
						>
							<div class="self-center">
								<div class="w-6 h-6 rounded-full flex items-center justify-center {assignmentStep >= 3 && moderationScenariosAccessed ? 'bg-green-500 text-white' : 'bg-gray-300 dark:bg-gray-600 text-gray-500'}">
									{#if assignmentCompleted}
										<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
										</svg>
									{:else}
										<span class="text-xs font-bold">3</span>
									{/if}
								</div>
							</div>
							<div class="flex self-center translate-y-[0.5px]">
								<div class="font-medium text-sm font-primary">Exit Survey</div>
							</div>
						</button>
					</div>

			{/if}
			</div>
		</div>

		<!-- Spacer to push user profile to bottom -->
		<div class="flex-1 min-h-0"></div>

		<div class="px-2">
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
							class=" flex items-center rounded-xl py-2.5 px-2.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => {
								showDropdown = !showDropdown;
							}}
						>
							<div class=" self-center mr-3">
								<img
									src={$user?.profile_image_url}
									class=" max-w-[30px] object-cover rounded-full"
									alt="User profile"
								/>
							</div>
							<div class=" self-center font-medium">{$user?.name}</div>
						</button>
					</UserMenu>
				{/if}

				<!-- Hidden character store -->
				<!--
				{#if currentPersonal}
					<div class="current-personal" on:click={() => showPersonalStore = true}>
						<span class="personal-avatar">{currentPersonal.avatar}</span>
						<span class="personal-name">{currentPersonal.name}</span>
						<span class="personal-prefix">"{currentPersonal.prefix}"</span>
					</div>
				{:else}
					<div class="no-personal" on:click={() => showPersonalStore = true}>
						<span class="personal-avatar">🎭</span>
						<span class="personal-name">Choose Character</span>
					</div>
				{/if}
				-->
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

	.current-personal,
	.no-personal {
		display: flex;
		align-items: center;
		padding: 0.75rem 1rem;
		margin: 0.5rem 0;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
		background: rgba(102, 126, 234, 0.1);
		border: 1px solid rgba(102, 126, 234, 0.2);
	}

	.current-personal:hover,
	.no-personal:hover {
		background: rgba(102, 126, 234, 0.15);
		border-color: rgba(102, 126, 234, 0.3);
	}

	.personal-avatar {
		font-size: 1.5rem;
		margin-right: 0.75rem;
	}

	.personal-name {
		font-weight: 500;
		color: #495057;
		margin-right: 0.5rem;
	}

	.personal-prefix {
		font-size: 0.8rem;
		color: #667eea;
		font-style: italic;
	}

	.no-personal .personal-name {
		color: #6c757d;
	}
</style>
