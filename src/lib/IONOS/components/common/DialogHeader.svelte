<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import XMark from '$lib/IONOS/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let closable = true;
	export let title = '';
	export let dialogId = title;
</script>

<div class="flex items-center justify-between {$$props.class}" class:border-b={closable}>
	<h1 class="font-semibold text-sm text-blue-800">
		{title}
	</h1>
	{#if closable}
		<button class="justify-self-end" data-id="dialog-close-{dialogId}" on:click={() => dispatch('close') }>
			<XMark />
		</button>
	{/if}
</div>
