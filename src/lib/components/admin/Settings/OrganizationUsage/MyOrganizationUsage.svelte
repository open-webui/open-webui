<script>
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';
	import { 
		getClientUsageSummary, 
		getTodayUsage, 
		getUsageByUser, 
		getUsageByModel, 
		getMAIModelPricing, 
		getSubscriptionBilling 
	} from '$lib/apis/organizations';
	
	// Import components
	import TabNavigation from './components/TabNavigation.svelte';
	import StatCard from './components/StatCard.svelte';
	import ExchangeRateNotice from './components/ExchangeRateNotice.svelte';
	import UsageStatsTab from './tabs/UsageStatsTab.svelte';
	import UserUsageTab from './tabs/UserUsageTab.svelte';
	import ModelUsageTab from './tabs/ModelUsageTab.svelte';
	import ModelPricingTab from './tabs/ModelPricingTab.svelte';
	import SubscriptionTab from './tabs/SubscriptionTab.svelte';
	
	// Import utilities
	import { formatNumber, formatDualCurrency } from './utils/formatters.js';
	
	const i18n = getContext('i18n');

	let loading = false;
	let activeTab = 'stats';
	
	// Core data
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
		client_org_name: 'My Organization'
	};
	
	// Tab-specific data
	let userUsageData = [];
	let modelUsageData = [];
	let subscriptionData = null;
	let modelPricingData = [];
	
	// State management
	let clientOrgId = null;
	let clientOrgIdValidated = false;
	let loadingPricing = false;
	let loadingUsers = false;
	let loadingModels = false;
	let loadingSubscription = false;
	
	// Fallback pricing data
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
		}
	];
	
	// Load initial data
	const loadUsageData = async () => {
		loading = true;
		try {
			const response = await getClientUsageSummary(localStorage.token);
			
			if (response && response.today) {
				usageData = response;
				
				// Extract and validate client org ID
				if (response.client_org_id) {
					clientOrgId = response.client_org_id;
					clientOrgIdValidated = true;
				}
			}
		} catch (error) {
			console.error('Error loading usage data:', error);
			toast.error($i18n.t('Failed to load usage data'));
		} finally {
			loading = false;
		}
	};
	
	// Load user usage data
	const loadUserUsage = async () => {
		if (!clientOrgIdValidated || !clientOrgId) return;
		
		loadingUsers = true;
		try {
			const response = await getUsageByUser(localStorage.token, clientOrgId);
			if (response && response.users) {
				userUsageData = response.users;
			}
		} catch (error) {
			console.error('Error loading user usage:', error);
			toast.error($i18n.t('Failed to load user usage data'));
		} finally {
			loadingUsers = false;
		}
	};
	
	// Load model usage data
	const loadModelUsage = async () => {
		if (!clientOrgIdValidated || !clientOrgId) return;
		
		loadingModels = true;
		try {
			const response = await getUsageByModel(localStorage.token, clientOrgId);
			if (response && response.models) {
				modelUsageData = response.models;
			}
		} catch (error) {
			console.error('Error loading model usage:', error);
			toast.error($i18n.t('Failed to load model usage data'));
		} finally {
			loadingModels = false;
		}
	};
	
	// Load subscription data
	const loadSubscriptionData = async () => {
		if (!clientOrgIdValidated || !clientOrgId) return;
		
		loadingSubscription = true;
		try {
			const response = await getSubscriptionBilling(localStorage.token, clientOrgId);
			if (response && response.current_month) {
				subscriptionData = response;
			}
		} catch (error) {
			console.error('Error loading subscription data:', error);
			toast.error($i18n.t('Failed to load subscription billing data'));
		} finally {
			loadingSubscription = false;
		}
	};
	
	// Load model pricing
	const loadModelPricing = async () => {
		loadingPricing = true;
		try {
			const response = await getMAIModelPricing(localStorage.token);
			if (response && Array.isArray(response)) {
				modelPricingData = response.sort((a, b) => {
					if (a.category !== b.category) {
						const categoryOrder = ['Budget', 'Fast', 'Standard', 'Premium', 'Reasoning'];
						return categoryOrder.indexOf(a.category) - categoryOrder.indexOf(b.category);
					}
					return a.price_per_million_input - b.price_per_million_input;
				});
			} else {
				modelPricingData = fallbackPricingData;
			}
		} catch (error) {
			console.error('Error loading model pricing:', error);
			modelPricingData = fallbackPricingData;
			toast.error($i18n.t('Using cached pricing data'));
		} finally {
			loadingPricing = false;
		}
	};
	
	// Handle tab changes
	const handleTabChange = async (tab) => {
		activeTab = tab;
		
		// Load data for specific tabs if needed
		if (clientOrgIdValidated && clientOrgId) {
			if (tab === 'users' && userUsageData.length === 0) {
				await loadUserUsage();
			} else if (tab === 'models' && modelUsageData.length === 0) {
				await loadModelUsage();
			} else if (tab === 'subscription' && subscriptionData === null) {
				await loadSubscriptionData();
			}
		}
		
		// Pricing tab doesn't need client ID
		if (tab === 'pricing' && modelPricingData.length === 0) {
			await loadModelPricing();
		}
	};
	
	onMount(() => {
		loadUsageData();
	});
</script>

<div class="mb-6">
	<div class="flex items-center justify-between mb-4">
		<h2 class="text-lg font-semibold">{$i18n.t('My Organization Usage')}</h2>
	</div>

	<!-- Exchange Rate Notice -->
	<ExchangeRateNotice 
		exchangeRateInfo={usageData.exchange_rate_info}
		plnConversionAvailable={usageData.pln_conversion_available}
	/>

	<!-- Summary Cards -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
		<!-- Today's Usage -->
		<StatCard
			title="Today's Tokens"
			value={formatNumber(usageData.today.tokens)}
			isLive={true}
			icon='<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>'
		/>
		
		<!-- Today's Cost -->
		<StatCard
			title="Today's Cost"
			value={formatDualCurrency(usageData.today.cost, usageData.today.cost_pln)}
			subtext={`${formatNumber(usageData.today.requests)} requests`}
			iconBgColor="bg-green-100 dark:bg-green-900"
			iconColor="text-green-600 dark:text-green-400"
			icon='<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>'
		/>
		
		<!-- Month Total -->
		<StatCard
			title="Month Total"
			value={formatDualCurrency(usageData.this_month.cost, usageData.this_month.cost_pln)}
			subtext={`${formatNumber(usageData.this_month.tokens)} tokens`}
			iconBgColor="bg-purple-100 dark:bg-purple-900"
			iconColor="text-purple-600 dark:text-purple-400"
			icon='<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>'
		/>
	</div>

	<!-- Tab Navigation -->
	<TabNavigation 
		{activeTab}
		onTabChange={handleTabChange}
		isAdmin={$user?.role === 'admin'}
	/>

	<!-- Tab Content -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white"></div>
			<span class="ml-2 text-gray-600 dark:text-gray-400">{$i18n.t('Loading usage data...')}</span>
		</div>
	{:else if activeTab === 'stats'}
		<UsageStatsTab {usageData} />
	{:else if activeTab === 'users' && $user?.role === 'admin'}
		<UserUsageTab 
			{userUsageData} 
			{clientOrgIdValidated}
			loading={loadingUsers}
		/>
	{:else if activeTab === 'models' && $user?.role === 'admin'}
		<ModelUsageTab 
			{modelUsageData}
			{clientOrgIdValidated}
			loading={loadingModels}
		/>
	{:else if activeTab === 'subscription' && $user?.role === 'admin'}
		<SubscriptionTab 
			{subscriptionData}
			{clientOrgIdValidated}
			loading={loadingSubscription}
		/>
	{:else if activeTab === 'pricing'}
		<ModelPricingTab 
			{modelPricingData}
			{loadingPricing}
		/>
	{/if}
</div>