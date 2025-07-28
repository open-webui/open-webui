<script lang="ts">
	/**
	 * My Organization Usage Container
	 * Component Composition pattern implementation
	 * Orchestrates all tab components and state management
	 */
	
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { user } from '$lib/stores';
	
	// Component imports - Clean separation of concerns
	import UsageStatsTab from './components/UsageStatsTab.svelte';
	import UserDetailsTab from './components/UserDetailsTab.svelte';
	import ModelUsageTab from './components/ModelUsageTab.svelte';
	import BillingTab from './components/BillingTab.svelte';
	import ModelPricingTab from './components/ModelPricingTab.svelte';
	import LoadingState from './components/shared/LoadingState.svelte';
	import StatCard from './components/shared/StatCard.svelte';
	import NoticeCard from './components/shared/NoticeCard.svelte';
	
	// Service imports - Data access layer
	import { OrganizationUsageService } from './services/organizationUsageService';
	import { PricingService } from './services/pricingService';
	import { FormatterService } from './services/formatters';
	
	// Store imports - State management
	import { usageStore, usageActions, pricingStore, pricingActions, billingStore, billingActions } from './stores';
	
	// Type imports - Type safety
	import type { TabType } from './types';
	
	const i18n = getContext('i18n');
	
	// Reactive store subscriptions
	$: ({ usageData, userUsageData, modelUsageData, clientOrgId, clientOrgIdValidated, activeTab, loading } = $usageStore);
	$: ({ modelPricingData, loading: pricingLoading } = $pricingStore);
	$: ({ subscriptionData } = $billingStore);
	
	// Reactive: Dynamic month name for Total Cost display
	$: currentMonthName = new Date().toLocaleDateString('en-US', { 
		month: 'long', 
		year: 'numeric' 
	});
	
	// Reactive: Ensure non-admin users don't access admin-only tabs
	$: if ($user?.role !== 'admin' && (activeTab === 'users' || activeTab === 'models' || activeTab === 'subscription')) {
		usageActions.setActiveTab('stats');
	}
	
	onMount(async () => {
		await loadInitialData();
	});
	
	/**
	 * Load initial usage data on component mount
	 */
	const loadInitialData = async (): Promise<void> => {
		usageActions.setLoading(true);
		
		try {
			const result = await OrganizationUsageService.getUsageSummary($user.token);
			
			if (result.success && result.data) {
				usageActions.setUsageData(result.data, result.clientId);
			} else {
				console.warn('Failed to load usage data:', result.error);
				const emptyData = OrganizationUsageService.createEmptyUsageData('No Data');
				usageActions.setUsageData(emptyData);
				
				if (result.error === 'Request timeout') {
					toast.error($i18n.t('Request timed out. The server may be slow. Please try again.'));
				} else {
					toast.error($i18n.t('Failed to load usage statistics'));
				}
			}
		} catch (error) {
			console.error('Error loading initial data:', error);
			const errorData = OrganizationUsageService.createEmptyUsageData('Error Loading Data');
			usageActions.setUsageData(errorData);
			toast.error($i18n.t('Failed to load usage statistics'));
		} finally {
			usageActions.setLoading(false);
		}
	};
	
	/**
	 * Load user usage data (admin only)
	 */
	const loadUserUsage = async (): Promise<void> => {
		if (!clientOrgIdValidated || !clientOrgId) {
			console.warn('Cannot load user usage: client organization ID not available');
			toast.error($i18n.t('Unable to load user usage data. Please try refreshing the page.'));
			return;
		}
		
		const result = await OrganizationUsageService.getUserUsage($user.token, clientOrgId);
		if (result.success && result.data) {
			usageActions.setUserUsageData(result.data);
		} else {
			console.error('Failed to load user usage:', result.error);
			toast.error($i18n.t('Failed to load user usage data'));
			usageActions.setUserUsageData([]);
		}
	};
	
	/**
	 * Load model usage data (admin only)
	 */
	const loadModelUsage = async (): Promise<void> => {
		if (!clientOrgIdValidated || !clientOrgId) {
			console.warn('Cannot load model usage: client organization ID not available');
			toast.error($i18n.t('Unable to load model usage data. Please try refreshing the page.'));
			return;
		}
		
		const result = await OrganizationUsageService.getModelUsage($user.token, clientOrgId);
		if (result.success && result.data) {
			usageActions.setModelUsageData(result.data);
		} else {
			console.error('Failed to load model usage:', result.error);
			toast.error($i18n.t('Failed to load model usage data'));
			usageActions.setModelUsageData([]);
		}
	};
	
	/**
	 * Load subscription billing data (admin only)
	 */
	const loadSubscriptionData = async (): Promise<void> => {
		if (!clientOrgIdValidated || !clientOrgId) {
			console.warn('Cannot load subscription data: client organization ID not available');
			toast.error($i18n.t('Unable to load subscription data. Please try refreshing the page.'));
			return;
		}
		
		const result = await OrganizationUsageService.getSubscriptionBilling($user.token, clientOrgId);
		if (result.success && result.data) {
			billingActions.setSubscriptionData(result.data);
		} else {
			console.error('Failed to load subscription data:', result.error);
			toast.error($i18n.t('Failed to load subscription billing data'));
		}
	};
	
	/**
	 * Load model pricing data
	 */
	const loadModelPricing = async (): Promise<void> => {
		console.log('[DEBUG] Container: Starting loadModelPricing()');
		pricingActions.setLoading(true);
		
		try {
			const result = await PricingService.getModelPricing();
			console.log('[DEBUG] Container: Received pricing result:', result);
			console.log('[DEBUG] Container: Data count:', result.data?.length);
			
			pricingActions.setPricingData(result.data);
			console.log('[DEBUG] Container: Called setPricingData with data count:', result.data?.length);
			
			if (result.error) {
				console.warn('Pricing API error, using fallback data:', result.error);
			}
		} catch (error) {
			console.error('Failed to load model pricing:', error);
			toast.error($i18n.t('Failed to load model pricing'));
		} finally {
			pricingActions.setLoading(false);
			console.log('[DEBUG] Container: Finished loadModelPricing()');
		}
	};
	
	/**
	 * Handle tab change with lazy loading
	 */
	const handleTabChange = async (tab: TabType): Promise<void> => {
		// Prevent non-admin users from accessing admin-only tabs
		if ($user?.role !== 'admin' && (tab === 'users' || tab === 'models' || tab === 'subscription')) {
			toast.error($i18n.t('Access denied. Administrator privileges required.'));
			return;
		}
		
		usageActions.setActiveTab(tab);
		
		// Lazy load data for specific tabs
		if (clientOrgIdValidated && clientOrgId) {
			if (tab === 'users' && userUsageData.length === 0) {
				await loadUserUsage();
			} else if (tab === 'models' && modelUsageData.length === 0) {
				await loadModelUsage();
			} else if (tab === 'subscription' && subscriptionData === null) {
				await loadSubscriptionData();
			}
		} else if (tab === 'users' || tab === 'models' || tab === 'subscription') {
			console.warn(`Cannot load ${tab} data: client organization ID not validated`);
			toast.error($i18n.t('Organization data not available. Please refresh the page.'));
		}
		
		// Pricing tab doesn't need client ID
		if (tab === 'pricing' && modelPricingData.length === 0) {
			console.log('[DEBUG] Container: Loading pricing data for pricing tab');
			await loadModelPricing();
		} else if (tab === 'pricing') {
			console.log('[DEBUG] Container: Pricing tab already has data, count:', modelPricingData.length);
		}
	};
</script>

<div class="mb-6">
	<!-- Header -->
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
	{#if usageData?.current_month?.exchange_rate_info}
		<NoticeCard type="info" title="Exchange rate: 1 USD = {usageData.current_month.exchange_rate_info.usd_pln.toFixed(4)} PLN (NBP rate from {usageData.current_month.exchange_rate_info.effective_date})" />
	{:else if usageData?.pln_conversion_available === false}
		<NoticeCard type="warning" title="PLN conversion temporarily unavailable - showing USD only" />
	{/if}

	<!-- Daily Batch Processing Status Notice -->
	<NoticeCard type="info" title="Daily Batch Processing: Data consolidated at 00:00 with NBP exchange rates & monthly totals (1st to current day)">
		<div slot="actions" class="text-xs bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded">
			Business Intelligence
		</div>
	</NoticeCard>

	<!-- Monthly Summary Cards -->
	{#if usageData}
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
			<StatCard
				title="Total Tokens"
				value={FormatterService.formatNumber(usageData.current_month?.total_tokens || 0)}
				subtitle="{usageData.current_month?.month || 'Loading...'} • Batch Calculated"
				iconColor="blue"
				iconPath="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
			/>
			
			<StatCard
				title="Total Cost"
				value={FormatterService.formatDualCurrency(usageData.current_month?.total_cost || 0, usageData.current_month?.total_cost_pln || 0)}
				subtitle="{currentMonthName} • Batch Calculated"
				iconColor="green"
				iconPath="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
			/>
			
		</div>
	{/if}

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
	{#if loading.loading}
		<LoadingState message="{$i18n.t('Loading daily batch data...')}" />
	{:else if activeTab === 'stats' && usageData}
		<UsageStatsTab {usageData} />
	{:else if activeTab === 'users' && $user?.role === 'admin'}
		<UserDetailsTab {userUsageData} {clientOrgIdValidated} />
	{:else if activeTab === 'models' && $user?.role === 'admin'}
		<ModelUsageTab {modelUsageData} {clientOrgIdValidated} />
	{:else if activeTab === 'subscription' && $user?.role === 'admin'}
		<BillingTab {subscriptionData} {clientOrgIdValidated} />
	{:else if activeTab === 'pricing'}
		<ModelPricingTab {modelPricingData} loading={pricingLoading} />
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