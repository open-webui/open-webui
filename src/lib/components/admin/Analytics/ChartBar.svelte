<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let labels: string[] = [];
	// tooltipLabels: optional per-point detail string shown in the tooltip
	// instead of the formatted raw value
	export let datasets: Array<{
		label: string;
		data: number[];
		color: string;
		colorDark?: string;
		tooltipLabels?: string[];
	}> = [];
	export let stacked = false;
	export let horizontal = false;
	export let height = 200;
	export let valueFormatter: (value: number) => string = (value) => value.toLocaleString();
	// Legend renders automatically for >1 dataset (identity is never color-alone)
	export let showLegend: boolean | null = null;

	let chartCanvas: HTMLCanvasElement;
	let chartInstance: any = null;
	let Chart: any = null;
	let themeObserver: MutationObserver | null = null;
	let darkMode = false;

	const isDark = () => document.documentElement.classList.contains('dark');

	$: legendVisible = showLegend ?? datasets.length > 1;
	$: hasData = labels.length > 0 && datasets.some((d) => d.data.some((v) => v > 0));

	const createChart = async () => {
		if (!chartCanvas || !hasData) return;

		if (!Chart) {
			const module = await import('chart.js/auto');
			Chart = module.default;
		}

		if (chartInstance) {
			chartInstance.destroy();
		}

		const dark = isDark();
		const surface = dark ? '#161616' : '#ffffff';

		chartInstance = new Chart(chartCanvas, {
			type: 'bar',
			data: {
				labels,
				datasets: datasets.map((d) => ({
					label: d.label,
					data: d.data,
					tooltipLabels: d.tooltipLabels,
					backgroundColor: dark && d.colorDark ? d.colorDark : d.color,
					borderColor: surface,
					borderWidth: stacked ? 1 : 0,
					borderRadius: 2,
					maxBarThickness: horizontal ? 14 : 32,
					barPercentage: 0.9,
					categoryPercentage: 0.9
				}))
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				indexAxis: horizontal ? 'y' : 'x',
				interaction: {
					intersect: false,
					mode: horizontal ? 'nearest' : 'index'
				},
				plugins: {
					legend: { display: false },
					tooltip: {
						backgroundColor: 'rgba(17, 24, 39, 0.9)',
						titleColor: '#f3f4f6',
						bodyColor: '#d1d5db',
						borderColor: 'rgba(75, 85, 99, 0.3)',
						borderWidth: 1,
						padding: 8,
						displayColors: true,
						boxWidth: 8,
						boxHeight: 8,
						callbacks: {
							label: (context: any) =>
								` ${context.dataset.label}: ${
									context.dataset.tooltipLabels?.[context.dataIndex] ??
									valueFormatter(context.raw ?? 0)
								}`
						},
						filter: (item: any) => (item.raw ?? 0) > 0
					}
				},
				scales: {
					x: {
						stacked,
						grid: { display: horizontal, color: 'rgba(107, 114, 128, 0.1)', drawTicks: false },
						ticks: {
							color: '#898781',
							font: { size: 10 },
							maxRotation: 0,
							autoSkip: true,
							maxTicksLimit: horizontal ? 6 : 8,
							...(horizontal ? { callback: (value: number) => valueFormatter(value) } : {})
						},
						border: { display: false }
					},
					y: {
						stacked,
						grid: { display: !horizontal, color: 'rgba(107, 114, 128, 0.1)', drawTicks: false },
						ticks: {
							color: '#898781',
							font: { size: 10 },
							padding: 6,
							...(horizontal
								? {}
								: { maxTicksLimit: 5, callback: (value: number) => valueFormatter(value) })
						},
						border: { display: false }
					}
				},
				animation: { duration: 400, easing: 'easeOutQuart' }
			}
		});
	};

	$: if (chartCanvas && labels && datasets && hasData !== undefined) {
		createChart();
	}

	onMount(() => {
		darkMode = isDark();
		themeObserver = new MutationObserver(() => {
			darkMode = isDark();
			if (chartInstance) createChart();
		});
		themeObserver.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class']
		});
	});

	onDestroy(() => {
		themeObserver?.disconnect();
		if (chartInstance) {
			chartInstance.destroy();
			chartInstance = null;
		}
	});
</script>

<div class="w-full">
	{#if hasData}
		{#if legendVisible}
			<div class="flex flex-wrap gap-x-3 gap-y-1 mb-1.5 px-0.5">
				{#each datasets as d}
					<div class="flex items-center gap-1.5 text-[10px] text-gray-500 dark:text-gray-400">
						<span
							class="size-2 rounded-full shrink-0"
							style="background-color: {darkMode && d.colorDark ? d.colorDark : d.color}"
						></span>
						<span class="truncate max-w-[120px]">{d.label}</span>
					</div>
				{/each}
			</div>
		{/if}
		<div style="height: {height}px">
			<canvas bind:this={chartCanvas}></canvas>
		</div>
	{:else}
		<div class="flex items-center justify-center text-gray-400 text-xs" style="height: {height}px">
			{$i18n.t('No data')}
		</div>
	{/if}
</div>
