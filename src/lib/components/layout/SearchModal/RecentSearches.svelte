<script lang="ts">
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import {
		searchHistoryGet,
		searchHistoryClear,
		type ChatSearchHistoryEntry
	} from '$lib/utils';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ClockRotateRight from '$lib/components/icons/ClockRotateRight.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	let history: ChatSearchHistoryEntry[] = [];

	const refresh = () => {
		history = searchHistoryGet();
	};

	onMount(refresh);

	export const reload = refresh;

	const pick = (q: string) => {
		dispatch('pick', q);
	};

	const clearAll = () => {
		searchHistoryClear();
		history = [];
	};
</script>

{#if history.length > 0}
	<div class="px-4 pb-2">
		<div class="flex items-center justify-between mb-1.5">
			<div class="text-xs font-medium text-gray-500 dark:text-gray-500 flex items-center gap-1">
				<ClockRotateRight className="size-3" strokeWidth="2" />
				{$i18n.t('Recent searches')}
			</div>
			<button
				class="text-[10px] text-gray-400 hover:text-gray-700 dark:hover:text-white"
				on:click={clearAll}
				type="button"
			>
				{$i18n.t('Clear')}
			</button>
		</div>
		<div class="flex flex-wrap gap-1.5">
			{#each history as entry (entry.timestamp)}
				<button
					class="flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-gray-50 dark:bg-gray-850 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={() => pick(entry.query)}
					type="button"
				>
					<span class="line-clamp-1 max-w-[180px]">{entry.query}</span>
				</button>
			{/each}
		</div>
	</div>
{/if}
