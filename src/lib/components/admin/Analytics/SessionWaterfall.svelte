<script lang="ts">
	import { getContext } from 'svelte';
	import type { TraceItem } from '$lib/apis/analytics/sessions';
	import { modelColor } from './UsageChart.svelte';

	export let items: TraceItem[];
	export let page: number;
	export let label: (item: TraceItem) => string;
	export let status: (item: TraceItem) => string;
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const timed = (item: TraceItem) =>
		item.started_at != null &&
		Number.isFinite(item.started_at) &&
		item.ended_at != null &&
		Number.isFinite(item.ended_at) &&
		item.ended_at >= item.started_at;
	const measured = (item: TraceItem) =>
		item.duration_seconds != null &&
		Number.isFinite(item.duration_seconds) &&
		item.duration_seconds >= 0;
	const duration = (seconds: number) =>
		seconds < 1
			? `${Math.round(seconds * 1000)}ms`
			: seconds < 60
				? `${seconds.toFixed(1)}s`
				: `${(seconds / 60).toFixed(1)}m`;
	$: waterfall = items.some(timed);
	$: sequence = !waterfall && !items.some(measured);
	$: bars = sequence ? items : items.filter(waterfall ? timed : measured);
	$: lanes = sequence
		? [...new Set(bars.map(label))].map((name) => ({
				name,
				entries: bars.flatMap((item, index) => (label(item) === name ? [{ item, index }] : []))
			}))
		: bars.map((item, index) => ({ name: label(item), entries: [{ item, index }] }));
	$: start = waterfall ? Math.min(...bars.map((item) => item.started_at!)) : 0;
	$: end = waterfall
		? Math.max(...bars.map((item) => item.ended_at!))
		: Math.max(0, ...bars.map((item) => item.duration_seconds ?? 0));
	$: span = end - start;
	const elapsed = (item: TraceItem) =>
		waterfall ? item.ended_at! - item.started_at! : item.duration_seconds!;
</script>

<figure class="mb-4" aria-label={$i18n.t('Execution timeline')}>
	<figcaption class="flex justify-between gap-3 mb-2 text-[0.6875rem]">
		<span
			>{sequence
				? $i18n.t('Recorded sequence')
				: waterfall
					? $i18n.t('Execution timeline')
					: $i18n.t('Recorded duration')}</span
		>
		<span>{$i18n.t('Page')} {page + 1}</span>
	</figcaption>
	{#if bars.length}
		<!-- Keyboard users must be able to scroll the bounded chart. -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
		<div
			class="max-h-48 overflow-y-auto scrollbar-hover focus-visible:outline focus-visible:outline-1 focus-visible:outline-gray-400"
			tabindex="0"
			role="region"
			aria-label={$i18n.t('Execution timeline')}
		>
			<div
				class="grid grid-cols-[6rem_minmax(0,1fr)_3rem] sm:grid-cols-[10rem_minmax(0,1fr)_3.5rem] gap-x-2 sticky top-0 z-10 bg-white dark:bg-gray-900 pb-1 text-[0.625rem] tabular-nums"
				aria-hidden="true"
			>
				<span></span>
				<div class="flex justify-between">
					{#if sequence}
						<span>1</span><span>{$i18n.t('Saved order')}</span><span>{bars.length}</span>
					{:else}
						<span>0s</span><span>{duration(span / 2)}</span><span>{duration(span)}</span>
					{/if}
				</div>
				<span class="text-right">{sequence ? $i18n.t('Count') : ''}</span>
			</div>
			{#each lanes as lane, laneIndex (laneIndex)}
				{@const item = lane.entries[0].item}
				<div
					data-waterfall-row
					class="grid grid-cols-[6rem_minmax(0,1fr)_3rem] sm:grid-cols-[10rem_minmax(0,1fr)_3.5rem] gap-x-2 items-center min-h-7 text-[0.6875rem]"
					title={sequence
						? lane.name
						: `${item.model_id || ''} · ${label(item)} · ${status(item)}${waterfall ? ` · ${duration(item.started_at! - start)}–${duration(item.ended_at! - start)}` : ''}`}
				>
					<span class="truncate"
						>{lane.name}{!sequence && item.status === 'failed' ? ` · ${status(item)}` : ''}</span
					>
					<div class="relative h-7" aria-hidden="true">
						{#each [0, 50, 100] as tick}<span
								class="absolute inset-y-0 w-px bg-gray-100 dark:bg-gray-850/50"
								style:left={`${tick}%`}
							></span>{/each}
						{#each lane.entries as entry (entry.index)}
							<span
								data-waterfall-bar={sequence ? undefined : ''}
								data-sequence-mark={sequence ? '' : undefined}
								class={sequence
									? 'absolute top-2.5 size-2 -translate-x-1/2'
									: 'absolute top-2 h-3 min-w-px max-w-full'}
								style:left={sequence
									? `${(100 * (entry.index + 0.5)) / bars.length}%`
									: `${waterfall && span > 0 ? (100 * (item.started_at! - start)) / span : 0}%`}
								style:width={sequence
									? `min(0.5rem, ${80 / bars.length}%)`
									: `${span > 0 ? (100 * elapsed(item)) / span : 0}%`}
								title={sequence
									? `#${entry.index + 1} · ${entry.item.model_id || ''} · ${status(entry.item)}`
									: undefined}
								style:background={entry.item.model_id
									? modelColor(entry.item.model_id)
									: 'var(--color-gray-400)'}
							></span>
						{/each}
					</div>
					<span class="text-right tabular-nums"
						>{sequence ? lane.entries.length : duration(elapsed(item))}</span
					>
				</div>
			{/each}
		</div>
		<p class="mt-2 text-[0.625rem] text-gray-400 dark:text-gray-500">
			{sequence
				? $i18n.t('Saved order only; spacing does not represent elapsed time.')
				: waterfall
					? $i18n.t('Time from first timed operation on this page.')
					: $i18n.t('Start/end times not recorded; bars compare durations only.')}
			{#if !sequence && bars.length < items.length}{items.length - bars.length}
				{waterfall
					? $i18n.t('items without recorded start/end times')
					: $i18n.t('items without recorded durations')}{/if}
		</p>
	{:else}
		<p class="text-[0.6875rem] text-gray-400 dark:text-gray-500">
			{$i18n.t('No saved items match this filter.')}
		</p>
	{/if}
</figure>
