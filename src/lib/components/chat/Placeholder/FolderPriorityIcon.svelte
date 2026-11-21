<script lang="ts">
	import { NO_PRIORITY, priorityKey, type FolderPriority } from '$lib/utils/folders';

	/** A priority, or NO_PRIORITY. Anything unknown reads as no priority. */
	export let priority: FolderPriority | string | null = NO_PRIORITY;
	export let className = 'size-3.5';

	$: current = priorityKey(priority);
	// Signal bars filled: High 3, Medium 2, Low 1.
	$: level = current === 'high' ? 3 : current === 'medium' ? 2 : current === 'low' ? 1 : 0;
</script>

<svg class="shrink-0 {className}" viewBox="0 0 16 16" fill="none" aria-hidden="true">
	{#if current === 'urgent'}
		<rect x="1.5" y="1.5" width="13" height="13" rx="3.5" class="fill-orange-500" />
		<path d="M8 4.75v4" stroke="white" stroke-width="1.75" stroke-linecap="round" />
		<circle cx="8" cy="11.25" r="1" fill="white" />
	{:else if level}
		{#each [0, 1, 2] as bar}
			<rect
				x={2 + bar * 4.5}
				y={10 - bar * 3.5}
				width="3"
				height={4 + bar * 3.5}
				rx="1"
				class={bar < level
					? 'fill-base-600 dark:fill-base-300'
					: 'fill-base-200 dark:fill-base-700'}
			/>
		{/each}
	{:else}
		<!-- No priority: three short dashes -->
		<path
			d="M2.5 8h2M7 8h2M11.5 8h2"
			stroke="currentColor"
			stroke-width="1.5"
			stroke-linecap="round"
			class="text-base-300 dark:text-base-600"
		/>
	{/if}
</svg>
