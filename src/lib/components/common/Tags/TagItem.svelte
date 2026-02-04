<script>
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';

	export let tag;
	export let onDelete = () => {};
</script>

{#if tag}
	<button
		type="button"
		class="flex items-center gap-0.5 px-1.5 py-[1px] rounded-lg bg-gray-500/20 text-gray-700 dark:text-gray-200 text-xs font-medium hover:bg-gray-500/30 transition-colors"
		on:click={() => {
			onDelete();
		}}
	>
		<span class="line-clamp-1">{tag.name}</span>
		<XMark className="size-3" strokeWidth="2.5" />
	</button>
{/if}
