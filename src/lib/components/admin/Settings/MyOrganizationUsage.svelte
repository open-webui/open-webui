<script>
	// Daily Batch Processing v4.0 - Data updates at 00:00 daily
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getClientUsageSummary, getUsageByUser, getUsageByModel, getMAIModelPricing, getSubscriptionBilling } from '$lib/apis/organizations';
	import Modal from '$lib/components/common/Modal.svelte';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');

	let loading = false;
	let activeTab = 'stats';
	
	// Daily batch processing structure - data updated at 00:00
	let usageData = {
		current_month: {
			month: 'Loading...',
			total_tokens: 0,
			total_cost: 0,
			total_cost_pln: 0,
			total_requests: 0,
			days_with_usage: 0,
			days_in_month: 0,
			usage_percentage: 0
		},
		daily_breakdown: [],
		monthly_summary: {
			average_daily_tokens: 0,
			average_daily_cost: 0,
			average_usage_day_tokens: 0,
			busiest_day: null,
			highest_cost_day: null,
			total_unique_users: 0,
			most_used_model: null
		},
		client_org_name: 'My Organization'
	};
	
	// Per-user and per-model data
	let userUsageData = [];
	let modelUsageData = [];
	let subscriptionData = null; // Subscription billing data
	let clientOrgId = null; // Will be determined from API response
	let clientOrgIdValidated = false; // Track if client ID has been validated
	
	// Model pricing data - will be loaded from API
	let modelPricingData = [];
	let loadingPricing = false;
	
	// Fallback static data (used if API fails)
	const fallbackPricingData = [
		{
			id: 'anthropic/claude-sonnet-4',
			name: 'Claude Sonnet 4',
			provider: 'Anthropic',
			price_per_million_input: 8.00,
			price_per_million_output: 24.00,
			context_length: 1000000,
			category: 'Premium'
		},
		{
			id: 'google/gemini-2.5-flash',
			name: 'Gemini 2.5 Flash',
			provider: 'Google',
			price_per_million_input: 1.50,
			price_per_million_output: 6.00,
			context_length: 2000000,
			category: 'Fast'
		},
		{
			id: 'google/gemini-2.5-pro',
			name: 'Gemini 2.5 Pro',
			provider: 'Google',
			price_per_million_input: 3.00,
			price_per_million_output: 12.00,
			context_length: 2000000,
			category: 'Premium'
		},
		{
			id: 'deepseek/deepseek-chat-v3-0324',
			name: 'DeepSeek Chat v3',
			provider: 'DeepSeek',
			price_per_million_input: 0.14,
			price_per_million_output: 0.28,
			context_length: 128000,
			category: 'Budget'
		},
		{
			id: 'anthropic/claude-3.7-sonnet',
			name: 'Claude 3.7 Sonnet',
			provider: 'Anthropic',
			price_per_million_input: 6.00,
			price_per_million_output: 18.00,
			context_length: 200000,
			category: 'Premium'
		},
		{
			id: 'google/gemini-2.5-flash-lite-preview-06-17',
			name: 'Gemini 2.5 Flash Lite',
			provider: 'Google',
			price_per_million_input: 0.50,
			price_per_million_output: 2.00,
			context_length: 1000000,
			category: 'Budget'
		},
		{
			id: 'openai/gpt-4.1',
			name: 'GPT-4.1',
			provider: 'OpenAI',
			price_per_million_input: 10.00,
			price_per_million_output: 30.00,
			context_length: 128000,
			category: 'Premium'
		},
		{
			id: 'x-ai/grok-4',
			name: 'Grok 4',
			provider: 'xAI',
			price_per_million_input: 8.00,
			price_per_million_output: 24.00,
			context_length: 131072,
			category: 'Premium'
		},
		{
			id: 'openai/gpt-4o-mini',
			name: 'GPT-4o Mini',
			provider: 'OpenAI',
			price_per_million_input: 0.15,
			price_per_million_output: 0.60,
			context_length: 128000,
			category: 'Budget'
		},
		{
			id: 'openai/o4-mini-high',
			name: 'O4 Mini High',
			provider: 'OpenAI',
			price_per_million_input: 3.00,
			price_per_million_output: 12.00,
			context_length: 128000,
			category: 'Standard'
		},
		{
			id: 'openai/o3',
			name: 'O3',
			provider: 'OpenAI',
			price_per_million_input: 60.00,
			price_per_million_output: 240.00,
			context_length: 200000,
			category: 'Reasoning'
		},
		{
			id: 'openai/chatgpt-4o-latest',
			name: 'ChatGPT-4o Latest',
			provider: 'OpenAI',
			price_per_million_input: 5.00,
			price_per_million_output: 15.00,
			context_length: 128000,
			category: 'Standard'
		}
	];

	// Daily batch processing - no refresh intervals needed, data updated at 00:00

	// Reactive: Ensure non-admin users don't access admin-only tabs
	$: if ($user?.role !== 'admin' && (activeTab === 'users' || activeTab === 'models' || activeTab === 'subscription')) {
		activeTab = 'stats';
	}

	const loadModelPricing = async () => {
		try {
			loadingPricing = true;
			const response = await getMAIModelPricing();
			
			if (response?.success && response.models) {
				modelPricingData = response.models;
			} else {
				// Use fallback data if API fails
				modelPricingData = response?.models || fallbackPricingData;
			}
		} catch (error) {
			console.error('Failed to load model pricing:', error);
			modelPricingData = fallbackPricingData;
		} finally {
			loadingPricing = false;
		}
	};

	onMount(async () => {
		await loadUsageData();
		// Daily batch processing approach - data loads once per session
		// Fresh data available after 00:30 daily when batch processing completes
	});

	/**
	 * Fallback mechanism to determine client organization ID
	 * when primary method fails or returns invalid ID
	 */
	const getClientIdFallback = async () => {
		try {
			// Try to get client organizations list (if user has access)
			const orgsResponse = await getClientOrganizations($user.token);
			if (orgsResponse && orgsResponse.length > 0) {
				// Return the first active organization
				const activeOrg = orgsResponse.find(org => org.is_active);
				if (activeOrg) {
					return activeOrg.id;
				}
			}
		} catch (orgError) {
			console.log('Unable to fetch organizations list:', orgError);
		}

		// If no organizations found, return a fallback identifier
		console.log('No fallback client ID methods available');
		return null;
	};

	const loadUsageData = async () => {
		try {
			loading = true;
			
			// Add timeout to prevent hanging on slow API responses
			const timeoutPromise = new Promise((_, reject) => 
				setTimeout(() => reject(new Error('Request timeout')), 10000)
			);
			
			// Get admin-focused daily breakdown data (no real-time)
			const response = await Promise.race([
				getClientUsageSummary($user.token),
				timeoutPromise
			]);
			
			if (response?.success && response.stats) {
				usageData = response.stats;
				
				// Validate and set client org ID with proper error handling
				if (response.client_id && response.client_id !== 'current') {
					clientOrgId = response.client_id;
					clientOrgIdValidated = true;
					console.log(`Client organization ID resolved: ${clientOrgId}`);
				} else {
					console.warn('Unable to determine client organization ID from response');
					clientOrgIdValidated = false;
				}
			} else {
				console.warn('Invalid response from usage summary API');
				// Set empty data instead of failing completely
				usageData = {
					current_month: {
						month: 'No Data',
						total_tokens: 0,
						total_cost: 0,
						total_cost_pln: 0,
						total_requests: 0,
						days_with_usage: 0,
						days_in_month: new Date().getDate(),
						usage_percentage: 0
					},
					daily_breakdown: [],
					monthly_summary: {
						average_daily_tokens: 0,
						average_daily_cost: 0,
						average_usage_day_tokens: 0,
						busiest_day: null,
						highest_cost_day: null,
						total_unique_users: 0,
						most_used_model: null
					},
					client_org_name: 'My Organization'
				};
				clientOrgIdValidated = false;
			}
			
			// Load per-user and per-model data for current tab if we have a valid client ID
			if (clientOrgIdValidated) {
				if (activeTab === 'users') {
					await loadUserUsage();
				} else if (activeTab === 'models') {
					await loadModelUsage();
				}
			}
			
		} catch (error) {
			console.error('Failed to load usage data:', error);
			
			// Show user-friendly error message
			if (error.message === 'Request timeout') {
				toast.error($i18n.t('Request timed out. The server may be slow. Please try again.'));
			} else {
				toast.error($i18n.t('Failed to load usage statistics'));
			}
			
			// Show helpful message if no organization mapping
			if (error?.detail?.includes('No organization mapping')) {
				toast.error($i18n.t('No organization assigned. Please contact your administrator.'));
			}
			
			// Set error state with empty data
			usageData = {
				current_month: {
					month: 'Error Loading Data',
					total_tokens: 0,
					total_cost: 0,
					total_cost_pln: 0,
					total_requests: 0,
					days_with_usage: 0,
					days_in_month: new Date().getDate(),
					usage_percentage: 0
				},
				daily_breakdown: [],
				monthly_summary: {
					average_daily_tokens: 0,
					average_daily_cost: 0,
					average_usage_day_tokens: 0,
					busiest_day: null,
					highest_cost_day: null,
					total_unique_users: 0,
					most_used_model: null
				},
				client_org_name: 'Error'
			};
			clientOrgIdValidated = false;
		} finally {
			loading = false;
		}
	};
	
	const loadUserUsage = async () => {
		// Validate client ID before making API call
		if (!clientOrgIdValidated || !clientOrgId) {
			console.warn('Cannot load user usage: client organization ID not available');
			toast.error($i18n.t('Unable to load user usage data. Please try refreshing the page.'));
			return;
		}

		try {
			const response = await getUsageByUser($user.token, clientOrgId);
			if (response?.success && response.user_usage) {
				userUsageData = response.user_usage;
			} else {
				console.warn('User usage API returned unsuccessful response:', response);
				userUsageData = [];
			}
		} catch (error) {
			console.error('Failed to load user usage:', error);
			toast.error($i18n.t('Failed to load user usage data'));
			userUsageData = [];
		}
	};
	
	const loadModelUsage = async () => {
		// Validate client ID before making API call
		if (!clientOrgIdValidated || !clientOrgId) {
			console.warn('Cannot load model usage: client organization ID not available');
			toast.error($i18n.t('Unable to load model usage data. Please try refreshing the page.'));
			return;
		}

		try {
			const response = await getUsageByModel($user.token, clientOrgId);
			if (response?.success && response.model_usage) {
				modelUsageData = response.model_usage;
			} else {
				console.warn('Model usage API returned unsuccessful response:', response);
				modelUsageData = [];
			}
		} catch (error) {
			console.error('Failed to load model usage:', error);
			toast.error($i18n.t('Failed to load model usage data'));
			modelUsageData = [];
		}
	};

	// Daily batch processing - all data consolidated at 00:00 with NBP rates

	const loadSubscriptionData = async () => {
		// Validate client ID before making API call
		if (!clientOrgIdValidated || !clientOrgId) {
			console.warn('Cannot load subscription data: client organization ID not available');
			toast.error($i18n.t('Unable to load subscription data. Please try refreshing the page.'));
			return;
		}

		try {
			const response = await getSubscriptionBilling($user.token, clientOrgId);
			if (response?.success && response.subscription_data) {
				subscriptionData = response.subscription_data;
			} else {
				console.warn('Subscription API returned unsuccessful response:', response);
				subscriptionData = null;
			}
		} catch (error) {
			console.error('Failed to load subscription data:', error);
			toast.error($i18n.t('Failed to load subscription billing data'));
			subscriptionData = null;
		}
	};

	
	const handleTabChange = async (tab) => {
		// Prevent non-admin users from accessing admin-only tabs
		if ($user?.role !== 'admin' && (tab === 'users' || tab === 'models' || tab === 'subscription')) {
			toast.error($i18n.t('Access denied. Administrator privileges required.'));
			return;
		}
		
		activeTab = tab;
		
		// Only load data if we have a validated client ID
		if (clientOrgIdValidated && clientOrgId) {
			if (tab === 'users' && userUsageData.length === 0) {
				await loadUserUsage();
			} else if (tab === 'models' && modelUsageData.length === 0) {
				await loadModelUsage();
			} else if (tab === 'subscription' && subscriptionData === null) {
				await loadSubscriptionData();
			}
		} else if (tab === 'users' || tab === 'models' || tab === 'subscription') {
			// Show informative message for usage tabs when client ID is not available
			console.warn(`Cannot load ${tab} data: client organization ID not validated`);
			toast.error($i18n.t('Organization data not available. Please refresh the page.'));
		}
		
		// Pricing tab doesn't need client ID
		if (tab === 'pricing' && modelPricingData.length === 0) {
			await loadModelPricing();
		}
	};

	const formatCurrency = (amount, currency = 'USD') => {
		// For very small amounts, show more decimal places
		const value = amount || 0;
		const currencyOptions = currency === 'PLN' 
			? { style: 'currency', currency: 'PLN' }
			: { style: 'currency', currency: 'USD' };
			
		if (value > 0 && value < 0.01 && currency === 'USD') {
			return new Intl.NumberFormat('en-US', {
				...currencyOptions,
				minimumFractionDigits: 6,
				maximumFractionDigits: 6
			}).format(value);
		}
		
		return new Intl.NumberFormat(currency === 'PLN' ? 'pl-PL' : 'en-US', currencyOptions).format(value);
	};
	
	const formatDualCurrency = (usdAmount, plnAmount) => {
		// Format as "$X.XX (Y.YY zł)"
		if (plnAmount !== undefined && plnAmount !== null) {
			return `${formatCurrency(usdAmount)} (${formatCurrency(plnAmount, 'PLN')})`;
		}
		// Fallback to USD only if PLN not available
		return formatCurrency(usdAmount);
	};

	const formatNumber = (number) => {
		return new Intl.NumberFormat('en-US').format(number || 0);
	};


</script>

<div class="mb-6">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold">{$i18n.t('My Organization Usage')}</h2>
		<div class="text-xs text-gray-500 dark:text-gray-400 flex items-center">
			<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
			</svg>
			Data updated daily at 00:00
		</div>
	</div>

	<!-- Exchange Rate Status Notice -->
	{#if usageData.exchange_rate_info}
		<div class="mb-4 text-xs text-gray-600 dark:text-gray-400 flex items-center justify-between bg-gray-50 dark:bg-gray-800 p-2 rounded">
			<span>
				Exchange rate: 1 USD = {usageData.exchange_rate_info.usd_pln.toFixed(4)} PLN 
				(NBP rate from {usageData.exchange_rate_info.effective_date})
			</span>
		</div>
	{:else if usageData.pln_conversion_available === false}
		<div class="mb-4 text-xs text-orange-600 dark:text-orange-400 flex items-center bg-orange-50 dark:bg-orange-900/20 p-2 rounded">
			<svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
				<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
			</svg>
			<span>PLN conversion temporarily unavailable - showing USD only</span>
		</div>
	{/if}

	<!-- Daily Batch Processing Status Notice -->
	<div class="mb-4 text-xs text-blue-600 dark:text-blue-400 flex items-center justify-between bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
		<div class="flex items-center">
			<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
			</svg>
			<span>
				<strong>Daily Batch Processing:</strong> Data consolidated at 00:00 with NBP exchange rates &amp; monthly totals (1st to current day)
			</span>
		</div>
		<div class="text-xs bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded">
			Business Intelligence
		</div>
	</div>

	<!-- Monthly Summary Cards (Admin Overview) -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
		<!-- Monthly Tokens -->
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Total Tokens</p>
					<p class="text-2xl font-semibold text-gray-900 dark:text-white">
						{formatNumber(usageData.current_month?.total_tokens || 0)}
					</p>
					<p class="text-xs text-gray-500 mt-1">{usageData.current_month?.month || 'Loading...'} • Batch Calculated</p>
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

		<!-- Monthly Cost -->
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Total Cost</p>
					<p class="text-2xl font-semibold text-gray-900 dark:text-white">
						{formatDualCurrency(usageData.current_month?.total_cost || 0, usageData.current_month?.total_cost_pln || 0)}
					</p>
					<p class="text-xs text-gray-500 mt-1">{usageData.current_month?.total_requests || 0} requests • NBP Daily Rates</p>
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

		<!-- Usage Activity -->
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-sm font-medium text-gray-600 dark:text-gray-400">Usage Activity</p>
					<p class="text-2xl font-semibold text-gray-900 dark:text-white">
						{usageData.current_month?.days_with_usage || 0}/{usageData.current_month?.days_in_month || 0}
					</p>
					<p class="text-xs text-gray-500 mt-1">{Math.round(usageData.current_month?.usage_percentage || 0)}% active • Cumulative 1st-Current</p>
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

	</div>

	<!-- Tabs Navigation -->
	<div class="border-b border-gray-200 dark:border-gray-700 mb-6">
		<nav class="-mb-px flex space-x-8">
			<button
				class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'stats' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
				on:click={() => handleTabChange('stats')}
			>
				{$i18n.t('Usage Stats')}
			</button>
			{#if $user?.role === 'admin'}
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
				<button
					class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'subscription' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
					on:click={() => handleTabChange('subscription')}
				>
					{$i18n.t('Subscription')}
				</button>
			{/if}
			<button
				class="py-2 px-1 border-b-2 font-medium text-sm {activeTab === 'pricing' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
				on:click={() => handleTabChange('pricing')}
			>
				{$i18n.t('Model Pricing')}
			</button>
		</nav>
	</div>

	<!-- Tab Content -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
			<span class="ml-2 text-gray-600 dark:text-gray-400">{$i18n.t('Loading daily batch data...')}</span>
		</div>
	{:else if activeTab === 'stats'}
		<div class="space-y-6">
			<!-- Monthly Summary Insights -->
			<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-medium">{$i18n.t('Monthly Summary')}</h3>
					<div class="text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded flex items-center">
						<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
						</svg>
						Daily Batch Calculated
					</div>
				</div>
				
				<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
					<div>
						<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Usage Averages')} 📊</h4>
						<div class="space-y-2">
							<div class="flex justify-between">
								<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Daily Average')}:</span>
								<span class="text-sm font-medium">{formatNumber(usageData.monthly_summary?.average_daily_tokens || 0)} tokens</span>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Usage Day Average')}:</span>
								<span class="text-sm font-medium">{formatNumber(usageData.monthly_summary?.average_usage_day_tokens || 0)} tokens</span>
							</div>
						</div>
					</div>
					
					<div>
						<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Peak Usage')} 🔥</h4>
						<div class="space-y-2">
							<div class="flex justify-between">
								<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Busiest Day')}:</span>
								<span class="text-sm font-medium">{usageData.monthly_summary?.busiest_day || 'N/A'}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Highest Cost Day')}:</span>
								<span class="text-sm font-medium">{usageData.monthly_summary?.highest_cost_day || 'N/A'}</span>
							</div>
						</div>
					</div>
					
					<div>
						<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Most Used')} ⭐</h4>
						<div class="space-y-2">
							<div class="flex justify-between">
								<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Primary Model')}:</span>
								<span class="text-sm font-medium">{usageData.monthly_summary?.most_used_model || 'N/A'}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Active Users')}:</span>
								<span class="text-sm font-medium">{usageData.monthly_summary?.total_unique_users || 0}</span>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Daily Breakdown Table -->
			<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-medium">{$i18n.t('Daily Breakdown')} - {usageData.current_month?.month || 'Current Month'}</h3>
					<div class="text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded flex items-center">
						<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
						</svg>
						Updated at 00:00 Daily
					</div>
				</div>
				
				{#if usageData.daily_breakdown && usageData.daily_breakdown.length > 0}
					<div class="overflow-x-auto">
						<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
							<thead>
								<tr>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										{$i18n.t('Date')}
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										{$i18n.t('Day')}
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										{$i18n.t('Tokens')}
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										{$i18n.t('Cost')}
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										{$i18n.t('Requests')}
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										{$i18n.t('Primary Model')}
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										{$i18n.t('Last Activity')}
									</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
								{#each usageData.daily_breakdown as day}
									<tr>
										<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
											{day?.date || 'N/A'}
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm">
											{day?.day_name || 'N/A'}
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm">
											{formatNumber(day?.tokens || 0)}
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
											{formatDualCurrency(day?.cost || 0, day?.cost_pln || 0)}
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm">
											{formatNumber(day?.requests || 0)}
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm">
											{day?.primary_model || 'N/A'}
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm">
											{day?.last_activity || 'N/A'}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<div class="text-center py-8">
						<svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
						</svg>
						<p class="text-gray-600 dark:text-gray-400 text-lg font-medium">{$i18n.t('No usage data available for this month.')}</p>
						<p class="text-gray-500 dark:text-gray-500 text-sm mt-2">Data is processed daily at 00:00. Usage will appear after first API calls.</p>
					</div>
				{/if}
			</div>
		</div>
	{:else if activeTab === 'users' && $user?.role === 'admin'}
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<h3 class="text-lg font-medium mb-4">{$i18n.t('Usage by User')}</h3>
			
			{#if !clientOrgIdValidated}
				<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
					<div class="flex">
						<div class="flex-shrink-0">
							<svg class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
							</svg>
						</div>
						<div class="ml-3">
							<p class="text-sm text-yellow-800 dark:text-yellow-200">
								{$i18n.t('Organization data unavailable. User usage cannot be displayed.')}<br>
								<span class="text-xs">{$i18n.t('Please refresh the page or contact your administrator.')}</span>
							</p>
						</div>
					</div>
				</div>
			{:else if userUsageData && userUsageData.length > 0}
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
										{formatDualCurrency(userUsage.markup_cost, userUsage.cost_pln)}
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
	{:else if activeTab === 'models' && $user?.role === 'admin'}
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<h3 class="text-lg font-medium mb-4">{$i18n.t('Usage by Model')}</h3>
			
			{#if !clientOrgIdValidated}
				<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
					<div class="flex">
						<div class="flex-shrink-0">
							<svg class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
							</svg>
						</div>
						<div class="ml-3">
							<p class="text-sm text-yellow-800 dark:text-yellow-200">
								{$i18n.t('Organization data unavailable. Model usage cannot be displayed.')}<br>
								<span class="text-xs">{$i18n.t('Please refresh the page or contact your administrator.')}</span>
							</p>
						</div>
					</div>
				</div>
			{:else if modelUsageData && modelUsageData.length > 0}
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
										{formatDualCurrency(modelUsage.markup_cost, modelUsage.cost_pln)}
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
	{:else if activeTab === 'subscription' && $user?.role === 'admin'}
		<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
			<h3 class="text-lg font-medium mb-4">{$i18n.t('Subscription Billing')}</h3>
			
			{#if !clientOrgIdValidated}
				<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
					<div class="flex">
						<div class="flex-shrink-0">
							<svg class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
							</svg>
						</div>
						<div class="ml-3">
							<p class="text-sm text-yellow-800 dark:text-yellow-200">
								{$i18n.t('Organization data unavailable. Subscription billing cannot be displayed.')}<br>
								<span class="text-xs">{$i18n.t('Please refresh the page or contact your administrator.')}</span>
							</p>
						</div>
					</div>
				</div>
			{:else if subscriptionData}
				<!-- Current Month Summary -->
				<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
					<div class="bg-gradient-to-r from-blue-50 to-blue-100 dark:from-blue-900 dark:to-blue-800 rounded-lg p-6">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm font-medium text-blue-600 dark:text-blue-400">Total Users</p>
								<p class="text-2xl font-semibold text-blue-900 dark:text-blue-100">
									{subscriptionData.current_month.total_users}
								</p>
								<p class="text-xs text-blue-700 dark:text-blue-300 mt-1">
									{subscriptionData.current_month.month}/{subscriptionData.current_month.year}
								</p>
							</div>
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-blue-200 dark:bg-blue-700 rounded-lg flex items-center justify-center">
									<svg class="w-4 h-4 text-blue-600 dark:text-blue-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"></path>
									</svg>
								</div>
							</div>
						</div>
					</div>
					
					<div class="bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900 dark:to-green-800 rounded-lg p-6">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm font-medium text-green-600 dark:text-green-400">Current Tier</p>
								<p class="text-2xl font-semibold text-green-900 dark:text-green-100">
									{subscriptionData.current_month.current_tier_price_pln} PLN
								</p>
								<p class="text-xs text-green-700 dark:text-green-300 mt-1">per user/month</p>
							</div>
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-green-200 dark:bg-green-700 rounded-lg flex items-center justify-center">
									<svg class="w-4 h-4 text-green-600 dark:text-green-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
									</svg>
								</div>
							</div>
						</div>
					</div>
					
					<div class="bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-900 dark:to-purple-800 rounded-lg p-6">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm font-medium text-purple-600 dark:text-purple-400">Monthly Total</p>
								<p class="text-2xl font-semibold text-purple-900 dark:text-purple-100">
									{subscriptionData.current_month.total_cost_pln} PLN
								</p>
								<p class="text-xs text-purple-700 dark:text-purple-300 mt-1">proportional billing</p>
							</div>
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-purple-200 dark:bg-purple-700 rounded-lg flex items-center justify-center">
									<svg class="w-4 h-4 text-purple-600 dark:text-purple-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"></path>
									</svg>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Pricing Tiers -->
				<div class="mb-6">
					<h4 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Pricing Tiers</h4>
					<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
						{#each subscriptionData.current_month.tier_breakdown as tier}
							<div class="border rounded-lg p-4 {tier.is_current_tier ? 'border-blue-500 bg-blue-50 dark:bg-blue-900' : 'border-gray-200 dark:border-gray-700'}">
								<div class="text-center">
									<h5 class="font-medium text-gray-900 dark:text-white">{tier.tier_range}</h5>
									<p class="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
										{tier.price_per_user_pln} PLN
									</p>
									<p class="text-sm text-gray-600 dark:text-gray-400">per user/month</p>
									{#if tier.is_current_tier}
										<span class="inline-block mt-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
											Current Tier
										</span>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</div>

				<!-- User Details Table -->
				<div class="mb-6">
					<h4 class="text-lg font-medium text-gray-900 dark:text-white mb-4">User Billing Details</h4>
					<div class="overflow-x-auto">
						<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
							<thead>
								<tr>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										User
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										Added Date
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										Days in Month
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										Billing %
									</th>
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
										Monthly Cost
									</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
								{#each subscriptionData.current_month.user_details as userDetail}
									<tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
										<td class="px-4 py-3 whitespace-nowrap">
											<div>
												<div class="text-sm font-medium text-gray-900 dark:text-white">
													{userDetail.user_name}
												</div>
												<div class="text-xs text-gray-500">
													{userDetail.user_email}
												</div>
											</div>
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
											{userDetail.created_date}
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
											{userDetail.days_remaining_when_added}
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
											{Math.round(userDetail.billing_proportion * 100)}%
										</td>
										<td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
											{userDetail.monthly_cost_pln} PLN
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>

				<!-- Billing Info -->
				<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
					<h4 class="font-medium text-gray-900 dark:text-white mb-2">💰 How Billing Works</h4>
					<div class="text-sm text-gray-600 dark:text-gray-400 space-y-1">
						<p>• Users are billed proportionally based on when they were added to the organization</p>
						<p>• Pricing tiers are applied based on total user count for the month</p>
						<p>• Billing cycles follow calendar months (1st to last day of month)</p>
						<p>• Users added mid-month pay only for the remaining days in that month</p>
					</div>
				</div>
			{:else}
				<p class="text-gray-600 dark:text-gray-400">{$i18n.t('No subscription billing data available.')}</p>
			{/if}
		</div>
	{:else if activeTab === 'pricing'}
	<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
		<div class="mb-4">
			<h3 class="text-lg font-medium">{$i18n.t('Available Models & Pricing')}</h3>
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{#if loadingPricing}
					{$i18n.t('Loading pricing information...')}
				{:else}
					{$i18n.t('Prices updated daily at 00:00')}
				{/if}
			</div>
		</div>
		
		<div class="mb-4 text-sm text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
			<p><strong>ℹ️ Pricing Information:</strong></p>
			<p>• All prices are per 1 million tokens in USD</p>
			<p>• Input and output tokens are priced separately</p>
			<p>• Context length shows maximum input size per request</p>
		</div>
		
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
			<!-- Category filters -->
			<div class="flex flex-wrap gap-2">
				<span class="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">Budget</span>
				<span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">Standard</span>
				<span class="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">Premium</span>
				<span class="px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded-full">Fast</span>
				<span class="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">Reasoning</span>
			</div>
			<div class="text-right text-sm text-gray-600 dark:text-gray-400">
				{modelPricingData.length} models available
			</div>
		</div>
		
		{#if loadingPricing}
			<div class="flex items-center justify-center py-12">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
				<span class="ml-2 text-gray-600 dark:text-gray-400">{$i18n.t('Loading model pricing...')}</span>
			</div>
		{:else}
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
							{$i18n.t('Input (per 1M tokens)')}
						</th>
						<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							{$i18n.t('Output (per 1M tokens)')}
						</th>
						<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							{$i18n.t('Context Length')}
						</th>
						<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							{$i18n.t('Category')}
						</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
					{#each modelPricingData as model}
						<tr class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
							<td class="px-4 py-3 whitespace-nowrap">
								<div>
									<div class="text-sm font-medium text-gray-900 dark:text-white">
										{model.name}
									</div>
									<div class="text-xs text-gray-500 font-mono">
										{model.id}
									</div>
								</div>
							</td>
							<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
								{model.provider}
							</td>
							<td class="px-4 py-3 whitespace-nowrap text-sm">
								<div class="font-medium text-gray-900 dark:text-white">
									${model.price_per_million_input.toFixed(2)}
								</div>
							</td>
							<td class="px-4 py-3 whitespace-nowrap text-sm">
								<div class="font-medium text-gray-900 dark:text-white">
									${model.price_per_million_output.toFixed(2)}
								</div>
							</td>
							<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
								{formatNumber(model.context_length)} tokens
							</td>
							<td class="px-4 py-3 whitespace-nowrap">
								<span class="px-2 py-1 text-xs rounded-full
									{model.category === 'Budget' ? 'bg-green-100 text-green-800' :
									 model.category === 'Standard' ? 'bg-blue-100 text-blue-800' :
									 model.category === 'Premium' ? 'bg-purple-100 text-purple-800' :
									 model.category === 'Fast' ? 'bg-orange-100 text-orange-800' :
									 'bg-red-100 text-red-800'}">
									{model.category}
								</span>
							</td>
						</tr>
					{/each}
					</tbody>
				</table>
			</div>
		{/if}
		
		<div class="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
			<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
				<h4 class="font-medium text-gray-900 dark:text-white mb-2">💰 Pricing</h4>
				<p class="text-gray-600 dark:text-gray-400 mb-1">Transparent per-million token pricing</p>
				<p class="text-xs text-gray-500">Input and output tokens priced separately</p>
			</div>
			<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
				<h4 class="font-medium text-gray-900 dark:text-white mb-2">📊 Usage Tracking</h4>
				<p class="text-gray-600 dark:text-gray-400 mb-1">All usage automatically tracked</p>
				<p class="text-xs text-gray-500">View detailed usage in other tabs</p>
			</div>
			<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
				<h4 class="font-medium text-gray-900 dark:text-white mb-2">⚡ Model Availability</h4>
				<p class="text-gray-600 dark:text-gray-400 mb-1">12 premium AI models available</p>
				<p class="text-xs text-gray-500">Choose the best model for your task</p>
			</div>
		</div>
	</div>
{/if}

	<!-- Daily Batch Processing Help Information -->
	<div class="mt-6 bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
		<h4 class="font-medium text-gray-900 dark:text-white mb-3 flex items-center">
			<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
			</svg>
			Daily Batch Processing Information
		</h4>
		<div class="text-sm text-gray-600 dark:text-gray-400 space-y-2">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<p class="font-medium text-gray-700 dark:text-gray-300 mb-1">🕰️ Processing Schedule</p>
					<p>• Data updates automatically at 00:00 daily</p>
					<p>• Monthly totals calculated from 1st to current day</p>
					<p>• NBP exchange rates refreshed with holiday-aware logic</p>
				</div>
				<div>
					<p class="font-medium text-gray-700 dark:text-gray-300 mb-1">📊 Business Intelligence</p>
					<p>• All metrics pre-calculated for fast loading</p>
					<p>• Automated data validation and corrections</p>
					<p>• Complete usage history maintained indefinitely</p>
				</div>
			</div>
			<div class="pt-2 border-t border-gray-200 dark:border-gray-600">
				<p class="text-xs text-gray-500 dark:text-gray-500">
					<strong>Best viewing time:</strong> After 00:30 daily when batch processing completes. 
					No real-time updates needed - designed for business oversight and strategic planning.
				</p>
			</div>
		</div>
	</div>
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