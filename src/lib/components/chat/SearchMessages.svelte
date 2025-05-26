<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { fade, slide } from 'svelte/transition';
	
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let searchQuery = '';
	export let searchResults = [];
	export let currentSearchIndex = -1;
	export let show = false;

	const handleSearch = (e) => {
		searchQuery = e.target.value;
		dispatch('search', searchQuery);
	};

	const handleKeydown = (e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			if (e.shiftKey) {
				dispatch('previous');
			} else {
				dispatch('next');
			}
		} else if (e.key === 'Escape') {
			dispatch('close');
		}
	};

	const truncateContent = (content, maxLength = 100) => {
		if (!content) return '';
		return content.length > maxLength ? content.substring(0, maxLength) + '...' : content;
	};

	const highlightMatch = (content, query) => {
		if (!query.trim()) return content;
		const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
		return content.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800">$1</mark>');
	};
</script>

{#if show}
	<div 
		class="fixed top-20 right-4 z-50 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 w-80"
		transition:fade={{ duration: 200 }}
	>
		<div class="flex items-center gap-2 mb-3">
			<div class="flex-1 relative">
				<input
					id="message-search-input"
					type="text"
					bind:value={searchQuery}
					on:input={handleSearch}
					on:keydown={handleKeydown}
					placeholder={$i18n.t('Search messages...')}
					class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
				{#if searchQuery}
					<button
						on:click={() => {
							searchQuery = '';
							dispatch('search', '');
						}}
						class="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				{/if}
			</div>
			<button
				on:click={() => dispatch('close')}
				class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		</div>

		{#if searchResults.length > 0}
			<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
				<span>{currentSearchIndex + 1} of {searchResults.length} results</span>
				<div class="flex gap-1">
					<button
						on:click={() => dispatch('previous')}
						disabled={searchResults.length === 0}
						class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
						title="Previous (Shift+Enter)"
					>
						<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
						</svg>
					</button>
					<button
						on:click={() => dispatch('next')}
						disabled={searchResults.length === 0}
						class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
						title="Next (Enter)"
					>
						<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
						</svg>
					</button>
				</div>
			</div>

			<div class="max-h-60 overflow-y-auto space-y-1">
				{#each searchResults as result, index}
					<button
						on:click={() => dispatch('jump', result.id)}
						class="w-full text-left p-2 rounded text-xs hover:bg-gray-50 dark:hover:bg-gray-800 border border-transparent {index === currentSearchIndex ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''}"
					>
						<div class="flex items-center gap-2 mb-1">
							<span class="px-1.5 py-0.5 rounded text-xs font-medium {result.role === 'user' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'}">
								{result.role === 'user' ? 'You' : 'Assistant'}
							</span>
							{#if result.timestamp}
								<span class="text-gray-400 text-xs">
									{new Date(result.timestamp * 1000).toLocaleDateString()}
								</span>
							{/if}
						</div>
						<div class="text-gray-600 dark:text-gray-300 line-clamp-2">
							{@html highlightMatch(truncateContent(result.content), searchQuery)}
						</div>
					</button>
				{/each}
			</div>
		{:else if searchQuery}
			<div class="text-center text-gray-500 dark:text-gray-400 text-sm py-4">
				{$i18n.t('No messages found')}
			</div>
		{/if}

		<div class="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
			<div class="flex justify-between">
				<span>Ctrl+F to search</span>
				<span>Esc to close</span>
			</div>
		</div>
	</div>
{/if}

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style> 