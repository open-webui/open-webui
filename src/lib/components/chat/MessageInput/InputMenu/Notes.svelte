<script lang="ts">
	import dayjs from 'dayjs';
	import { onDestroy, onMount, tick, getContext } from 'svelte';

	import { decodeString } from '$lib/utils';
	import { getNoteList, searchNotes } from '$lib/apis/notes';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
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
	let searchedQuery = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let requestId = 0;

	// Only re-run the search when the query actually changes. Flipping `initialized`
	// after the initial load would otherwise trigger a second, identical request.
	$: if (initialized && query !== searchedQuery) {
		scheduleSearch();
	}

	const scheduleSearch = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(init, 200);
	};

	const init = async () => {
		requestId += 1;
		searchedQuery = query;
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
			? await searchNotes(localStorage.token, query.trim(), null, null, null, page).catch(
					() => null
				)
			: await getNoteList(localStorage.token, page).catch(() => {
					return [];
				});
		if (activeRequestId !== requestId) return res;

		const pageItems = query.trim() ? (res?.items ?? []) : (res ?? []);

		if ((pageItems ?? []).length === 0) {
			allItemsLoaded = true;
		} else {
			allItemsLoaded = false;
		}

		items = [
			...items,
			...pageItems.map((note) => {
				return {
					...note,
					type: 'note',
					name: note.title,
					description: dayjs(note.updated_at / 1000000).fromNow()
				};
			})
		];

		itemsLoading = false;

		return res;
	};

	let selectedFilter: 'all' | 'question' | 'context' = 'all';

	$: displayedItems = items.filter((item) => {
		const isQuestion = item.meta?.type === 'question' || item.data?.content?.type === 'question';
		if (selectedFilter === 'question') return isQuestion;
		if (selectedFilter === 'context') return !isQuestion;
		return true;
	});

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
		<SearchInput bind:value={query} placeholder={$i18n.t('Search Notes')} />

		<!-- Tabs to divide Question Notes vs Context Notes -->
		<div class="flex items-center gap-1 px-2 py-1 border-b border-gray-100 dark:border-gray-800 shrink-0 text-xs">
			<button
				type="button"
				class="px-2 py-0.5 rounded-lg transition font-medium cursor-pointer {selectedFilter === 'all'
					? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white font-semibold'
					: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
				on:click={() => (selectedFilter = 'all')}
			>
				{$i18n.t('All')}
			</button>
			<button
				type="button"
				class="px-2 py-0.5 rounded-lg transition font-medium cursor-pointer flex items-center gap-1 {selectedFilter === 'question'
					? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 font-semibold border border-amber-500/30'
					: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
				on:click={() => (selectedFilter = 'question')}
			>
				<span>❓ Questions</span>
			</button>
			<button
				type="button"
				class="px-2 py-0.5 rounded-lg transition font-medium cursor-pointer flex items-center gap-1 {selectedFilter === 'context'
					? 'bg-sky-500/20 text-sky-700 dark:text-sky-300 font-semibold border border-sky-500/30'
					: 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}"
				on:click={() => (selectedFilter = 'context')}
			>
				<span>📄 Context</span>
			</button>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin">
			{#if displayedItems.length === 0 && itemsLoading}
				<div class="py-4.5">
					<Spinner />
				</div>
			{:else if displayedItems.length === 0}
				<div class="text-center text-xs text-gray-500 py-3">{$i18n.t('No notes found')}</div>
			{:else}
				<div class="flex flex-col gap-0.5">
					{#each displayedItems as item, idx}
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
							<div class="text-black dark:text-gray-100 flex items-center gap-1.5 min-w-0 flex-1">
								<Tooltip content={$i18n.t('Note')} placement="top">
									<PageEdit className="size-3.5 shrink-0" />
								</Tooltip>

								<Tooltip
									content={item.description || decodeString(item?.name)}
									placement="top-start"
								>
									<div class="line-clamp-1 flex-1">
										{decodeString(item?.name)}
									</div>
								</Tooltip>
							</div>

							{#if item.meta?.type === 'question' || item.data?.content?.type === 'question'}
								<span class="text-[10px] px-1.5 py-0.5 bg-amber-500/15 text-amber-700 dark:text-amber-300 rounded font-medium shrink-0 ml-1.5">
									❓ Question
								</span>
							{:else}
								<span class="text-[10px] px-1.5 py-0.5 bg-sky-500/15 text-sky-700 dark:text-sky-300 rounded font-medium shrink-0 ml-1.5">
									📄 Context
								</span>
							{/if}
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
