<script lang="ts">
	import { onDestroy, onMount, tick, getContext } from 'svelte';

	import { decodeString } from '$lib/utils';
	import { searchKnowledgeBases, searchKnowledgeFilesById } from '$lib/apis/knowledge';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import SearchInput from './SearchInput.svelte';
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};

	let loaded = false;
	let selectedIdx = 0;
	let query = '';

	let selectedItem = null;

	// --- Directory browsing state within expanded KB ---
	let currentDirectoryId = null; // null = root level of the KB
	let selectedFileDirectories = [];
	let selectedFileBreadcrumbs = [];

	let selectedFileItemsPage = 1;

	let selectedFileItems = null;
	let selectedFileItemsTotal = null;

	let selectedFileItemsLoading = false;
	let selectedFileAllItemsLoaded = false;
	let selectedFileRequestId = 0;

	$: if (selectedItem) {
		currentDirectoryId = null;
		selectedFileDirectories = [];
		selectedFileBreadcrumbs = [];
		initSelectedFileItems();
	}

	const initSelectedFileItems = async () => {
		selectedFileRequestId += 1;
		selectedFileItemsPage = 1;
		selectedFileItems = null;
		selectedFileItemsTotal = null;
		selectedFileAllItemsLoaded = false;
		selectedFileItemsLoading = false;
		await tick();
		await getSelectedFileItemsPage(selectedFileRequestId);
	};

	const loadMoreSelectedFileItems = async () => {
		if (selectedFileAllItemsLoaded) return;
		selectedFileItemsPage += 1;
		await getSelectedFileItemsPage(selectedFileRequestId);
	};

	const getSelectedFileItemsPage = async (activeRequestId = selectedFileRequestId) => {
		if (!selectedItem) return;
		selectedFileItemsLoading = true;

		const res = await searchKnowledgeFilesById(
			localStorage.token,
			selectedItem.id,
			query.trim() || null,
			null,
			null,
			null,
			selectedFileItemsPage,
			currentDirectoryId
		).catch(() => {
			return null;
		});
		if (activeRequestId !== selectedFileRequestId) return res;

		if (res) {
			selectedFileItemsTotal = res.total;
			selectedFileDirectories = res.directories || [];
			selectedFileBreadcrumbs = res.breadcrumbs || [];
			const pageItems = res.items;

			if ((pageItems ?? []).length === 0) {
				selectedFileAllItemsLoaded = true;
			} else {
				selectedFileAllItemsLoaded = false;
			}

			if (selectedFileItems) {
				const existingIds = new Set(selectedFileItems.map((item) => item.id));
				const newItems = pageItems.filter((item) => !existingIds.has(item.id));
				selectedFileItems = [...selectedFileItems, ...newItems];
			} else {
				selectedFileItems = pageItems;
			}
		}

		selectedFileItemsLoading = false;
		return res;
	};

	const navigateToDirectory = async (dirId) => {
		currentDirectoryId = dirId;
		selectedFileItemsPage = 1;
		selectedFileItems = null;
		selectedFileItemsTotal = null;
		selectedFileAllItemsLoaded = false;
		selectedFileItemsLoading = false;
		await tick();
		await getSelectedFileItemsPage();
	};

	const selectDirectory = async (dir) => {
		// Fetch all files directly in this directory and select them all
		const allFiles = [];
		let page = 1;
		while (true) {
			const res = await searchKnowledgeFilesById(
				localStorage.token,
				selectedItem.id,
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
			onSelect({
				type: 'file',
				name: file?.meta?.name,
				...file
			});
		}
	};

	let page = 1;
	let items = [];
	let total = null;

	let itemsLoading = false;
	let allItemsLoaded = false;
	let initialized = false;
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let requestId = 0;

	$: if (initialized) {
		query;
		scheduleSearch();
	}

	const scheduleSearch = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(init, 200);
	};

	const init = async () => {
		requestId += 1;
		reset();
		selectedItem = null;
		await tick();
		await getItemsPage(requestId);
	};

	const reset = () => {
		page = 1;
		items = [];
		total = null;
		allItemsLoaded = false;
		itemsLoading = false;
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded) return;
		page += 1;
		await getItemsPage(requestId);
	};

	const getItemsPage = async (activeRequestId = requestId) => {
		itemsLoading = true;
		const res = await searchKnowledgeBases(
			localStorage.token,
			query.trim() || null,
			null,
			page
		).catch(() => {
			return null;
		});
		if (activeRequestId !== requestId) return res;

		if (res) {
			total = res.total;
			const pageItems = res.items;

			if ((pageItems ?? []).length === 0) {
				allItemsLoaded = true;
			} else {
				allItemsLoaded = false;
			}

			if (items) {
				const existingIds = new Set(items.map((item) => item.id));
				const newItems = pageItems.filter((item) => !existingIds.has(item.id));
				items = [...items, ...newItems];
			} else {
				items = pageItems;
			}
		}

		itemsLoading = false;
		return res;
	};

	onMount(async () => {
		await init();
		await tick();
		loaded = true;
		initialized = true;
	});

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

{#if loaded}
	<div class="flex min-h-0 flex-1 flex-col gap-0.5 overflow-hidden">
		<SearchInput bind:value={query} placeholder={$i18n.t('Search Knowledge')} />

		<div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
			{#if items.length === 0 && itemsLoading}
				<div class="py-4.5">
					<Spinner />
				</div>
			{:else if items.length === 0}
				<div class="py-4 text-center text-sm text-gray-500 dark:text-gray-400">
					{$i18n.t('No knowledge bases found.')}
				</div>
			{:else}
				{#each items as item, idx (item.id)}
					<div
						class=" h-[1.6875rem] px-2 rounded-xl w-full text-left flex justify-between items-center text-[13px] font-normal hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 {idx ===
						selectedIdx
							? ' bg-gray-50/40 dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button'
							: ''}"
					>
						<button
							class="w-full flex-1"
							type="button"
							on:click={() => {
								onSelect({
									type: 'collection',
									...item
								});
							}}
							on:mousemove={() => {
								selectedIdx = idx;
							}}
							on:mouseleave={() => {
								if (idx === 0) {
									selectedIdx = -1;
								}
							}}
							data-selected={idx === selectedIdx}
						>
							<div class="w-full text-left text-black dark:text-gray-100 flex items-center gap-1">
								<Tooltip content={$i18n.t('Collection')} placement="top">
									<Database className="size-3.5" />
								</Tooltip>

								<Tooltip
									content={item.description || decodeString(item?.name)}
									placement="top-start"
									className="flex flex-1 min-w-0"
								>
									<div class="line-clamp-1 flex-1 text-[13px]">
										{decodeString(item?.name)}
									</div>
								</Tooltip>
							</div>
						</button>

						<Tooltip content={$i18n.t('Show Files')} placement="top">
							<button
								type="button"
								class=" ml-2 opacity-50 hover:opacity-100 transition"
								on:click={() => {
									if (selectedItem && selectedItem.id === item.id) {
										selectedItem = null;
									} else {
										selectedItem = item;
									}
								}}
							>
								{#if selectedItem && selectedItem.id === item.id}
									<ChevronDown className="size-3" />
								{:else}
									<ChevronRight className="size-3" />
								{/if}
							</button>
						</Tooltip>
					</div>

					{#if selectedItem && selectedItem.id === item.id}
						<div class="pl-3 mb-1 flex flex-col gap-0.5">
							{#if selectedFileItems === null && selectedFileItemsTotal === null}
								<div class=" py-1 flex justify-center">
									<Spinner className="size-3" />
								</div>
							{:else if selectedFileItemsTotal === 0 && selectedFileDirectories.length === 0}
								<div class=" text-xs text-gray-500 dark:text-gray-400 italic py-0.5 px-2">
									{$i18n.t('No files in this knowledge base.')}
								</div>
							{:else}
								{#if selectedFileBreadcrumbs.length > 0}
									<div
										class="px-2 py-1 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400"
									>
										<button
											type="button"
											class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition"
											on:click={() => navigateToDirectory(null)}
										>
											<ArrowLeft className="size-3" strokeWidth="2" />
										</button>

										<button
											type="button"
											class="hover:text-gray-700 dark:hover:text-gray-200 transition truncate"
											on:click={() => navigateToDirectory(null)}
										>
											{decodeString(selectedItem?.name)}
										</button>
										{#each selectedFileBreadcrumbs as crumb, i}
											<span class="flex-shrink-0">/</span>
											<button
												type="button"
												class="hover:text-gray-700 dark:hover:text-gray-200 transition truncate"
												on:click={() => navigateToDirectory(crumb.id)}
											>
												{crumb.name}
											</button>
										{/each}
									</div>
								{/if}

								{#each selectedFileDirectories as dir (dir.id)}
									<div
										class="h-[1.6875rem] px-2 rounded-xl w-full text-left flex items-center text-[13px] font-normal hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100"
									>
										<button
											type="button"
											class="flex-1 flex min-w-0 items-center gap-1.5"
											on:click={() => navigateToDirectory(dir.id)}
										>
											<Tooltip content={$i18n.t('Directory')} placement="top">
												<Folder className="size-3.5" />
											</Tooltip>
											<Tooltip content={dir.name} placement="top-start">
												<div class="line-clamp-1 flex-1 text-[13px]">
													{dir.name}
												</div>
											</Tooltip>
										</button>

										<div class="flex items-center gap-0.5 ml-1">
											<Tooltip content={$i18n.t('Select directory')} placement="top">
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

								{#each selectedFileItems as file, fileIdx (file.id)}
									<button
										class=" h-[1.6875rem] px-2 rounded-xl w-full text-left flex justify-between items-center text-[13px] font-normal hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100"
										type="button"
										on:click={() => {
											console.log(file);
											onSelect({
												type: 'file',
												name: file?.meta?.name,
												...file
											});
										}}
									>
										<div class=" flex items-center gap-1.5">
											<Tooltip content={$i18n.t('File')} placement="top">
												<DocumentPage className="size-3.5" />
											</Tooltip>

											<Tooltip content={decodeString(file?.meta?.name)} placement="top-start">
												<div class="line-clamp-1 flex-1 text-[13px]">
													{decodeString(file?.meta?.name)}
												</div>
											</Tooltip>
										</div>
									</button>
								{/each}

								{#if !selectedFileAllItemsLoaded && !selectedFileItemsLoading}
									<Loader
										on:visible={async (e) => {
											if (!selectedFileItemsLoading) {
												await loadMoreSelectedFileItems();
											}
										}}
									>
										<div
											class="w-full flex justify-center py-4 text-xs animate-pulse items-center gap-2"
										>
											<Spinner className=" size-3" />
											<div class=" ">{$i18n.t('Loading...')}</div>
										</div>
									</Loader>
								{/if}
							{/if}
						</div>
					{/if}
				{/each}

				{#if !allItemsLoaded}
					<Loader
						on:visible={(e) => {
							if (!itemsLoading) {
								loadMoreItems();
							}
						}}
					>
						<div class="w-full flex justify-center py-4 text-xs animate-pulse items-center gap-2">
							<Spinner className=" size-4" />
							<div class=" ">{$i18n.t('Loading...')}</div>
						</div>
					</Loader>
				{/if}
			{/if}
		</div>
	</div>
{:else}
	<div class="py-4.5">
		<Spinner />
	</div>
{/if}
