<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { Chart } from 'chart.js';
	import {
		CategoryScale,
		LinearScale,
		PointElement,
		LineElement,
		LineController,
		Title,
		Tooltip,
		Legend
	} from 'chart.js';
	import {
		getDailyPrompts,
		getDailyTokens,
		getDailyUsers,
		getDomains,
		getHistoricalPrompts,
		getHistoricalTokens,
		getHistoricalUsers,
		getTotalPrompts,
		getTotalTokens,
		getTotalUsers,
		getModels,
		getModelPrompts,
		getModelDailyPrompts,
		getModelHistoricalPrompts
	} from '$lib/apis/metrics';

	// Register the Chart.js components
	Chart.register(
		CategoryScale,
		LinearScale,
		PointElement,
		LineElement,
		LineController,
		Title,
		Tooltip,
		Legend
	);

	const i18n = getContext('i18n');
	let unsubscribe: () => void;

	let domains: string[] = [];
	let models: string[] = [];
	let totalUsers: number = 0,
		totalPrompts: number = 0,
		totalTokens: number = 0,
		dailyUsers: number = 0,
		dailyPrompts: number = 0,
		dailyTokens: number = 0;
	let selectedDomain: string | null = null; // Allow null for "no domain"
	let selectedModel: string | null = null; // Allow null for "no model"

	// Model specific metrics
	let modelPrompts: number = 0,
		modelDailyPrompts: number = 0;

	// Chart objects
	let dailyActiveUsersChart: any, dailyPromptsChart: any, dailyTokensChart: any;
	let modelPromptsChart: any;

	// Chart data
	let dailyActiveUsersData: any[] = [];
	let dailyPromptsData: any[] = [];
	let dailyTokensData: any[] = [];
	let modelPromptsData: any[] = [];

	// For chart options
	const chartOptions = {
		responsive: true,
		maintainAspectRatio: false,
		plugins: {
			legend: {
				display: true,
				labels: {
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937'
				},
				onClick: null, // Disable the default click behavior
				onHover: null // Also disable hover state changes
			},
			tooltip: {
				mode: 'index',
				intersect: false
			}
		},
		scales: {
			x: {
				ticks: {
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937'
				},
				grid: {
					color: document.documentElement.classList.contains('dark')
						? 'rgba(255, 255, 255, 0.1)'
						: 'rgba(0, 0, 0, 0.1)'
				}
			},
			y: {
				beginAtZero: true,
				ticks: {
					color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937'
				},
				grid: {
					color: document.documentElement.classList.contains('dark')
						? 'rgba(255, 255, 255, 0.1)'
						: 'rgba(0, 0, 0, 0.1)'
				}
			}
		}
	};

	async function updateCharts(selectedDomain: string | null, selectedModel: string | null) {
		try {
			let updatedDomain = selectedDomain ?? undefined;
			let updatedModel = selectedModel ?? undefined;

			// Reset all data to ensure no stale values
			totalUsers = 0;
			totalPrompts = 0;
			totalTokens = 0;
			dailyUsers = 0;
			dailyPrompts = 0;
			dailyTokens = 0;
			modelPrompts = 0;
			modelDailyPrompts = 0;

			// Fetch simple metrics
			try {
				totalUsers = await getTotalUsers(localStorage.token, updatedDomain);
				totalPrompts = await getTotalPrompts(localStorage.token, updatedDomain);
				dailyUsers = await getDailyUsers(localStorage.token, updatedDomain);
				totalTokens = await getTotalTokens(localStorage.token, updatedDomain);
				dailyPrompts = await getDailyPrompts(localStorage.token, updatedDomain);
				dailyTokens = await getDailyTokens(localStorage.token, updatedDomain);

				// Only fetch model metrics if a model is selected
				if (updatedModel) {
					modelPrompts = await getModelPrompts(localStorage.token, updatedModel, updatedDomain);
					modelDailyPrompts = await getModelDailyPrompts(
						localStorage.token,
						updatedModel,
						updatedDomain
					);
				}
			} catch (metricsError) {
				console.error('Error fetching basic metrics:', metricsError);
			}

			// Set default empty data
			const datesArray = Array.from({ length: 7 }, (_, i) => {
				const date = new Date();
				date.setDate(date.getDate() - (6 - i));
				return date.toISOString().split('T')[0];
			});

			// Set default empty data
			dailyActiveUsersData = datesArray.map((date) => ({ date, count: 0 }));
			dailyPromptsData = datesArray.map((date) => ({ date, count: 0 }));
			dailyTokensData = datesArray.map((date) => ({ date, count: 0 }));
			modelPromptsData = datesArray.map((date) => ({ date, count: 0 }));

			try {
				// Try to fetch historical data, but the API client will provide fallbacks if needed
				dailyActiveUsersData = await getHistoricalUsers(localStorage.token, 7, updatedDomain);
				dailyPromptsData = await getHistoricalPrompts(localStorage.token, 7, updatedDomain);
				dailyTokensData = await getHistoricalTokens(localStorage.token, 7, updatedDomain);

				// Only fetch model historical data if a model is selected
				if (updatedModel) {
					modelPromptsData = await getModelHistoricalPrompts(
						localStorage.token,
						7,
						updatedModel,
						updatedDomain
					);
				}
			} catch (histError) {
				console.error('Error fetching historical data:', histError);
				// Fallback data is already set above
			}

			// Reinitialize charts completely rather than updating
			initializeCharts();
		} catch (error) {
			console.error('Error updating charts:', error);
		}
	}

	// Ensure charts are properly initialized after data is loaded
	function initializeCharts() {
		// Initialize charts
		const isDarkMode = document.documentElement.classList.contains('dark');
		const lineColor = isDarkMode ? '#e5e7eb' : '#1f2937';

		// Initialize User Chart
		const ctx1 = document.getElementById('dailyActiveUsersChart')?.getContext('2d');
		if (ctx1) {
			// Always destroy existing chart before creating a new one
			if (dailyActiveUsersChart) {
				dailyActiveUsersChart.destroy();
			}

			dailyActiveUsersChart = new Chart(ctx1, {
				type: 'line',
				data: {
					labels: dailyActiveUsersData.map((item) => item.date),
					datasets: [
						{
							label: $i18n.t('Daily Active Users'),
							data: dailyActiveUsersData.map((item) => item.count),
							borderColor: 'rgb(59, 130, 246)',
							backgroundColor: 'rgba(59, 130, 246, 0.2)',
							borderWidth: 2,
							pointBackgroundColor: 'rgb(59, 130, 246)',
							pointBorderColor: '#fff',
							pointHoverBackgroundColor: '#fff',
							pointHoverBorderColor: 'rgb(59, 130, 246)',
							tension: 0.1
						}
					]
				},
				options: chartOptions
			});
		}

		// Initialize Prompts Chart
		const ctx2 = document.getElementById('dailyPromptsChart')?.getContext('2d');
		if (ctx2) {
			// Always destroy existing chart before creating a new one
			if (dailyPromptsChart) {
				dailyPromptsChart.destroy();
			}

			dailyPromptsChart = new Chart(ctx2, {
				type: 'line',
				data: {
					labels: dailyPromptsData.map((item) => item.date),
					datasets: [
						{
							label: $i18n.t('Daily Prompts'),
							data: dailyPromptsData.map((item) => item.count),
							borderColor: 'rgb(34, 197, 94)',
							backgroundColor: 'rgba(34, 197, 94, 0.2)',
							borderWidth: 2,
							pointBackgroundColor: 'rgb(34, 197, 94)',
							pointBorderColor: '#fff',
							pointHoverBackgroundColor: '#fff',
							pointHoverBorderColor: 'rgb(34, 197, 94)',
							tension: 0.1
						}
					]
				},
				options: chartOptions
			});
		}

		// Initialize Tokens Chart
		const ctx3 = document.getElementById('dailyTokensChart')?.getContext('2d');
		if (ctx3) {
			// Always destroy existing chart before creating a new one
			if (dailyTokensChart) {
				dailyTokensChart.destroy();
			}

			dailyTokensChart = new Chart(ctx3, {
				type: 'line',
				data: {
					labels: dailyTokensData.map((item) => item.date),
					datasets: [
						{
							label: $i18n.t('Daily Tokens'),
							data: dailyTokensData.map((item) => item.count),
							borderColor: 'rgb(239, 68, 68)',
							backgroundColor: 'rgba(239, 68, 68, 0.2)',
							borderWidth: 2,
							pointBackgroundColor: 'rgb(239, 68, 68)',
							pointBorderColor: '#fff',
							pointHoverBackgroundColor: '#fff',
							pointHoverBorderColor: 'rgb(239, 68, 68)',
							tension: 0.1
						}
					]
				},
				options: chartOptions
			});
		}

		// Initialize Model Prompts Chart (only if a model is selected)
		if (selectedModel) {
			const ctx4 = document.getElementById('modelPromptsChart')?.getContext('2d');
			if (ctx4) {
				// Always destroy existing chart before creating a new one
				if (modelPromptsChart) {
					modelPromptsChart.destroy();
				}

				modelPromptsChart = new Chart(ctx4, {
					type: 'line',
					data: {
						labels: modelPromptsData.map((item) => item.date),
						datasets: [
							{
								label: $i18n.t('Model Prompts'),
								data: modelPromptsData.map((item) => item.count),
								borderColor: 'rgb(147, 51, 234)', // Purple for model data
								backgroundColor: 'rgba(147, 51, 234, 0.2)',
								borderWidth: 2,
								pointBackgroundColor: 'rgb(147, 51, 234)',
								pointBorderColor: '#fff',
								pointHoverBackgroundColor: '#fff',
								pointHoverBorderColor: 'rgb(147, 51, 234)',
								tension: 0.1
							}
						]
					},
					options: chartOptions
				});
			}
		}
	}

	// Function to update chart labels when language changes
	function updateChartLabels() {
		if (dailyActiveUsersChart) {
			dailyActiveUsersChart.data.datasets[0].label = $i18n.t('Daily Active Users');
			dailyActiveUsersChart.update();
		}

		if (dailyPromptsChart) {
			dailyPromptsChart.data.datasets[0].label = $i18n.t('Daily Prompts');
			dailyPromptsChart.update();
		}

		if (dailyTokensChart) {
			dailyTokensChart.data.datasets[0].label = $i18n.t('Daily Tokens');
			dailyTokensChart.update();
		}

		if (modelPromptsChart) {
			modelPromptsChart.data.datasets[0].label = $i18n.t('Model Prompts');
			modelPromptsChart.update();
		}
	}

	onMount(async () => {
		try {
			// Subscribe to language changes
			unsubscribe = i18n.subscribe(() => {
				updateChartLabels();
			});

			domains = await getDomains(localStorage.token);
			models = await getModels(localStorage.token);
			await updateCharts(selectedDomain, selectedModel);
		} catch (error) {
			console.error('Error initializing charts:', error);
		}
	});

	onDestroy(() => {
		// Clean up subscription when component is destroyed
		if (unsubscribe) {
			unsubscribe();
		}

		// Clean up charts
		if (dailyActiveUsersChart) dailyActiveUsersChart.destroy();
		if (dailyPromptsChart) dailyPromptsChart.destroy();
		if (dailyTokensChart) dailyTokensChart.destroy();
		if (modelPromptsChart) modelPromptsChart.destroy();
	});

	// Update domain change handler to simplify
	function handleDomainChange(event) {
		const newDomain = event.target.value || null;
		selectedDomain = newDomain;
		updateCharts(selectedDomain, selectedModel);
	}

	// Handler for model selection changes
	function handleModelChange(event) {
		const newModel = event.target.value || null;
		selectedModel = newModel;
		updateCharts(selectedDomain, selectedModel);
	}
</script>

<div class="container mx-auto p-6">
	<div class="mb-4 flex justify-between items-center">
		<h2 class="text-3xl font-extrabold text-gray-900 dark:text-gray-100">
			{$i18n.t('Metrics Dashboard')}
		</h2>
		<div class="flex items-center space-x-4">
			<div>
				<label
					for="domain-select"
					class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
					>{$i18n.t('Select Domain:')}</label
				>
				<select
					id="domain-select"
					bind:value={selectedDomain}
					on:change={handleDomainChange}
					class="block w-48 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
				>
					<option value={null}>{$i18n.t('All')}</option>
					{#each domains as domain}
						<option value={domain}>{domain}</option>
					{/each}
				</select>
			</div>
			<div>
				<label
					for="model-select"
					class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
					>{$i18n.t('Select Model:')}</label
				>
				<select
					id="model-select"
					bind:value={selectedModel}
					on:change={handleModelChange}
					class="block w-48 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
				>
					<option value={null}>{$i18n.t('None')}</option>
					{#each models as model}
						<option value={model}>{model}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	<div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
				{$i18n.t('Total Users')}
			</h5>
			<h4 class="text-3xl font-bold text-blue-700 dark:text-blue-400">{totalUsers}</h4>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
				{$i18n.t('Total Prompts')}
			</h5>
			<h4 class="text-3xl font-bold text-green-700 dark:text-green-400">{totalPrompts}</h4>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
				{$i18n.t('Total Tokens')}
			</h5>
			<h4 class="text-3xl font-bold text-red-700 dark:text-red-400">{totalTokens}</h4>
		</div>
	</div>

	<div class="mb-10">
		<div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
					{$i18n.t('Daily Users')}
				</h5>
				<h4 class="text-3xl font-bold text-blue-700 dark:text-blue-400">{dailyUsers}</h4>
			</div>
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
					{$i18n.t('Daily Prompts')}
				</h5>
				<h4 class="text-3xl font-bold text-green-700 dark:text-green-400">{dailyPrompts}</h4>
			</div>
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
					{$i18n.t('Daily Tokens')}
				</h5>
				<h4 class="text-3xl font-bold text-red-700 dark:text-red-400">{dailyTokens}</h4>
			</div>
		</div>
	</div>

	<hr class="border-gray-400 dark:border-gray-600 my-8" />

	<div class="space-y-8">
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				{$i18n.t('Daily Active Users')}
			</h5>
			<div class="h-64">
				<canvas id="dailyActiveUsersChart"></canvas>
			</div>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				{$i18n.t('Daily Prompts Sent')}
			</h5>
			<div class="h-64">
				<canvas id="dailyPromptsChart"></canvas>
			</div>
		</div>
		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				{$i18n.t('Daily Tokens Used')}
			</h5>
			<div class="h-64">
				<canvas id="dailyTokensChart"></canvas>
			</div>
		</div>
	</div>

	<!-- Model usage section (only shown when a model is selected) -->
	{#if selectedModel}
		<hr class="border-gray-400 dark:border-gray-600 my-8" />

		<h3 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
			{$i18n.t('Model Usage')} - {selectedModel}
		</h3>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
					{$i18n.t('Total Model Prompts')}
				</h5>
				<h4 class="text-3xl font-bold text-purple-700 dark:text-purple-400">{modelPrompts}</h4>
			</div>
			<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800">
				<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
					{$i18n.t('Daily Model Prompts')}
				</h5>
				<h4 class="text-3xl font-bold text-purple-700 dark:text-purple-400">{modelDailyPrompts}</h4>
			</div>
		</div>

		<div class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800 mb-8">
			<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
				{$i18n.t('Daily Model Prompts')}
			</h5>
			<div class="h-64">
				<canvas id="modelPromptsChart"></canvas>
			</div>
		</div>
	{/if}
</div>
