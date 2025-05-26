<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { fade } from 'svelte/transition';
	
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let history = {};
	export let show = false;

	let selectedDate = '';
	let availableDates = [];

	// Calculate available dates from message history
	$: if (history?.messages) {
		const dates = new Set();
		Object.values(history.messages).forEach((message: any) => {
			if (message.timestamp) {
				const date = new Date(message.timestamp * 1000).toISOString().split('T')[0];
				dates.add(date);
			}
		});
		availableDates = Array.from(dates).sort().reverse(); // Most recent first
	}

	const jumpToDate = (date) => {
		if (!date) return;

		// Find the first message from this date
		const targetTimestamp = new Date(date).getTime() / 1000;
		const messagesFromDate = Object.values(history.messages || {})
			.filter((msg: any) => {
				if (!msg.timestamp) return false;
				const msgDate = new Date(msg.timestamp * 1000).toISOString().split('T')[0];
				return msgDate === date;
			})
			.sort((a: any, b: any) => a.timestamp - b.timestamp);

		if (messagesFromDate.length > 0) {
			dispatch('jump', messagesFromDate[0].id);
		}
	};

	const formatDate = (dateStr) => {
		const date = new Date(dateStr);
		const today = new Date();
		const yesterday = new Date(today);
		yesterday.setDate(yesterday.getDate() - 1);

		if (date.toDateString() === today.toDateString()) {
			return 'Today';
		} else if (date.toDateString() === yesterday.toDateString()) {
			return 'Yesterday';
		} else {
			return date.toLocaleDateString(undefined, { 
				weekday: 'short', 
				month: 'short', 
				day: 'numeric',
				year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
			});
		}
	};

	const getMessageCount = (date) => {
		return Object.values(history.messages || {}).filter((msg: any) => {
			if (!msg.timestamp) return false;
			const msgDate = new Date(msg.timestamp * 1000).toISOString().split('T')[0];
			return msgDate === date;
		}).length;
	};
</script>

{#if show}
	<div 
		class="fixed top-4 left-4 z-50 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4 w-72"
		transition:fade={{ duration: 200 }}
	>
		<div class="flex items-center justify-between mb-3">
			<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">
				{$i18n.t('Jump to Date')}
			</h3>
			<button
				on:click={() => dispatch('close')}
				class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		</div>

		{#if availableDates.length > 0}
			<div class="space-y-1 max-h-80 overflow-y-auto">
				{#each availableDates as date}
					<button
						on:click={() => jumpToDate(date)}
						class="w-full text-left p-2 rounded text-sm hover:bg-gray-50 dark:hover:bg-gray-800 flex items-center justify-between"
					>
						<div>
							<div class="font-medium text-gray-900 dark:text-gray-100">
								{formatDate(date)}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">
								{date}
							</div>
						</div>
						<div class="text-xs text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
							{getMessageCount(date)} messages
						</div>
					</button>
				{/each}
			</div>
		{:else}
			<div class="text-center text-gray-500 dark:text-gray-400 text-sm py-4">
				{$i18n.t('No dated messages found')}
			</div>
		{/if}

		<div class="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
			<input
				type="date"
				bind:value={selectedDate}
				on:change={() => jumpToDate(selectedDate)}
				class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
			/>
		</div>
	</div>
{/if} 