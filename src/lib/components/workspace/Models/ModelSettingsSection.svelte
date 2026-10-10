<script lang="ts">
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	export let label = '';
	export let summary = '';
	export let open = false;
</script>

<details bind:open class="group/setting min-w-0">
	<summary
		class="grid cursor-pointer list-none grid-cols-[7rem_minmax(0,1fr)_auto] items-center gap-2 rounded-md px-1 py-1.5 text-xs font-normal focus-visible:outline focus-visible:outline-2 sm:grid-cols-[8rem_minmax(0,1fr)_auto] [&::-webkit-details-marker]:hidden"
	>
		<span class="text-gray-600 dark:text-gray-400">{label}</span>
		<slot name="summary">
			<span class="truncate text-gray-900 dark:text-gray-100" title={summary}>{summary}</span>
		</slot>
		<ChevronRight
			className="size-3 text-gray-400 transition-transform group-open/setting:rotate-90"
		/>
	</summary>
	{#if open}
		<div class="pb-2 pl-3 pt-1"><slot /></div>
	{/if}
</details>
