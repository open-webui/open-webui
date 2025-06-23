<script lang="ts">
	import Modal from '$lib/components/common/Modal.svelte';
	import { getContext, onMount, afterUpdate } from 'svelte';
	export let show = false;
	export let model = null;
	export let modelRatingHistory = new Map();
	export let feedbacks = [];
	export let onClose: () => void = () => {};
	const i18n = getContext('i18n');

	const close = () => {
		show = false;
		onClose();
	};

	$: topTags = model ? getTopTagsForModel(model.id, feedbacks) : [];

	const getTopTagsForModel = (modelId: string, feedbacks: any[], topN = 5) => {
		const tagCounts = new Map();
		feedbacks
			.filter((fb) => fb.data.model_id === modelId)
			.forEach((fb) => {
				(fb.data.tags || []).forEach((tag) => {
					tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
				});
			});
		return Array.from(tagCounts.entries())
			.sort((a, b) => b[1] - a[1])
			.slice(0, topN)
			.map(([tag, count]) => ({ tag, count }));
	};

	let chartCanvas;
	let chart;

	$: chartData =
		model && modelRatingHistory && modelRatingHistory.has(model.id)
			? modelRatingHistory.get(model.id)
			: [];

	async function renderChart() {
		if (!chartCanvas || !chartData || chartData.length < 2) return;
		const { Chart, registerables } = await import('chart.js');
		Chart.register(...registerables);
		if (chart) chart.destroy();
		chart = new Chart(chartCanvas, {
			type: 'line',
			data: {
				labels: chartData.map((d) => new Date(d.timestamp * 1000).toLocaleDateString()),
				datasets: [
					{
						label: 'Rating',
						data: chartData.map((d) => d.rating),
						borderColor: 'rgba(75,192,192,1)',
						backgroundColor: 'rgba(75,192,192,0.1)',
						tension: 0.2,
						pointRadius: 2,
						fill: false
					}
				]
			},
			options: {
				scales: {
					y: { beginAtZero: false, title: { display: true, text: 'Elo Rating' } },
					x: { title: { display: true, text: 'Date' } }
				},
				plugins: { legend: { display: false } },
				responsive: true,
				maintainAspectRatio: false
			}
		});
	}

	onMount(renderChart);
	afterUpdate(renderChart);
</script>

<Modal size="sm" bind:show>
	{#if model}
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">
				{model.name}
			</div>
			<button class="self-center" on:click={close} aria-label="Close">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<div class="px-5 pb-4 dark:text-gray-200">
			<div class="mb-2">
				{#if topTags.length}
					<div class="flex flex-wrap gap-1 mt-1 -mx-1">
						{#each topTags as tagInfo}
							<span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-850 text-xs">
								{tagInfo.tag} <span class="text-gray-500 font-medium">{tagInfo.count}</span>
							</span>
						{/each}
					</div>
				{:else}
					<span>-</span>
				{/if}
			</div>

			<div class="my-4" style="height:150px;">
				{#if chartData.length > 1}
					<canvas bind:this={chartCanvas}></canvas>
				{:else}
					<div class="text-xs text-gray-400 text-center py-10">
						{i18n && i18n.t
							? i18n.t('Not enough data for rating history')
							: 'Not enough data for rating history'}
					</div>
				{/if}
			</div>

			<div class="flex justify-end pt-2">
				<button
					class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
					type="button"
					on:click={close}
				>
					{i18n && i18n.t ? i18n.t('Close') : 'Close'}
				</button>
			</div>
		</div>
	{/if}
</Modal>
