<script lang="ts">
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import { billingStats } from '$lib/stores';
	import { getBillingStats } from '$lib/apis/billing';
	import { toast } from 'svelte-sonner';
	import * as echarts from 'echarts';

	const i18n = getContext('i18n');

	let dailyChartContainer: HTMLDivElement;
	let modelChartContainer: HTMLDivElement;
	let dailyChart: echarts.ECharts | null = null;
	let modelChart: echarts.ECharts | null = null;
	let days = 7;
	let loading = false;

	const loadStats = async () => {
		loading = true;
		try {
			const stats = await getBillingStats(localStorage.token, days);
			billingStats.set(stats);

			// 等待 DOM 更新后初始化图表
			await tick();
			await initCharts();

			// 渲染图表
			renderCharts();
		} catch (error) {
			toast.error($i18n.t('查询统计失败: ') + error.message);
		} finally {
			loading = false;
		}
	};

	const renderCharts = () => {
		if (!$billingStats || !dailyChart || !modelChart) return;

		// 按日统计图表
		if (dailyChart && $billingStats.daily.length > 0) {
			dailyChart.setOption({
				title: {
					text: $i18n.t('每日消费趋势'),
					left: 'center',
					textStyle: {
						fontSize: 16,
						fontWeight: 'normal'
					}
				},
				tooltip: {
					trigger: 'axis',
					formatter: (params: any) => {
						const data = params[0];
						return `${data.name}<br/>费用: ¥${data.value.toFixed(4)}`;
					}
				},
				grid: {
					left: '3%',
					right: '4%',
					bottom: '3%',
					containLabel: true
				},
				xAxis: {
					type: 'category',
					data: $billingStats.daily.map((d) => d.date),
					axisLabel: {
						rotate: 45
					}
				},
				yAxis: {
					type: 'value',
					name: '费用（元）',
					axisLabel: {
						formatter: '¥{value}'
					}
				},
				series: [
					{
						data: $billingStats.daily.map((d) => d.cost),
						type: 'line',
						smooth: true,
						areaStyle: {
							color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
								{ offset: 0, color: 'rgba(59, 130, 246, 0.5)' },
								{ offset: 1, color: 'rgba(59, 130, 246, 0.1)' }
							])
						},
						lineStyle: {
							color: '#3b82f6',
							width: 2
						},
						itemStyle: {
							color: '#3b82f6'
						}
					}
				]
			});
		}

		// 按模型统计图表
		if (modelChart && $billingStats.by_model.length > 0) {
			modelChart.setOption({
				title: {
					text: $i18n.t('模型消费分布'),
					left: 'center',
					textStyle: {
						fontSize: 16,
						fontWeight: 'normal'
					}
				},
				tooltip: {
					trigger: 'item',
					formatter: (params: any) => {
						return `${params.name}<br/>费用: ¥${params.value.toFixed(4)}<br/>占比: ${params.percent}%`;
					}
				},
				legend: {
					orient: 'vertical',
					left: 'left',
					top: 'middle'
				},
				series: [
					{
						type: 'pie',
						radius: ['40%', '70%'],
						center: ['60%', '50%'],
						data: $billingStats.by_model.map((m) => ({
							name: m.model,
							value: m.cost
						})),
						emphasis: {
							itemStyle: {
								shadowBlur: 10,
								shadowOffsetX: 0,
								shadowColor: 'rgba(0, 0, 0, 0.5)'
							}
						},
						label: {
							formatter: '{b}: ¥{c}'
						}
					}
				]
			});
		}
	};

	const initCharts = async () => {
		// 等待 DOM 更新
		await tick();

		// 确保 DOM 元素存在后再初始化
		if (dailyChartContainer && !dailyChart) {
			dailyChart = echarts.init(dailyChartContainer);
		}
		if (modelChartContainer && !modelChart) {
			modelChart = echarts.init(modelChartContainer);
		}
	};

	onMount(async () => {
		// loadStats 会处理图表初始化和渲染
		await loadStats();

		// 响应式调整（等待图表初始化完成）
		await tick();
		let resizeObserver: ResizeObserver | null = null;
		if (dailyChartContainer && modelChartContainer && dailyChart && modelChart) {
			resizeObserver = new ResizeObserver(() => {
				dailyChart?.resize();
				modelChart?.resize();
			});

			resizeObserver.observe(dailyChartContainer);
			resizeObserver.observe(modelChartContainer);
		}

		return () => {
			resizeObserver?.disconnect();
		};
	});

	onDestroy(() => {
		dailyChart?.dispose();
		modelChart?.dispose();
	});
</script>

<div class="billing-stats bg-white dark:bg-gray-850 rounded-xl shadow-sm p-4">
	<div class="stats-header flex justify-between items-center mb-4">
		<h2 class="text-lg font-semibold">{$i18n.t('消费统计')}</h2>
		<select
			bind:value={days}
			on:change={loadStats}
			class="px-3 py-1.5 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-sm"
		>
			<option value={7}>{$i18n.t('最近7天')}</option>
			<option value={30}>{$i18n.t('最近30天')}</option>
			<option value={90}>{$i18n.t('最近90天')}</option>
		</select>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
		</div>
	{:else if $billingStats}
		<div class="charts-container grid grid-cols-1 lg:grid-cols-2 gap-4">
			<div class="chart-wrapper">
				<div bind:this={dailyChartContainer} class="chart h-80"></div>
			</div>
			<div class="chart-wrapper">
				<div bind:this={modelChartContainer} class="chart h-80"></div>
			</div>
		</div>

		{#if $billingStats.daily.length === 0 && $billingStats.by_model.length === 0}
			<div class="flex flex-col items-center justify-center py-12 text-gray-500">
				<svg
					class="w-16 h-16 mb-4 opacity-50"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="1.5"
						d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
					/>
				</svg>
				<p class="text-sm">暂无统计数据</p>
			</div>
		{/if}
	{/if}
</div>
