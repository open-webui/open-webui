<script lang="ts">
	// @ts-ignore
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import dayjs from 'dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import {
		archiveChatById,
		deleteChatById,
		getAllArchivedChats,
		getArchivedChatCount,
		getArchivedChatList,
		unarchiveAllChats
	} from '$lib/apis/chats';
	import { chatId, showSettings } from '$lib/stores';
	import { refreshChatList } from '$lib/stores/chat-list';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	dayjs.extend(localizedFormat);
	dayjs.extend(calendar);

	const i18n: Writable<any> = getContext('i18n');

	let loading = false;
	let chatList: any[] | null = null;
	let chatCount: number | null = null;
	let page = 1;

	let query = '';
	let orderBy = 'updated_at';
	let direction = 'desc';

	let allChatsLoaded = false;
	let chatListLoading = false;
	let searchDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

	let selectedChatId: string | null = null;
	let showDeleteConfirmDialog = false;
	let showUnarchiveAllConfirmDialog = false;

	const getFilter = () => ({
		...(query ? { query } : {}),
		...(orderBy ? { order_by: orderBy } : {}),
		...(direction ? { direction } : {})
	});

	const loadChats = async () => {
		page = 1;
		chatList = null;
		chatList = await getArchivedChatList(localStorage.token, page, getFilter());
		allChatsLoaded = (chatList ?? []).length === 0;
		chatCount = await getArchivedChatCount(localStorage.token);
	};

	const searchHandler = () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		if (query === '') {
			loadChats();
		} else {
			searchDebounceTimeout = setTimeout(loadChats, 300);
		}
	};

	const loadMoreChats = async () => {
		chatListLoading = true;
		page += 1;

		const newChatList = await getArchivedChatList(localStorage.token, page, getFilter());
		allChatsLoaded = newChatList.length === 0;

		if (newChatList.length > 0) {
			chatList = [...(chatList || []), ...newChatList];
		}

		chatListLoading = false;
	};

	const setSortKey = async (key: string) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}

		await loadChats();
	};

	const exportChatsHandler = async () => {
		const chats = await getAllArchivedChats(localStorage.token);
		const blob = new Blob([JSON.stringify(chats)], {
			type: 'application/json'
		});
		saveAs(blob, `${$i18n.t('archived-chat-export')}-${Date.now()}.json`);
	};

	const unarchiveHandler = async (id: string) => {
		await archiveChatById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
		});

		chatList = chatList?.filter((chat) => chat.id !== id) ?? null;
		if (chatCount !== null) chatCount -= 1;
		await refreshChatList(localStorage.token);
	};

	const deleteHandler = async () => {
		if (!selectedChatId) return;

		const id = selectedChatId;
		await deleteChatById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
		});

		chatList = chatList?.filter((chat) => chat.id !== id) ?? null;
		if (chatCount !== null) chatCount -= 1;
		selectedChatId = null;

		if ($chatId === id) {
			await goto('/');
			chatId.set('');
		}

		await refreshChatList(localStorage.token);
	};

	const unarchiveAllHandler = async () => {
		loading = true;
		try {
			await unarchiveAllChats(localStorage.token);
			toast.success($i18n.t('All chats have been unarchived.'));
			await loadChats();
			await refreshChatList(localStorage.token);
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	onMount(loadChats);
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		deleteHandler();
	}}
/>

<ConfirmDialog
	bind:show={showUnarchiveAllConfirmDialog}
	message={$i18n.t('Are you sure you want to unarchive all archived chats?')}
	confirmLabel={$i18n.t('Unarchive All')}
	on:confirm={() => {
		unarchiveAllHandler();
	}}
/>

<div id="tab-archived-chats" class="flex flex-col h-full text-sm">
	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5 -mr-1.5">
		<div>
			<div class="text-xs text-gray-400 dark:text-gray-600 mb-2">
				{$i18n.t('Conversations')}
				{#if chatCount !== null}
					<span>{chatCount}</span>
				{/if}
			</div>

			<div class="py-0.5 flex w-full justify-between">
				<div class="self-center text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Search')}</div>
				<div class="flex min-w-0 items-center justify-end gap-1">
					<input
						class="w-40 bg-transparent py-1 text-right text-xs outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-600"
						bind:value={query}
						on:input={searchHandler}
						placeholder={$i18n.t('Search')}
						maxlength="500"
					/>
					{#if query}
						<button
							class="rounded-sm p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-850"
							type="button"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
								searchHandler();
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					{/if}
				</div>
			</div>
		</div>

		{#if chatList === null}
			<div class="flex min-h-20 items-center justify-center">
				<Spinner className="size-5" />
			</div>
		{:else if chatList.length === 0}
			<div
				class="flex min-h-20 items-center justify-center px-4 text-center text-xs text-gray-500 dark:text-gray-400"
			>
				{$i18n.t('You have no archived conversations.')}
			</div>
		{:else}
			<div class="mt-3 flex items-center text-xs text-gray-400 dark:text-gray-600">
				<button
					class="flex flex-1 items-center gap-1 py-0.5 text-left"
					type="button"
					on:click={() => setSortKey('title')}
				>
					{$i18n.t('Title')}
					{#if orderBy === 'title'}
						{#if direction === 'asc'}
							<ChevronUp className="size-2" />
						{:else}
							<ChevronDown className="size-2" />
						{/if}
					{/if}
				</button>
				<button
					class="hidden w-24 items-center justify-end gap-1 py-0.5 text-right sm:flex"
					type="button"
					on:click={() => setSortKey('updated_at')}
				>
					{$i18n.t('Updated at')}
					{#if orderBy === 'updated_at'}
						{#if direction === 'asc'}
							<ChevronUp className="size-2" />
						{:else}
							<ChevronDown className="size-2" />
						{/if}
					{/if}
				</button>
			</div>

			<div>
				{#each chatList as chat (chat.id)}
					<div class="py-0.5 flex w-full justify-between gap-2 text-xs">
						<a
							class="min-w-0 flex-1 self-center truncate text-gray-600 hover:text-black dark:text-gray-400 dark:hover:text-white"
							href={`/c/${chat.id}`}
							on:click={(event) => {
								event.preventDefault();
								showSettings.set(false);
								goto(`/c/${chat.id}`);
							}}
						>
							{chat?.title}
						</a>
						<div
							class="hidden w-24 shrink-0 self-center justify-end text-gray-400 dark:text-gray-600 sm:flex"
						>
							{$i18n.t(
								dayjs(chat?.updated_at * 1000).calendar(null, {
									sameDay: '[Today]',
									nextDay: '[Tomorrow]',
									nextWeek: 'dddd',
									lastDay: '[Yesterday]',
									lastWeek: '[Last] dddd',
									sameElse: 'L'
								})
							)}
						</div>
						<div class="flex shrink-0 items-center justify-end text-gray-500 dark:text-gray-500">
							<Tooltip content={$i18n.t('Unarchive Chat')}>
								<button
									class="rounded-sm p-1 hover:bg-gray-100 dark:hover:bg-gray-850"
									type="button"
									aria-label={$i18n.t('Unarchive Chat')}
									on:click={() => {
										unarchiveHandler(chat.id);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M9 8.25H7.5a2.25 2.25 0 0 0-2.25 2.25v9a2.25 2.25 0 0 0 2.25 2.25h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25H15m0-3-3-3m0 0-3 3m3-3V15"
										/>
									</svg>
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Delete Chat')}>
								<button
									class="rounded-sm p-1 hover:bg-gray-100 dark:hover:bg-gray-850"
									type="button"
									aria-label={$i18n.t('Delete Chat')}
									on:click={() => {
										selectedChatId = chat.id;
										showDeleteConfirmDialog = true;
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
										/>
									</svg>
								</button>
							</Tooltip>
						</div>
					</div>
				{/each}
			</div>

			{#if !allChatsLoaded}
				<Loader
					on:visible={() => {
						if (!chatListLoading) {
							loadMoreChats();
						}
					}}
				>
					<div class="flex w-full items-center justify-center gap-2 py-1 text-xs animate-pulse">
						<Spinner className="size-4" />
						<div>{$i18n.t('Loading...')}</div>
					</div>
				</Loader>
			{/if}
		{/if}
	</div>

	<div class="shrink-0 pt-3 flex justify-end gap-1.5 text-sm font-normal">
		{#if query === ''}
			<button
				class="px-3.5 py-1.5 font-normal hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-300 dark:outline-gray-800 rounded-3xl disabled:opacity-50"
				disabled={loading || chatCount === 0}
				type="button"
				on:click={() => {
					showUnarchiveAllConfirmDialog = true;
				}}
			>
				{#if loading}
					<Spinner className="size-4" />
				{:else}
					{$i18n.t('Unarchive All')}
				{/if}
			</button>

			<button
				class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-50"
				disabled={loading || chatCount === 0}
				type="button"
				on:click={exportChatsHandler}
			>
				{$i18n.t('Export')}
			</button>
		{/if}
	</div>
</div>
