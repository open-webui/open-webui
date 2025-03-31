<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { ScrollerItem } from './scrollerItem.d.ts';
	import type { Prompt } from '$lib/IONOS/stores/prompts';
	import { prompts, init } from '$lib/IONOS/stores/prompts';
	import { split, shuffle } from '$lib/IONOS/utils/arrays';
	import Scroller from './Scroller.svelte';

	const dispatch = createEventDispatcher();

	const mapper = (prompt: Prompt): ScrollerItem => ({ id: prompt.id, text: prompt.promptDisplayName });

	$: mapped = shuffle<ScrollerItem>($prompts.map(mapper));
	$: mappedSplit = split<ScrollerItem>(mapped);
	$: mappedA = mappedSplit[0];
	$: mappedB = mappedSplit[1];

	onMount(async () => {
		await init();
	});
</script>

<div>
	<Scroller
		on:click={({ detail: id }) => dispatch('select', id)}
		direction="left"
		items={mappedA}
	/>
	<Scroller
		on:click={({ detail: id }) => dispatch('select', id)}
		direction="right"
		items={mappedB}
	/>
</div>
