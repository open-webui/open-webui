<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { chats, chatId, mobile, showSidebar } from '$lib/stores';
	import { getChatListBySearchText } from '$lib/apis/chats';
	import PencilSquare from '../icons/PencilSquare.svelte';

	const i18n = getContext('i18n') as any;

	let search = '';
	let searchResults: any[] = [];
	let searchDebounceTimeout: ReturnType<typeof setTimeout> | null = null;
	type BaseChat = {
		id: string;
		title: string;
		time_range: string;
	};

	type RenderChat = {
		id: string;
		title: string;
		time_range: string;
		showTimeRange: boolean;
	};

	const toRenderChatList = (list: any[]): RenderChat[] => {
		const normalized: BaseChat[] = (list ?? []).map((item: any) => ({
			id: item?.id ?? '',
			title: item?.title ?? '',
			time_range: item?.time_range ?? 'Previous'
		}));

		return normalized.map((chat: BaseChat, idx: number) => ({
			...chat,
			showTimeRange: idx === 0 || chat.time_range !== normalized[idx - 1]?.time_range
		}));
	};

	$: sourceChats = (search ? searchResults : (($chats as any[] | null) ?? [])) as any[];
	$: displayChats = toRenderChatList(sourceChats);

	const searchDebounceHandler = async () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		if (search === '') {
			searchResults = [];
			return;
		}

		searchDebounceTimeout = setTimeout(async () => {
			searchResults = await getChatListBySearchText(localStorage.token, search);
		}, 500);
	};

	const handleNewChat = async () => {
		chatId.set('');
		await goto('/');
		if ($mobile) {
			showSidebar.set(false);
		}
	};

	const handleChatClick = async (id: string) => {
		chatId.set(id);
		await goto(`/c/${id}`);
	};

</script>

<div class="w-full h-screen max-h-[100dvh] bg-white dark:bg-gray-900 flex flex-col">
	<!-- Search Header -->
	<div class="px-6 py-6 border-b border-gray-200/50 dark:border-gray-800/50 bg-gradient-to-r from-white to-gray-50/50 dark:from-gray-900 dark:to-gray-900/50">
		<div class="max-w-4xl mx-auto flex items-center gap-4">
			<button
				class="p-2 rounded-lg hover:bg-gray-200/60 dark:hover:bg-gray-800/80 transition-all duration-200 active:scale-95"
				on:click={() => goto('/')}
				aria-label="Back"
			>
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-6 h-6 text-gray-600 dark:text-gray-400">
					<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
				</svg>
			</button>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2.5"
				stroke="currentColor"
				class="w-5 h-5 text-gray-400 dark:text-gray-500 flex-shrink-0"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="m21 21-5.197-5.197a7.5 7.5 0 1 0-10.607 0L21 21"
				/>
			</svg>
			<input
				type="text"
				bind:value={search}
				on:input={searchDebounceHandler}
				placeholder={$i18n.t('Search chats...')}
				class="flex-1 bg-transparent text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 outline-none text-sm sm:text-lg font-medium"
			/>
		</div>
	</div>

	<!-- Search Results -->
	<div class="flex-1 overflow-y-auto px-6 py-6">
		<div class="max-w-4xl mx-auto space-y-4">
			<!-- New Chat Option - Enhanced -->
			<button
				on:click={handleNewChat}
				class="w-full flex items-center gap-4 px-4 py-4 rounded-xl border border-orange-200/40 dark:border-orange-900/30 bg-gradient-to-r from-orange-50/60 to-orange-100/40 dark:from-orange-950/20 dark:to-orange-900/10 hover:from-orange-100/80 hover:to-orange-200/60 dark:hover:from-orange-950/40 dark:hover:to-orange-900/20 cursor-pointer transition-all duration-200 active:scale-[0.98] group mb-2 text-left"
			>
				<div class="flex-shrink-0 p-2.5 bg-gradient-to-br from-orange-100 to-orange-200 dark:from-orange-900/40 dark:to-orange-800/30 rounded-lg group-hover:from-orange-200 group-hover:to-orange-300 dark:group-hover:from-orange-900/60 dark:group-hover:to-orange-800/50 transition-all duration-200">
					<PencilSquare className="size-6 text-orange-600 dark:text-orange-400" strokeWidth="2.5" />
				</div>
			<span class="font-semibold text-gray-900 dark:text-white group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors text-base sm:text-lg">{$i18n.t('New chat')}</span>
			</button>

			<!-- Chat Results Groups -->
			{#if displayChats.length > 0}
				{#each displayChats as chat, idx (chat.id)}
					{#if chat.showTimeRange}
						<div class="pt-4 pb-3 first:pt-0">
							<div class="text-[10px] sm:text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest px-2 mb-4">{chat.time_range}</div>
						</div>
					{/if}

					<button
						on:click={() => handleChatClick(chat.id)}
						class="w-full flex items-center gap-4 px-4 py-4 rounded-lg hover:bg-gray-100/80 dark:hover:bg-gray-800/60 cursor-pointer transition-all duration-150 active:scale-[0.98] group border border-transparent hover:border-gray-200/50 dark:hover:border-gray-700/50 text-left"
					>
						<div class="flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 dark:from-orange-500 dark:to-orange-700 flex items-center justify-center shadow-sm group-hover:shadow-md transition-all">
							<span class="text-white font-semibold">
								{chat.title.charAt(0).toUpperCase()}
							</span>
						</div>
						<div class="flex-1 min-w-0">
							<div class="text-sm sm:text-base font-semibold text-gray-900 dark:text-gray-100 truncate group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">{chat.title}</div>
							<div class="text-xs sm:text-sm text-gray-400 dark:text-gray-500 mt-1">{chat.time_range}</div>
						</div>
					</button>
				{/each}
			{:else if search}
				<div class="flex flex-col items-center justify-center py-16 text-center">
					<div class="flex items-center justify-center w-20 h-20 rounded-full bg-gray-100 dark:bg-gray-800/50 mb-4">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-10 h-10 text-gray-400 dark:text-gray-600"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
							/>
						</svg>
					</div>
				<p class="text-base sm:text-lg font-semibold text-gray-600 dark:text-gray-400">{$i18n.t('No chats found')}</p>
				<p class="text-sm sm:text-base text-gray-500 dark:text-gray-500 mt-2">Try different keywords</p>
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center py-16 text-center">
					<div class="flex items-center justify-center w-20 h-20 rounded-full bg-gray-100 dark:bg-gray-800/50 mb-4">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-10 h-10 text-gray-400 dark:text-gray-600"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m21 21-5.197-5.197a7.5 7.5 0 1 0-10.607 0L21 21"
							/>
						</svg>
					</div>
					<p class="text-base sm:text-lg font-semibold text-gray-600 dark:text-gray-400">Start typing to search</p>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	/* Custom scrollbar for search results */
	::-webkit-scrollbar {
		width: 8px;
	}

	::-webkit-scrollbar-track {
		background: transparent;
	}

	::-webkit-scrollbar-thumb {
		background: #d1d5db;
		border-radius: 4px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: #9ca3af;
	}

	:global(.dark) ::-webkit-scrollbar-thumb {
		background: #4b5563;
	}

	:global(.dark) ::-webkit-scrollbar-thumb:hover {
		background: #6b7280;
	}
</style>
