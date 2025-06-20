<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';
	import { fly } from 'svelte/transition';
	
	// Import existing icon components
	import Search from '../icons/Search.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import XMark from '../icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let show = false;
	export let history = { messages: {}, currentId: null };
	
	let searchInput: HTMLInputElement;
	let searchContainer: HTMLDivElement;
	let searchQuery = '';
	let matchingMessageIds: string[] = [];
	let currentIndex = 0;

	// Computed values
	$: totalResults = matchingMessageIds.length;
	$: currentResult = totalResults > 0 ? currentIndex + 1 : 0;

	// Auto-focus when search opens
	$: if (show && searchInput) {
		searchInput.focus();
	}

	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Escape') {
			closeSearch();
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (e.shiftKey) {
				navigateToPrevious();
			} else {
				navigateToNext();
			}
		}
	};

	const closeSearch = () => {
		searchQuery = '';
		matchingMessageIds = [];
		currentIndex = 0;
		dispatch('close');
	};

	const performSearch = (query: string) => {
		if (!query.trim() || !history?.messages) {
			matchingMessageIds = [];
			currentIndex = 0;
			return;
		}

		const searchTerm = query.toLowerCase().trim();
		const messageIds: string[] = [];

		// Search through all messages
		Object.values(history.messages).forEach((message: any) => {
			if (message?.content && typeof message.content === 'string') {
				if (message.content.toLowerCase().includes(searchTerm)) {
					messageIds.push(message.id);
				}
			}
		});

		matchingMessageIds = messageIds;
		currentIndex = messageIds.length > 0 ? 0 : 0;
	};

	const handleInput = () => {
		performSearch(searchQuery);
	};

	const navigateToNext = () => {
		if (totalResults > 0) {
			currentIndex = (currentIndex + 1) % totalResults;
			scrollToCurrentResult();
		}
	};

	const navigateToPrevious = () => {
		if (totalResults > 0) {
			currentIndex = currentIndex === 0 ? totalResults - 1 : currentIndex - 1;
			scrollToCurrentResult();
		}
	};

	const scrollToCurrentResult = () => {
		if (matchingMessageIds.length > 0 && currentIndex < matchingMessageIds.length) {
			const messageId = matchingMessageIds[currentIndex];
			const messageElement = document.getElementById(`message-${messageId}`);
			if (messageElement) {
				// Use same scroll pattern as Chat.svelte
				messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
			}
		}
	};

	// Click outside handler
	const handleClickOutside = (e: MouseEvent) => {
		if (show && searchContainer && !searchContainer.contains(e.target as Node)) {
			closeSearch();
		}
	};

	onMount(() => {
		document.addEventListener('click', handleClickOutside);
	});

	onDestroy(() => {
		document.removeEventListener('click', handleClickOutside);
	});
</script>

{#if show}
	<div 
		bind:this={searchContainer}
		class="fixed top-4 right-4 z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 min-w-80"
		transition:fly={{ y: -20, duration: 200 }}
		on:keydown={handleKeydown}
		role="dialog"
		aria-label="Chat search"
	>
		<div class="flex items-center gap-2">
			<Search className="w-4 h-4 text-gray-500 dark:text-gray-400" />

			<input
				bind:this={searchInput}
				bind:value={searchQuery}
				on:input={handleInput}
				type="text"
				placeholder="Search in chat..."
				class="flex-1 bg-transparent border-none outline-none text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
			/>

			<!-- Results Counter -->
			{#if totalResults > 0}
				<div class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
					{currentResult} of {totalResults}
				</div>
			{:else if searchQuery.trim()}
				<div class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
					No results
				</div>
			{/if}

			<!-- Navigation Buttons -->
			<div class="flex items-center gap-1">
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
					disabled={totalResults === 0}
					title="Previous (Shift+Enter)"
					aria-label="Previous result"
					on:click={navigateToPrevious}
				>
					<ChevronUp className="w-3 h-3" />
				</button>
				
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
					disabled={totalResults === 0}
					title="Next (Enter)"
					aria-label="Next result"
					on:click={navigateToNext}
				>
					<ChevronDown className="w-3 h-3" />
				</button>
			</div>

			<button
				on:click={closeSearch}
				class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
				title="Close (Esc)"
				aria-label="Close search"
			>
				<XMark className="w-3 h-3" />
			</button>
		</div>

		<!-- Search Tips -->
		{#if searchQuery === ''}
			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				Press <kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">Enter</kbd> to navigate results
			</div>
		{/if}
	</div>
{/if}

<style>
	kbd {
		font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
	}
</style> 