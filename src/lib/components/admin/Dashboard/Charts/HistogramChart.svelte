<script lang="ts">
	import { onMount } from 'svelte';
	import type { OrientationBin } from '$lib/apis/dashboard';

	export let title: string = '';
	export let subtitle: string = '';
	export let data: OrientationBin[] = [];
	export let color: string = '#5CC9D3';
	export let isDark: boolean = false;
	export let height: number = 200;
	export let showGrid: boolean = true;
	export let xAxisLabel: string = 'X Position';
	export let yAxisLabel: string = 'Count';

	let containerWidth = 800;
	let container: HTMLDivElement;

	// Chart dimensions
	const padding = { top: 20, right: 20, bottom: 40, left: 60 };

	$: chartWidth = containerWidth - padding.left - padding.right;
	$: chartHeight = height - padding.top - padding.bottom;

	// Calculate scales
	$: counts = data.map((d) => d.count);
	$: maxCount = Math.max(...counts, 1);

	// Bar width based on data
	$: barWidth = data.length > 0 ? Math.max(2, (chartWidth / data.length) - 2) : 20;

	// Scale functions
	$: xScale = (index: number) => (index / data.length) * chartWidth + barWidth / 2;
	$: yScale = (value: number) => chartHeight - (value / maxCount) * chartHeight;
	$: barHeight = (value: number) => (value / maxCount) * chartHeight;

	// Y-axis ticks
	$: yTicks = Array.from({ length: 5 }, (_, i) => {
		const value = (maxCount * (4 - i)) / 4;
		return { value, y: yScale(value) };
	});

	// X-axis labels (show a few position labels)
	$: xLabels = data.length > 0
		? [
				{ index: 0, label: data[0].bin_start.toString() },
				{ index: Math.floor(data.length / 2), label: data[Math.floor(data.length / 2)]?.bin_start.toString() },
				{ index: data.length - 1, label: data[data.length - 1]?.bin_end.toString() }
			]
		: [];

	function formatValue(value: number): string {
		if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
		if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
		return value.toFixed(0);
	}

	onMount(() => {
		if (container) {
			const resizeObserver = new ResizeObserver((entries) => {
				containerWidth = entries[0].contentRect.width;
			});
			resizeObserver.observe(container);
			return () => resizeObserver.disconnect();
		}
	});
</script>

<div class="w-full" bind:this={container}>
	{#if title || subtitle}
		<div class="mb-2">
			{#if title}
				<h3 class="text-sm font-semibold {isDark ? 'text-white' : 'text-gray-900'}">{title}</h3>
			{/if}
			{#if subtitle}
				<p class="text-xs {isDark ? 'text-gray-400' : 'text-gray-500'}">{subtitle}</p>
			{/if}
		</div>
	{/if}

	<svg width="100%" {height} class="overflow-visible">
		<defs>
			<linearGradient id="barGradient-{title}" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0%" stop-color={color} stop-opacity="0.9" />
				<stop offset="100%" stop-color={color} stop-opacity="0.6" />
			</linearGradient>
		</defs>

		<g transform="translate({padding.left}, {padding.top})">
			<!-- Grid lines -->
			{#if showGrid}
				{#each yTicks as tick}
					<line
						x1="0"
						y1={tick.y}
						x2={chartWidth}
						y2={tick.y}
						stroke={isDark ? '#374151' : '#e5e7eb'}
						stroke-dasharray="4"
					/>
				{/each}
			{/if}

			<!-- Y-axis labels -->
			{#each yTicks as tick}
				<text
					x="-8"
					y={tick.y}
					text-anchor="end"
					dominant-baseline="middle"
					class="text-xs {isDark ? 'fill-gray-400' : 'fill-gray-500'}"
				>
					{formatValue(tick.value)}
				</text>
			{/each}

			<!-- Y-axis label -->
			<text
				x={-padding.left + 15}
				y={chartHeight / 2}
				text-anchor="middle"
				dominant-baseline="middle"
				transform="rotate(-90, {-padding.left + 15}, {chartHeight / 2})"
				class="text-xs {isDark ? 'fill-gray-400' : 'fill-gray-500'}"
			>
				{yAxisLabel}
			</text>

			<!-- X-axis labels -->
			{#each xLabels as label}
				<text
					x={xScale(label.index)}
					y={chartHeight + 20}
					text-anchor="middle"
					class="text-xs {isDark ? 'fill-gray-400' : 'fill-gray-500'}"
				>
					{label.label}
				</text>
			{/each}

			<!-- X-axis label -->
			<text
				x={chartWidth / 2}
				y={chartHeight + 35}
				text-anchor="middle"
				class="text-xs {isDark ? 'fill-gray-400' : 'fill-gray-500'}"
			>
				{xAxisLabel}
			</text>

			<!-- Bars -->
			{#if data.length > 0}
				{#each data as bin, i}
					<rect
						x={xScale(i) - barWidth / 2}
						y={yScale(bin.count)}
						width={barWidth}
						height={barHeight(bin.count)}
						fill="url(#barGradient-{title})"
						rx="1"
					/>
				{/each}
			{/if}

			<!-- No data message -->
			{#if data.length === 0}
				<text
					x={chartWidth / 2}
					y={chartHeight / 2}
					text-anchor="middle"
					dominant-baseline="middle"
					class="text-sm {isDark ? 'fill-gray-500' : 'fill-gray-400'}"
				>
					No data available
				</text>
			{/if}
		</g>
	</svg>
</div>
