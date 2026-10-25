<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let summary = '';
</script>

{#if summary.trim()}
	<!-- Only stop the response card's click handler; summary provides keyboard interaction. -->
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
	<details class="my-1" on:click|stopPropagation>
		<summary
			class="flex w-full cursor-pointer items-center gap-2 text-xs leading-5 text-gray-500 outline-offset-4 transition-colors before:flex-1 before:border-t before:border-dashed before:border-current before:opacity-25 after:flex-1 after:border-t after:border-dashed after:border-current after:opacity-25 hover:text-gray-700 focus-visible:outline-2 focus-visible:outline-gray-400 dark:text-gray-400 dark:hover:text-gray-200 [&::-webkit-details-marker]:hidden"
		>
			<span class="min-w-0 px-2 text-center">
				{$i18n.t('Context compacted')}
			</span>
		</summary>
		<div
			role="region"
			aria-label={$i18n.t('Compaction summary')}
			class="my-1.5 max-h-80 overflow-y-auto whitespace-pre-wrap break-words text-xs leading-5 text-gray-600 dark:text-gray-300"
		>
			{summary}
		</div>
	</details>
{:else}
	<div
		class="my-1 flex w-full items-center gap-2 text-xs leading-5 text-gray-500 before:flex-1 before:border-t before:border-dashed before:border-current before:opacity-25 after:flex-1 after:border-t after:border-dashed after:border-current after:opacity-25 dark:text-gray-400"
	>
		<span class="min-w-0 px-2 text-center">{$i18n.t('Context compacted')}</span>
	</div>
{/if}
