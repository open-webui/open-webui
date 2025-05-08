<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import {
		getDomains,
		getModels,
		getTotalUsers,
		getDailyUsers,
		getTotalPrompts,
		getDailyPrompts,
		getTotalTokens,
		getDailyTokens,
		getHistoricalUsers,
		getHistoricalDailyUsers,
		getHistoricalPrompts,
		getHistoricalTokens,
		getModelPrompts,
		getModelDailyPrompts,
		getModelHistoricalPrompts,
		getRangeMetrics
	} from '$lib/apis/metrics';
	import { Chart, registerables } from 'chart.js';

	// Replace date-fns with native date formatting
	function formatDate(date) {
		return date.toISOString().split('T')[0]; // Returns YYYY-MM-DD format
	}

	// Register all Chart.js components
	Chart.register(...registerables);

	const i18n = getContext('i18n');
	let unsubscribe: () => void;

	// Data variables
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
	let enrolledUsersChart: any,
		dailyActiveUsersChart: any,
		dailyPromptsChart: any,
		dailyTokensChart: any;
	let modelPromptsChart: any;

	// Chart data
	let enrolledUsersData: any[] = [];
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

	// Function to update chart theme colors
	function updateChartThemeColors() {
		const isDark = document.documentElement.classList.contains('dark');
		const textColor = isDark ? '#e5e7eb' : '#1f2937';
		const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

		// Update chart options
		chartOptions.plugins.legend.labels.color = textColor;
		chartOptions.scales.x.ticks.color = textColor;
		chartOptions.scales.x.grid.color = gridColor;
		chartOptions.scales.y.ticks.color = textColor;
		chartOptions.scales.y.grid.color = gridColor;

		// Update existing charts with new theme colors
		const charts = [
			enrolledUsersChart,
			dailyActiveUsersChart,
			dailyPromptsChart,
			dailyTokensChart,
			modelPromptsChart
		];
		charts.forEach((chart) => {
			if (chart) {
				chart.options.plugins.legend.labels.color = textColor;
				chart.options.scales.x.ticks.color = textColor;
				chart.options.scales.x.grid.color = gridColor;
				chart.options.scales.y.ticks.color = textColor;
				chart.options.scales.y.grid.color = gridColor;
				chart.update();
			}
		});
	}

	// Update chart labels function
	function updateChartLabels() {
		if (enrolledUsersChart) {
			enrolledUsersChart.data.datasets[0].label = $i18n.t('Enrolled Users');
			enrolledUsersChart.update();
		}
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

	// Date range controls
	let dateRangeOptions = [
		{ value: '7days', label: $i18n.t('Last 7 Days') },
		{ value: '30days', label: $i18n.t('Last 30 Days') },
		{ value: '60days', label: $i18n.t('Last 60 Days') },
		{ value: '90days', label: $i18n.t('Last 90 Days') },
		{ value: 'custom', label: $i18n.t('Custom Range') }
	];
	let selectedDateRange = '7days';
	let startDate = formatDate(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000));
	let endDate = formatDate(new Date());
	let showCustomDateRange = false;

	// Advanced metrics
	let rangeMetrics = null;

	// Change default tab name from 'cost' to 'business' for clarity
	let activeTab = 'users'; // Changed from 'business' to 'users'

	// Helper function to calculate days between dates
	function calculateDaysFromDateRange(start, end) {
		if (start && end) {
			const startDate = new Date(start);
			const endDate = new Date(end);
			const daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
			return Math.max(daysDiff, 1); // Ensure at least 1 day
		}
		return 7; // Default to 7 days
	}

	// Function to update all charts with new data
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

			// Load summary metrics
			try {
				totalUsers = await getTotalUsers(localStorage.token, updatedDomain);
				totalPrompts = await getTotalPrompts(localStorage.token, updatedDomain);
				totalTokens = await getTotalTokens(localStorage.token, updatedDomain);
				dailyUsers = await getDailyUsers(localStorage.token, updatedDomain);
				dailyPrompts = await getDailyPrompts(localStorage.token, updatedDomain);
				dailyTokens = await getDailyTokens(localStorage.token, updatedDomain);
			} catch (err) {
				console.error('Error fetching summary metrics:', err);
			}

			// Load model-specific data if a model is selected
			if (selectedModel) {
				try {
					modelPrompts = await getModelPrompts(localStorage.token, selectedModel, updatedDomain);
					modelDailyPrompts = await getModelDailyPrompts(
						localStorage.token,
						selectedModel,
						updatedDomain
					);
				} catch (err) {
					console.error('Error fetching model metrics:', err);
				}
			}

			// Calculate days from date range
			const days = calculateDaysFromDateRange(startDate, endDate);

			// Fetch historical data for charts
			try {
				enrolledUsersData = await getHistoricalUsers(localStorage.token, days, updatedDomain);
				dailyActiveUsersData = await getHistoricalDailyUsers(
					localStorage.token,
					days,
					updatedDomain
				);
				dailyPromptsData = await getHistoricalPrompts(localStorage.token, days, updatedDomain);
				dailyTokensData = await getHistoricalTokens(localStorage.token, days, updatedDomain);

				// Fetch model-specific historical data if a model is selected
				if (selectedModel) {
					modelPromptsData = await getModelHistoricalPrompts(
						localStorage.token,
						days,
						selectedModel,
						updatedDomain
					);
				}
			} catch (err) {
				console.error('Error fetching historical data:', err);
			}

			// Initialize charts with the data
			setTimeout(() => {
				initializeCharts();
			}, 50);
		} catch (error) {
			console.error('Error updating charts:', error);
		}
	}

	// Initialize charts function
	function initializeCharts() {
		// Users chart - for both overview and users tabs
		if (activeTab === 'users' && dailyActiveUsersData.length > 0 && enrolledUsersData.length > 0) {
			// Enrolled Users Chart
			const enrolledChartId = 'userEnrollmentsOverTimeChart';
			const enrolledCanvas = document.getElementById(enrolledChartId);
			const enrolledCtx = enrolledCanvas?.getContext('2d');
			if (enrolledCtx) {
				if (enrolledUsersChart) {
					enrolledUsersChart.destroy();
				}
				enrolledUsersChart = new Chart(enrolledCtx, {
					type: 'line',
					data: {
						labels: enrolledUsersData.map((item) => item.date),
						datasets: [
							{
								label: $i18n.t('Enrolled Users'),
								data: enrolledUsersData.map((item) => item.count),
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

			// Daily Active Users Chart
			const dailyChartId = 'usersOverTimeChart';
			const dailyCanvas = document.getElementById(dailyChartId);
			const dailyCtx = dailyCanvas?.getContext('2d');
			if (dailyCtx) {
				if (dailyActiveUsersChart) {
					dailyActiveUsersChart.destroy();
				}
				dailyActiveUsersChart = new Chart(dailyCtx, {
					type: 'line',
					data: {
						labels: dailyActiveUsersData.map((item) => item.date),
						datasets: [
							{
								label: $i18n.t('Daily Active Users'),
								data: dailyActiveUsersData.map((item) => item.count),
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
		}

		// Prompts chart - for both overview and prompts tabs
		if ((activeTab === 'prompts' || activeTab === 'overview') && dailyPromptsData.length > 0) {
			const chartId = activeTab === 'overview' ? 'dailyPromptsChart' : 'promptsOverTimeChart';
			const canvas = document.getElementById(chartId);
			const ctx = canvas?.getContext('2d');
			if (ctx) {
				if (dailyPromptsChart) {
					dailyPromptsChart.destroy();
				}
				dailyPromptsChart = new Chart(ctx, {
					type: 'line',
					data: {
						labels: dailyPromptsData.map((item) => item.date),
						datasets: [
							{
								label: $i18n.t('Daily Prompts'),
								data: dailyPromptsData.map((item) => item.count),
								borderColor: 'rgb(16, 185, 129)',
								backgroundColor: 'rgba(16, 185, 129, 0.2)',
								borderWidth: 2,
								pointBackgroundColor: 'rgb(16, 185, 129)',
								pointBorderColor: '#fff',
								pointHoverBackgroundColor: '#fff',
								pointHoverBorderColor: 'rgb(16, 185, 129)',
								tension: 0.1
							}
						]
					},
					options: chartOptions
				});
			}
		}

		// Tokens chart - for tokens tab
		if (activeTab === 'tokens' && dailyTokensData.length > 0) {
			const canvas = document.getElementById('tokensOverTimeChart');
			const ctx = canvas?.getContext('2d');
			if (ctx) {
				if (dailyTokensChart) {
					dailyTokensChart.destroy();
				}
				dailyTokensChart = new Chart(ctx, {
					type: 'line',
					data: {
						labels: dailyTokensData.map((item) => item.date),
						datasets: [
							{
								label: $i18n.t('Daily Tokens'),
								data: dailyTokensData.map((item) => item.count),
								borderColor: 'rgb(220, 38, 38)',
								backgroundColor: 'rgba(220, 38, 38, 0.2)',
								borderWidth: 2,
								pointBackgroundColor: 'rgb(220, 38, 38)',
								pointBorderColor: '#fff',
								pointHoverBackgroundColor: '#fff',
								pointHoverBorderColor: 'rgb(220, 38, 38)',
								tension: 0.1
							}
						]
					},
					options: chartOptions
				});
			}
		}

		// Model chart - for models tab
		if (activeTab === 'models' && selectedModel && modelPromptsData.length > 0) {
			const canvas = document.getElementById('modelOverTimeChart');
			const ctx = canvas?.getContext('2d');
			if (ctx) {
				if (modelPromptsChart) {
					modelPromptsChart.destroy();
				}
				modelPromptsChart = new Chart(ctx, {
					type: 'line',
					data: {
						labels: modelPromptsData.map((item) => item.date),
						datasets: [
							{
								label: $i18n.t('Model Prompts'),
								data: modelPromptsData.map((item) => item.count),
								borderColor: 'rgb(124, 58, 237)',
								backgroundColor: 'rgba(124, 58, 237, 0.2)',
								borderWidth: 2,
								pointBackgroundColor: 'rgb(124, 58, 237)',
								pointBorderColor: '#fff',
								pointHoverBackgroundColor: '#fff',
								pointHoverBorderColor: 'rgb(124, 58, 237)',
								tension: 0.1
							}
						]
					},
					options: chartOptions
				});
			}
		}
	}

	// Improved setActiveTab function
	function setActiveTab(tab: string) {
		activeTab = tab;

		// Additional data loading for model-specific tab
		if (tab === 'models' && selectedModel) {
			getModelPrompts(localStorage.token, selectedModel, selectedDomain)
				.then((data) => {
					modelPrompts = data;
					return getModelDailyPrompts(localStorage.token, selectedModel, selectedDomain);
				})
				.then((data) => {
					modelDailyPrompts = data;
					// Use the existing date range when calculating model historical data
					const days = calculateDaysFromDateRange(startDate, endDate);
					return getModelHistoricalPrompts(localStorage.token, days, selectedModel, selectedDomain);
				})
				.then((data) => {
					modelPromptsData = data;
					initializeCharts();
				})
				.catch((error) => console.error('Error loading model data:', error));
		} else if (tab === 'business') {
			// Just update charts for now
			setTimeout(() => {
				initializeCharts();
			}, 100);
		} else {
			// Give time for DOM to update
			setTimeout(() => {
				initializeCharts();
			}, 100);
		}
	}

	function handleDateRangeChange(event) {
		const range = event.target.value;
		selectedDateRange = range;

		const today = new Date();

		if (range === '7days') {
			startDate = formatDate(new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000));
			endDate = formatDate(today);
			showCustomDateRange = false;
		} else if (range === '30days') {
			startDate = formatDate(new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000));
			endDate = formatDate(today);
			showCustomDateRange = false;
		} else if (range === '60days') {
			startDate = formatDate(new Date(today.getTime() - 60 * 24 * 60 * 60 * 1000));
			endDate = formatDate(today);
			showCustomDateRange = false;
		} else if (range === '90days') {
			startDate = formatDate(new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000));
			endDate = formatDate(today);
			showCustomDateRange = false;
		} else if (range === 'custom') {
			showCustomDateRange = true;
			// Don't reset the date values when switching to custom
		}

		updateRangeMetrics();
	}

	async function updateRangeMetrics() {
		try {
			rangeMetrics = await getRangeMetrics(
				localStorage.token,
				startDate,
				endDate,
				selectedDomain,
				selectedModel
			);
			// Remove costAnalysis fetch

			// Also update the chart data based on the selected date range
			await updateCharts(selectedDomain, selectedModel);
		} catch (error) {
			console.error('Error fetching range metrics:', error);
		}
	}

	onMount(async () => {
		try {
			// Subscribe to language changes
			unsubscribe = i18n.subscribe(() => {
				updateChartLabels();
			});

			// Add theme change observer
			const observer = new MutationObserver((mutations) => {
				mutations.forEach((mutation) => {
					if (
						mutation.type === 'attributes' &&
						mutation.attributeName === 'class' &&
						mutation.target === document.documentElement
					) {
						updateChartThemeColors();
					}
				});
			});

			observer.observe(document.documentElement, {
				attributes: true,
				attributeFilter: ['class']
			});

			domains = await getDomains(localStorage.token);
			models = await getModels(localStorage.token);

			// Set the first model as the selected model if available
			if (models.length > 0) {
				selectedModel = models[0];
			}

			await updateCharts(selectedDomain, selectedModel);
			updateRangeMetrics(); // Load initial range metrics

			// Store the observer in a variable for cleanup
			return () => observer.disconnect();
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
		if (enrolledUsersChart) enrolledUsersChart.destroy();
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

<div class="flex flex-col h-screen">
	<div class="p-4 lg:p-6 flex-shrink-0">
		<div class="mb-4 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
			<h2 class="text-2xl font-extrabold text-gray-900 dark:text-gray-100">
				{$i18n.t('Metrics Dashboard')}
			</h2>
			<!-- Date Range Controls -->
			<div class="flex flex-wrap items-center gap-3">
				<div>
					<label
						class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
						for="date-range-select"
					>
						{$i18n.t('Date Range')}
					</label>
					<select
						id="date-range-select"
						bind:value={selectedDateRange}
						on:change={handleDateRangeChange}
						class="block w-36 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
					>
						{#each dateRangeOptions as option}
							<option value={option.value}>{$i18n.t(option.label)}</option>
						{/each}
					</select>
				</div>
				{#if showCustomDateRange}
					<div>
						<label
							class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
							for="start-date"
						>
							{$i18n.t('Start Date')}
						</label>
						<input
							type="date"
							id="start-date"
							bind:value={startDate}
							max={formatDate(new Date())}
							required
							on:change={updateRangeMetrics}
							class="block w-40 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
						/>
					</div>
					<div>
						<label
							class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
							for="end-date"
						>
							{$i18n.t('End Date')}
						</label>
						<input
							type="date"
							id="end-date"
							bind:value={endDate}
							max={formatDate(new Date())}
							min={startDate}
							required
							on:change={updateRangeMetrics}
							class="block w-40 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
						/>
					</div>
				{/if}
				<!-- Domain Selector -->
				<div>
					<label
						class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
						for="domain-select"
					>
						{$i18n.t('Select Domain:')}
					</label>
					<select
						id="domain-select"
						bind:value={selectedDomain}
						on:change={(e) => {
							handleDomainChange(e);
							updateRangeMetrics();
						}}
						class="block w-36 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
					>
						<option value={null}>{$i18n.t('All')}</option>
						{#each domains as domain}
							<option value={domain}>{domain}</option>
						{/each}
					</select>
				</div>
				<!-- Model Selector (shown only on models tab) -->
				{#if activeTab === 'models'}
					<div>
						<label
							class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
							for="model-select"
						>
							{$i18n.t('Select Model:')}
						</label>
						<select
							id="model-select"
							bind:value={selectedModel}
							on:change={(e) => {
								handleModelChange(e);
								updateRangeMetrics();
							}}
							class="block w-36 p-2 text-sm border border-gray-400 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-200"
						>
							{#each models as model}
								<option value={model}>{model}</option>
							{/each}
						</select>
					</div>
				{/if}
			</div>
		</div>

		<!-- Enhanced Tab Navigation - Rename Cost Analysis to Business Insights -->
		<div class="border-b border-gray-300 dark:border-gray-700">
			<ul
				class="flex flex-wrap -mb-px text-sm font-medium text-center text-gray-700 dark:text-gray-300"
			>
				<li class="mr-2">
					<button
						class={`inline-block p-4 rounded-t-lg border-b-2 ${
							activeTab === 'users'
								? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-500'
								: 'border-transparent hover:text-gray-900 hover:border-gray-300 dark:hover:text-gray-100'
						}`}
						on:click={() => setActiveTab('users')}
					>
						{$i18n.t('Users')}
					</button>
				</li>
				<li class="mr-2">
					<button
						class={`inline-block p-4 rounded-t-lg border-b-2 ${
							activeTab === 'prompts'
								? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-500'
								: 'border-transparent hover:text-gray-900 hover:border-gray-300 dark:hover:text-gray-100'
						}`}
						on:click={() => setActiveTab('prompts')}
					>
						{$i18n.t('Prompts')}
					</button>
				</li>
				<li class="mr-2">
					<button
						class={`inline-block p-4 rounded-t-lg border-b-2 ${
							activeTab === 'tokens'
								? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-500'
								: 'border-transparent hover:text-gray-900 hover:border-gray-300 dark:hover:text-gray-100'
						}`}
						on:click={() => setActiveTab('tokens')}
					>
						{$i18n.t('Tokens')}
					</button>
				</li>
				<li class="mr-2">
					<button
						class={`inline-block p-4 rounded-t-lg border-b-2 ${
							activeTab === 'models'
								? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-500'
								: 'border-transparent hover:text-gray-900 hover:border-gray-300 dark:hover:text-gray-100'
						}`}
						on:click={() => setActiveTab('models')}
					>
						{$i18n.t('Model Analysis')}
					</button>
				</li>
				<!-- Business Insights tab hidden for now
				<li class="mr-2">
					<button
						class={`inline-block p-4 rounded-t-lg border-b-2 ${
							activeTab === 'business'
								? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-500'
								: 'border-transparent hover:text-gray-900 hover:border-gray-300 dark:hover:text-gray-100'
						}`}
						on:click={() => setActiveTab('business')}
					>
						{$i18n.t('Business Insights')}
					</button>
				</li>
				-->
			</ul>
		</div>

		<!-- Tab Content Container - Takes up remaining height -->
		<div class="flex-grow overflow-hidden">
			<!-- Tab Content - Users -->
			<div class={`${activeTab === 'users' ? 'flex flex-col h-full' : 'hidden'}`}>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 mt-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Total Users')}
						</h5>
						<h4 class="text-3xl font-bold text-blue-700 dark:text-blue-400">{totalUsers}</h4>
						<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
							{$i18n.t('Total number of registered users')}
						</div>
					</div>
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Daily Active Users')}
						</h5>
						<h4 class="text-3xl font-bold text-blue-700 dark:text-blue-400">{dailyUsers}</h4>
						<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
							{$i18n.t('Number of users active in the last 24 hours')}
						</div>
					</div>
				</div>
				<div class="grid grid-cols-1 gap-6 mb-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('User Enrollments Over Time')}
						</h5>
						<div class="h-80">
							<canvas id="userEnrollmentsOverTimeChart"></canvas>
						</div>
					</div>
				</div>
				<div class="grid grid-cols-1 gap-6 mb-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Daily Active Users Over Time')}
						</h5>
						<div class="h-80">
							<canvas id="usersOverTimeChart"></canvas>
						</div>
					</div>
				</div>
			</div>

			<!-- Tab Content - Prompts -->
			<div class={`${activeTab === 'prompts' ? 'flex flex-col h-full' : 'hidden'}`}>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 mt-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Total Prompts')}
						</h5>
						<h4 class="text-3xl font-bold text-green-700 dark:text-green-400">{totalPrompts}</h4>
						<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
							{$i18n.t('Total number of prompts submitted')}
						</div>
					</div>
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Daily Prompts')}
						</h5>
						<h4 class="text-3xl font-bold text-green-700 dark:text-green-400">{dailyPrompts}</h4>
						<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
							{$i18n.t('Number of prompts sent in the last 24 hours')}
						</div>
					</div>
				</div>
				<div class="grid grid-cols-1 gap-6 mb-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Daily Prompts Over Time')}
						</h5>
						<div class="h-80">
							<canvas id="promptsOverTimeChart"></canvas>
						</div>
					</div>
				</div>
			</div>

			<!-- Tab Content - Tokens -->
			<div class={`${activeTab === 'tokens' ? 'flex flex-col h-full' : 'hidden'}`}>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 mt-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Total Tokens')}
						</h5>
						<h4 class="text-3xl font-bold text-red-700 dark:text-red-400">{totalTokens}</h4>
						<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
							{$i18n.t('Total number of tokens used')}
						</div>
					</div>
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Daily Tokens')}
						</h5>
						<h4 class="text-3xl font-bold text-red-700 dark:text-red-400">{dailyTokens}</h4>
						<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
							{$i18n.t('Number of tokens used in the last 24 hours')}
						</div>
					</div>
				</div>
				<div class="grid grid-cols-1 gap-6 mb-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Daily Tokens Over Time')}
						</h5>
						<div class="h-80">
							<canvas id="tokensOverTimeChart"></canvas>
						</div>
					</div>
				</div>
			</div>

			<!-- Tab Content - Model Analysis -->
			<div class={`${activeTab === 'models' ? 'flex flex-col h-full' : 'hidden'}`}>
				{#if models.length === 0}
					<div
						class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800 flex items-center justify-center h-64 mt-6"
					>
						<div class="text-center">
							<p class="text-xl text-gray-500 dark:text-gray-400 mb-4">
								{$i18n.t('No models found')}
							</p>
						</div>
					</div>
				{:else if selectedModel}
					<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 mt-6">
						<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
							<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
								{$i18n.t('Total Model Prompts')}
							</h5>
							<h4 class="text-3xl font-bold text-purple-700 dark:text-purple-400">
								{modelPrompts}
							</h4>
							<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
								{$i18n.t('Total prompts processed by this model')}
							</div>
						</div>
						<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
							<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
								{$i18n.t('Daily Model Prompts')}
							</h5>
							<h4 class="text-3xl font-bold text-purple-700 dark:text-purple-400">
								{modelDailyPrompts}
							</h4>
							<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
								{$i18n.t('Prompts processed by this model in the last 24 hours')}
							</div>
						</div>
					</div>

					<div class="grid grid-cols-1 gap-6 mb-6">
						<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
							<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
								{$i18n.t('Daily Model Usage')} - {selectedModel}
							</h5>
							<div class="h-80">
								<canvas id="modelOverTimeChart"></canvas>
							</div>
						</div>
					</div>
				{:else}
					<div
						class="bg-white shadow-lg rounded-lg p-6 dark:bg-gray-800 flex items-center justify-center h-64 mt-6"
					>
						<div class="text-center">
							<p class="text-xl text-gray-500 dark:text-gray-400 mb-4">
								{$i18n.t('No model selected')}
							</p>
							<p class="text-gray-600 dark:text-gray-400">
								{$i18n.t('Please select a model from the dropdown to view model-specific metrics')}
							</p>
						</div>
					</div>
				{/if}
			</div>

			<!-- Replace Cost Analysis Tab Content with Business Insights in matching style -->
			<div class={`${activeTab === 'business' ? 'flex flex-col h-full' : 'hidden'}`}>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 mt-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Cost Analysis')}
						</h5>
						<h4 class="text-3xl font-bold text-indigo-700 dark:text-indigo-400">
							{$i18n.t('Coming Soon')}
						</h4>
						<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
							{$i18n.t('Analyze AI spending patterns and model efficiency')}
						</div>
					</div>
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Usage Trends')}
						</h5>
						<h4 class="text-3xl font-bold text-indigo-700 dark:text-indigo-400">
							{$i18n.t('Coming Soon')}
						</h4>
						<div class="text-sm text-gray-600 dark:text-gray-400 mt-2">
							{$i18n.t('Track key performance indicators over time')}
						</div>
					</div>
				</div>
				<div class="grid grid-cols-1 gap-6 mb-6">
					<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
						<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
							{$i18n.t('Business Intelligence')}
						</h5>
						<div class="flex flex-col items-center justify-center h-80 text-center">
							<div class="mb-4">
								<svg
									class="w-16 h-16 text-indigo-500 mx-auto"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
									></path>
								</svg>
							</div>
							<p class="text-gray-600 dark:text-gray-400 max-w-lg">
								{$i18n.t(
									"We're working on advanced analytics features to help you understand and optimize your AI usage patterns."
								)}
							</p>
							<p class="text-gray-600 dark:text-gray-400 max-w-lg mt-4">
								{$i18n.t(
									'This feature will provide detailed breakdowns by model, cost analysis, and usage trends to help manage your AI budget effectively.'
								)}
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
