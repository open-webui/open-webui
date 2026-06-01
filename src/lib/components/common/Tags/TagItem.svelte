<script>
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';

	export let tag;
	export let disabled = false;
	export let onDelete = () => {};
</script>

{#if tag}
	{#if disabled}
		<span
			class="flex items-center gap-1 px-1.5 py-[1px] rounded-full bg-gray-100/50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 text-gray-600 dark:text-gray-300 text-xs font-medium"
		>
			<span class="line-clamp-1">{tag.name}</span>
		</span>
	{:else}
		<button
			type="button"
			class="flex items-center gap-1 px-1.5 py-[1px] rounded-full bg-gray-100/50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 text-gray-600 dark:text-gray-300 text-xs font-medium hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
			on:click={() => {
				onDelete();
			}}
		>
			<span class="line-clamp-1">{tag.name}</span>
			<XMark className="size-3" strokeWidth="2.5" />
		</button>
	{/if}
{/if}
