<script lang="ts">
	import { afterUpdate, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	export let rootLabel: string = 'Root';
	export let breadcrumbs: { id: string; name: string }[] = [];
	export let onNavigate: (directoryId: string | null) => void = () => {};

	let breadcrumbEl: HTMLDivElement;

	afterUpdate(() => {
		if (breadcrumbEl) breadcrumbEl.scrollLeft = breadcrumbEl.scrollWidth;
	});
</script>

<div
	bind:this={breadcrumbEl}
	class="flex items-center flex-1 min-w-0 overflow-x-auto scrollbar-none"
>
	<button
		class="text-xs shrink-0 py-0.5 hover:underline transition
			{breadcrumbs.length === 0
			? 'text-gray-700 dark:text-gray-300'
			: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400'}"
		on:click={() => onNavigate(null)}
	>
		{rootLabel}
	</button>

	{#each breadcrumbs as crumb, i}
		<ChevronRight className="size-3 shrink-0 mx-0.5 text-gray-300 dark:text-gray-600" />
		<button
			class="text-xs shrink-0 py-0.5 hover:underline transition
				{i === breadcrumbs.length - 1
				? 'text-gray-700 dark:text-gray-300'
				: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400'}"
			on:click={() => onNavigate(crumb.id)}
		>
			{crumb.name}
		</button>
	{/each}
</div>
