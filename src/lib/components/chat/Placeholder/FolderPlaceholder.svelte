<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';

	const i18n: Writable<any> = getContext('i18n');

	import { user } from '$lib/stores';

	import { fade } from 'svelte/transition';

	import ChatList from './ChatList.svelte';
	import FolderKnowledge from './FolderKnowledge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getSharedFolderChats } from '$lib/apis/folders';

	export let folder: any = null;

	let selectedTab = 'chats';

	const CHATS_PAGE_SIZE = 10;
	let page = 1;
	let totalChats = 0;
	let orderBy: 'title' | 'updated_at' = 'updated_at';
	let direction: 'asc' | 'desc' = 'desc';
	let currentFolderId: string | null = null;

	let chats: any[] | null = null;
	let chatListLoading = false;

	$: showOwnerInfo = Boolean(
		folder?.shared ||
		(folder?.user_id && folder.user_id !== $user?.id) ||
		(folder?.access_grants?.length ?? 0) > 0
	);

	const setSortKey = (key: 'title' | 'updated_at') => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = key === 'title' ? 'asc' : 'desc';
		}
		page = 1;
		setChatList();
	};

	const setPage = (nextPage: number) => {
		if (nextPage === page || chatListLoading) {
			return;
		}

		page = nextPage;
		setChatList();
	};

	const setChatList = async () => {
		const folderId = folder?.id;
		chats = null;

		if (folderId) {
			// Always use the shared folder endpoint so owners also see
			// chats created by users who have write access to this folder.
			chatListLoading = true;
			const res = await getSharedFolderChats(localStorage.token, folderId, {
				page,
				sortBy: orderBy,
				sortDir: direction
			}).catch((error) => {
				console.error(error);
				return null;
			});
			chatListLoading = false;

			if (res && res.chats) {
				chats = res.chats;
				totalChats = res.total ?? res.chats.length;
			} else {
				chats = [];
				totalChats = 0;
			}
		} else {
			chats = [];
			totalChats = 0;
		}
	};

	$: if (folder?.id && folder.id !== currentFolderId) {
		currentFolderId = folder.id;
		page = 1;
		setChatList();
	}

	$: if (!folder?.id && currentFolderId !== null) {
		currentFolderId = null;
		chats = [];
		totalChats = 0;
	}
</script>

<div>
	<!-- <div class="mb-1">
		<div
			class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-normal rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
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
					{showOwnerInfo}
					{page}
					total={totalChats}
					perPage={CHATS_PAGE_SIZE}
					{orderBy}
					{direction}
					onPageChange={setPage}
					onSort={setSortKey}
				/>
			{:else}
				<div class="py-10">
					<Spinner />
				</div>
			{/if}
		{/if}
	</div>
</div>
