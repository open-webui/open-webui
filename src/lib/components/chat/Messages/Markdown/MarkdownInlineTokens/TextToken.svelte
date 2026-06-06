<script lang="ts">
	export let token;
	export let done = true;
</script>

{#if done}
	{token?.raw}
{:else}
	{#each (token?.raw ?? '').split(' ') as text}
		<span class="fade-in-token">
			{text}{' '}
		</span>
	{/each}
{/if}
