<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	export let label = '';
	export let description = '';
	export let className = '';
	export let labelClassName = '';

	const labelId = `admin-setting-${uuidv4()}`;
</script>

<div class="group/setting-row flex items-center justify-between gap-4 {className}">
	<label
		for={`${labelId}-control`}
		id={labelId}
		class="min-w-0 text-xs text-base-600 group-has-[button[id$=-control]:enabled]/setting-row:cursor-pointer group-has-[button[id$=-control]:disabled]/setting-row:cursor-not-allowed transition-colors duration-150 group-hover/setting-row:text-base-900 group-focus-within/setting-row:text-base-900 dark:text-base-400 dark:group-hover/setting-row:text-white dark:group-focus-within/setting-row:text-white {labelClassName}"
	>
		<slot name="label">{label}</slot>
	</label>

	<div class="min-w-0">
		<slot {labelId} />
	</div>
</div>

{#if description}
	<p class="-mt-1 text-[0.6875rem] text-base-400 dark:text-base-600">
		{description}
	</p>
{/if}
