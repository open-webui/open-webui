<script lang="ts">
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import { deleteSharedChatById, getSharedChatList } from '$lib/apis/chats';

	import ChatsModal from './ChatsModal.svelte';

	const i18n: Writable<any> = getContext('i18n');

	export let show = false;
	export let onUpdate = () => {};

	let chatList: any[] | null = null;
	let page = 1;

	let query = '';
	let orderBy = 'updated_at';
	let direction = 'desc';

	let allChatsLoaded = false;
	let chatListLoading = false;
	let searchDebounceTimeout: any;

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

	const init = async () => {
		chatList = await getSharedChatList(localStorage.token);
	};

	$: if (show) {
		init();
	}
</script>

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
/>
