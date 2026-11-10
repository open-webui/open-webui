<script lang="ts">
	import { onMount } from 'svelte';

	import { socket, user } from '$lib/stores';

	import ChatList from './ChatList.svelte';
	import FolderKnowledge from './FolderKnowledge.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import {
		folderStates,
		folderChatPageKey,
		loadFolderChatPage,
		updateFolderChatLists,
		isCancelledFolderRequest,
	} from '$lib/stores/folderStates';
	import { registerFolderRefreshHandler } from '$lib/stores/chatList';

	type FolderPlaceholderFolder = {
		id?: string;
		shared?: boolean;
		user_id?: string;
		access_grants?: unknown[];
	};

	type FolderChat = {
		id: string;
		active?: boolean;
		[key: string]: unknown;
	};

	export let folder: FolderPlaceholderFolder | null = null;

	let selectedTab = 'chats';

	const CHATS_PAGE_SIZE = 10;
	let page = 1;
	let totalChats = 0;
	let orderBy: 'title' | 'updated_at' = 'updated_at';
	let direction: 'asc' | 'desc' = 'desc';
	let currentFolderId: string | null = null;

	let chats: FolderChat[] | null = null;
	let chatListLoading = false;
	let refreshQueued = false;

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

	const updateChatActive = (chatId: string, active: boolean) => {
		const found = chats?.some((chat) => chat.id === chatId) ?? false;
		updateFolderChatLists({ id: chatId, active });
		return found;
	};

	const refreshChatListSoon = (resetPage = false) => {
		if (refreshQueued) {
			if (resetPage) {
				page = 1;
			}
			return;
		}
		if (resetPage) {
			page = 1;
		}
		refreshQueued = true;
		queueMicrotask(async () => {
			refreshQueued = false;
			await setChatList();
		});
	};

	let requestGeneration = 0;
	let loadError = '';
	$: retainedPage = folder?.id ? $folderStates[folder.id]?.chatPages[folderChatPageKey({ page, sortBy: orderBy, sortDir: direction })] : null;
	$: chats = retainedPage?.chats ?? null;
	$: totalChats = retainedPage?.total ?? 0;

	const setChatList = async () => {
		const folderId = folder?.id;
		const generation = ++requestGeneration;
		if (!folderId) return;
		chatListLoading = true;
		loadError = '';
		try {
			await loadFolderChatPage(localStorage.token, folderId, { page, sortBy: orderBy, sortDir: direction }, true);
		} catch (error) {
			if (generation === requestGeneration && !isCancelledFolderRequest(error)) loadError = String(error);
		} finally {
			if (generation === requestGeneration) chatListLoading = false;
		}
	};

	const chatEventHandler = (event: {
		chat_id?: string;
		data?: { type?: string; data?: { active?: boolean } };
	}) => {
		if (event.data?.type === 'chat:active' && event.chat_id) {
			const active = event.data.data?.active ?? false;
			if (!updateChatActive(event.chat_id, active) && active) {
				refreshChatListSoon(true);
			}
		} else if (event.data?.type === 'chat:list') {
			refreshChatListSoon(true);
		}
	};

	onMount(() => {
		const unregister = registerFolderRefreshHandler((id) => {
			if (id === undefined || id === folder?.id) return setChatList();
		});
		const socketInstance = $socket;
		socketInstance?.on('events', chatEventHandler);
		socketInstance?.on('connect', refreshChatListSoon);

		return () => {
			unregister();
			requestGeneration++;
			socketInstance?.off('events', chatEventHandler);
			socketInstance?.off('connect', refreshChatListSoon);
		};
	});

	$: if (folder?.id && folder.id !== currentFolderId) {
		currentFolderId = folder.id;
		page = 1;
		setChatList();
	}

	$: if (!folder?.id && currentFolderId !== null) {
		currentFolderId = null;
		requestGeneration++;
	}
</script>

<div>
	<!-- <div class="mb-1">
		<div
			class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-normal bg-transparent py-1 touch-auto pointer-events-auto"
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
			{:else if loadError}
				<div class="py-10" role="alert">{loadError}</div>
			{:else}
				<div class="py-10">
					<Spinner />
				</div>
			{/if}
		{/if}
	</div>
</div>
