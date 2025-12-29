<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getUserModelUsage, formatTokenCount, type ModelUsage } from '$lib/apis/analytics';

	const i18n = getContext('i18n');

	export let year: number | undefined = undefined;

	let loading = true;
	let error: string | null = null;
	let modelUsage: ModelUsage[] = [];

	// Colors for the pie chart segments
	const COLORS = [
		'#10B981', // emerald-500
		'#3B82F6', // blue-500
		'#F59E0B', // amber-500
		'#EF4444', // red-500
		'#8B5CF6', // violet-500
		'#EC4899', // pink-500
		'#06B6D4', // cyan-500
		'#F97316', // orange-500
		'#84CC16', // lime-500
		'#6366F1'  // indigo-500
	];

	onMount(async () => {
		await loadModelUsage();
	});

	async function loadModelUsage() {
		loading = true;
		error = null;

		try {
			const token = localStorage.getItem('token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			modelUsage = await getUserModelUsage(token, year);
		} catch (e) {
			error = 'Error loading model usage';
			console.error(e);
		}

		loading = false;
	}

	function getColor(index: number): string {
		return COLORS[index % COLORS.length];
	}

	function getModelDisplayName(modelId: string): string {
		// Extract a cleaner model name from the ID
		const parts = modelId.split('/');
		return parts[parts.length - 1] || modelId;
	}

	// Calculate pie chart segments
	function calculatePieSegments() {
		let cumulativePercentage = 0;
		return modelUsage.map((model, index) => {
			const segment = {
				...model,
				color: getColor(index),
				startPercentage: cumulativePercentage,
				endPercentage: cumulativePercentage + model.percentage
			};
			cumulativePercentage += model.percentage;
			return segment;
		});
	}

	function createPieChartPath(startPercent: number, endPercent: number): string {
		// Convert percentages to angles (in radians)
		const startAngle = (startPercent / 100) * 2 * Math.PI - Math.PI / 2;
		const endAngle = (endPercent / 100) * 2 * Math.PI - Math.PI / 2;
		
		const radius = 45;
		const centerX = 50;
		const centerY = 50;
		
		// Calculate points
		const x1 = centerX + radius * Math.cos(startAngle);
		const y1 = centerY + radius * Math.sin(startAngle);
		const x2 = centerX + radius * Math.cos(endAngle);
		const y2 = centerY + radius * Math.sin(endAngle);
		
		// Large arc flag
		const largeArcFlag = (endPercent - startPercent) > 50 ? 1 : 0;
		
		// Create path
		return `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
	}

	$: pieSegments = calculatePieSegments();
	$: totalTokens = modelUsage.reduce((sum, m) => sum + m.total_tokens, 0);
</script>

<div class="w-full">
	<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
		{$i18n.t('Model Usage')}
	</h3>

	{#if loading}
		<div class="flex items-center justify-center py-8">
			<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-500"></div>
		</div>
	{:else if error}
		<div class="text-center py-6 text-gray-500 dark:text-gray-400">
			{error}
		</div>
	{:else if modelUsage.length === 0}
		<div class="text-center py-6 text-gray-500 dark:text-gray-400">
			{$i18n.t('No model usage data yet')}
		</div>
	{:else}
		<div class="flex flex-col lg:flex-row gap-6">
			<!-- Pie Chart -->
			<div class="flex-shrink-0 flex justify-center">
				<div class="relative w-40 h-40">
					<svg viewBox="0 0 100 100" class="w-full h-full transform -rotate-90">
						{#each pieSegments as segment, index}
							{#if segment.percentage > 0}
								<path
									d={createPieChartPath(segment.startPercentage, segment.endPercentage)}
									fill={segment.color}
									class="transition-opacity hover:opacity-80"
								/>
							{/if}
						{/each}
						<!-- Center circle for donut effect -->
						<circle cx="50" cy="50" r="25" fill="white" class="dark:fill-gray-900" />
					</svg>
					<!-- Center text -->
					<div class="absolute inset-0 flex flex-col items-center justify-center">
						<span class="text-lg font-bold text-gray-900 dark:text-gray-100">
							{modelUsage.length}
						</span>
						<span class="text-xs text-gray-500 dark:text-gray-400">
							{$i18n.t('models')}
						</span>
					</div>
				</div>
			</div>

			<!-- Model List -->
			<div class="flex-1 space-y-2">
				{#each modelUsage.slice(0, 6) as model, index}
					<div class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 transition-colors">
						<div 
							class="w-3 h-3 rounded-full flex-shrink-0"
							style="background-color: {getColor(index)}"
						></div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center justify-between gap-2">
								<span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
									{getModelDisplayName(model.model_id)}
								</span>
								<span class="text-sm font-medium text-gray-600 dark:text-gray-400">
									{model.percentage.toFixed(1)}%
								</span>
							</div>
							<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
								<span>{formatTokenCount(model.total_tokens)} tokens</span>
								<span>•</span>
								<span>{model.conversation_count} chats</span>
							</div>
						</div>
					</div>
				{/each}

				{#if modelUsage.length > 6}
					<div class="text-xs text-gray-500 dark:text-gray-400 pl-6">
						+{modelUsage.length - 6} {$i18n.t('more models')}
					</div>
				{/if}
			</div>
		</div>

		<!-- Total footer -->
		<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
			<span class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Total tokens processed')}
			</span>
			<span class="text-lg font-bold text-emerald-600 dark:text-emerald-400">
				{formatTokenCount(totalTokens)}
			</span>
		</div>
	{/if}
</div>
