<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';

	const i18n: Writable<any> = getContext('i18n');

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import { getTimeRange } from '$lib/utils';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	dayjs.extend(localizedFormat);

	export let chats: any[] = [];

	export let chatListLoading = false;
	export let showOwnerInfo = false;
	export let page = 1;
	export let total = 0;
	export let perPage = 10;
	export let orderBy: 'title' | 'updated_at' = 'updated_at';
	export let direction: 'asc' | 'desc' = 'desc';
	export let onPageChange: Function = () => {};
	export let onSort: Function = () => {};

	let chatList: any[] | null = null;
	let totalPages = 1;
	let pages: (number | 'ellipsis')[] = [];

	const init = async () => {
		if (chats.length === 0) {
			chatList = [];
		} else {
			chatList = chats.map((chat) => ({
				...chat,
				time_range: getTimeRange(chat.updated_at)
			}));
		}
	};

	const setSortKey = (key: 'title' | 'updated_at') => {
		onSort(key);
	};

	const buildPages = (currentPage: number, pageCount: number): (number | 'ellipsis')[] => {
		if (pageCount <= 7) {
			return Array.from({ length: pageCount }, (_, i) => i + 1);
		}

		const items: (number | 'ellipsis')[] = [1];
		if (currentPage > 3) {
			items.push('ellipsis');
		}

		const start = Math.max(2, currentPage - 1);
		const end = Math.min(pageCount - 1, currentPage + 1);
		for (let i = start; i <= end; i++) {
			items.push(i);
		}

		if (currentPage < pageCount - 2) {
			items.push('ellipsis');
		}
		items.push(pageCount);

		return items;
	};

	$: if (chats) {
		init();
	}

	$: totalPages = Math.max(1, Math.ceil(total / perPage));
	$: pages = buildPages(page, totalPages);
</script>

{#if chatList}
	{#if chatList.length > 0}
		<div class="flex text-xs font-normal mb-1 items-center -mr-0.5">
			<button
				class="px-1.5 py-1 cursor-pointer select-none basis-3/5"
				on:click={() => setSortKey('title')}
			>
				<div class="flex gap-1.5 items-center">
					{$i18n.t('Title')}

					{#if orderBy === 'title'}
						<span class="font-normal"
							>{#if direction === 'asc'}
								<ChevronUp className="size-2" />
							{:else}
								<ChevronDown className="size-2" />
							{/if}
						</span>
					{:else}
						<span class="invisible">
							<ChevronUp className="size-2" />
						</span>
					{/if}
				</div>
			</button>
			<button
				class="px-1.5 py-1 cursor-pointer select-none hidden sm:flex sm:basis-2/5 justify-end"
				on:click={() => setSortKey('updated_at')}
			>
				<div class="flex gap-1.5 items-center">
					{$i18n.t('Updated at')}

					{#if orderBy === 'updated_at'}
						<span class="font-normal"
							>{#if direction === 'asc'}
								<ChevronUp className="size-2" />
							{:else}
								<ChevronDown className="size-2" />
							{/if}
						</span>
					{:else}
						<span class="invisible">
							<ChevronUp className="size-2" />
						</span>
					{/if}
				</div>
			</button>
		</div>
	{/if}

	<div class="text-left text-sm w-full mb-3">
		{#if chatList.length === 0}
			<div
				class="text-xs text-gray-500 dark:text-gray-400 text-center px-5 min-h-20 w-full h-full flex justify-center items-center"
			>
				{$i18n.t('No chats found')}
			</div>
		{/if}

		{#each chatList as chat, idx (chat.id)}
			{#if (idx === 0 || (idx > 0 && chat.time_range !== chatList[idx - 1].time_range)) && chat?.time_range}
				<div
					class="w-full text-xs text-gray-500 dark:text-gray-500 font-normal {idx === 0
						? ''
						: 'pt-5'} pb-2 px-2"
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

			<a
				class=" w-full flex justify-between items-center rounded-lg text-sm py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-850"
				draggable="false"
				href={`/c/${chat.id}`}
			>
				<div class="text-ellipsis line-clamp-1 w-full sm:basis-3/5">
					{chat?.title}
				</div>

				<div class="hidden sm:flex sm:basis-2/5 items-center justify-end gap-2">
					<div class=" text-gray-500 dark:text-gray-400 text-xs">
						{dayjs(chat?.updated_at * 1000).calendar()}
					</div>

					{#if showOwnerInfo && chat.user_id && chat.owner_name}
						<Tooltip content={chat.owner_name}>
							<img
								src="/api/v1/users/{chat.user_id}/profile/image"
								alt=""
								class="size-4 rounded-full shrink-0 object-cover"
							/>
						</Tooltip>
					{/if}
				</div>
			</a>
		{/each}

		{#if totalPages > 1}
			<div class="flex items-center justify-center gap-1.5 pt-2">
				<button
					class="inline-flex size-7 items-center justify-center rounded-lg text-xs font-medium text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-25 dark:text-gray-500 dark:hover:bg-gray-850 dark:hover:text-gray-300"
					disabled={chatListLoading || page <= 1}
					aria-label={$i18n.t('Previous page')}
					on:click={() => onPageChange(page - 1)}
				>
					<ChevronLeft className="size-3.5" strokeWidth="2" />
				</button>

				{#each pages as item, index (item === 'ellipsis' ? `ellipsis-${index}` : item)}
					{#if item === 'ellipsis'}
						<span
							class="inline-flex size-7 items-center justify-center text-xs text-gray-400 select-none dark:text-gray-600"
						>
							...
						</span>
					{:else}
						<button
							class="inline-flex size-7 items-center justify-center rounded-lg text-xs font-medium transition hover:bg-gray-50 hover:text-gray-700 dark:hover:bg-gray-850 dark:hover:text-gray-300 {item ===
							page
								? 'bg-gray-50 text-gray-800 dark:bg-gray-850 dark:text-gray-100'
								: 'text-gray-500 dark:text-gray-500'}"
							aria-label={`Page ${item}`}
							aria-current={item === page ? 'page' : undefined}
							on:click={() => onPageChange(item)}
						>
							{item}
						</button>
					{/if}
				{/each}

				<button
					class="inline-flex size-7 items-center justify-center rounded-lg text-xs font-medium text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-25 dark:text-gray-500 dark:hover:bg-gray-850 dark:hover:text-gray-300"
					disabled={chatListLoading || page >= totalPages}
					aria-label={$i18n.t('Next page')}
					on:click={() => onPageChange(page + 1)}
				>
					<ChevronRight className="size-3.5" strokeWidth="2" />
				</button>
			</div>
		{/if}
	</div>
{/if}
