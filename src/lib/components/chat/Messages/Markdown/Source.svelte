<script lang="ts">
	import { getContext } from 'svelte';
	import { getCitationPreview } from '$lib/utils/citations';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let citation: any;
	/** The cited paragraphs of the source, when the citation names them, as in [1#3]. */
	export let paragraphIds: number[] = [];
	export let onClick: () => void = () => {};

	$: preview = getCitationPreview(citation, paragraphIds);
</script>

<button
	type="button"
	aria-label={$i18n.t('View source: {{title}}', { title: preview.title })}
	class="group flex h-full w-full flex-col px-3.5 py-2.5 text-left text-xs"
	on:click={onClick}
>
	<div
		class="max-w-full break-words text-[0.8125rem] leading-5 text-base-900 group-hover:underline dark:text-base-100"
	>
		{preview.title}
	</div>
	{#if preview.url || preview.page !== null}
		<div class="max-w-full truncate text-base-500 dark:text-base-400">
			{preview.url ?? $i18n.t('Page {{number}}', { number: preview.page })}
		</div>
	{/if}
	{#if preview.passage}
		<div class="mt-1 break-words line-clamp-3 text-base-600 dark:text-base-300">
			{preview.passage}
		</div>
	{/if}
</button>
