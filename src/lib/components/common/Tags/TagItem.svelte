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
			class="flex items-center gap-1 px-1.5 py-[0.0625rem] rounded-full bg-base-100/50 dark:bg-base-800/50 border border-base-100 dark:border-base-800 text-base-600 dark:text-base-300 text-xs font-normal"
		>
			<span class="line-clamp-1">{tag.name}</span>
		</span>
	{:else}
		<button
			type="button"
			class="flex items-center gap-1 px-1.5 py-[0.0625rem] rounded-full bg-base-100/50 dark:bg-base-800/50 border border-base-100 dark:border-base-800 text-base-600 dark:text-base-300 text-xs font-normal hover:bg-base-100 dark:hover:bg-base-800 transition-colors"
			on:click={() => {
				onDelete();
			}}
		>
			<span class="line-clamp-1">{tag.name}</span>
			<XMark className="size-3" strokeWidth="2.5" />
		</button>
	{/if}
{/if}
