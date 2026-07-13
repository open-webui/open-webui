<script lang="ts">
	import { getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let label = '';
	export let value = '';
	// Percent change vs the previous period; null hides the delta chip
	export let delta: number | null = null;
	export let tooltip = '';
	// Accent color for the icon chip and sparkline
	export let accent = '#2a78d6';
	// Daily values for the sparkline; empty hides it
	export let trend: number[] = [];

	const SPARK_W = 72;
	const SPARK_H = 26;

	$: sparkPoints = (() => {
		if (!trend || trend.length < 2) return '';
		const max = Math.max(...trend, 1);
		const step = SPARK_W / (trend.length - 1);
		return trend
			.map(
				(v, i) => `${(i * step).toFixed(1)},${(SPARK_H - 2 - (v / max) * (SPARK_H - 4)).toFixed(1)}`
			)
			.join(' ');
	})();
	$: sparkArea = sparkPoints ? `${sparkPoints} ${SPARK_W},${SPARK_H} 0,${SPARK_H}` : '';
</script>

<div
	class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/50 dark:bg-gray-850/30 px-3.5 py-3 flex flex-col gap-2 min-w-0"
>
	<div class="flex items-center justify-between gap-2 min-w-0">
		<div class="flex items-center gap-2 min-w-0">
			<div
				class="size-6 rounded-lg flex items-center justify-center shrink-0"
				style="background-color: {accent}1c; color: {accent}"
			>
				<slot name="icon" />
			</div>
			<span class="text-[11px] font-medium text-gray-500 dark:text-gray-400 truncate">{label}</span>
		</div>
		{#if delta !== null && isFinite(delta)}
			<Tooltip content={$i18n.t('vs previous period')}>
				<span
					class="text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 cursor-help {delta >= 0
						? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
						: 'bg-red-500/10 text-red-600 dark:text-red-400'}"
				>
					{delta > 0 ? '↑' : delta < 0 ? '↓' : ''}
					{Math.abs(delta) >= 1000 ? '>999' : Math.abs(delta).toFixed(0)}%
				</span>
			</Tooltip>
		{/if}
	</div>
	<div class="flex items-end justify-between gap-2 min-w-0">
		{#if tooltip}
			<Tooltip content={tooltip}>
				<span
					class="text-xl font-semibold tracking-tight text-gray-900 dark:text-white cursor-help truncate"
					>{value}</span
				>
			</Tooltip>
		{:else}
			<span class="text-xl font-semibold tracking-tight text-gray-900 dark:text-white truncate"
				>{value}</span
			>
		{/if}
		{#if sparkPoints}
			<svg
				viewBox="0 0 {SPARK_W} {SPARK_H}"
				class="w-[72px] h-[26px] shrink-0"
				preserveAspectRatio="none"
				aria-hidden="true"
			>
				<polygon points={sparkArea} fill={accent} opacity="0.12" />
				<polyline
					points={sparkPoints}
					fill="none"
					stroke={accent}
					stroke-width="1.5"
					stroke-linejoin="round"
					stroke-linecap="round"
				/>
			</svg>
		{/if}
	</div>
</div>
