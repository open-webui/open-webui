<script lang="ts">
	import { getContext } from 'svelte';
	import { SESSION_TOKEN_RANGES, type SessionOverview } from '$lib/apis/analytics/sessions';
	export let overview: SessionOverview;
	export let selectedRange: number | null = null;
	export let onSelect: (index: number | null) => void;
	$: counts = overview.token_distribution ?? [];
	$: peak = Math.max(1, ...counts);
	$: tickUnit = Math.max(1, 10 ** Math.floor(Math.log10(peak / 4)));
	$: ceiling = Math.ceil(peak / 4 / tickUnit) * tickUnit * 4;
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	$: number = new Intl.NumberFormat($i18n.language, {
		notation: 'compact',
		maximumFractionDigits: 1
	});
</script>

<section
	class="mb-4 text-xs font-normal text-gray-500 dark:text-gray-400"
	aria-label={$i18n.t('Session summary')}
>
	<dl class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
		{#each [{ label: $i18n.t('Sessions'), value: number.format(overview.sessions) }, { label: $i18n.t('Prompts'), value: number.format(overview.prompts) }, { label: $i18n.t('Recorded tokens'), value: overview.recorded_responses ? number.format(overview.tokens) + (overview.complete_responses < overview.responses ? '*' : '') : '-' }, { label: $i18n.t('Response errors'), value: overview.responses ? `${((overview.errors / overview.responses) * 100).toFixed(1)}%` : '-' }] as stat}
			<div class="flex items-baseline gap-1.5 whitespace-nowrap">
				<dt>{stat.label}</dt>
				<dd class="tabular-nums text-gray-900 dark:text-gray-200">{stat.value}</dd>
			</div>
		{/each}
	</dl>
	{#if counts.some((count) => count > 0)}
		<figure class="mt-4" aria-label={$i18n.t('Sessions by recorded token usage')}>
			<figcaption class="flex items-center justify-between gap-3 mb-3 text-[0.6875rem]">
				<span>{$i18n.t('Sessions by recorded token usage')}</span>
				{#if selectedRange !== null}<button
						type="button"
						class="py-1 hover:text-gray-900 dark:hover:text-gray-100"
						on:click={() => onSelect(null)}>{$i18n.t('All sessions')}</button
					>{:else}<span>{$i18n.t('Sessions')}</span>{/if}
			</figcaption>
			<div class="relative h-40 pl-12">
				{#each [ceiling, ceiling * 0.75, ceiling / 2, ceiling * 0.25, 0] as count}
					<div
						class="absolute inset-x-0 flex items-center gap-2 pointer-events-none translate-y-1/2"
						style:bottom={`${(100 * count) / ceiling}%`}
					>
						<span class="w-10 shrink-0 text-right text-[0.6875rem] tabular-nums"
							>{number.format(count)}</span
						><span class="h-px flex-1 bg-gray-100 dark:bg-gray-850/50"></span>
					</div>
				{/each}
				<div class="relative flex h-full">
					{#each SESSION_TOKEN_RANGES as range, index}
						<button
							type="button"
							data-token-range
							class="relative flex flex-1 min-w-0 items-end justify-center focus-visible:outline focus-visible:outline-1 focus-visible:outline-gray-400"
							disabled={!counts[index]}
							aria-pressed={selectedRange === index}
							aria-label={`${range.label} ${$i18n.t('Recorded tokens')}: ${counts[index]} ${$i18n.t('Sessions')}`}
							on:click={() => onSelect(selectedRange === index ? null : index)}
						>
							<span
								class="relative w-3/4 max-w-12 bg-gray-400 dark:bg-gray-500"
								style:height={`${(100 * counts[index]) / ceiling}%`}
								style:opacity={selectedRange === null || selectedRange === index ? 1 : 0.3}
							>
								{#if counts[index]}<span
										class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 w-max whitespace-nowrap text-[0.6875rem] tabular-nums text-gray-700 dark:text-gray-300"
										>{number.format(counts[index])}</span
									>{/if}
							</span>
						</button>
					{/each}
				</div>
			</div>
			<div class="ml-12 mt-2 flex text-[0.625rem] tabular-nums">
				{#each SESSION_TOKEN_RANGES as range}<span
						class="flex-1 min-w-0 text-center whitespace-nowrap"
						>{range.label.replace('–<', '–')}</span
					>{/each}
			</div>
			<p class="mt-3 text-[0.625rem] text-gray-400 dark:text-gray-500">
				{$i18n.t('Select a range to filter sessions. Partial usage is included.')}
				{#if overview.unrecorded_sessions}
					{number.format(overview.unrecorded_sessions)}
					{$i18n.t(
						overview.unrecorded_sessions === 1
							? 'session without recorded usage'
							: 'sessions without recorded usage'
					)}{/if}
			</p>
		</figure>
	{/if}
</section>
