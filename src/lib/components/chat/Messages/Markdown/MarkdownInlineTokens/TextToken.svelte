<script lang="ts">
	import { fade } from 'svelte/transition';

	export let token;
	export let done = true;

	const normalizeTimestampText = (text) =>
		text.replace(/(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})\.\d+(?:Z)?/, '$1');

	let texts = [];
	$: texts = normalizeTimestampText(token?.raw ?? '').split(' ');
</script>

{#if done}
	{normalizeTimestampText(token?.raw ?? '')}
{:else}
	{#each texts as text}
		<span class="" transition:fade={{ duration: 100 }}>
			{text}{' '}
		</span>
	{/each}
{/if}
