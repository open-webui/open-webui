<script lang="ts">
	import { onMount } from 'svelte';
	import type { TimeSeriesPoint } from '$lib/apis/dashboard';

	export let title: string = '';
	export let subtitle: string = '';
	export let data: TimeSeriesPoint[] = [];
	export let color: string = '#5CC9D3';
	export let isDark: boolean = false;
	export let height: number = 200;
	export let showGrid: boolean = true;
	export let showDots: boolean = false;

	let containerWidth = 800;
	let container: HTMLDivElement;

	// Chart dimensions
	const padding = { top: 20, right: 20, bottom: 30, left: 50 };

	$: chartWidth = containerWidth - padding.left - padding.right;
	$: chartHeight = height - padding.top - padding.bottom;

	// Calculate scales
	$: values = data.map((d) => d.value);
	$: minValue = Math.min(...values, 0);
	$: maxValue = Math.max(...values, 1);
	$: valueRange = maxValue - minValue || 1;

	// Scale functions
	$: xScale = (index: number) => (index / (data.length - 1 || 1)) * chartWidth;
	$: yScale = (value: number) => chartHeight - ((value - minValue) / valueRange) * chartHeight;

	// Generate path
	$: pathD = data.length > 0
		? data
				.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.value)}`)
				.join(' ')
		: '';

	// Generate area path (for gradient fill)
	$: areaD = data.length > 0
		? `${pathD} L ${xScale(data.length - 1)} ${chartHeight} L ${xScale(0)} ${chartHeight} Z`
		: '';

	// Y-axis ticks
	$: yTicks = Array.from({ length: 5 }, (_, i) => {
		const value = minValue + (valueRange * (4 - i)) / 4;
		return { value, y: yScale(value) };
	});

	// X-axis labels (show first, middle, last dates)
	$: xLabels = data.length > 0
		? [
				{ index: 0, label: formatDate(data[0].time) },
				{ index: Math.floor(data.length / 2), label: formatDate(data[Math.floor(data.length / 2)]?.time) },
				{ index: data.length - 1, label: formatDate(data[data.length - 1].time) }
			]
		: [];

	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return `${date.getMonth() + 1}/${date.getDate()}`;
	}

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
			<linearGradient id="areaGradient-{title}" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0%" stop-color={color} stop-opacity="0.3" />
				<stop offset="100%" stop-color={color} stop-opacity="0" />
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

			<!-- Area fill -->
			{#if data.length > 0}
				<path d={areaD} fill="url(#areaGradient-{title})" />
			{/if}

			<!-- Line -->
			{#if data.length > 0}
				<path d={pathD} fill="none" stroke={color} stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
			{/if}

			<!-- Dots -->
			{#if showDots && data.length > 0}
				{#each data as point, i}
					<circle
						cx={xScale(i)}
						cy={yScale(point.value)}
						r="3"
						fill={color}
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
