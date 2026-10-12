<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let label = '';
	export let description = '';
	export let checked = false;
	export let disabled = false;
	const dispatch = createEventDispatcher<{ change: boolean }>();
	const change = (value: boolean) => {
		if (disabled) return;
		checked = value;
		dispatch('change', checked);
	};
</script>

<div
	class="flex min-h-8 items-center justify-between gap-3 px-1 text-xs font-normal text-gray-900 dark:text-gray-100"
>
	<Tooltip content={description} placement="top-start">
		<button
			type="button"
			class="text-left font-normal disabled:cursor-default disabled:opacity-50"
			{disabled}
			on:click={() => change(!checked)}>{label}</button
		>
	</Tooltip>
	<Switch state={checked} {disabled} ariaLabel={label} on:change={(e) => change(e.detail)} />
</div>
