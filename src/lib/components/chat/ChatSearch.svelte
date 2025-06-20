<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	
	// Import existing icon components
	import Search from '../icons/Search.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import XMark from '../icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let show = false;
	
	let searchInput: HTMLInputElement;
	let searchContainer: HTMLDivElement;
	let searchQuery = '';
	let totalResults = 0;
	let currentResult = 0;

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
				// Previous result (Shift+Enter)
				console.log('Previous result');
			} else {
				// Next result (Enter)
				console.log('Next result');
			}
		}
	};

	const closeSearch = () => {
		searchQuery = '';
		dispatch('close');
	};

	const handleInput = () => {
		// For now, just simulate some results
		if (searchQuery.trim()) {
			totalResults = 3; // Placeholder
			currentResult = 1; // Placeholder
		} else {
			totalResults = 0;
			currentResult = 0;
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
	<!-- Search Overlay -->
	<div 
		bind:this={searchContainer}
		class="fixed top-4 right-4 z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 min-w-80"
		transition:fly={{ y: -20, duration: 200 }}
		on:keydown={handleKeydown}
		role="dialog"
		aria-label="Chat search"
	>
		<div class="flex items-center gap-2">
			<!-- Search Icon -->
			<Search className="w-4 h-4 text-gray-500 dark:text-gray-400" />

			<!-- Search Input -->
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
			{/if}

			<!-- Navigation Buttons -->
			<div class="flex items-center gap-1">
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
					disabled={totalResults === 0}
					title="Previous (Shift+Enter)"
					aria-label="Previous result"
				>
					<ChevronUp className="w-3 h-3" />
				</button>
				
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
					disabled={totalResults === 0}
					title="Next (Enter)"
					aria-label="Next result"
				>
					<ChevronDown className="w-3 h-3" />
				</button>
			</div>

			<!-- Close Button -->
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