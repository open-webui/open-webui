<script lang="ts">
	import type { Writable } from 'svelte/store';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getSharedChatListV2, getSharedChatsCount, revokeSharedChatsBatch } from '$lib/apis/chats';
	import { selectedChatIds, clearSelection, selectAllOnPage, deselectAllOnPage } from '$lib/stores/sharedChats';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SharedChatsTable from './SharedChatsTable.svelte';

	const i18n: Writable<any> = getContext('i18n');
	const PAGE_SIZE = 20;

	export let show = false;
	export let onUpdate = () => {};

	let query = '';
	let orderBy = 'updated_at';
	let direction = 'desc';
	let page = 1;
	let chatList: any[] = [];
	let loading = false;
	let hasNextPage = false;
	let totalCount = 0;
	let searchDebounceTimeout: ReturnType<typeof setTimeout> | null = null;
	let requestVersion = 0;
	let prevShow = false;

	$: hasPrevPage = page > 1;
	$: selectedCount = $selectedChatIds.size;

	const clearScheduledLoad = () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
			searchDebounceTimeout = null;
		}
	};

	const loadChats = async () => {
		if (!show) return;
		const currentRequest = ++requestVersion;
		loading = true;

		try {
			const filters: any = {};
			if (query) filters.query = query;
			if (orderBy) filters.order_by = orderBy;
			if (direction) filters.direction = direction;

			const res = await getSharedChatListV2(localStorage.token, page, filters);
			if (currentRequest !== requestVersion) return;
			const nextChatList = Array.isArray(res) ? res : (res?.data ?? []);
			
			const countRes = await getSharedChatsCount(localStorage.token, query);
			if (currentRequest !== requestVersion) return;
			const nextTotalCount = Array.isArray(countRes) ? countRes.length : (countRes?.total ?? 0);

			chatList = nextChatList;
			totalCount = nextTotalCount;
			hasNextPage = page * PAGE_SIZE < nextTotalCount;
		} catch (error: any) {
			toast.error(error.message || 'Failed to load shared chats');
		} finally {
			if (currentRequest === requestVersion) {
				loading = false;
			}
		}
	};

	const scheduleLoad = () => {
		clearScheduledLoad();
		searchDebounceTimeout = setTimeout(loadChats, 300);
	};

	const setSortKey = (key: string) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
		page = 1;
		loadChats();
	};

	const unshareSingle = async (chatId: string) => {
		const res = await deleteSharedChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res === true) {
			toast.success('Chat unshared successfully.');
			onUpdate();
			loadChats();
		} else if (res === false) {
			toast.error('Failed to unshare chat.');
		}
	};

	const unshareSelected = async () => {
		const ids = Array.from($selectedChatIds);
		
		if (ids.length === 0) return;
		
		try {
			await revokeSharedChatsBatch(localStorage.token, ids);
			toast.success(`${ids.length} chat${ids.length > 1 ? 's' : ''} unshared successfully.`);
			clearSelection();
			onUpdate();
			loadChats();
		} catch (error: any) {
			toast.error(error.message || 'Failed to revoke selected chats');
		}
	};

	const toggleSelectChatHandler = (chatId: string, checked: boolean) => {
		if (checked) {
			selectAllOnPage([chatId]);
		} else {
			deselectAllOnPage([chatId]);
		}
	};

	const toggleSelectAllPage = (checked: boolean) => {
		const chatIds = chatList.map(c => c.id);
		if (checked) {
			selectAllOnPage(chatIds);
		} else {
			deselectAllOnPage(chatIds);
		}
	};

	const prevPage = () => {
		if (!hasPrevPage) return;
		page -= 1;
		loadChats();
	};

	const nextPage = () => {
		if (!hasNextPage) return;
		page += 1;
		loadChats();
	};

	$: if (show && !prevShow) {
		prevShow = true;
		page = 1;
		loadChats();
	}

	$: if (!show && prevShow) {
		prevShow = false;
		clearScheduledLoad();
		page = 1;
		query = '';
	}
</script>

<Modal size="xl" bind:show>
	<div class="px-5 pt-4 pb-4 dark:text-gray-200">
		<div class="flex items-center justify-between mb-3">
			<div class="text-lg font-medium">{$i18n.t('Shared Chats')}</div>
			<button
				class="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-850"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-4" strokeWidth="2.5" />
			</button>
		</div>

		<div class="flex items-center justify-between gap-3 mb-3">
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Total')}: {totalCount} | {$i18n.t('Selected')}: {selectedCount}
			</div>
			<div class="flex items-center gap-2">
				<input
					class="w-64 text-sm px-3 py-1.5 rounded-lg outline-hidden bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-850"
					bind:value={query}
					placeholder={$i18n.t('Search Chats')}
					maxlength="500"
					on:input={() => {
						page = 1;
						scheduleLoad();
					}}
				/>
				<button
					class="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-800 disabled:opacity-50"
					disabled={selectedCount === 0 || loading}
					on:click={unshareSelected}
				>
					{$i18n.t('Unshare Selected')}
				</button>
				<button
					class="px-3 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-gray-800 disabled:opacity-50"
					disabled={selectedCount === 0 || loading}
					on:click={clearSelection}
				>
					{$i18n.t('Clear Selection')}
				</button>
			</div>
		</div>

		<SharedChatsTable
			{chatList}
			{query}
			{loading}
			{page}
			{hasPrevPage}
			{hasNextPage}
			{orderBy}
			{direction}
			selectedChatIds={$selectedChatIds}
			onToggleSort={setSortKey}
			onToggleSelectAllPage={toggleSelectAllPage}
			onToggleSelectChat={toggleSelectChatHandler}
			onPrevPage={prevPage}
			onNextPage={nextPage}
			onUnshareSingle={unshareSingle}
		/>
	</div>
</Modal>
