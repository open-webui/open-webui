<script lang="ts">
	import { fade } from 'svelte/transition';

	export let token;
	export let done = true;

	let texts = [];
	$: texts = (token?.raw ?? '').split(' ');
</script>

{#if done}
	{token?.raw}
{:else}
	{#each texts as text}
		<span class="" transition:fade={{ duration: 100 }}>
			{text}
		</span>
	{/each}
{/if}
