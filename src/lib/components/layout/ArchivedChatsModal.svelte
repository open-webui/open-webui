<script lang="ts">
	// @ts-ignore
	import fileSaver from 'file-saver';
	import type { Writable } from 'svelte/store';
	const { saveAs } = fileSaver;

	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	import {
		archiveChatById,
		getAllArchivedChats,
		getArchivedChatList,
		unarchiveAllChats
	} from '$lib/apis/chats';

	import ChatsModal from './ChatsModal.svelte';
	import UnarchiveAllConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
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

	let showUnarchiveAllConfirmDialog = false;

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
			chatList = await getArchivedChatList(localStorage.token, page, filter);
		} else {
			searchDebounceTimeout = setTimeout(async () => {
				chatList = await getArchivedChatList(localStorage.token, page, filter);
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
			newChatList = await getArchivedChatList(localStorage.token, page, filter);
		} else {
			newChatList = await getArchivedChatList(localStorage.token, page, filter);
		}

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;

		if (newChatList.length > 0) {
			chatList = [...(chatList || []), ...newChatList];
		}

		chatListLoading = false;
	};

	const exportChatsHandler = async () => {
		const chats = await getAllArchivedChats(localStorage.token);
		let blob = new Blob([JSON.stringify(chats)], {
			type: 'application/json'
		});
		saveAs(blob, `${$i18n.t('archived-chat-export')}-${Date.now()}.json`);
	};

	const unarchiveHandler = async (chatId: string) => {
		const res = await archiveChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});

		onUpdate();
		init();
	};

	const unarchiveAllHandler = async () => {
		loading = true;
		try {
			await unarchiveAllChats(localStorage.token);
			toast.success($i18n.t('All chats have been unarchived.'));
			onUpdate();
			await init();
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	const init = async () => {
		chatList = await getArchivedChatList(localStorage.token);
	};

	$: if (show) {
		init();
	}
</script>

<UnarchiveAllConfirmDialog
	bind:show={showUnarchiveAllConfirmDialog}
	message={$i18n.t('Are you sure you want to unarchive all archived chats?')}
	confirmLabel={$i18n.t('Unarchive All')}
	on:confirm={() => {
		unarchiveAllHandler();
	}}
/>

<ChatsModal
	bind:show
	bind:query
	bind:orderBy
	bind:direction
	title={$i18n.t('Archived Chats')}
	emptyPlaceholder={$i18n.t('You have no archived conversations.')}
	{chatList}
	{allChatsLoaded}
	{chatListLoading}
	onUpdate={() => {
		init();
	}}
	loadHandler={loadMoreChats}
	{unarchiveHandler}
>
	<div slot="footer">
		<div class="flex flex-wrap text-sm font-medium gap-1.5 mt-2 m-1 justify-end w-full">
			<button
				class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-800 rounded-3xl"
				disabled={loading}
				on:click={() => {
					showUnarchiveAllConfirmDialog = true;
				}}
			>
				{#if loading}
					<Spinner className="size-4" />
				{:else}
					{$i18n.t('Unarchive All Archived Chats')}
				{/if}
			</button>

			<button
				class="px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-800 rounded-3xl"
				disabled={loading}
				on:click={() => {
					exportChatsHandler();
				}}
			>
				{$i18n.t('Export All Archived Chats')}
			</button>
		</div>
	</div>
</ChatsModal>
