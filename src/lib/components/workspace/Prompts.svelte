<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';
	import {
		WEBUI_NAME,
		config,
		prompts as _prompts,
		user,
		showSidebar,
		mobile,
		theme
	} from '$lib/stores';

	import {
		createNewPrompt,
		deletePromptByCommand,
		getPrompts,
		getPromptList,
		getUserTagsForPrompts
	} from '$lib/apis/prompts';

	import PromptMenu from './Prompts/PromptMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import { capitalizeFirstLetter, tagColorsLight } from '$lib/utils';
	import ShowSidebarIcon from '../icons/ShowSidebarIcon.svelte';
	import { getGroups } from '$lib/apis/groups';
	import GroupIcon from '../icons/GroupIcon.svelte';
	import PublicIcon from '../icons/PublicIcon.svelte';
	import PrivateIcon from '../icons/PrivateIcon.svelte';
	import MenuIcon from '../icons/MenuIcon.svelte';
	import FilterDropdown from './Models/FilterDropdown.svelte';
	import BackIcon from '../icons/BackIcon.svelte';
	import BookmarkIcon from '../icons/BookmarkIcon.svelte';
	import BookmarkedIcon from '../icons/BookmarkedIcon.svelte';
	import { bookmarkPrompt } from '$lib/apis/prompts';

	const i18n = getContext('i18n');
	let promptsImportInputElement: HTMLInputElement;
	let loaded = false;

	let importFiles = '';
	let query = '';
	let showInput = false;

	let prompts = [];

	let showDeleteConfirm = false;
	let deletePrompt = null;

	let tags = [];
	let selectedTags = new Set();
	let filteredItems = [];
	let accessFilter = 'all';
	let groupsForPrompts = [];

	let loadingBookmark = null;

	// $: if (prompts) {
	// 	tags = Array.from(
	// 		new Set(prompts.flatMap((p) => p.meta?.tags?.map((t) => t.name) || []))
	// 	);
	// }

	onMount(async () => {
		groupsForPrompts = await getGroups(localStorage.token);
	});

	$: {
		filteredItems = prompts.filter((p) => {
			const nameMatch = query === '' || p.command.includes(query);
			const isPublic = p.access_control === null && !p.prebuilt;
			// const isPrivate = p.access_control !== null;
			const isPrivate = p?.user_id === $user?.id;
			const isPrebuilt = p.prebuilt;

			const promptTags = p.meta?.tags?.map((t) => t.name.toLowerCase()) || [];

			const tagsMatch =
				selectedTags.size === 0 ||
				Array.from(selectedTags)
					?.map((tag) => tag?.toLowerCase())
					?.some((tag) => promptTags.includes(tag));

			const accessMatch =
				accessFilter === 'all' ||
				(accessFilter === 'public' && isPublic) ||
				(accessFilter === 'private' && isPrivate) ||
				(accessFilter === 'pre-built' && isPrebuilt);

			return nameMatch && accessMatch && tagsMatch;
		});
	}

	const shareHandler = async (prompt) => {
		toast.success($i18n.t('Redirecting you to OpenWebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/prompts/create`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(JSON.stringify(prompt), '*');
				}
			},
			false
		);
	};

	const cloneHandler = async (prompt) => {
		sessionStorage.prompt = JSON.stringify(prompt);
		goto('/workspace/prompts/create');
	};

	const exportHandler = async (prompt) => {
		let blob = new Blob([JSON.stringify([prompt])], {
			type: 'application/json'
		});
		saveAs(blob, `prompt-export-${Date.now()}.json`);
	};

	const deleteHandler = async (prompt) => {
		const command = prompt.command;
		await deletePromptByCommand(localStorage.token, command);
		await init();
	};

	const init = async () => {
		prompts = await getPromptList(localStorage.token);
		await _prompts.set(await getPrompts(localStorage.token));
	};

	const getTags = async () => {
		const res = await getUserTagsForPrompts(localStorage.token);
		tags = res.filter((tag) => tag.is_system).map((tag) => tag.name);
	};

	onMount(async () => {
		await init();
		await getTags();
		loaded = true;
	});

	function getGroupNamesFromAccess(model) {
		if (!model.access_control) return [];

		const readGroups = model.access_control.read?.group_ids || [];
		const writeGroups = model.access_control.write?.group_ids || [];

		const allGroupIds = Array.from(new Set([...readGroups, ...writeGroups]));

		const matchedGroups = allGroupIds
			.map((id) => groupsForPrompts.find((g) => g.id === id))
			.filter(Boolean)
			.map((g) => g.name);

		return matchedGroups;
	}
	let scrollContainer;

	function updateScrollHeight() {
		const header = document.getElementById('prompts-header');
		const filters = document.getElementById('prompts-filters');

		if (header && filters && scrollContainer) {
			const totalOffset = header.offsetHeight + filters.offsetHeight;
			scrollContainer.style.height = `calc(100dvh - ${totalOffset}px)`;
		}
	}

	onMount(() => {
		window.addEventListener('resize', updateScrollHeight);
		return () => {
			window.removeEventListener('resize', updateScrollHeight);
		};
	});
	$: if (loaded) {
		setTimeout(() => {
			updateScrollHeight();
		}, 0);
	}
	let hoveredPrompt = null;
	let menuIdOpened = null;

	const bookmarkPromptHandler = async (command) => {
		loadingBookmark = command;
		const res = await bookmarkPrompt(localStorage.token, command);
		if (res) {
			prompts = await getPromptList(localStorage.token);
			_prompts.set(await getPrompts(localStorage.token));
		}
		loadingBookmark = null;
	};
</script>

<svelte:head>
	<title>
		{$i18n.t('Prompts')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete prompt?')}
		on:confirm={() => {
			deleteHandler(deletePrompt);
		}}
	>
		<div class=" text-sm text-gray-500">
			{$i18n.t('This will delete')} <span class="  font-semibold">{deletePrompt.command}</span>.
		</div>
	</DeleteConfirmDialog>

	<div
		id="prompts-header"
		class="pl-4 md:pl-[22px] pr-4 py-2.5 border-b border-lightGray-400 dark:border-customGray-700"
	>
		<div class="flex justify-between items-center">
			<div class="flex items-center">
				<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
					{#if $mobile}
						<button class="flex items-center gap-1" on:click={() => history.back()}>
							<BackIcon />
							<div
								class="flex items-center md:self-center text-base font-medium leading-none px-0.5 text-lightGray-100 dark:text-customGray-100"
							>
								{$i18n.t('Prompts')}
							</div>
						</button>
					{:else}
						<button
							id="sidebar-toggle-button"
							class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
							aria-label="Toggle Sidebar"
						>
							<div class=" m-auto self-center">
								<ShowSidebarIcon />
							</div>
						</button>
					{/if}
				</div>
				{#if !$mobile}
					<div
						class="flex items-center text-lightGray-100 dark:text-customGray-100 md:self-center text-base font-medium leading-none px-0.5"
					>
						{$i18n.t('Prompts')}
					</div>
				{/if}
			</div>
			<div class="flex">
				<div
					class="flex flex-1 items-center p-2.5 rounded-lg mr-1 border border-lightGray-400 dark:border-customGray-700 hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:hover:text-white transition"
				>
					<button
						class=""
						on:click={() => {
							showInput = !showInput;
							if (!showInput) query = '';
						}}
						aria-label="Toggle Search"
					>
						<Search className="size-3.5" />
					</button>
					<!-- </div> -->
					{#if showInput}
						<input
							class="w-[5rem] md:w-full text-xs outline-none text-lightGray-100 dark:text-customGray-100 bg-transparent leading-none pl-2"
							bind:value={query}
							placeholder={$i18n.t('Search Prompts')}
							autofocus
							on:blur={() => {
								if (query.trim() === '') showInput = false;
							}}
						/>
					{/if}
				</div>
				<div>
					<a
						class=" px-2 py-2.5 md:w-[220px] rounded-lg leading-none border border-lightGray-400 dark:border-customGray-700 hover:bg-lightGray-700 dark:hover:bg-customGray-950 text-lightGray-100 dark:text-customGray-200 dark:hover:text-white transition font-medium text-xs flex items-center justify-center space-x-1"
						href="/workspace/prompts/create"
					>
						<Plus className="size-3.5" />
						<span class="">{$i18n.t('Create new')}</span>
					</a>
				</div>
			</div>
		</div>
	</div>

	<div class="pl-4 md:pl-[22px] pr-4">
		<div id="prompts-filters" class="flex justify-between py-5 md:pr-[22px] flex-row items-start">
			<div class="flex items-start space-x-[5px] flex-col sm:flex-row mb-3 sm:mb-0">
				{#if $mobile}
					<FilterDropdown>
						<div class="flex flex-wrap gap-1">
							{#each tags as tag, i}
								<button
									style={`background-color: ${
										$theme === 'light' ? tagColorsLight[i % tagColorsLight.length] : ''
									}`}
									class={`font-medium flex items-center justify-center rounded-md text-xs leading-none px-[6px] py-[6px] ${selectedTags.has(tag) ? 'dark:bg-customBlue-800 bg-customViolet-200' : 'bg-lightGray-400 dark:bg-customGray-800'} dark:text-white`}
									on:click={() => {
										selectedTags.has(tag) ? selectedTags.delete(tag) : selectedTags.add(tag);
										selectedTags = new Set(selectedTags);
									}}
								>
									{$i18n.t(tag)}
								</button>
							{/each}
						</div>
					</FilterDropdown>
				{:else}
					<div
						class="font-medium text-lightGray-100 dark:text-customGray-300 text-xs whitespace-nowrap h-[22px] flex items-center mb-2 sm:mb-0"
					>
						{$i18n.t('Filter by category:')}
					</div>
					<div class="flex flex-wrap gap-1">
						{#each tags as tag, i}
							<button
								style={`background-color: ${
									$theme === 'light' ? tagColorsLight[i % tagColorsLight.length] : ''
								}`}
								class={`font-medium flex items-center justify-center rounded-md text-xs leading-none px-[6px] py-[6px] ${selectedTags.has(tag) ? 'dark:bg-customBlue-800 bg-customViolet-200' : 'bg-lightGray-400 hover:bg-customViolet-200 dark:bg-customGray-800 dark:hover:bg-customBlue-800'} dark:text-white`}
								on:click={() => {
									selectedTags.has(tag) ? selectedTags.delete(tag) : selectedTags.add(tag);
									selectedTags = new Set(selectedTags);
								}}
							>
								{$i18n.t(tag)}
							</button>
						{/each}
					</div>
				{/if}
			</div>
			<div class="flex bg-lightGray-700 dark:bg-customGray-800 rounded-md flex-shrink-0">
				<button
					on:click={() => (accessFilter = 'all')}
					class={`${accessFilter === 'all' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-2 md:px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('All')}</button
				>
				<button
					on:click={() => (accessFilter = 'private')}
					class={`${accessFilter === 'private' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-2 md:px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('My Prompts')}</button
				>
				<button
					on:click={() => (accessFilter = 'public')}
					class={`${accessFilter === 'public' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-2 md:px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('Public')}</button
				>
				<button
					on:click={() => (accessFilter = 'pre-built')}
					class={`${accessFilter === 'pre-built' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-2 md:px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('Pre-built')}</button
				>
			</div>
		</div>
		<div
			id="prompts-scroll-container"
			bind:this={scrollContainer}
			class="overflow-y-scroll pr-[3px]"
		>
			{#if filteredItems.length === 0}
				{#if selectedTags?.size > 0}
					<div class="flex h-[calc(100dvh-200px)] w-full justify-center items-center">
						<div class="text-sm dark:text-customGray-100/50">
							{$i18n.t('No prompts match the selected filters')}
						</div>
					</div>
				{:else}
					<div class="flex h-[calc(100dvh-200px)] w-full justify-center items-center">
						<div class="text-sm dark:text-customGray-100/50">
							{$i18n.t('No prompts created yet')}
						</div>
					</div>
				{/if}
			{/if}
			<!-- {#if prompts?.length < 1}
				<div class="flex h-[calc(100dvh-200px)] w-full justify-center items-center">
					<div class="text-sm dark:text-customGray-100/50">{$i18n.t('No Prompts created yet')}</div>
				</div>
			{/if} -->
			<div class="mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
				{#each filteredItems as prompt}
					<div
						on:mouseenter={() => (hoveredPrompt = prompt.command)}
						on:mouseleave={() => (hoveredPrompt = null)}
						class=" group flex flex-col gap-y-1 cursor-pointer w-full px-3 py-2 bg-lightGray-550 dark:bg-customGray-800 rounded-2xl transition"
					>
						<div class="flex items-start justify-between">
							<div class="flex items-center">
								{#if loadingBookmark === prompt?.command}
									<Spinner className="size-3 mr-1" />
								{:else}
									<button
										on:click={() => bookmarkPromptHandler(prompt.command)}
										class="text-lightGray-100 dark:text-customGray-300 mr-1"
									>
										{#if prompt?.bookmarked_by_user}
											<BookmarkedIcon />
										{:else}
											<BookmarkIcon />
										{/if}
									</button>
								{/if}

								<div class="flex items-center gap-1 flex-wrap">
									{#if prompt.access_control == null && prompt.prebuilt}
										<div
											class="flex gap-1 items-center {hoveredPrompt === prompt.command ||
											menuIdOpened === prompt.command
												? 'dark:text-white'
												: 'dark:text-customGray-300'} text-lightGray-100 font-medium bg-lightGray-400 text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
										>
											<span>{$i18n.t('Prebuilt')}</span>
										</div>
									{:else if prompt.access_control == null}
										<div
											class="flex gap-1 items-center {hoveredPrompt === prompt.command ||
											menuIdOpened === prompt.command
												? 'dark:text-white'
												: 'dark:text-customGray-300'} text-lightGray-100 font-medium bg-lightGray-400 text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
										>
											<PublicIcon />
											<span>{$i18n.t('Public')}</span>
										</div>
									{:else if getGroupNamesFromAccess(prompt).length < 1}
										<div
											class="flex gap-1 items-center {hoveredPrompt === prompt.command ||
											menuIdOpened === prompt.command
												? 'dark:text-white'
												: 'dark:text-customGray-300'} text-lightGray-100 font-medium bg-lightGray-400 text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
										>
											<PrivateIcon />
											<span>{$i18n.t('Private')}</span>
										</div>
									{:else}
										{#each getGroupNamesFromAccess(prompt) as groupName}
											<div
												class="flex gap-1 items-center {hoveredPrompt === prompt.command ||
												menuIdOpened === prompt.command
													? 'dark:text-white'
													: 'dark:text-customGray-300'} text-lightGray-100 font-medium bg-lightGray-400 text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
											>
												<GroupIcon />
												<span>{groupName}</span>
											</div>
										{/each}
									{/if}
									{#if prompt.meta && Array.isArray(prompt.meta.tags)}
										{#each prompt?.meta?.tags as promptTag}
											<div
												class="flex items-center {hoveredPrompt === prompt.command ||
												menuIdOpened === prompt.command
													? 'dark:text-white'
													: 'dark:text-customGray-100'} text-xs text-lightGray-100 font-medium bg-customViolet-200 dark:bg-customBlue-800 px-[6px] py-[3px] rounded-md"
											>
												{$i18n.t(promptTag.name)}
											</div>
										{/each}
									{/if}
								</div>
							</div>
							{#if !prompt.prebuilt && (prompt.user_id === $user?.id || $user?.role === 'admin')}
								<div
									class={hoveredPrompt === prompt.command || menuIdOpened === prompt.command
										? 'md:visible'
										: 'md:invisible'}
								>
									<PromptMenu
										{prompt}
										shareHandler={() => {
											shareHandler(prompt);
										}}
										cloneHandler={() => {
											cloneHandler(prompt);
										}}
										exportHandler={() => {
											exportHandler(prompt);
										}}
										deleteHandler={async () => {
											deletePrompt = prompt;
											showDeleteConfirm = true;
										}}
										onClose={() => {}}
										on:openMenu={() => {
											menuIdOpened = prompt.command;
										}}
										on:closeMenu={() => {
											menuIdOpened = null;
										}}
									>
										<button
											class="self-center w-fit text-sm px-0.5 h-[21px] dark:text-white dark:hover:text-white rounded-md"
											type="button"
										>
											<EllipsisHorizontal className="size-5" />
										</button>
									</PromptMenu>
								</div>
							{/if}
						</div>
						<div class=" flex flex-1 space-x-4 cursor-pointer w-full">
							<button
								type="button"
								class="w-full"
								on:click={() => {
									localStorage.setItem('selectedPrompt', JSON.stringify(prompt));
									goto('/');
								}}
							>
								<div class=" flex-1 flex items-center gap-2 self-center">
									<div
										class="text-left text-base line-clamp-1 capitalize text-lightGray-100 {hoveredPrompt ===
											prompt.command || menuIdOpened === prompt.command
											? 'dark:text-white'
											: 'dark:text-customGray-100'}"
									>
										{prompt.title}
									</div>
								</div>
								<div
									class="text-xs line-clamp-1 text-lightGray-1200 dark:text-customGray-100/50 text-left"
								>
									{prompt.description}
								</div>
							</button>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
