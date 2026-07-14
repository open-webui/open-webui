<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	// Slices are folded to at most `maxSlices` (tail becomes "Other")
	export let data: Array<{ label: string; value: number; color?: string; colorDark?: string }> = [];
	export let colors: string[] = [];
	export let colorsDark: string[] = [];
	export let centerLabel = '';
	export let centerValue = '';
	export let otherLabel = 'Other';
	export let maxSlices = 6;
	export let valueFormatter: (value: number) => string = (value) => value.toLocaleString();
	// Compact variant for tight containers (e.g. the chat context panel).
	export let small = false;

	const OTHER_COLOR = '#898781';

	let chartCanvas: HTMLCanvasElement;
	let chartInstance: any = null;
	let Chart: any = null;
	let themeObserver: MutationObserver | null = null;
	let darkMode = false;

	const isDark = () => document.documentElement.classList.contains('dark');

	$: slices = (() => {
		const sorted = [...data].filter((d) => d.value > 0).sort((a, b) => b.value - a.value);
		if (sorted.length <= maxSlices) return sorted;
		const head = sorted.slice(0, maxSlices - 1);
		const tail = sorted.slice(maxSlices - 1);
		return [
			...head,
			{ label: otherLabel, value: tail.reduce((sum, d) => sum + d.value, 0), color: OTHER_COLOR }
		];
	})();

	$: total = slices.reduce((sum, d) => sum + d.value, 0);

	const sliceColor = (
		slice: { label: string; color?: string; colorDark?: string },
		idx: number,
		dark: boolean
	) => {
		if (dark && slice.colorDark) return slice.colorDark;
		if (slice.color) return slice.color;
		const palette = dark && colorsDark.length ? colorsDark : colors;
		return palette[idx % palette.length];
	};

	const createChart = async () => {
		if (!chartCanvas || !slices.length) return;

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
			type: 'doughnut',
			data: {
				labels: slices.map((s) => s.label),
				datasets: [
					{
						data: slices.map((s) => s.value),
						backgroundColor: slices.map((s, i) => sliceColor(s, i, dark)),
						borderColor: surface,
						borderWidth: 2,
						hoverOffset: 3
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '68%',
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
							label: (context: any) => {
								const value = context.raw ?? 0;
								const pct = total > 0 ? ((value / total) * 100).toFixed(1) : '0';
								return ` ${valueFormatter(value)} (${pct}%)`;
							}
						}
					}
				},
				animation: { duration: 400, easing: 'easeOutQuart' }
			}
		});
	};

	$: if (chartCanvas && slices) {
		createChart();
	}

	onMount(() => {
		darkMode = isDark();
		// Re-render when the app theme flips so surface gaps stay invisible
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

{#if slices.length}
	<div class="flex items-center {small ? 'gap-3' : 'gap-4'}">
		<div class="relative {small ? 'size-24' : 'size-36'} shrink-0">
			<canvas bind:this={chartCanvas}></canvas>
			<div
				class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center {small
					? 'px-4'
					: 'px-6'}"
			>
				<span
					class="{small
						? 'text-sm'
						: 'text-base'} font-semibold text-gray-900 dark:text-white truncate max-w-full"
					>{centerValue}</span
				>
				{#if centerLabel}
					<span class="text-[10px] text-gray-400 truncate max-w-full">{centerLabel}</span>
				{/if}
			</div>
		</div>
		<div class="flex-1 min-w-0 flex flex-col gap-1 {small ? 'text-xs' : 'text-sm'}">
			{#each slices as slice, idx}
				<div class="flex items-center gap-2 min-w-0">
					<span
						class="size-2 rounded-full shrink-0"
						style="background-color: {sliceColor(slice, idx, darkMode)}"
					></span>
					<span class="flex-1 min-w-0 truncate text-gray-600 dark:text-gray-300">{slice.label}</span
					>
					<span class="shrink-0 text-right text-gray-900 dark:text-white tabular-nums">
						{valueFormatter(slice.value)}
					</span>
					<span class="w-11 shrink-0 text-right text-gray-400 tabular-nums">
						({total > 0 ? ((slice.value / total) * 100).toFixed(0) : 0}%)
					</span>
				</div>
			{/each}
		</div>
	</div>
{:else}
	<div class="flex items-center justify-center h-36 text-gray-400 text-xs">
		{$i18n.t('No data')}
	</div>
{/if}
