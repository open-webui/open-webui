<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getUserHeatmap, formatTokenCount, type HeatmapDataPoint } from '$lib/apis/analytics';
	import Tooltip from '../common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let year: number | undefined = undefined;
	export let global: boolean = false;

	let loading = true;
	let error: string | null = null;
	let heatmapData: HeatmapDataPoint[] = [];
	let maxTokens = 0;
	let totalDaysActive = 0;
	let totalTokens = 0;

	// Generate weeks structure for display
	let weeks: { date: string; tokens: number; level: number; dayOfWeek: number }[][] = [];

	const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
	const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

	// Color levels for heatmap (0-4 scale, from light to dark)
	const COLORS = [
		'bg-gray-100 dark:bg-gray-800', // Level 0 - no activity
		'bg-emerald-200 dark:bg-emerald-900', // Level 1 - low
		'bg-emerald-300 dark:bg-emerald-700', // Level 2 - medium-low
		'bg-emerald-400 dark:bg-emerald-600', // Level 3 - medium-high
		'bg-emerald-500 dark:bg-emerald-500' // Level 4 - high
	];

	onMount(async () => {
		await loadHeatmapData();
	});

	async function loadHeatmapData() {
		loading = true;
		error = null;

		try {
			const token = localStorage.getItem('token');
			if (!token) {
				error = 'Not authenticated';
				loading = false;
				return;
			}

			const response = await getUserHeatmap(token, year);
			if (response) {
				heatmapData = response.data;
				maxTokens = response.max_tokens;
				totalDaysActive = response.total_days_active;
				
				// Calculate total tokens
				totalTokens = heatmapData.reduce((sum, d) => sum + d.tokens, 0);
				
				// Generate weeks structure
				generateWeeksStructure(response.year);
			} else {
				error = 'Failed to load heatmap data';
			}
		} catch (e) {
			error = 'Error loading heatmap data';
			console.error(e);
		}

		loading = false;
	}

	function generateWeeksStructure(displayYear: number) {
		// Create a map of date -> data for quick lookup
		const dataMap = new Map<string, HeatmapDataPoint>();
		for (const point of heatmapData) {
			dataMap.set(point.date, point);
		}

		// Generate all days for the year
		const startDate = new Date(displayYear, 0, 1);
		const endDate = new Date(displayYear, 11, 31);
		
		// Adjust start to first Sunday
		const firstDayOfWeek = startDate.getDay();
		if (firstDayOfWeek > 0) {
			startDate.setDate(startDate.getDate() - firstDayOfWeek);
		}

		// Adjust end to last Saturday
		const lastDayOfWeek = endDate.getDay();
		if (lastDayOfWeek < 6) {
			endDate.setDate(endDate.getDate() + (6 - lastDayOfWeek));
		}

		weeks = [];
		let currentWeek: { date: string; tokens: number; level: number; dayOfWeek: number }[] = [];

		const currentDate = new Date(startDate);
		while (currentDate <= endDate) {
			const dateStr = currentDate.toISOString().split('T')[0];
			const dayOfWeek = currentDate.getDay();
			
			const point = dataMap.get(dateStr);
			currentWeek.push({
				date: dateStr,
				tokens: point?.tokens || 0,
				level: point?.level || 0,
				dayOfWeek
			});

			if (dayOfWeek === 6) {
				weeks.push(currentWeek);
				currentWeek = [];
			}

			currentDate.setDate(currentDate.getDate() + 1);
		}

		if (currentWeek.length > 0) {
			weeks.push(currentWeek);
		}
	}

	function getMonthLabels() {
		if (weeks.length === 0) return [];
		
		const labels: { month: string; weekIndex: number }[] = [];
		let lastMonth = -1;
		
		for (let i = 0; i < weeks.length; i++) {
			// Check the first day of each week
			const firstDay = weeks[i][0];
			if (firstDay) {
				const date = new Date(firstDay.date);
				const month = date.getMonth();
				if (month !== lastMonth) {
					labels.push({ month: MONTHS[month], weekIndex: i });
					lastMonth = month;
				}
			}
		}
		
		return labels;
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString(undefined, { 
			weekday: 'short', 
			year: 'numeric', 
			month: 'short', 
			day: 'numeric' 
		});
	}

	$: monthLabels = getMonthLabels();
</script>

<div class="w-full">
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
		</div>
	{:else if error}
		<div class="text-center py-8 text-gray-500 dark:text-gray-400">
			{error}
		</div>
	{:else}
		<!-- Summary stats -->
		<div class="flex items-center justify-between mb-4">
			<div class="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
				<span>
					<span class="font-medium text-gray-900 dark:text-gray-100">{totalDaysActive}</span>
					{$i18n.t('days active')}
				</span>
				<span>•</span>
				<span>
					<span class="font-medium text-gray-900 dark:text-gray-100">{formatTokenCount(totalTokens)}</span>
					{$i18n.t('tokens total')}
				</span>
			</div>
			
			<!-- Legend -->
			<div class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
				<span>{$i18n.t('Less')}</span>
				{#each COLORS as color, i}
					<div class="w-3 h-3 rounded-sm {color}"></div>
				{/each}
				<span>{$i18n.t('More')}</span>
			</div>
		</div>

		<!-- Heatmap grid -->
		<div class="overflow-x-auto">
			<div class="inline-block min-w-full">
				<!-- Month labels -->
				<div class="flex mb-1 text-xs text-gray-500 dark:text-gray-400" style="padding-left: 32px;">
					{#each monthLabels as label, i}
						<div 
							class="absolute"
							style="transform: translateX({label.weekIndex * 14}px);"
						>
							{label.month}
						</div>
					{/each}
				</div>

				<div class="flex gap-0.5 mt-6">
					<!-- Day labels -->
					<div class="flex flex-col gap-0.5 text-xs text-gray-500 dark:text-gray-400 mr-1" style="width: 24px;">
						<div class="h-3"></div> <!-- Sun - hidden -->
						<div class="h-3 flex items-center">{DAYS[1].substring(0, 1)}</div>
						<div class="h-3"></div> <!-- Tue - hidden -->
						<div class="h-3 flex items-center">{DAYS[3].substring(0, 1)}</div>
						<div class="h-3"></div> <!-- Thu - hidden -->
						<div class="h-3 flex items-center">{DAYS[5].substring(0, 1)}</div>
						<div class="h-3"></div> <!-- Sat - hidden -->
					</div>

					<!-- Weeks -->
					{#each weeks as week, weekIndex}
						<div class="flex flex-col gap-0.5">
							{#each week as day}
								<Tooltip
									content={`
										<div class="text-xs">
											<div class="font-medium">${formatDate(day.date)}</div>
											<div class="text-gray-300">${day.tokens > 0 ? formatTokenCount(day.tokens) + ' tokens' : 'No activity'}</div>
										</div>
									`}
									placement="top"
								>
									<div 
										class="w-3 h-3 rounded-sm {COLORS[day.level]} cursor-default transition-all hover:ring-2 hover:ring-gray-400 dark:hover:ring-gray-500"
									></div>
								</Tooltip>
							{/each}
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>
