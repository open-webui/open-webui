<script lang="ts">
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy } from 'svelte';
	import { unshareAllChats, deleteSharedChatById, getSharedChatList } from '$lib/apis/chats';

	import ChatsModal from './ChatsModal.svelte';
	import UnshareAllConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '../common/Spinner.svelte';

	const i18n: Writable<any> = getContext('i18n');

	export let show = false;
	export let onUpdate = () => {};

	let loading = false;
	let chatList: any[] | null = null;
	let page = 1;

	let query = '';
	let orderBy = 'updated_at';
	let direction = 'desc';

	let allChatsLoaded = false;
	let chatListLoading = false;
	let searchDebounceTimeout: ReturnType<typeof setTimeout>;
	let searchController: AbortController;

	let showUnshareAllConfirmDialog = false;

	let filter: any = {};
	$: filter = {
		...(query ? { query } : {}),
		...(orderBy ? { order_by: orderBy } : {}),
		...(direction ? { direction } : {})
	};

	$: if (filter !== null) {
		searchHandler();
	}

	const cancelSearch = () => {
		searchController?.abort();
		clearTimeout(searchDebounceTimeout);
	};

	const searchHandler = async () => {
		cancelSearch();
		if (!show) return;

		searchController = new AbortController();
		const { signal } = searchController;
		page = 1;
		chatList = null;
		chatListLoading = false;

		const loadChats = async () => {
			const res = await getSharedChatList(localStorage.token, page, filter, signal);
			if (signal.aborted) return;
			chatList = res;
			allChatsLoaded = (chatList ?? []).length === 0;
		};

		if (query === '') {
			await loadChats();
		} else {
			searchDebounceTimeout = setTimeout(loadChats, 500);
		}
	};

	const loadMoreChats = async () => {
		if (chatListLoading || !chatList || allChatsLoaded || searchController.signal.aborted) return;
		const { signal } = searchController;
		chatListLoading = true;
		page += 1;

		const newChatList = await getSharedChatList(localStorage.token, page, filter, signal);
		if (signal.aborted) return;
		allChatsLoaded = newChatList.length === 0;

		if (newChatList.length > 0) {
			chatList = [...(chatList || []), ...newChatList];
		}

		chatListLoading = false;
	};

	const unshareHandler = async (chatId: string) => {
		const res = await deleteSharedChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res === true) {
			toast.success($i18n.t('Chat unshared successfully.'));
			onUpdate();
			searchHandler();
		} else if (res === false) {
			toast.error($i18n.t('Failed to unshare chat.'));
		}
	};

	const unshareAllHandler = async () => {
		loading = true;
		try {
			await unshareAllChats(localStorage.token);
			toast.success($i18n.t('All shared chats have been unshared.'));
			onUpdate();
			await searchHandler();
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	$: if (show) {
		searchHandler();
	} else {
		cancelSearch();
	}

	onDestroy(cancelSearch);
</script>

<UnshareAllConfirmDialog
	bind:show={showUnshareAllConfirmDialog}
	message={$i18n.t(
		'Are you sure you want to unshare all shared chats? This will remove all share links.'
	)}
	confirmLabel={$i18n.t('Unshare All')}
	on:confirm={() => {
		unshareAllHandler();
	}}
/>

<ChatsModal
	bind:show
	bind:query
	bind:orderBy
	bind:direction
	title={$i18n.t('Shared Chats')}
	emptyPlaceholder={$i18n.t('You have no shared conversations.')}
	shareUrl={false}
	{chatList}
	{allChatsLoaded}
	{chatListLoading}
	onUpdate={() => {
		onUpdate();
		searchHandler();
	}}
	loadHandler={loadMoreChats}
	{unshareHandler}
>
	<div slot="footer">
		<div class="flex flex-wrap text-sm font-normal gap-1.5 mt-2 m-1 justify-end w-full">
			<button
				class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-100 px-2.5 text-xs font-normal text-gray-800 transition hover:bg-gray-100/70 disabled:opacity-60 dark:bg-gray-850 dark:text-white dark:hover:bg-gray-850/60"
				disabled={loading}
				on:click={() => {
					showUnshareAllConfirmDialog = true;
				}}
			>
				{#if loading}
					<Spinner className="size-4" />
				{:else}
					{$i18n.t('Unshare All Shared Chats')}
				{/if}
			</button>
		</div>
	</div>
</ChatsModal>
