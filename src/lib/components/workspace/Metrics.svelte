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
		getRangeMetrics,
		getInterPromptLatencyHistogram,
		exportMetricsData,
		getExportLogs
	} from '$lib/apis/metrics';
	import { Chart, registerables } from 'chart.js';
	import { user } from '$lib/stores';

	// Replace date-fns with native date formatting
	function formatDate(date) {
		return date.toISOString().split('T')[0]; // Returns YYYY-MM-DD format
	}

	// Register all Chart.js components
	Chart.register(...registerables);

	const i18n = getContext('i18n');
	let unsubscribe: () => void;
	let componentLoaded = false;

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

	// Export functionality variables
	let isExporting = false;
	let exportLogs: any[] = [];
	let showExportLogs = false;

	// Model specific metrics
	let modelPrompts: number = 0,
		modelDailyPrompts: number = 0;

	// Chart objects
	let enrolledUsersChart: any,
		dailyActiveUsersChart: any,
		dailyPromptsChart: any,
		dailyTokensChart: any;
	let modelPromptsChart: any;
	let interPromptLatencyChart: any;

	// Chart data
	let enrolledUsersData: any[] = [];
	let dailyActiveUsersData: any[] = [];
	let dailyPromptsData: any[] = [];
	let dailyTokensData: any[] = [];
	let modelPromptsData: any[] = [];
	let interPromptLatencyData: any = { bins: [], counts: [], total_latencies: 0 };

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
			modelPromptsChart,
			interPromptLatencyChart
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

		if (interPromptLatencyChart) {
			interPromptLatencyChart.data.datasets[0].label = $i18n.t('Number of Prompts');
			interPromptLatencyChart.options.scales.x.title.text = $i18n.t(
				'Time Between Prompts (logarithmic scale)'
			);
			interPromptLatencyChart.options.scales.y.title.text = $i18n.t('Number of Prompts');
			interPromptLatencyChart.update();
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

	// Check if user is an analyst with domain restrictions
	$: isAnalyst = $user?.role === 'analyst';

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

				// Fetch inter-prompt latency data (don't filter by model since this is a user behavior metric)
				interPromptLatencyData = await getInterPromptLatencyHistogram(
					localStorage.token,
					updatedDomain,
					null // Don't filter by model for inter-prompt latency
				);
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

		// Inter-prompt latency histogram - for behavior tab
		if (activeTab === 'behavior' && interPromptLatencyData.counts.length > 0) {
			const canvas = document.getElementById('interPromptLatencyChart');
			const ctx = canvas?.getContext('2d');
			if (ctx) {
				if (interPromptLatencyChart) {
					interPromptLatencyChart.destroy();
				}
				interPromptLatencyChart = new Chart(ctx, {
					type: 'bar',
					data: {
						labels: interPromptLatencyData.bins,
						datasets: [
							{
								label: $i18n.t('Number of Prompts'),
								data: interPromptLatencyData.counts,
								backgroundColor: 'rgba(147, 51, 234, 0.7)',
								borderColor: 'rgb(147, 51, 234)',
								borderWidth: 1
							}
						]
					},
					options: {
						...chartOptions,
						scales: {
							...chartOptions.scales,
							x: {
								...chartOptions.scales.x,
								type: 'category',
								title: {
									display: true,
									text: $i18n.t('Time Between Prompts (logarithmic scale)'),
									color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937'
								}
							},
							y: {
								...chartOptions.scales.y,
								title: {
									display: true,
									text: $i18n.t('Number of Prompts'),
									color: document.documentElement.classList.contains('dark') ? '#e5e7eb' : '#1f2937'
								}
							}
						},
						plugins: {
							...chartOptions.plugins,
							tooltip: {
								callbacks: {
									label: function (context) {
										const count = context.parsed.y;
										const total = interPromptLatencyData.total_latencies;
										const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
										return `${context.dataset.label}: ${count} (${percentage}%)`;
									}
								}
							}
						}
					}
				});
			}
		} else if (activeTab === 'behavior') {
			// Chart not created - no data or wrong tab
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
		} else if (tab === 'behavior') {
			// Load inter-prompt latency data and update charts
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
			startDate = formatDate(new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000));
			endDate = formatDate(today);
			showCustomDateRange = false;
		} else if (range === '30days') {
			startDate = formatDate(new Date(today.getTime() - 29 * 24 * 60 * 60 * 1000));
			endDate = formatDate(today);
			showCustomDateRange = false;
		} else if (range === '60days') {
			startDate = formatDate(new Date(today.getTime() - 59 * 24 * 60 * 60 * 1000));
			endDate = formatDate(today);
			showCustomDateRange = false;
		} else if (range === '90days') {
			startDate = formatDate(new Date(today.getTime() - 89 * 24 * 60 * 60 * 1000));
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

			// For analyst role, automatically select their domain and don't allow changing it
			if (isAnalyst && $user?.email) {
				selectedDomain = $user.email.split('@')[1];
			}

			// Get models based on user role
			models = await getModels(localStorage.token);

			// Note: For analysts, the models list shows all available models
			// but the actual metrics data will be filtered by domain in the API calls
			// This allows analysts to see what models are available for selection

			// Set the first model as the selected model if available
			if (models.length > 0) {
				selectedModel = models[0];
			}

			await updateCharts(selectedDomain, selectedModel);
			updateRangeMetrics(); // Load initial range metrics

			// Mark component as loaded
			componentLoaded = true;

			// Store the observer in a variable for cleanup
			return () => observer.disconnect();
		} catch (error) {
			console.error('Error initializing charts:', error);
			// Even if there's an error, mark as loaded to show the UI
			componentLoaded = true;
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
		if (interPromptLatencyChart) interPromptLatencyChart.destroy();
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

	// Export functionality

	async function handleExportData() {
		// Validate that we have valid dates
		if (!startDate || !endDate) {
			alert($i18n.t('Please select both start and end dates'));
			return;
		}

		// Check if date range exceeds 90 days (using same logic as backend)
		const start = new Date(startDate);
		const end = new Date(endDate);
		const diffDays = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1; // +1 to include both start and end days

		if (diffDays > 90) {
			alert($i18n.t('Date range cannot exceed 90 days. Please select a shorter range.'));
			return;
		}

		isExporting = true;
		try {
			// For analysts, always use their domain regardless of selectedDomain
			const exportDomain = $user?.role === 'analyst' ? $user?.email?.split('@')[1] : selectedDomain;

			const blob = await exportMetricsData(localStorage.token, startDate, endDate, exportDomain);

			// Create download link
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `metrics_export_${startDate}_to_${endDate}.csv`;
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);

			// Refresh export logs (for admin, global_analyst, and analyst users)
			if (
				$user?.role === 'admin' ||
				$user?.role === 'global_analyst' ||
				$user?.role === 'analyst'
			) {
				await loadExportLogs();
			}
		} catch (error) {
			console.error('Export failed:', error);
			alert($i18n.t('Export failed. Please try again.'));
		} finally {
			isExporting = false;
		}
	}

	async function loadExportLogs() {
		try {
			exportLogs = await getExportLogs(localStorage.token);
		} catch (error) {
			console.error('Failed to load export logs:', error);
		}
	}

	function openExportLogs() {
		showExportLogs = true;
		loadExportLogs();
	}

	function closeExportLogs() {
		showExportLogs = false;
	}

	// Check if user can export (admin, global_analyst, or analyst)
	$: canExport =
		$user?.role === 'admin' || $user?.role === 'global_analyst' || $user?.role === 'analyst';
</script>

{#if componentLoaded && $user}
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
					<!-- Domain Selector with better visibility for analyst's domain -->
					<div>
						<label
							class="block text-sm font-medium text-gray-800 dark:text-gray-200 mb-2"
							for="domain-select"
						>
							{#if isAnalyst}
								{$i18n.t('Your Domain:')}
							{:else}
								{$i18n.t('Select Domain:')}
							{/if}
						</label>
						{#if isAnalyst}
							<!-- For analysts, show a static display with their domain -->
							<div
								class="block w-52 p-2 text-sm border border-gray-400 bg-gray-100 dark:bg-gray-700 rounded-md shadow-sm dark:text-gray-200"
							>
								{$user?.email?.split('@')[1] || $i18n.t('Loading...')}
							</div>
						{:else}
							<!-- For admins and global analysts, show the domain selector -->
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
									<option value={domain}>
										{domain}
									</option>
								{/each}
							</select>
						{/if}
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
					<!-- Export Data Button (for admin, global_analyst, and analyst) -->
					{#if canExport}
						<div class="flex flex-col">
							<div class="flex items-center gap-2 mt-6">
								<button
									on:click={handleExportData}
									disabled={isExporting || !startDate || !endDate}
									title="Export raw message metrics data including tokens, timestamps, and user information in CSV format"
									class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white text-sm font-medium rounded-md transition-colors duration-200 flex items-center gap-2"
								>
									{#if isExporting}
										<svg
											class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
										>
											<circle
												class="opacity-25"
												cx="12"
												cy="12"
												r="10"
												stroke="currentColor"
												stroke-width="4"
											></circle>
											<path
												class="opacity-75"
												fill="currentColor"
												d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
											></path>
										</svg>
										{$i18n.t('Exporting...')}
									{:else}
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
											/>
										</svg>
										{$i18n.t('Export Raw Data')}
									{/if}
								</button>
								{#if $user?.role === 'admin' || $user?.role === 'global_analyst' || $user?.role === 'analyst'}
									<button
										on:click={openExportLogs}
										class="px-3 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium rounded-md transition-colors duration-200 flex items-center gap-2"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
											/>
										</svg>
										{$i18n.t('View Exports')}
									</button>
								{/if}
							</div>
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
					<li class="mr-2">
						<button
							class={`inline-block p-4 rounded-t-lg border-b-2 ${
								activeTab === 'behavior'
									? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-500'
									: 'border-transparent hover:text-gray-900 hover:border-gray-300 dark:hover:text-gray-100'
							}`}
							on:click={() => setActiveTab('behavior')}
						>
							{$i18n.t('User Behavior')}
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
									{$i18n.t(
										'Please select a model from the dropdown to view model-specific metrics'
									)}
								</p>
							</div>
						</div>
					{/if}
				</div>

				<!-- Tab Content - User Behavior -->
				<div class={`${activeTab === 'behavior' ? 'flex flex-col h-full' : 'hidden'}`}>
					<div class="grid grid-cols-1 gap-6 mb-6 mt-6">
						<div class="bg-white shadow-lg rounded-lg p-4 dark:bg-gray-800">
							<h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">
								{$i18n.t('Inter-Prompt Latency Distribution')}
							</h5>
							<div class="text-sm text-gray-600 dark:text-gray-400 mb-4">
								{$i18n.t(
									'Time between consecutive user prompts in a chat session. Shows user engagement and cognitive load patterns.'
								)}
							</div>
							{#if interPromptLatencyData.total_latencies > 0}
								<div class="h-96">
									<canvas id="interPromptLatencyChart"></canvas>
								</div>
								<div class="mt-4 text-sm text-gray-600 dark:text-gray-400 text-center">
									{$i18n.t('Total analyzed prompt intervals')}: {interPromptLatencyData.total_latencies}
								</div>
							{:else}
								<div class="flex items-center justify-center h-64">
									<div class="text-center">
										<div class="mb-4">
											<svg
												class="w-16 h-16 text-gray-400 mx-auto"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
												></path>
											</svg>
										</div>
										<p class="text-gray-500 dark:text-gray-400">
											{$i18n.t('No inter-prompt latency data available')}
										</p>
										<p class="text-sm text-gray-400 dark:text-gray-500 mt-2">
											{$i18n.t('Data will appear once users engage in multi-turn conversations')}
										</p>
									</div>
								</div>
							{/if}
						</div>
					</div>
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

	<!-- Export Logs Modal -->
	{#if showExportLogs}
		<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
			<div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-4xl mx-4 max-h-96">
				<div class="flex justify-between items-center mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{$i18n.t('Export History')}
					</h3>
					<button
						on:click={closeExportLogs}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>

				<div class="overflow-y-auto max-h-64">
					{#if exportLogs.length > 0}
						<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400">
							<thead
								class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-700 dark:text-gray-400"
							>
								<tr>
									<th class="px-4 py-2">{$i18n.t('User')}</th>
									<th class="px-4 py-2">{$i18n.t('Domain')}</th>
									<th class="px-4 py-2">{$i18n.t('Export Date')}</th>
									<th class="px-4 py-2">{$i18n.t('Date Range')}</th>
									<th class="px-4 py-2">{$i18n.t('Records')}</th>
									<th class="px-4 py-2">{$i18n.t('File Size')}</th>
								</tr>
							</thead>
							<tbody>
								{#each exportLogs as log}
									<tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
										<td class="px-4 py-2 font-medium text-gray-900 dark:text-white">
											{log.user_id}
										</td>
										<td class="px-4 py-2">{log.email_domain}</td>
										<td class="px-4 py-2">
											{new Date(log.export_timestamp * 1000).toLocaleDateString()}
										</td>
										<td class="px-4 py-2">
											{new Date(log.date_range_start * 1000).toLocaleDateString()} - {new Date(
												log.date_range_end * 1000
											).toLocaleDateString()}
										</td>
										<td class="px-4 py-2">{log.row_count.toLocaleString()}</td>
										<td class="px-4 py-2">{(log.file_size / 1024).toFixed(1)} KB</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<div class="text-center py-8 text-gray-500 dark:text-gray-400">
							{$i18n.t('No export history found')}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
{:else}
	<div class="flex justify-center items-center h-64">
		<div class="text-gray-500 dark:text-gray-400">
			{$i18n.t('Loading metrics...')}
		</div>
	</div>
{/if}
