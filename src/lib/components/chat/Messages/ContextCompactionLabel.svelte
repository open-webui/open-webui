<script lang="ts">
	import { getContext } from 'svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let summary = '';
	export let status: 'in_progress' | { error: string } | undefined = undefined;
	export let compactPreview = false;

	$: rowClass = `flex w-full min-w-0 items-center gap-1.5 pt-0.5 pb-0.5 ${
		compactPreview ? 'text-xs' : 'text-[0.9375rem]'
	} text-gray-400 dark:text-gray-500`;
</script>

{#if status}
	<div role="status" class={rowClass}>
		{#if status === 'in_progress'}
			<Spinner className="size-4 shrink-0" />
			<span class="shimmer">{$i18n.t('Compacting context')}</span>
		{:else}
			<span>{status.error}</span>
		{/if}
	</div>
{:else if summary.trim()}
	<!-- Keep expanding the summary from selecting a different model's response. -->
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div on:click|stopPropagation>
		<Collapsible
			title={$i18n.t('Context compacted')}
			chevronClassName="hidden"
			buttonClassName="{rowClass} cursor-pointer outline-offset-4 transition-colors hover:text-gray-500 focus-visible:outline-2 focus-visible:outline-gray-400 dark:hover:text-gray-400"
		>
			<div
				slot="content"
				role="region"
				aria-label={$i18n.t('Compaction summary')}
				class="my-1.5 max-h-80 overflow-y-auto whitespace-pre-wrap break-words text-xs leading-5 text-gray-600 dark:text-gray-300"
			>
				{summary}
			</div>
		</Collapsible>
	</div>
{:else}
	<div class={rowClass}>
		<span>{$i18n.t('Context compacted')}</span>
	</div>
{/if}
