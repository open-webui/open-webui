<script lang="ts">
	import type { Knowledge } from '$lib/apis/knowledge/types';
	import { createEventDispatcher } from 'svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	export let items: Knowledge[] = [];

	const dispatch = createEventDispatcher();
</script>

{#each items as { id, name, description }}
	<div
		data-id={id}
		class="flex flex-row border-b last:border-none items-center px-2.5"
	>
		<div class="grow shrink w-[0] py-3 cursor-default">
			<span class="block text-nowrap overflow-hidden text-ellipsis">{name}</span>
			<span class="block text-sm">{description}</span>
		</div>
		<div class="w-5 h-5 ml-5">
			<button on:click={() => dispatch('select', id)}>
				<ChevronRight className="w-5 h-5" />
			</button>
		</div>
	</div>
{/each}
