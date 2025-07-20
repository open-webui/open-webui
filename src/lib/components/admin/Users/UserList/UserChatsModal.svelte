<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(localizedFormat);

	import { getChatListByUserId, deleteChatById, getArchivedChatList } from '$lib/apis/chats';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChatsModal from '$lib/components/layout/ChatsModal.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let user;

	let chatList = null;
	let page = 1;

	let query = '';
	let orderBy = 'updated_at';
	let direction = 'desc';

	let filter = {};
	$: filter = {
		...(query ? { query } : {}),
		...(orderBy ? { order_by: orderBy } : {}),
		...(direction ? { direction } : {})
	};

	$: if (filter !== null) {
		searchHandler();
	}

	let allChatsLoaded = false;
	let chatListLoading = false;

	let searchDebounceTimeout;

	const searchHandler = async () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		page = 1;
		chatList = null;

		if (query === '') {
			chatList = await getChatListByUserId(localStorage.token, user.id, page, filter);
		} else {
			searchDebounceTimeout = setTimeout(async () => {
				chatList = await getChatListByUserId(localStorage.token, user.id, page, filter);
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

		newChatList = await getChatListByUserId(localStorage.token, user.id, page, filter);

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;

		if (newChatList.length > 0) {
			chatList = [...chatList, ...newChatList];
		}

		chatListLoading = false;
	};

	const init = async () => {
		chatList = await getChatListByUserId(localStorage.token, user.id, page, filter);
	};

	$: if (show) {
		init();
	} else {
		chatList = null;
		page = 1;

		allChatsLoaded = false;
		chatListLoading = false;
	}
</script>

<ChatsModal
	bind:show
	bind:query
	bind:orderBy
	bind:direction
	title={$i18n.t("{{user}}'s Chats", { user: user.name })}
	emptyPlaceholder={$i18n.t('No chats found for this user.')}
	shareUrl={true}
	{chatList}
	{allChatsLoaded}
	{chatListLoading}
	onUpdate={() => {
		init();
	}}
	loadHandler={loadMoreChats}
></ChatsModal>
