<script lang="ts">
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	export let status = { queries: [] };
	let state = false;
</script>

<Collapsible bind:open={state} className="w-full space-y-1">
	<div
		class="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
	>
		<slot />

		{#if state}
			<ChevronUp strokeWidth="3.5" className="size-3.5 " />
		{:else}
			<ChevronDown strokeWidth="3.5" className="size-3.5 " />
		{/if}
	</div>
	<div
		class="text-sm border border-gray-300/30 dark:border-gray-700/50 rounded-xl mb-1.5"
		slot="content"
	>
		{#each status.queries || [] as query, queryIdx}
			<div
				class="flex w-full items-center p-3 px-4 {queryIdx === (status.queries || []).length - 1
					? ''
					: 'border-b border-gray-300/30 dark:border-gray-700/50'} group/item justify-between font-normal text-gray-800 dark:text-gray-300"
			>
				<div class="flex gap-2 items-center">
					<Search />

					<div class=" line-clamp-1">
						{query}
					</div>
				</div>
			</div>
		{/each}
	</div>
</Collapsible>