<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	export let label = '';
	export let description = '';
	export let className = '';
	export let labelClassName = '';

	const labelId = `admin-setting-${uuidv4()}`;
</script>

<div class="flex items-center justify-between gap-4 {className}">
	<div id={labelId} class="min-w-0 text-xs text-gray-600 dark:text-gray-400 {labelClassName}">
		<slot name="label">{label}</slot>
	</div>

	<div class="min-w-0">
		<slot {labelId} />
	</div>
</div>

{#if description}
	<p class="-mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
		{description}
	</p>
{/if}
