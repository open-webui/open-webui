<script lang="ts">
	export let token;
	export let done = true;

	$: raw = token?.raw ?? '';
</script>

{#if done}
	{raw}
{:else}
	{#each raw.split(' ') as text}
		<span class="fade-in-token">
			{text}{' '}
		</span>
	{/each}
{/if}
