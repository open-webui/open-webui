<script lang="ts">
	import { settings } from '$lib/stores';

	export let token;
	export let done = true;

	$: raw = token?.raw ?? '';
	$: fade = !done && ($settings?.chatFadeStreamingText ?? true);
</script>

{#if !fade}
	{raw}
{:else}
	{#each raw.split(' ') as text}
		<span class="fade-in-token">
			{text}{' '}
		</span>
	{/each}
{/if}
