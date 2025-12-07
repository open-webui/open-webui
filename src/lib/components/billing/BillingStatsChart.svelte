<script lang="ts">
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import { billingStats } from '$lib/stores';
	import { getBillingStats } from '$lib/apis/billing';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let chartContainer: HTMLDivElement;
	let chart: any = null;
	let period = '7d'; // 24h, 7d, 30d, 12m
	let loading = false;
	let showLoading = false;  // 延迟显示 loading
	let loadingTimer: ReturnType<typeof setTimeout> | null = null;
	let echarts: any = null;

	// 时间选项配置
	const periodOptions = [
		{ value: '24h', label: '过去24小时', days: 1, granularity: 'hour' },
		{ value: '7d', label: '过去7天', days: 7, granularity: 'day' },
		{ value: '30d', label: '过去1个月', days: 30, granularity: 'day' },
		{ value: '1y', label: '过去1年', days: 365, granularity: 'month' }
	];

	$: currentPeriod = periodOptions.find((p) => p.value === period) || periodOptions[1];

	const loadStats = async () => {
		loading = true;
		// 延迟 500ms 后才显示 loading，避免快速加载时闪烁
		loadingTimer = setTimeout(() => {
			if (loading) {
				showLoading = true;
			}
		}, 500);

		try {
			const stats = await getBillingStats(localStorage.token, currentPeriod.days, currentPeriod.granularity);
			billingStats.set(stats);
		} catch (error) {
			toast.error($i18n.t('查询统计失败: ') + error.message);
		} finally {
			loading = false;
			// 清除定时器并隐藏 loading
			if (loadingTimer) {
				clearTimeout(loadingTimer);
				loadingTimer = null;
			}
			showLoading = false;

			// 等待 DOM 更新后渲染图表
			await tick();
			setTimeout(() => {
				if (!chart && chartContainer) {
					initChart();
				}
				renderChart();
			}, 50);
		}
	};

	// 模型颜色配置
	const MODEL_COLORS = [
		'#4F46E5', // indigo
		'#10B981', // emerald
		'#F59E0B', // amber
		'#EF4444', // red
		'#8B5CF6', // violet
		'#06B6D4', // cyan
		'#EC4899', // pink
		'#84CC16', // lime
		'#F97316', // orange
		'#6366F1', // indigo-light
	];

	const getModelColor = (index: number) => MODEL_COLORS[index % MODEL_COLORS.length];

	const renderChart = () => {
		if (!$billingStats || !echarts || !chart) return;

		const data = $billingStats.daily || [];
		const models = $billingStats.models || [];
		if (data.length === 0) return;

		// 计算Y轴最大值，确保至少为1（当所有数据为0时）
		const maxCost = Math.max(...data.map((d: any) => d.cost || 0));
		const yAxisMax = maxCost > 0 ? undefined : 1;

		// 为每个模型创建一个 series
		const series = models.length > 0
			? models.map((model: string, index: number) => ({
					name: model,
					type: 'bar',
					stack: 'total',
					barWidth: '50%',
					data: data.map((d: any) => d.by_model?.[model] || 0),
					itemStyle: {
						color: getModelColor(index),
						// 只有最后一个（堆叠顶部）才有圆角
						borderRadius: index === models.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]
					}
				}))
			: [{
					name: '消费',
					type: 'bar',
					barWidth: '50%',
					data: data.map((d: any) => d.cost),
					itemStyle: {
						color: '#4F46E5',
						borderRadius: [4, 4, 0, 0]
					}
				}];

		chart.setOption({
			tooltip: {
				trigger: 'axis',
				formatter: (params: any) => {
					if (!params || params.length === 0) return '';
					const date = params[0].name;
					let total = 0;
					let details = params
						.filter((p: any) => p.value > 0)
						.map((p: any) => {
							total += p.value;
							return `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};margin-right:5px;"></span>${p.seriesName}: ¥${p.value.toFixed(4)}`;
						})
						.join('<br/>');
					return `<strong>${date}</strong><br/>${details || '无消费'}<br/><strong>合计: ¥${total.toFixed(4)}</strong>`;
				}
			},
			legend: models.length > 0 ? {
				data: models,
				bottom: 0,
				type: 'scroll',
				textStyle: { fontSize: 10, color: '#6b7280' }
			} : undefined,
			grid: {
				left: '3%',
				right: '4%',
				bottom: models.length > 0 ? '18%' : '12%',
				top: '8%',
				containLabel: true
			},
			xAxis: {
				type: 'category',
				data: data.map((d: any) => d.date),
				axisLabel: {
					rotate: data.length > 12 ? 45 : 0,
					fontSize: 11,
					color: '#6b7280'
				},
				axisLine: {
					lineStyle: { color: '#e5e7eb' }
				},
				axisTick: {
					show: false
				}
			},
			yAxis: {
				type: 'value',
				min: 0,
				max: yAxisMax,
				axisLabel: {
					formatter: (value: number) => `¥${value.toFixed(2)}`,
					fontSize: 11,
					color: '#6b7280'
				},
				splitLine: {
					lineStyle: { color: '#f3f4f6', type: 'dashed' }
				},
				axisLine: {
					show: false
				}
			},
			series
		}, true);  // true = 不合并，完全替换
	};

	const initChart = () => {
		if (!echarts) return;

		// 确保 DOM 元素存在且有尺寸后再初始化
		if (chartContainer && !chart) {
			const width = chartContainer.offsetWidth;
			const height = chartContainer.offsetHeight;
			if (width > 0 && height > 0) {
				chart = echarts.init(chartContainer);
			}
		}
	};

	onMount(async () => {
		// 动态导入 echarts（避免 SSR 问题）
		try {
			echarts = await import('echarts');
		} catch (e) {
			console.error('Failed to load echarts:', e);
			return;
		}

		// loadStats 会处理图表初始化和渲染
		await loadStats();

		// 响应式调整
		let resizeObserver: ResizeObserver | null = null;

		// 延迟设置 ResizeObserver，确保图表已初始化
		setTimeout(() => {
			if (chartContainer) {
				resizeObserver = new ResizeObserver(() => {
					chart?.resize();
				});
				resizeObserver.observe(chartContainer);
			}
		}, 200);

		return () => {
			resizeObserver?.disconnect();
		};
	});

	onDestroy(() => {
		chart?.dispose();
		chart = null;
		if (loadingTimer) {
			clearTimeout(loadingTimer);
			loadingTimer = null;
		}
	});
</script>

<div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-inner">
	<!-- 标题和时间选择器 -->
	<div class="flex justify-between items-center mb-4">
		<p class="text-sm font-semibold text-gray-700 dark:text-gray-300">{$i18n.t('消费统计')}</p>
		<select
			bind:value={period}
			on:change={loadStats}
			class="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:outline-none focus:ring-1 focus:ring-indigo-500"
		>
			{#each periodOptions as opt}
				<option value={opt.value}>{opt.label}</option>
			{/each}
		</select>
	</div>

	<div class="relative h-56">
		{#if showLoading}
			<div class="absolute inset-0 flex justify-center items-center bg-gray-50/80 dark:bg-gray-800/80 z-10">
				<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-500"></div>
			</div>
		{/if}

		{#if !$billingStats || !$billingStats.daily || $billingStats.daily.length === 0}
			{#if !loading && !showLoading}
				<div class="absolute inset-0 flex flex-col items-center justify-center text-gray-400 dark:text-gray-500">
					<svg class="w-10 h-10 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
					</svg>
					<p class="text-xs">{$i18n.t('暂无消费记录')}</p>
				</div>
			{/if}
		{/if}

		<div bind:this={chartContainer} class="w-full h-full"></div>
	</div>
</div>
