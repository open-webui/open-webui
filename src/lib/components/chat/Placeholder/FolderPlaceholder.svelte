<script>
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { fade } from 'svelte/transition';

	import ChatList from './ChatList.svelte';
	import FolderKnowledge from './FolderKnowledge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getChatListByFolderId } from '$lib/apis/chats';

	export let folder = null;

	let selectedTab = 'chats';

	let page = 1;

	let chats = null;
	let chatListLoading = false;
	let allChatsLoaded = false;

	const loadChats = async () => {
		chatListLoading = true;

		page += 1;

		let newChatList = [];

		newChatList = await getChatListByFolderId(localStorage.token, folder.id, page).catch(
			(error) => {
				console.error(error);
				return [];
			}
		);

		// once the bottom of the list has been reached (no results) there is no need to continue querying
		allChatsLoaded = newChatList.length === 0;
		chats = [...chats, ...newChatList];

		chatListLoading = false;
	};

	const setChatList = async () => {
		chats = null;
		page = 1;
		allChatsLoaded = false;
		chatListLoading = false;

		if (folder && folder.id) {
			const res = await getChatListByFolderId(localStorage.token, folder.id, page);

			if (res) {
				chats = res;
			} else {
				chats = [];
			}
		} else {
			chats = [];
		}
	};

	$: if (folder) {
		setChatList();
	}
</script>

<div>
	<!-- <div class="mb-1">
		<div
			class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
		>
			<button
				class="min-w-fit p-1.5 {selectedTab === 'knowledge'
					? ''
					: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
				type="button"
				on:click={() => {
					selectedTab = 'knowledge';
				}}>{$i18n.t('Knowledge')}</button
			>

			<button
				class="min-w-fit p-1.5 {selectedTab === 'chats'
					? ''
					: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
				type="button"
				on:click={() => {
					selectedTab = 'chats';
				}}
			>
				{$i18n.t('Chats')}
			</button>
		</div>
	</div> -->

	<div class="">
		{#if selectedTab === 'knowledge'}
			<FolderKnowledge />
		{:else if selectedTab === 'chats'}
			{#if chats !== null}
				<ChatList {chats} {chatListLoading} {allChatsLoaded} loadHandler={loadChats} />
			{:else}
				<div class="py-10">
					<Spinner />
				</div>
			{/if}
		{/if}
	</div>
</div>
