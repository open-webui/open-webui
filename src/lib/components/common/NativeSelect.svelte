<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let value = '';
	export let options: ({ label?: string; value: string } | string)[] = [];
	export let placeholder = '';
	export let className = '';
	export let required = false;
</script>

<select
	class={className}
	bind:value
	{required}
	on:change={() => {
		dispatch('change');
	}}
>
	{#if placeholder}
		<option value="" disabled>{placeholder}</option>
	{/if}

	{#each options as option}
		{@const optionValue = typeof option === 'object' && option !== null ? option.value : option}
		{@const optionLabel =
			typeof option === 'object' && option !== null ? (option.label ?? option.value) : option}
		<option value={optionValue} selected={optionValue === value}>{optionLabel}</option>
	{/each}
</select>
