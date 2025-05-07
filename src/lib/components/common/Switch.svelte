<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	export let state = false;
	export let label = '';
	export let id = crypto.randomUUID();
	export let description = '';
	export let messages: string[] = [];

	const dispatch = createEventDispatcher();

	function handleChange(event: Event) {
		const target = event.target as HTMLInputElement;
		state = target.checked;
		dispatch('change', state);
	}
</script>

<div class="fr-toggle">
	<input
		type="checkbox"
		class="fr-toggle__input"
		aria-describedby="{id}-messages"
		{id}
		bind:checked={state}
		on:change={handleChange}
	/>
	<label class="fr-toggle__label" for={id}>{label}</label>
	{#if messages.length > 0 || description}
		<div class="fr-messages-group" id="{id}-messages" aria-live="polite">
			{#if description}
				<p class="fr-message">{description}</p>
			{/if}
			{#each messages as message}
				<p class="fr-message">{message}</p>
			{/each}
		</div>
	{/if}
</div>
