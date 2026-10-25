<script lang="ts">
	import { getContext } from 'svelte';
	import type { UsageBar } from '$lib/apis/analytics/sessions';
	import { modelColor } from './UsageChart.svelte';

	export let usage: UsageBar[];
	export let onSelect: (offset: number) => void;
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	let width = 0;
	let active = 0;
	let plot: HTMLDivElement;
	$: formatter = new Intl.NumberFormat($i18n.language, {
		notation: 'compact',
		maximumFractionDigits: 1
	});
	// Consecutive groups keep the full session visible with usable targets on narrow screens.
	$: groupSize = Math.max(1, Math.ceil(usage.length / Math.max(1, Math.floor(width / 16))));
	$: bars = group(usage, groupSize);
	$: active = Math.min(active, Math.max(0, bars.length - 1));
	$: highest = Math.max(1, ...bars.map(total));
	$: unit = 10 ** Math.floor(Math.log10(highest));
	$: ceiling = Math.ceil(highest / unit) * unit;
	$: current = bars[active];
	const total = (bar: UsageBar) => (bar.input_tokens ?? 0) + (bar.output_tokens ?? 0);
	const partial = (bar: UsageBar) => bar.complete < bar.last - bar.first + 1;
	const range = (bar: UsageBar) =>
		`${bar.first === bar.last ? $i18n.t('Response') : $i18n.t('Responses')} ${bar.first}${bar.last > bar.first ? `–${bar.last}` : ''}`;
	const amount = (value: number | null) =>
		value == null ? '-' : value.toLocaleString($i18n.language);
	const description = (bar: UsageBar) =>
		`${range(bar)} · ${$i18n.t('Input')} ${amount(bar.input_tokens)} · ${$i18n.t('Output')} ${amount(bar.output_tokens)}${partial(bar) ? ` · ${$i18n.t('Partial usage')}` : ''}${bar.errors ? ` · ${bar.errors} ${$i18n.t('Response errors')}` : ''}`;
	function group(points: UsageBar[], size: number): UsageBar[] {
		const result: UsageBar[] = [];
		for (let i = 0; i < points.length; i += size) {
			const slice = points.slice(i, i + size);
			const sum = (key: 'input_tokens' | 'output_tokens') =>
				slice.some((p) => p[key] != null) ? slice.reduce((n, p) => n + (p[key] ?? 0), 0) : null;
			result.push({
				...slice[0],
				last: slice[slice.length - 1].last,
				input_tokens: sum('input_tokens'),
				output_tokens: sum('output_tokens'),
				recorded: slice.reduce((n, p) => n + p.recorded, 0),
				complete: slice.reduce((n, p) => n + p.complete, 0),
				errors: slice.reduce((n, p) => n + p.errors, 0),
				model_id: slice.every((p) => p.model_id === slice[0].model_id) ? slice[0].model_id : null
			});
		}
		return result;
	}
	function navigate(event: KeyboardEvent, index: number) {
		let next = index;
		if (event.key === 'ArrowRight') next = Math.min(index + 1, bars.length - 1);
		else if (event.key === 'ArrowLeft') next = Math.max(index - 1, 0);
		else if (event.key === 'Home') next = 0;
		else if (event.key === 'End') next = bars.length - 1;
		else return;
		event.preventDefault();
		active = next;
		plot.querySelectorAll<HTMLButtonElement>('[data-usage-bar]')[next]?.focus();
	}
</script>

{#if bars.length}
	<figure class="mb-4" aria-label={$i18n.t('Recorded tokens by response')}>
		<figcaption
			class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 mb-3 text-[0.6875rem]"
		>
			<span>{$i18n.t('Recorded tokens by response')}</span>
			<span class="flex items-center gap-3">
				<span class="flex items-center gap-1.5"
					><span class="size-2 bg-gray-400 opacity-45"></span>{$i18n.t('Input')}</span
				>
				<span class="flex items-center gap-1.5"
					><span class="size-2 bg-gray-400"></span>{$i18n.t('Output')}</span
				>
				{#if usage.some((bar) => bar.errors > 0)}<span class="flex items-center gap-1.5"
						><span class="size-1.5 bg-gray-400 dark:bg-gray-500"></span>{$i18n.t(
							'Response errors'
						)}</span
					>{/if}
			</span>
		</figcaption>
		<div class="relative h-40 pl-12">
			{#each [ceiling, ceiling * 0.75, ceiling / 2, ceiling * 0.25, 0] as value}
				<div
					class="absolute inset-x-0 flex items-center gap-2 pointer-events-none translate-y-1/2"
					style:bottom={`${(100 * value) / ceiling}%`}
				>
					<span class="w-10 shrink-0 text-right text-[0.6875rem] tabular-nums"
						>{formatter.format(value)}</span
					>
					<span class="h-px flex-1 bg-gray-100 dark:bg-gray-850/50"></span>
				</div>
			{/each}
			<div
				bind:this={plot}
				bind:clientWidth={width}
				class="relative flex h-full"
				role="group"
				aria-label={$i18n.t('Use arrow keys to explore the chart')}
			>
				{#each bars as bar, index (bar.first)}
					<button
						type="button"
						data-usage-bar
						class="relative flex-1 min-w-0 flex items-end justify-center focus-visible:outline focus-visible:outline-1 focus-visible:outline-gray-400"
						tabindex={index === active ? 0 : -1}
						aria-label={description(bar)}
						title={description(bar)}
						on:mouseenter={() => (active = index)}
						on:focus={() => (active = index)}
						on:keydown={(event) => navigate(event, index)}
						on:click={() => onSelect(bar.offset)}
					>
						<span
							class="w-3/4 max-w-12 h-full flex flex-col-reverse"
							aria-hidden="true"
							style:color={bar.model_id ? modelColor(bar.model_id) : 'var(--color-gray-400)'}
						>
							{#if !bar.recorded}<span class="absolute bottom-0 text-[0.6875rem] leading-none"
									>-</span
								>
							{:else if total(bar) === 0}<span class="h-px w-full bg-current"></span>
							{:else}
								<span
									class="block shrink-0 bg-current opacity-45"
									style:height={`${(100 * (bar.input_tokens ?? 0)) / ceiling}%`}
								></span>
								<span
									class="block shrink-0 bg-current"
									style:height={`${(100 * (bar.output_tokens ?? 0)) / ceiling}%`}
								></span>
							{/if}
						</span>
						{#if bar.errors}<span
								aria-hidden="true"
								class="absolute top-0 size-1.5 bg-gray-400 dark:bg-gray-500"
							></span>{/if}
					</button>
				{/each}
			</div>
		</div>
		<div class="ml-12 mt-2 flex justify-between text-[0.625rem] tabular-nums">
			<span>{bars[0].first}</span><span>{$i18n.t('Response order')}</span><span
				>{bars[bars.length - 1].last}</span
			>
		</div>
		{#if current}
			<div
				class="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[0.6875rem] tabular-nums"
				aria-live="polite"
			>
				<span class="text-gray-900 dark:text-gray-200">{range(current)}</span>
				<span>{$i18n.t('Input')} {amount(current.input_tokens)}</span><span
					>{$i18n.t('Output')} {amount(current.output_tokens)}</span
				>
				{#if partial(current)}<span
						>{$i18n.t('Partial usage')} · {current.complete}/{current.last - current.first + 1}
						{$i18n.t('complete')}</span
					>{/if}
				{#if current.errors}<span>{current.errors} {$i18n.t('Response errors')}</span>{/if}
			</div>
		{/if}
		<p class="mt-1 text-[0.625rem] text-gray-400 dark:text-gray-500">
			{$i18n.t(
				'Select a bar to jump to its saved responses. Grouped bars sum consecutive responses.'
			)}
			{$i18n.t('- usage not recorded')}
		</p>
	</figure>
{/if}
