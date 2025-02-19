<script lang="ts">
	import { fade } from 'svelte/transition';
	import { getAllTags, getChatListBySearchText } from '$lib/apis/chats';
	import { tags, chats } from '$lib/stores';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import XMark from '$lib/components/icons/XMark.svelte';
	import SearchIcon from '$lib/components/icons/Search.svelte';
	import ChatItem from './ChatItem.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	interface Chat {
		id: string;
		title: string;
		time_range?: string;
		created_at?: number;
		updated_at?: number;
		folder_id?: string | null;
		pinned?: boolean;
		archived?: boolean;
		tags?: string[];
	}

	const i18n = getContext('i18n');

	export let show = false;

	let search = '';
	let searchResults: Chat[] = [];
	let loading = false;
	let searchDebounceTimeout: NodeJS.Timeout | null = null;
	let selectedIndex = -1;

	const handleKeydown = (e: KeyboardEvent) => {
		if (searchResults.length === 0) return;

		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				selectedIndex = (selectedIndex + 1) % searchResults.length;
				break;
			case 'ArrowUp':
				e.preventDefault();
				selectedIndex = selectedIndex <= 0 ? searchResults.length - 1 : selectedIndex - 1;
				break;
			case 'Enter':
				e.preventDefault();
				if (selectedIndex >= 0 && selectedIndex < searchResults.length) {
					const selectedChat = searchResults[selectedIndex];
					show = false;
					search = '';
					goto(`/c/${selectedChat.id}`);
				}
				break;
			case 'Escape':
				e.preventDefault();
				show = false;
				search = '';
				break;
		}
	};

	const searchDebounceHandler = async () => {
		selectedIndex = -1;
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		if (search === '') {
			searchResults = [];
			return;
		}

		searchDebounceTimeout = setTimeout(async () => {
			loading = true;
			searchResults = await getChatListBySearchText(localStorage.token, search);
			loading = false;
		}, 300);
	};

	$: if (show && !search) {
		searchResults = [];
		selectedIndex = -1;
	}
</script>

{#if show}
	<div
		class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
		transition:fade={{ duration: 200 }}
		on:click|self={() => {
			show = false;
			search = '';
		}}
		role="dialog"
		aria-label={$i18n.t('Search Chats')}
	>
		<div
			class="fr-background-default--grey w-full max-w-2xl rounded-xl shadow-xl flex flex-col h-[60vh]"
			transition:fade={{ duration: 150 }}
		>
			<!-- Header -->
			<div class="p-4 border-b dark:border-gray-800 flex justify-between items-center">
				<div class="text-lg font-medium" id="search-modal-title">{$i18n.t('Search Chats')}</div>
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					on:click={() => {
						show = false;
						search = '';
					}}
					aria-label={$i18n.t('Close search')}
				>
					<XMark className="size-5" strokeWidth="2" />
				</button>
			</div>

			<!-- Search Input -->
			<div class="p-4 border-b dark:border-gray-800">
				<div class="relative">
					<div
						class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"
						aria-hidden="true"
					>
						<SearchIcon className="size-4 text-gray-400" strokeWidth="2" />
					</div>
					<input
						type="text"
						class="block w-full pl-10 pr-3 py-2 border dark:border-gray-800 rounded-lg bg-gray-50 dark:bg-gray-950 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-600 focus:border-transparent"
						placeholder={$i18n.t('Search chats...')}
						bind:value={search}
						on:input={searchDebounceHandler}
						on:keydown={handleKeydown}
						aria-label={$i18n.t('Search chats')}
						aria-controls="search-results"
						aria-expanded={searchResults.length > 0}
					/>
				</div>
			</div>

			<!-- Results -->
			<div
				class="flex-1 overflow-y-auto p-2"
				id="search-results"
				role="listbox"
				aria-label={$i18n.t('Search results')}
			>
				{#if loading}
					<div class="flex justify-center items-center py-8" aria-live="polite">
						<Spinner className="size-6" />
					</div>
				{:else if searchResults.length > 0}
					<div class="space-y-1">
						{#each searchResults as chat, index}
							<div
								class="relative {selectedIndex === index ? 'bg-gray-100 dark:bg-gray-800' : ''}"
								role="option"
								aria-selected={selectedIndex === index}
							>
								<ChatItem
									id={chat.id}
									title={chat.title}
									on:change={() => searchDebounceHandler()}
									on:select={() => {
										show = false;
										search = '';
									}}
								/>
							</div>
						{/each}
					</div>
				{:else if search}
					<div class="text-center py-8 text-gray-500" role="status">
						{$i18n.t('No chats found')}
					</div>
				{:else}
					<div class="text-center py-8 text-gray-500" role="status">
						{$i18n.t('Start typing to search chats')}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
