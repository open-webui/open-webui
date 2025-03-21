<script lang="ts">
	import type { KnowledgeFile } from '$lib/apis/knowledge/types';
	import { createEventDispatcher } from 'svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	const dispatch = createEventDispatcher();

	export let items: KnowledgeFile[] = [];
</script>

{#each items as { id, meta: { name } }}
	<div class="flex flex-row border-b last:border-none items-center" data-id={id}>
		<div class="grow px-3 py-3 cursor-default">
			<span class="block text-nowrap overflow-hidden text-ellipsis">{name}</span>
		</div>
		<div class="grow-0 w-5 h-5 ml-5">
			<button on:click={() => dispatch('delete', id)}>
				<GarbageBin className="w-5 h-5" />
			</button>
		</div>
	</div>
{/each}
