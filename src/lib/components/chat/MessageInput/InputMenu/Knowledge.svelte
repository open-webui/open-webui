<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import { decodeString } from '$lib/utils';
	import { knowledge } from '$lib/stores';

	import { getKnowledgeBases, searchKnowledgeFilesById } from '$lib/apis/knowledge';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};

	let loaded = false;
	let selectedIdx = 0;

	let selectedItem = null;

	let selectedFileItemsPage = 1;

	let selectedFileItems = null;
	let selectedFileItemsTotal = null;

	let selectedFileItemsLoading = false;
	let selectedFileAllItemsLoaded = false;

	$: if (selectedItem) {
		initSelectedFileItems();
	}

	const initSelectedFileItems = async () => {
		selectedFileItemsPage = 1;
		selectedFileItems = null;
		selectedFileItemsTotal = null;
		selectedFileAllItemsLoaded = false;
		selectedFileItemsLoading = false;
		await tick();
		await getSelectedFileItemsPage();
	};

	const loadMoreSelectedFileItems = async () => {
		if (selectedFileAllItemsLoaded) return;
		selectedFileItemsPage += 1;
		await getSelectedFileItemsPage();
	};

	const getSelectedFileItemsPage = async () => {
		if (!selectedItem) return;
		selectedFileItemsLoading = true;

		const res = await searchKnowledgeFilesById(
			localStorage.token,
			selectedItem.id,
			null,
			null,
			null,
			null,
			selectedFileItemsPage
		).catch(() => {
			return null;
		});

		if (res) {
			selectedFileItemsTotal = res.total;
			const pageItems = res.items;

			if ((pageItems ?? []).length === 0) {
				selectedFileAllItemsLoaded = true;
			} else {
				selectedFileAllItemsLoaded = false;
			}

			if (selectedFileItems) {
				selectedFileItems = [...selectedFileItems, ...pageItems];
			} else {
				selectedFileItems = pageItems;
			}
		}

		selectedFileItemsLoading = false;
		return res;
	};

	let page = 1;
	let items = null;
	let total = null;

	let itemsLoading = false;
	let allItemsLoaded = false;

	$: if (loaded) {
		init();
	}

	const init = async () => {
		reset();
		await tick();
		await getItemsPage();
	};

	const reset = () => {
		page = 1;
		items = null;
		total = null;
		allItemsLoaded = false;
		itemsLoading = false;
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded) return;
		page += 1;
		await getItemsPage();
	};

	const getItemsPage = async () => {
		itemsLoading = true;
		const res = await getKnowledgeBases(localStorage.token, page).catch(() => {
			return null;
		});

		if (res) {
			console.log(res);
			total = res.total;
			const pageItems = res.items;

			if ((pageItems ?? []).length === 0) {
				allItemsLoaded = true;
			} else {
				allItemsLoaded = false;
			}

			if (items) {
				items = [...items, ...pageItems];
			} else {
				items = pageItems;
			}
		}

		itemsLoading = false;
		return res;
	};

	onMount(async () => {
		await tick();
		loaded = true;
	});
</script>

{#if loaded && items !== null}
	<div class="flex flex-col gap-0.5">
		{#if items.length === 0}
			<div class="py-4 text-center text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('No knowledge bases found.')}
			</div>
		{:else}
			{#each items as item, idx (item.id)}
				<div
					class=" px-2.5 py-1 rounded-xl w-full text-left flex justify-between items-center text-sm {idx ===
					selectedIdx
						? ' bg-gray-50 dark:bg-gray-800 dark:text-gray-100 selected-command-option-button'
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
								<Database className="size-4" />
							</Tooltip>

							<Tooltip
								content={item.description || decodeString(item?.name)}
								placement="top-start"
								className="flex flex-1 min-w-0"
							>
								<div class="line-clamp-1 flex-1 text-sm">
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
						{:else if selectedFileItemsTotal === 0}
							<div class=" text-xs text-gray-500 dark:text-gray-400 italic py-0.5 px-2">
								{$i18n.t('No files in this knowledge base.')}
							</div>
						{:else}
							{#each selectedFileItems as file, fileIdx (file.id)}
								<button
									class=" px-2.5 py-1 rounded-xl w-full text-left flex justify-between items-center text-sm hover:bg-gray-50 hover:dark:bg-gray-800 hover:dark:text-gray-100"
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
										<Tooltip content={$i18n.t('Collection')} placement="top">
											<DocumentPage className="size-4" />
										</Tooltip>

										<Tooltip content={decodeString(file?.meta?.name)} placement="top-start">
											<div class="line-clamp-1 flex-1 text-sm">
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
{:else}
	<div class="py-4.5">
		<Spinner />
	</div>
{/if}
