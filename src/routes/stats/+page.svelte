<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { getStatsData } from '$lib/apis/stats';
	import { toast } from 'svelte-sonner';
	import Chart from 'chart.js/auto';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	interface StatsData {
		global_indicators: {
			total_users: number;
			total_messages: number;
			total_conversations: number;
		};
		current_stats: {
			active_users: number;
			model_usage: Record<string, number>;
		};
		evolution_stats: {
			users_over_time: Array<{ date: string; count: number }>;
			conversations_over_time: Array<{ date: string; count: number }>;
		};
	}

	let statsData: StatsData | null = null;
	let loading = true;
	let usersChart: Chart | null = null;
	let conversationsChart: Chart | null = null;

	onMount(async () => {
		await loadStats();
	});

	const loadStats = async () => {
		try {
			loading = true;
			statsData = await getStatsData();
			
			// Create charts after data is loaded
			setTimeout(() => {
				createCharts();
			}, 100);
		} catch (error) {
			console.error('Failed to load stats:', error);
			toast.error('Failed to load statistics');
		} finally {
			loading = false;
		}
	};

	const createCharts = () => {
		if (!statsData) return;

		// Destroy existing charts to avoid canvas reuse issues
		if (usersChart) {
			usersChart.destroy();
			usersChart = null;
		}
		if (conversationsChart) {
			conversationsChart.destroy();
			conversationsChart = null;
		}

		// Users evolution chart
		const usersCtx = document.getElementById('usersChart') as HTMLCanvasElement | null;
		if (usersCtx && statsData.evolution_stats.users_over_time.length > 0) {
			usersChart = new Chart(usersCtx, {
				type: 'line',
				data: {
					labels: statsData.evolution_stats.users_over_time.map((item: { date: string; count: number }) => item.date),
					datasets: [{
						label: 'Nouveaux utilisateurs',
						data: statsData.evolution_stats.users_over_time.map((item: { date: string; count: number }) => item.count),
						borderColor: 'rgb(59, 130, 246)',
						backgroundColor: 'rgba(59, 130, 246, 0.1)',
						tension: 0.1
					}]
				},
				options: {
					responsive: true,
					scales: {
						y: {
							beginAtZero: true
						}
					}
				}
			});
		}

		// Conversations evolution chart
		const conversationsCtx = document.getElementById('conversationsChart') as HTMLCanvasElement | null;
		if (conversationsCtx && statsData.evolution_stats.conversations_over_time.length > 0) {
			conversationsChart = new Chart(conversationsCtx, {
				type: 'line',
				data: {
					labels: statsData.evolution_stats.conversations_over_time.map((item: { date: string; count: number }) => item.date),
					datasets: [{
						label: 'Nouvelles conversations',
						data: statsData.evolution_stats.conversations_over_time.map((item: { date: string; count: number }) => item.count),
						borderColor: 'rgb(34, 197, 94)',
						backgroundColor: 'rgba(34, 197, 94, 0.1)',
						tension: 0.1
					}]
				},
				options: {
					responsive: true,
					scales: {
						y: {
							beginAtZero: true
						}
					}
				}
			});
		}

		// Model usage pie chart
		const modelUsageCtx = document.getElementById('modelUsageChart') as HTMLCanvasElement | null;
		if (modelUsageCtx && statsData.current_stats.model_usage && Object.keys(statsData.current_stats.model_usage).length > 0) {
			const modelEntries = Object.entries(statsData.current_stats.model_usage);
			const modelNames = modelEntries.map(([name, _]) => name);
			const modelCounts = modelEntries.map(([_, count]) => count);
			
			// Generate distinct colors for each model
			const colors = [
				'rgb(59, 130, 246)',   // Blue
				'rgb(34, 197, 94)',    // Green  
				'rgb(156, 163, 175)',  // Gray
				'rgb(239, 68, 68)',    // Red
				'rgb(245, 158, 11)',   // Amber
				'rgb(168, 85, 247)',   // Purple
				'rgb(236, 72, 153)',   // Pink
				'rgb(14, 165, 233)',   // Sky
				'rgb(34, 197, 94)',    // Emerald
				'rgb(251, 146, 60)'    // Orange
			];
			
			new Chart(modelUsageCtx, {
				type: 'doughnut',
				data: {
					labels: modelNames,
					datasets: [{
						data: modelCounts,
						backgroundColor: colors.slice(0, modelNames.length)
					}]
				},
				options: {
					responsive: true,
					plugins: {
						legend: {
							position: 'bottom'
						}
					}
				}
			});
		}
	};

	const formatNumber = (num: number) => {
		return new Intl.NumberFormat('fr-FR').format(num);
	};
</script>

<svelte:head>
	<title>Statistiques | Albert</title>
</svelte:head>

<div class="bg-gray-50 dark:bg-gray-900 min-h-screen w-full overflow-y-auto">
	<!-- Header -->
	<div class="bg-white dark:bg-gray-800 shadow sticky top-0 z-10">
		<div class="max-w-6xl mx-auto px-4 py-6">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
						{#if $i18n}{$i18n.t('stats.title')}{/if}
					</h1>
					<p class="text-gray-600 dark:text-gray-400 mt-2">
						{#if $i18n}{$i18n.t('stats.subtitle')}{/if}
					</p>
				</div>
				<div class="flex items-center space-x-4">
					<a 
						href="/" 
						class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200 dark:hover:bg-blue-800 transition-colors"
					>
						{#if $i18n}← {$i18n.t('stats.back_to_assistant')}{/if}
					</a>
				</div>
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="max-w-6xl mx-auto px-4 py-8 pb-16">
		{#if loading}
			<div class="flex items-center justify-center h-64">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
			</div>
		{:else if statsData}
			<!-- Global Indicators -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<div class="flex items-start">
						<div class="flex-shrink-0">
							<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
								<svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
									<path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
								</svg>
							</div>
						</div>
						<div class="ml-4 flex-1">
							<h2 class="text-lg font-medium text-gray-900 dark:text-white mb-2 leading-tight">Utilisateurs totaux</h2>
							<p class="text-3xl font-bold text-blue-600 dark:text-blue-400 leading-none">
								{formatNumber(statsData.global_indicators.total_users)}
							</p>
						</div>
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<div class="flex items-start">
						<div class="flex-shrink-0">
							<div class="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
								<svg class="w-5 h-5 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd"></path>
								</svg>
							</div>
						</div>
						<div class="ml-4 flex-1">
							<h2 class="text-lg font-medium text-gray-900 dark:text-white mb-2 leading-tight">Messages totaux</h2>
							<p class="text-3xl font-bold text-green-600 dark:text-green-400 leading-none">
								{formatNumber(statsData.global_indicators.total_messages)}
							</p>
						</div>
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<div class="flex items-start">
						<div class="flex-shrink-0">
							<div class="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
								<svg class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="currentColor" viewBox="0 0 20 20">
									<path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z"></path>
									<path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z"></path>
								</svg>
							</div>
						</div>
						<div class="ml-4 flex-1">
							<h2 class="text-lg font-medium text-gray-900 dark:text-white mb-2 leading-tight">Conversations totales</h2>
							<p class="text-3xl font-bold text-purple-600 dark:text-purple-400 leading-none">
								{formatNumber(statsData.global_indicators.total_conversations)}
							</p>
						</div>
					</div>
				</div>
			</div>

			<!-- Current Stats -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
				<!-- Active Users -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Utilisateurs actifs (24h)</h3>
					<div class="text-4xl font-bold text-blue-600 dark:text-blue-400 mb-2">
						{formatNumber(statsData.current_stats.active_users)}
					</div>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Utilisateurs connectés dans les dernières 24 heures
					</p>
				</div>

				<!-- Model Usage -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Répartition d'usage des modèles</h3>
					
					{#if statsData.current_stats.model_usage && Object.keys(statsData.current_stats.model_usage).length > 0}
						<div class="space-y-4">
							<!-- Chart -->
							<div class="h-64">
								<canvas id="modelUsageChart"></canvas>
							</div>
							
							<!-- Stats Table -->
							<div class="space-y-2">
								{#each Object.entries(statsData.current_stats.model_usage).sort(([,a], [,b]) => b - a) as [modelName, count]}
									{@const totalUsage = Object.values(statsData.current_stats.model_usage).reduce((a, b) => a + b, 0)}
									{@const percentage = totalUsage > 0 ? ((count / totalUsage) * 100).toFixed(1) : '0'}
									<div class="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
										<div class="flex-1">
											<div class="font-medium text-gray-900 dark:text-white text-sm">
												{modelName}
											</div>
											<div class="text-xs text-gray-500 dark:text-gray-400">
												{formatNumber(count)} messages • {percentage}%
											</div>
										</div>
										<div class="ml-4 text-right">
											<div class="w-16 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
												<div 
													class="bg-blue-500 h-2 rounded-full transition-all duration-300" 
													style="width: {percentage}%"
												></div>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{:else}
						<div class="text-center text-gray-500 dark:text-gray-400 py-8">
							Aucune donnée d'usage de modèle disponible
						</div>
					{/if}
				</div>
			</div>

			<!-- Evolution Charts -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Users Evolution -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<div class="mb-6">
						<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
							<h3 class="text-lg font-medium text-gray-900 dark:text-white">
								Évolution des utilisateurs (90 derniers jours)
							</h3>
							{#if statsData.evolution_stats.users_over_time.length > 0}
								{@const totalNewUsers = statsData.evolution_stats.users_over_time.reduce((sum, item) => sum + item.count, 0)}
								<span class="text-xs font-medium text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900 px-3 py-1.5 rounded-full whitespace-nowrap self-start sm:self-center">
									+ {formatNumber(totalNewUsers)} nouveaux utilisateurs
								</span>
							{/if}
						</div>
					</div>
					<div class="h-64">
						<canvas id="usersChart"></canvas>
					</div>
				</div>

				<!-- Conversations Evolution -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
					<div class="mb-6">
						<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
							<h3 class="text-lg font-medium text-gray-900 dark:text-white">
								Évolution des conversations (90 derniers jours)
							</h3>
							{#if statsData.evolution_stats.conversations_over_time.length > 0}
								{@const totalNewConversations = statsData.evolution_stats.conversations_over_time.reduce((sum, item) => sum + item.count, 0)}
								<span class="text-xs font-medium text-purple-600 dark:text-purple-400 bg-purple-100 dark:bg-purple-900 px-3 py-1.5 rounded-full whitespace-nowrap self-start sm:self-center">
									+ {formatNumber(totalNewConversations)} nouvelles conversations
								</span>
							{/if}
						</div>
					</div>
					<div class="h-64">
						<canvas id="conversationsChart"></canvas>
					</div>
				</div>
			</div>

			<!-- Footer with update info -->
			<div class="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
				<p>
					Données mises à jour en temps réel • 
					<button 
						on:click={loadStats}
						class="text-blue-600 dark:text-blue-400 hover:underline"
					>
						Actualiser
					</button>
				</p>
			</div>
		{:else}
			<div class="text-center py-12">
				<p class="text-gray-500 dark:text-gray-400">Aucune donnée disponible</p>
			</div>
		{/if}
	</div>
</div> 