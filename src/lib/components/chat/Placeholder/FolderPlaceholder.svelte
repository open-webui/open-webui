<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';

	const i18n: Writable<any> = getContext('i18n');

	import { user } from '$lib/stores';

	import { fade } from 'svelte/transition';

	import ChatList from './ChatList.svelte';
	import FolderKnowledge from './FolderKnowledge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getChatListByFolderId } from '$lib/apis/chats';
	import { getSharedFolderChats } from '$lib/apis/folders';

	export let folder: any = null;

	let selectedTab = 'chats';

	let page = 1;

	let chats: any[] | null = null;
	let chatListLoading = false;
	let allChatsLoaded = false;

	$: showOwnerInfo = Boolean(
		folder?.shared ||
		(folder?.user_id && folder.user_id !== $user?.id) ||
		(folder?.access_grants?.length ?? 0) > 0
	);

	const loadChats = async () => {
		// getSharedFolderChats returns all users' chats in one shot; no pagination
		allChatsLoaded = true;
	};

	const setChatList = async () => {
		chats = null;
		page = 1;
		allChatsLoaded = false;
		chatListLoading = false;

		if (folder && folder.id) {
			// Always use the shared folder endpoint so owners also see
			// chats created by users who have write access to this folder.
			const res = await getSharedFolderChats(localStorage.token, folder.id).catch((error) => {
				console.error(error);
				return null;
			});
			if (res && res.chats) {
				chats = res.chats;
				allChatsLoaded = true;
			} else {
				// Fallback to regular API (e.g. if user has no shared access)
				const fallback = await getChatListByFolderId(localStorage.token, folder.id, page).catch(
					() => []
				);
				chats = fallback || [];
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
				<ChatList
					{chats}
					{chatListLoading}
					{allChatsLoaded}
					loadHandler={loadChats}
					{showOwnerInfo}
				/>
			{:else}
				<div class="py-10">
					<Spinner />
				</div>
			{/if}
		{/if}
	</div>
</div>
