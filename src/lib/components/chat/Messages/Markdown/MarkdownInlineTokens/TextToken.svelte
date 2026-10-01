<script lang="ts">
	import { settings } from '$lib/stores';

	export let token;
	export let done = true;

	$: raw = token?.raw ?? '';
</script>

{#if done || !($settings?.chatFadeStreamingText ?? true)}
	{raw}
{:else}
	{#each raw.split(' ') as text}
		<span class="fade-in-token">
			{text}{' '}
		</span>
	{/each}
{/if}
