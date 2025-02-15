<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import Tooltip from '../Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Badge from '../Badge.svelte';
	const dispatch = createEventDispatcher();

	export let tags = [];
</script>

{#each tags as tag}
	<Tooltip content={tag.name}>
		<div
			class="relative group/tags px-1.5 py-[0.2px] gap-0.5 flex justify-between h-fit max-h-fit w-fit items-center rounded-full bg-gray-500/20 text-gray-700 dark:text-gray-200 transition cursor-pointer"
		>
			<div class=" text-[0.7rem] font-medium self-center line-clamp-1 w-fit">
				{tag.name}
			</div>
			<div class="absolute invisible right-0.5 group-hover/tags:visible transition">
				<button
					class="rounded-full border bg-white dark:bg-gray-700 h-full flex self-center cursor-pointer"
					on:click={() => {
						dispatch('delete', tag.name);
					}}
					type="button"
				>
					<XMark className="size-3" strokeWidth="2.5" />
				</button>
			</div>
		</div>
	</Tooltip>
{/each}
