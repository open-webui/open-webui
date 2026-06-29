<script lang="ts">
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
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
	let searchDebounceTimeout: any;

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

	const searchHandler = async () => {
		if (!show) {
			return;
		}

		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		page = 1;
		chatList = null;

		if (query === '') {
			chatList = await getSharedChatList(localStorage.token, page, filter);
		} else {
			searchDebounceTimeout = setTimeout(async () => {
				chatList = await getSharedChatList(localStorage.token, page, filter);
			}, 500);
		}

		if ((chatList ?? []).length === 0) {
			allChatsLoaded = true;
		} else {
			allChatsLoaded = false;
		}
	};

	const loadMoreChats = async () => {
		chatListLoading = true;
		page += 1;

		let newChatList = [];

		if (query) {
			newChatList = await getSharedChatList(localStorage.token, page, filter);
		} else {
			newChatList = await getSharedChatList(localStorage.token, page, filter);
		}

		// once the bottom of the list has been reached (no results) there is no need to continue querying
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
			init();
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
			await init();
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	const init = async () => {
		chatList = await getSharedChatList(localStorage.token);
	};

	$: if (show) {
		init();
	}
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
		init();
	}}
	loadHandler={loadMoreChats}
	{unshareHandler}
>
	<div slot="footer">
		<div class="flex flex-wrap text-sm font-medium gap-1.5 mt-2 m-1 justify-end w-full">
			<button
				class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-800 rounded-3xl"
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
