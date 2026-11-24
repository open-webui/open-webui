<script lang="ts">
	import { getContext } from 'svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext<any>('i18n');

	export let content: string;

	let expanded = false;
</script>

<div class="w-full min-w-0 text-[0.90625rem]">
	<button
		type="button"
		class="group flex max-w-full min-w-0 items-center gap-1.5 py-0.5 text-left text-base-500 transition hover:text-base-700 dark:hover:text-base-300"
		aria-expanded={expanded}
		on:click={() => (expanded = !expanded)}
	>
		<span dir="auto" class="min-w-0 truncate">{$i18n.t('Timer')} · {content}</span>
		<ChevronDown
			strokeWidth="3.5"
			className="size-3 shrink-0 transition {expanded
				? 'rotate-180'
				: 'opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'}"
		/>
	</button>
	{#if expanded}
		<div
			dir="auto"
			class="my-1 whitespace-pre-wrap break-words border-l border-base-100 pl-2.5 text-base-500 dark:border-base-800 dark:text-base-400"
		>
			{content}
		</div>
	{/if}
</div>
