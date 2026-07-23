<script lang="ts">
	import { onDestroy, onMount, tick, getContext } from 'svelte';

	import { searchFiles } from '$lib/apis/files';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import SearchInput from './SearchInput.svelte';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};

	let loaded = false;
	let items = [];
	let selectedIdx = 0;
	let query = '';

	let page = 0;
	let limit = 50;
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
		page = 0;
		items = [];
		selectedIdx = 0;
		allItemsLoaded = false;
		itemsLoading = false;
		await tick();
		await getItemsPage(requestId);
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded) return;
		page += 1;
		await getItemsPage(requestId);
	};

	const getItemsPage = async (activeRequestId = requestId) => {
		itemsLoading = true;
		const value = query.trim();
		const filename = value ? (/[?*]/.test(value) ? value : `*${value}*`) : '*';
		let res = await searchFiles(localStorage.token, filename, page * limit, limit).catch(() => []);
		if (activeRequestId !== requestId) return res;

		if ((res ?? []).length < limit) {
			allItemsLoaded = true;
		}

		items = [
			...items,
			...(res ?? []).map((file) => ({
				...file,
				type: file?.meta?.content_type?.startsWith('image/') ? 'image' : 'file',
				name: file.filename,
				url: file.id,
				content_type: file?.meta?.content_type,
				size: file?.meta?.size
			}))
		];

		itemsLoading = false;
		return res;
	};

	onMount(async () => {
		await getItemsPage();
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
		<SearchInput bind:value={query} placeholder={$i18n.t('Search Files')} />

		<div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
			{#if items.length === 0 && itemsLoading}
				<div class="py-4.5">
					<Spinner />
				</div>
			{:else if items.length === 0}
				<div class="text-center text-xs text-gray-500 py-3">{$i18n.t('No files found')}</div>
			{:else}
				<div class="flex flex-col gap-0.5">
					{#each items as item, idx}
						<button
							class=" h-[1.6875rem] px-2 rounded-xl w-full text-left flex justify-between items-center text-[13px] font-normal {idx ===
							selectedIdx
								? ' bg-gray-50/40 dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								onSelect(item);
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
							<div class="text-black dark:text-gray-100 flex items-center gap-1.5 overflow-hidden">
								<Tooltip content={$i18n.t('File')} placement="top">
									<DocumentPage className="size-3.5 shrink-0" />
								</Tooltip>

								<Tooltip content={item?.name} placement="top-start">
									<div class="line-clamp-1 flex-1">
										{item?.name}
									</div>
								</Tooltip>
							</div>
						</button>
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
				</div>
			{/if}
		</div>
	</div>
{:else}
	<div class="py-4.5">
		<Spinner />
	</div>
{/if}
