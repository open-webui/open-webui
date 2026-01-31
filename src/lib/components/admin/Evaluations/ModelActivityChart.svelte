<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let history: Array<{ date: string; won: number; lost: number }> = [];
	export let loading = false;
	export let aggregateWeekly = false;

	let chartCanvas: HTMLCanvasElement;
	let chartInstance: any = null;
	let Chart: any = null;

	const createChart = async () => {
		if (!chartCanvas || !history.length) return;

		// Dynamically import Chart.js
		if (!Chart) {
			const module = await import('chart.js/auto');
			Chart = module.default;
		}

		// Destroy previous chart instance
		if (chartInstance) {
			chartInstance.destroy();
		}

		// For year/all views, aggregate by week
		let chartData = history;

		if (aggregateWeekly && history.length > 7) {
			// Aggregate daily data into weekly buckets
			const weeklyData: { [key: string]: { won: number; lost: number; startDate: string } } = {};
			history.forEach((h) => {
				const date = new Date(h.date);
				// Get the Monday of this week as the bucket key
				const day = date.getDay();
				const diff = date.getDate() - day + (day === 0 ? -6 : 1);
				const monday = new Date(date);
				monday.setDate(diff);
				const weekKey = monday.toISOString().split('T')[0];

				if (!weeklyData[weekKey]) {
					weeklyData[weekKey] = { won: 0, lost: 0, startDate: weekKey };
				}
				weeklyData[weekKey].won += h.won;
				weeklyData[weekKey].lost += h.lost;
			});

			chartData = Object.values(weeklyData).sort(
				(a, b) => new Date(a.startDate).getTime() - new Date(b.startDate).getTime()
			);
		}

		const labels = chartData.map((h) => {
			const date = new Date('startDate' in h ? h.startDate : h.date);
			if (aggregateWeekly) {
				return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
			}
			return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
		});

		// Diverging chart: wins go UP (positive), losses go DOWN (negative)
		const wonData = chartData.map((h) => h.won);
		const lostData = chartData.map((h) => -h.lost); // Negative for below-zero bars

		// Thicker bars for weekly aggregated data
		const barPercentage = aggregateWeekly ? 0.95 : 0.9;
		const categoryPercentage = aggregateWeekly ? 1.0 : 0.95;

		chartInstance = new Chart(chartCanvas, {
			type: 'bar',
			data: {
				labels,
				datasets: [
					{
						label: 'Won',
						data: wonData,
						backgroundColor: '#5ba3c8',
						borderRadius: 2,
						barPercentage,
						categoryPercentage
					},
					{
						label: 'Lost',
						data: lostData,
						backgroundColor: '#d97c5a',
						borderRadius: 2,
						barPercentage,
						categoryPercentage
					}
				]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: {
					intersect: false,
					mode: 'index'
				},
				plugins: {
					legend: {
						display: false // Hide legend for cleaner look
					},
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
							label: function (context: any) {
								const value = Math.abs(context.raw);
								return `${context.dataset.label}: ${value}`;
							}
						}
					}
				},
				scales: {
					x: {
						stacked: true,
						grid: {
							display: false
						},
						ticks: {
							display: false // Hide x-axis labels for cleaner look
						},
						border: {
							display: false
						}
					},
					y: {
						stacked: true,
						grid: {
							color: 'rgba(107, 114, 128, 0.1)',
							drawTicks: false
						},
						ticks: {
							color: '#6b7280',
							font: {
								size: 10
							},
							padding: 8,
							stepSize: 1,
							precision: 0,
							callback: function (value: number) {
								return Math.abs(value); // Show absolute values on y-axis
							}
						},
						border: {
							display: false
						}
					}
				},
				animation: {
					duration: 400,
					easing: 'easeOutQuart'
				}
			}
		});
	};

	$: if (chartCanvas && history.length && !loading && aggregateWeekly !== undefined) {
		createChart();
	}

	onDestroy(() => {
		if (chartInstance) {
			chartInstance.destroy();
			chartInstance = null;
		}
	});
</script>

<div class="w-full">
	{#if loading}
		<div class="flex items-center justify-center h-40">
			<Spinner className="size-5" />
		</div>
	{:else if !history.length || history.every((h) => h.won === 0 && h.lost === 0)}
		<div class="flex items-center justify-center h-40 text-gray-500 text-sm">
			{$i18n.t('No activity data')}
		</div>
	{:else}
		<div class="h-48">
			<canvas bind:this={chartCanvas}></canvas>
		</div>
	{/if}
</div>
