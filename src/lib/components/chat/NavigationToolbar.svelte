<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { fade } from 'svelte/transition';
	
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let history = {};
	export let messagesCount = 20;
	export let totalMessages = 0;

	let showToolbar = false;

	// Calculate total messages
	$: totalMessages = Object.keys(history?.messages || {}).length;

	const scrollToTop = () => {
		const container = document.getElementById('messages-container');
		if (container) {
			container.scrollTo({ top: 0, behavior: 'smooth' });
		}
	};

	const scrollToBottom = () => {
		const container = document.getElementById('messages-container');
		if (container) {
			container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
		}
	};

	const loadAllMessages = () => {
		dispatch('loadAll');
	};

	const exportChat = () => {
		dispatch('export');
	};
</script>

{#if totalMessages > 50}
	<div class="fixed bottom-20 right-4 z-40">
		{#if showToolbar}
			<div 
				class="mb-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-2 flex flex-col gap-1"
				transition:fade={{ duration: 200 }}
			>
				<!-- Search Button -->
				<button
					on:click={() => dispatch('search')}
					class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md transition-colors"
					title="Search messages (Ctrl+F)"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
					</svg>
					<span>Search</span>
				</button>

				<!-- Date Navigation Button -->
				<button
					on:click={() => dispatch('dateNav')}
					class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md transition-colors"
					title="Jump to date"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
					</svg>
					<span>Jump to Date</span>
				</button>

				<!-- Scroll to Top -->
				<button
					on:click={scrollToTop}
					class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md transition-colors"
					title="Scroll to top"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11l5-5m0 0l5 5m-5-5v12"></path>
					</svg>
					<span>Top</span>
				</button>

				<!-- Scroll to Bottom -->
				<button
					on:click={scrollToBottom}
					class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md transition-colors"
					title="Scroll to bottom"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 13l-5 5m0 0l-5-5m5 5V6"></path>
					</svg>
					<span>Bottom</span>
				</button>

				<!-- Load All Messages -->
				{#if messagesCount < totalMessages}
					<button
						on:click={loadAllMessages}
						class="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
						title="Load all {totalMessages} messages"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
						</svg>
						<span>Load All ({totalMessages})</span>
					</button>
				{/if}

				<!-- Export Chat -->
				<button
					on:click={exportChat}
					class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md transition-colors"
					title="Export chat"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
					</svg>
					<span>Export</span>
				</button>

				<!-- Message Count Info -->
				<div class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-700">
					Showing {messagesCount} of {totalMessages} messages
				</div>
			</div>
		{/if}

		<!-- Toggle Button -->
		<button
			on:click={() => showToolbar = !showToolbar}
			class="w-12 h-12 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center transition-all duration-200 {showToolbar ? 'rotate-45' : ''}"
			title="Navigation tools"
		>
			{#if showToolbar}
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			{:else}
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4"></path>
				</svg>
			{/if}
		</button>
	</div>
{/if} 