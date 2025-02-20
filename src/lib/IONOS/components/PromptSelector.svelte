<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { prompts, init } from '$lib/IONOS/stores/prompts';
	import { selectPrompt } from '$lib/IONOS/services/prompt';

	onMount(async () => {
		await init();
	});
</script>

<div>
	{#each $prompts as { id, prompt, promptDisplayName, agentId }}
		<button
			class="fw-60 m-2 py-4 px-2 bg-white hover:bg-gray-100 shadow-md rounded-lg max-w-64 text-sm"
			data-id={id}
			on:click={() => selectPrompt(id)}
		>
			{promptDisplayName} →
		</button>
	{/each}
</div>

