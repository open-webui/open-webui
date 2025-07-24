<script>
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getClientUsageSummary, getTodayUsage, getUsageByUser, getUsageByModel } from '$lib/apis/organizations';
	import Modal from '$lib/components/common/Modal.svelte';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');

	let loading = false;
	let activeTab = 'overview';
	
	// Option 1: Simplified data structure
	let usageData = {
		today: {
			tokens: 0,
			cost: 0,
			requests: 0,
			last_updated: 'No usage today'
		},
		this_month: {
			tokens: 0,
			cost: 0,
			requests: 0,
			days_active: 0
		},
		daily_history: [], // Last 30 days
		client_org_name: 'My Organization'
	};
	
	// Per-user and per-model data
	let userUsageData = [];
	let modelUsageData = [];
	let clientOrgId = 'current'; // Placeholder for client org ID

	let refreshInterval = null;

	onMount(async () => {
		await loadUsageData();
		// Refresh today's data every 30 seconds for real-time updates
		refreshInterval = setInterval(loadTodaysUsage, 30000);
		
		// Cleanup interval on component destroy
		return () => {
			if (refreshInterval) {
				clearInterval(refreshInterval);
			}
		};
	});

	const loadUsageData = async () => {
		try {
			loading = true;
			
			// Get Option 1 hybrid data (today real-time + daily history)
			const response = await getClientUsageSummary($user.token);
			
			if (response?.success && response.stats) {
				usageData = response.stats;
				// Extract client org ID from response if available
				if (response.client_id) {
					clientOrgId = response.client_id;
				}
			}
			
			// Load per-user and per-model data for current tab
			if (activeTab === 'users') {
				await loadUserUsage();
			} else if (activeTab === 'models') {
				await loadModelUsage();
			}
			
		} catch (error) {
			console.error('Failed to load usage data:', error);
			toast.error($i18n.t('Failed to load usage statistics'));
			
			// Show helpful message if no organization mapping
			if (error?.detail?.includes('No organization mapping')) {
				toast.error($i18n.t('No organization assigned. Please contact your administrator.'));
			}
		} finally {
			loading = false;
		}
	};
	
	const loadUserUsage = async () => {
		try {
			const response = await getUsageByUser($user.token, clientOrgId);
			if (response?.success && response.user_usage) {
				userUsageData = response.user_usage;
			}
		} catch (error) {
			console.error('Failed to load user usage:', error);
		}
	};
	
	const loadModelUsage = async () => {
		try {
			const response = await getUsageByModel($user.token, clientOrgId);
			if (response?.success && response.model_usage) {
				modelUsageData = response.model_usage;
			}
		} catch (error) {
			console.error('Failed to load model usage:', error);
		}
	};

	const loadTodaysUsage = async () => {
		// Refresh only today's live counters (lightweight)
		try {
			const response = await getTodayUsage($user.token, 'current'); // Using 'current' as placeholder
			
			if (response?.success && response.today) {
				usageData.today = response.today;
			}
			
		} catch (error) {
			console.error('Failed to refresh today data:', error);
		}
	};

	const handleRefresh = async () => {
		await loadUsageData();
		toast.success($i18n.t('Usage data refreshed'));
	};
	
	const handleTabChange = async (tab) => {
		activeTab = tab;
		if (tab === 'users' && userUsageData.length === 0) {
			await loadUserUsage();
		} else if (tab === 'models' && modelUsageData.length === 0) {
			await loadModelUsage();
		}
	};

	const formatCurrency = (amount) => {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD'
		}).format(amount || 0);
	};

	const formatNumber = (number) => {
		return new Intl.NumberFormat('en-US').format(number || 0);
	};

	const formatDate = (dateString) => {
		return new Date(dateString).toLocaleDateString();
	};

	const getDailyAverage = () => {
		if (usageData.this_month.days_active > 0) {
			return usageData.this_month.cost / usageData.this_month.days_active;
		}
		return 0;
	};
</script>

<div class="mb-6">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold">{$i18n.t('My Organization Usage')}</h2>
		<div class="flex items-center gap-3">
			<div class="text-sm text-gray-500">
				Last updated: {usageData.today.last_updated}
			</div>
			<button
				class="px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
				on:click={handleRefresh}
			>
				{$i18n.t('Refresh')}
			</button>
		</div>
	</div>

	<!-- Real-time Today + Monthly Summary Cards -->
	<div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
		<!-- Today's Usage (Real-time) -->
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Today's Tokens</p>
					<p class="text-2xl font-semibold text-gray-900 dark:text-white">
						{formatNumber(usageData.today.tokens)}
					</p>
					<div class="flex items-center text-xs text-green-600 mt-1">
						<div class="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></div>
						Live
					</div>
				</div>
				<div class="flex-shrink-0">
					<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
						<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
						</svg>
					</div>
				</div>
			</div>
		</div>

		<!-- Today's Cost (Real-time) -->
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Today's Cost</p>
					<p class="text-2xl font-semibold text-gray-900 dark:text-white">
						{formatCurrency(usageData.today.cost)}
					</p>
					<div class="flex items-center text-xs text-green-600 mt-1">
						<div class="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></div>
						Live
					</div>
				</div>
				<div class="flex-shrink-0">
					<div class="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
						<svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"></path>
						</svg>
					</div>
				</div>
			</div>
		</div>

		<!-- This Month Total -->
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Month Total</p>
					<p class="text-2xl font-semibold text-gray-900 dark:text-white">
						{formatCurrency(usageData.this_month.cost)}
					</p>
					<p class="text-xs text-gray-500 mt-1">{usageData.this_month.days_active} days active</p>
				</div>
				<div class="flex-shrink-0">
					<div class="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
						<svg class="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3a2 2 0 012-2h8a2 2 0 012 2v4m0 0V7a2 2 0 11-4 0m4 0a2 2 0 104 0M3 19h18m-9-15a2 2 0 11-4 0m4 0V3a2 2 0 11-4 0"></path>
						</svg>
					</div>
				</div>
			</div>
		</div>

		<!-- Daily Average -->
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Daily Average</p>
					<p class="text-2xl font-semibold text-gray-900 dark:text-white">
						{formatCurrency(getDailyAverage())}
					</p>
					<p class="text-xs text-gray-500 mt-1">This month</p>
				</div>
				<div class="flex-shrink-0">
					<div class="w-8 h-8 bg-orange-100 dark:bg-orange-900 rounded-lg flex items-center justify-center">
						<svg class="w-4 h-4 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
						</svg>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Tabs Navigation -->
	<div class="border-b border-gray-200 dark:border-gray-700 mb-6">
		<nav class="-mb-px flex space-x-8">
			<button
				class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'overview' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
				on:click={() => handleTabChange('overview')}
			>
				{$i18n.t('Daily Trend')}
			</button>
			<button
				class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'stats' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
				on:click={() => handleTabChange('stats')}
			>
				{$i18n.t('Usage Stats')}
			</button>
			<button
				class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'users' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
				on:click={() => handleTabChange('users')}
			>
				{$i18n.t('By User')}
			</button>
			<button
				class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'models' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
				on:click={() => handleTabChange('models')}
			>
				{$i18n.t('By Model')}
			</button>
		</nav>
	</div>

	<!-- Tab Content -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
			<span class="ml-2 text-gray-600 dark:text-gray-400">{$i18n.t('Loading usage data...')}</span>
		</div>
	{:else if activeTab === 'overview'}
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<h3 class="text-lg font-medium mb-4">{$i18n.t('Daily Usage Trend')}</h3>
			
			{#if usageData.daily_history && usageData.daily_history.length > 0}
				<div class="space-y-2">
					{#each usageData.daily_history.slice(-10) as day, index}
						<div class="flex justify-between items-center py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
							<div class="text-sm font-medium">
								{formatDate(day.date)}
								{#if day.date === new Date().toISOString().split('T')[0]}
									<span class="text-green-600 text-xs ml-2 font-semibold">• Today (Live)</span>
								{/if}
							</div>
							<div class="text-right">
								<div class="text-sm font-semibold">{formatCurrency(day.cost)}</div>
								<div class="text-xs text-gray-500">{formatNumber(day.tokens)} tokens • {day.requests} requests</div>
							</div>
						</div>
					{/each}
				</div>
				
				{#if usageData.daily_history.length > 10}
					<div class="mt-4 text-center">
						<p class="text-sm text-gray-500">Showing last 10 days • Total history: {usageData.daily_history.length} days</p>
					</div>
				{/if}
			{:else}
				<p class="text-gray-600 dark:text-gray-400">{$i18n.t('No usage history available.')}</p>
			{/if}
		</div>
	{:else if activeTab === 'stats'}
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<h3 class="text-lg font-medium mb-4">{$i18n.t('Usage Statistics')}</h3>
			
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Today vs Month')}</h4>
					<div class="space-y-2">
						<div class="flex justify-between">
							<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Today Tokens')}:</span>
							<span class="text-sm font-medium">{formatNumber(usageData.today.tokens)}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Month Total')}:</span>
							<span class="text-sm font-medium">{formatNumber(usageData.this_month.tokens)}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Today % of Month')}:</span>
							<span class="text-sm font-medium">
								{usageData.this_month.tokens > 0 ? ((usageData.today.tokens / usageData.this_month.tokens) * 100).toFixed(1) : 0}%
							</span>
						</div>
					</div>
				</div>
				
				<div>
					<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Cost Analysis')}</h4>
					<div class="space-y-2">
						<div class="flex justify-between">
							<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Today Cost')}:</span>
							<span class="text-sm font-medium">{formatCurrency(usageData.today.cost)}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Month Total')}:</span>
							<span class="text-sm font-medium">{formatCurrency(usageData.this_month.cost)}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Avg per Token')}:</span>
							<span class="text-sm font-medium">
								{usageData.this_month.tokens > 0 ? formatCurrency((usageData.this_month.cost / usageData.this_month.tokens) * 1000) + '/1K' : '$0.00/1K'}
							</span>
						</div>
					</div>
				</div>
			</div>

			<div class="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
				<h4 class="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">{$i18n.t('Data Refresh Information')}</h4>
				<div class="text-sm text-blue-700 dark:text-blue-400 space-y-1">
					<p>• {$i18n.t('Today\'s usage: Real-time updates every 30 seconds')}</p>
					<p>• {$i18n.t('Historical data: Daily summaries (updated at midnight)')}</p>
					<p>• {$i18n.t('Monthly totals: Combination of daily summaries + today\'s live data')}</p>
				</div>
			</div>
		</div>
	{:else if activeTab === 'users'}
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<h3 class="text-lg font-medium mb-4">{$i18n.t('Usage by User')}</h3>
			
			{#if userUsageData && userUsageData.length > 0}
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
						<thead>
							<tr>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('User ID')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Total Tokens')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Requests')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Cost')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Days Active')}
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each userUsageData as userUsage}
								<tr>
									<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
										{userUsage.user_id}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm">
										{formatNumber(userUsage.total_tokens)}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm">
										{formatNumber(userUsage.total_requests)}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
										{formatCurrency(userUsage.markup_cost)}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm">
										{userUsage.days_active}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="text-gray-600 dark:text-gray-400">{$i18n.t('No user usage data available.')}</p>
			{/if}
		</div>
	{:else if activeTab === 'models'}
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<h3 class="text-lg font-medium mb-4">{$i18n.t('Usage by Model')}</h3>
			
			{#if modelUsageData && modelUsageData.length > 0}
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
						<thead>
							<tr>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Model')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Provider')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Total Tokens')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Requests')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Cost')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
									{$i18n.t('Days Used')}
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each modelUsageData as modelUsage}
								<tr>
									<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
										{modelUsage.model_name}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm">
										{modelUsage.provider || 'N/A'}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm">
										{formatNumber(modelUsage.total_tokens)}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm">
										{formatNumber(modelUsage.total_requests)}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
										{formatCurrency(modelUsage.markup_cost)}
									</td>
									<td class="px-4 py-3 whitespace-nowrap text-sm">
										{modelUsage.days_used}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="text-gray-600 dark:text-gray-400">{$i18n.t('No model usage data available.')}</p>
			{/if}
		</div>
	{/if}
</div>

<style>
	.animate-pulse {
		animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}
	
	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: .5; }
	}
</style>