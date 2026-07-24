<script lang="ts">
	import dayjs from 'dayjs';

	import { onMount, onDestroy, getContext, createEventDispatcher, tick } from 'svelte';
	import { searchNotes } from '$lib/apis/notes';
	import {
		searchKnowledgeBases,
		searchKnowledgeFiles,
		searchKnowledgeFilesById
	} from '$lib/apis/knowledge';

	import { decodeString } from '$lib/utils';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let onClose: Function = () => {};

	let show = false;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let noteItems = [];
	let knowledgeItems = [];
	let fileItems = [];

	let items = [];

	$: items = [...noteItems, ...knowledgeItems, ...fileItems];

	// --- Browsing state ---
	let browsingCollection = null;
	let currentDirectoryId = null;
	let browsingFiles = [];
	let browsingDirectories = [];
	let browsingBreadcrumbs = [];
	let browsingLoading = false;

	const handleSearchInput = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (browsingCollection) {
				loadBrowsingItems();
			} else {
				getItems();
			}
		}, 300);
	};

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	const getItems = () => {
		getNoteItems();
		getKnowledgeItems();
		getKnowledgeFileItems();
	};

	const getNoteItems = async () => {
		const res = await searchNotes(localStorage.token, query).catch(() => {
			return null;
		});

		if (res) {
			noteItems = res.items.map((note) => {
				return {
					...note,
					type: 'note',
					name: note.title,
					description: dayjs(note.updated_at / 1000000).fromNow()
				};
			});
		}
	};

	const getKnowledgeItems = async () => {
		const res = await searchKnowledgeBases(localStorage.token, query).catch(() => {
			return null;
		});

		if (res) {
			knowledgeItems = res.items.map((note) => {
				return {
					...note,
					type: 'collection'
				};
			});
		}
	};

	const getKnowledgeFileItems = async () => {
		const res = await searchKnowledgeFiles(localStorage.token, query).catch(() => {
			return null;
		});

		if (res) {
			fileItems = res.items.map((file) => {
				return {
					...file,
					type: 'file',
					name: file.meta?.name || file.filename,
					description: file.description || ''
				};
			});
		}
	};

	// --- Browsing functions ---

	const browseIntoCollection = async (collection) => {
		browsingCollection = collection;
		currentDirectoryId = null;
		await loadBrowsingItems();
	};

	const browseIntoDirectory = async (dir) => {
		currentDirectoryId = dir.id;
		await loadBrowsingItems();
	};

	const navigateBack = async () => {
		if (browsingBreadcrumbs.length > 0) {
			const parentCrumb =
				browsingBreadcrumbs.length >= 2
					? browsingBreadcrumbs[browsingBreadcrumbs.length - 2]
					: null;
			currentDirectoryId = parentCrumb ? parentCrumb.id : null;
			await loadBrowsingItems();
		} else {
			browsingCollection = null;
			currentDirectoryId = null;
			browsingFiles = [];
			browsingDirectories = [];
			browsingBreadcrumbs = [];
		}
	};

	const loadBrowsingItems = async () => {
		if (!browsingCollection) return;
		browsingLoading = true;

		const res = await searchKnowledgeFilesById(
			localStorage.token,
			browsingCollection.id,
			query || null,
			null,
			null,
			null,
			1,
			currentDirectoryId
		).catch(() => null);

		if (res) {
			browsingFiles = res.items || [];
			browsingDirectories = res.directories || [];
			browsingBreadcrumbs = res.breadcrumbs || [];
		}

		browsingLoading = false;
	};

	const selectDirectory = async (dir) => {
		const allFiles = [];
		let page = 1;
		while (true) {
			const res = await searchKnowledgeFilesById(
				localStorage.token,
				browsingCollection.id,
				null,
				null,
				null,
				null,
				page,
				dir.id
			).catch(() => null);

			if (!res || !res.items || res.items.length === 0) break;
			allFiles.push(...res.items);
			if (allFiles.length >= res.total) break;
			page++;
		}

		for (const file of allFiles) {
			dispatch('select', {
				...file,
				type: 'file',
				name: file?.meta?.name || file.filename
			});
		}
		show = false;
	};

	const resetBrowsing = () => {
		browsingCollection = null;
		currentDirectoryId = null;
		browsingFiles = [];
		browsingDirectories = [];
		browsingBreadcrumbs = [];
	};

	onMount(async () => {
		getItems();
	});
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
			query = '';
			handleSearchInput();
			resetBrowsing();
		}
	}}
>
	<slot />

	<div slot="content">
		<div
			class="z-[10000] text-black dark:text-white rounded-xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-64 p-0.5"
		>
			<div class=" flex w-full space-x-1.5 px-1.5 pb-0.5">
				<div class="flex flex-1">
					<div class=" self-center mr-1.5">
						<Search className="size-3.5" />
					</div>
					<input
						class="w-full text-[13px] py-0.5 outline-hidden bg-transparent"
						bind:value={query}
						on:input={handleSearchInput}
						placeholder={$i18n.t('Search')}
					/>
				</div>
			</div>

			<div class="max-h-56 overflow-y-scroll gap-0.5 flex flex-col">
				{#if browsingCollection}
					<!-- Browsing view: inside a knowledge base -->
					<div
						class="px-2 py-1.5 flex items-center gap-1.5 border-b border-gray-100 dark:border-gray-800"
					>
						<button
							type="button"
							class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition"
							on:click={navigateBack}
						>
							<ArrowLeft className="size-3" strokeWidth="2" />
						</button>

						<div class="flex-1 min-w-0">
							<div
								class="text-xs text-gray-500 dark:text-gray-400 truncate flex items-center gap-0.5"
							>
								<button
									type="button"
									class="hover:text-gray-700 dark:hover:text-gray-200 transition truncate"
									on:click={() => {
										if (browsingBreadcrumbs.length > 0) {
											currentDirectoryId = null;
											loadBrowsingItems();
										}
									}}
								>
									{decodeString(browsingCollection?.name)}
								</button>
								{#each browsingBreadcrumbs as crumb, i}
									<span class="flex-shrink-0">/</span>
									<button
										type="button"
										class="hover:text-gray-700 dark:hover:text-gray-200 transition truncate"
										on:click={() => {
											currentDirectoryId = crumb.id;
											loadBrowsingItems();
										}}
									>
										{crumb.name}
									</button>
								{/each}
							</div>
						</div>

						<Tooltip
							content={browsingBreadcrumbs.length > 0
								? $i18n.t('Select directory')
								: $i18n.t('Select collection')}
							placement="top"
							tippyOptions={{ zIndex: 100000 }}
						>
							<button
								type="button"
								class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition opacity-60 hover:opacity-100"
								on:click={() => {
									if (browsingBreadcrumbs.length > 0) {
										selectDirectory({
											id: currentDirectoryId,
											name:
												browsingBreadcrumbs.length > 0
													? browsingBreadcrumbs[browsingBreadcrumbs.length - 1]?.name
													: browsingCollection?.name
										});
									} else {
										dispatch('select', {
											...browsingCollection,
											type: 'collection'
										});
										show = false;
									}
								}}
							>
								<Plus className="size-3.5" />
							</button>
						</Tooltip>
					</div>

					{#if browsingLoading}
						<div class="flex justify-center py-3">
							<Spinner className="size-3.5" />
						</div>
					{:else if browsingDirectories.length === 0 && browsingFiles.length === 0}
						<div class="px-2 py-3 text-center text-xs text-gray-400 dark:text-gray-500 italic">
							{$i18n.t('This directory is empty.')}
						</div>
					{:else}
						{#if browsingDirectories.length > 0}
							<div class="px-1.5 text-[11px] text-gray-500 py-0.5">
								{$i18n.t('Directories')}
							</div>
						{/if}

						{#each browsingDirectories as dir (dir.id)}
							<div
								class="min-h-[1.6875rem] px-2 rounded-xl w-full text-left flex items-center text-[13px] bg-transparent transition-colors hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100"
							>
								<button
									type="button"
									class="flex-1 flex min-w-0 items-center gap-1 text-black dark:text-gray-100"
									on:click={() => browseIntoDirectory(dir)}
								>
									<Folder className="size-3.5 flex-shrink-0" />
									<Tooltip
										content={dir.name}
										placement="top-start"
										tippyOptions={{ zIndex: 100000 }}
									>
										<div class="line-clamp-1 flex-1 text-[13px] text-left">{dir.name}</div>
									</Tooltip>
								</button>

								<div class="flex items-center gap-0.5 ml-1">
									<Tooltip
										content={$i18n.t('Select directory')}
										placement="top"
										tippyOptions={{ zIndex: 100000 }}
									>
										<button
											type="button"
											class="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition opacity-40 hover:opacity-100"
											on:click|stopPropagation={() => selectDirectory(dir)}
										>
											<Plus className="size-3" />
										</button>
									</Tooltip>
									<ChevronRight className="size-3 opacity-30" />
								</div>
							</div>
						{/each}

						{#if browsingFiles.length > 0}
							<div class="px-1.5 text-[11px] text-gray-500 py-0.5">
								{$i18n.t('Files')}
							</div>
						{/if}

						{#each browsingFiles as file (file.id)}
							<button
								class="min-h-[1.6875rem] px-2 rounded-xl w-full text-left flex items-center gap-1 text-[13px] bg-transparent transition-colors hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 text-black dark:text-gray-100"
								type="button"
								on:click={() => {
									dispatch('select', {
										...file,
										type: 'file',
										name: file?.meta?.name || file.filename
									});
									show = false;
								}}
							>
								<Tooltip
									content={$i18n.t('File')}
									placement="top"
									tippyOptions={{ zIndex: 100000 }}
								>
									<DocumentPage className="size-3.5 flex-shrink-0" />
								</Tooltip>
								<Tooltip
									content={decodeString(file?.meta?.name || file.filename)}
									placement="top-start"
									tippyOptions={{ zIndex: 100000 }}
								>
									<div class="line-clamp-1 flex-1 text-[13px] text-left">
										{decodeString(file?.meta?.name || file.filename)}
									</div>
								</Tooltip>
							</button>
						{/each}
					{/if}
				{:else if items.length === 0}
					<div class="text-center text-xs text-gray-500 dark:text-gray-400 pt-4 pb-6">
						{$i18n.t('No knowledge found')}
					</div>
				{:else}
					<!-- Top-level view -->
					{#each items as item, i}
						{#if i === 0 || item?.type !== items[i - 1]?.type}
							<div class="px-1.5 text-[11px] text-gray-500 py-0.5">
								{#if item?.type === 'note'}
									{$i18n.t('Notes')}
								{:else if item?.type === 'collection'}
									{$i18n.t('Collections')}
								{:else if item?.type === 'file'}
									{$i18n.t('Files')}
								{/if}
							</div>
						{/if}

						{#if item.type === 'collection'}
							<div
								class="min-h-[1.6875rem] px-2 rounded-xl w-full text-left flex justify-between items-center text-[13px] bg-transparent transition-colors hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 selected-command-option-button"
							>
								<button
									class="w-full flex-1"
									type="button"
									on:click={() => browseIntoCollection(item)}
								>
									<div class="  text-black dark:text-gray-100 flex items-center gap-1 shrink-0">
										<Tooltip
											content={$i18n.t('Collection')}
											placement="top"
											tippyOptions={{ zIndex: 100000 }}
										>
											<Database className="size-3.5" />
										</Tooltip>

										<Tooltip
											content={item.description || decodeString(item?.name)}
											placement="top-start"
											tippyOptions={{ zIndex: 100000 }}
										>
											<div class="line-clamp-1 flex-1 text-[13px] text-left">
												{decodeString(item?.name)}
											</div>
										</Tooltip>
									</div>
								</button>

								<div class="flex items-center gap-0.5 ml-1">
									<Tooltip
										content={$i18n.t('Select collection')}
										placement="top"
										tippyOptions={{ zIndex: 100000 }}
									>
										<button
											type="button"
											class="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition opacity-40 hover:opacity-100"
											on:click|stopPropagation={() => {
												dispatch('select', item);
												show = false;
											}}
										>
											<Plus className="size-3" />
										</button>
									</Tooltip>
									<ChevronRight className="size-3 opacity-30" />
								</div>
							</div>
						{:else}
							<div
								class="min-h-[1.6875rem] px-2 rounded-xl w-full text-left flex justify-between items-center text-[13px] bg-transparent transition-colors hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 selected-command-option-button"
							>
								<button
									class="w-full flex-1"
									type="button"
									on:click={() => {
										dispatch('select', item);
										show = false;
									}}
								>
									<div class="  text-black dark:text-gray-100 flex items-center gap-1 shrink-0">
										{#if item.type === 'note'}
											<Tooltip
												content={$i18n.t('Note')}
												placement="top"
												tippyOptions={{ zIndex: 100000 }}
											>
												<PageEdit className="size-3.5" />
											</Tooltip>
										{:else if item.type === 'file'}
											<Tooltip
												content={$i18n.t('File')}
												placement="top"
												tippyOptions={{ zIndex: 100000 }}
											>
												<DocumentPage className="size-3.5" />
											</Tooltip>
										{/if}

										<Tooltip
											content={item.description || decodeString(item?.name)}
											placement="top-start"
											tippyOptions={{ zIndex: 100000 }}
										>
											<div class="line-clamp-1 flex-1 text-[13px] text-left">
												{decodeString(item?.name)}
											</div>
										</Tooltip>
									</div>
								</button>
							</div>
						{/if}
					{/each}
				{/if}
			</div>
		</div>
	</div>
</Dropdown>
