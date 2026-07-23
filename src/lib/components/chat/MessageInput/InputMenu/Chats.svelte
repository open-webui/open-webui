<script lang="ts">
	import dayjs from 'dayjs';
	import { onDestroy, onMount, tick, getContext } from 'svelte';

	import { decodeString } from '$lib/utils';
	import { getChatList, getChatListBySearchText } from '$lib/apis/chats';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import { chatId } from '$lib/stores';
	import SearchInput from './SearchInput.svelte';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};

	let loaded = false;

	let items = [];
	let selectedIdx = 0;
	let query = '';

	let page = 1;
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
		page = 1;
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
		const res = query.trim()
			? await getChatListBySearchText(localStorage.token, query.trim(), page).catch(() => {
					return [];
				})
			: await getChatList(localStorage.token, page, true, true).catch(() => {
					return [];
				});
		if (activeRequestId !== requestId) return res;

		if ((res ?? []).length === 0) {
			allItemsLoaded = true;
		} else {
			allItemsLoaded = false;
		}

		items = [
			...items,
			...res
				.filter((item) => item?.id !== $chatId)
				.map((item) => {
					return {
						...item,
						type: 'chat',
						name: item.title,
						description: item.snippet || dayjs(item.updated_at * 1000).fromNow()
					};
				})
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
		<SearchInput bind:value={query} placeholder={$i18n.t('Search Chats')} />

		<div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
			{#if items.length === 0 && itemsLoading}
				<div class="py-4.5">
					<Spinner />
				</div>
			{:else if items.length === 0}
				<div class="text-center text-xs text-gray-500 py-3">{$i18n.t('No chats found')}</div>
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
							<div class="text-black dark:text-gray-100 flex items-center gap-1.5">
								<Tooltip
									content={item.description || decodeString(item?.name)}
									placement="top-start"
								>
									<div class="line-clamp-1 flex-1">
										{decodeString(item?.name)}
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
