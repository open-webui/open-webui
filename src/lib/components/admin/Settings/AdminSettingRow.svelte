<script lang="ts">
	export let label = '';
	export let description = '';
	export let className = '';
	export let labelClassName = '';
</script>

<div class="flex items-center justify-between gap-4 {className}">
	<div class="min-w-0 text-xs text-gray-600 dark:text-gray-400 {labelClassName}">
		<slot name="label">{label}</slot>
	</div>

	<div class="shrink-0">
		<slot />
	</div>
</div>

{#if description}
	<p class="-mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
		{description}
	</p>
{/if}
