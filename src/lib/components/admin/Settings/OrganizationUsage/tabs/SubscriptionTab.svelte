<script>
	import { getContext } from 'svelte';
	import { formatNumber, formatPercentage } from '../utils/formatters.js';
	
	export let subscriptionData = null;
	export let clientOrgIdValidated = false;
	export let loading = false;
	
	const i18n = getContext('i18n');
</script>

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
	{:else if loading}
		<div class="flex items-center justify-center py-8">
			<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900 dark:border-white"></div>
			<span class="ml-2 text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Loading subscription data...')}</span>
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
							{subscriptionData.current_month.pricing_tier}
						</p>
					</div>
				</div>
			</div>
			
			<div class="bg-gradient-to-r from-green-50 to-green-100 dark:from-green-900 dark:to-green-800 rounded-lg p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-green-600 dark:text-green-400">Monthly Cost</p>
						<p class="text-2xl font-semibold text-green-900 dark:text-green-100">
							{subscriptionData.current_month.total_cost_pln} PLN
						</p>
						<p class="text-xs text-green-700 dark:text-green-300 mt-1">
							Per user: {subscriptionData.current_month.per_user_cost_pln} PLN
						</p>
					</div>
				</div>
			</div>
			
			<div class="bg-gradient-to-r from-purple-50 to-purple-100 dark:from-purple-900 dark:to-purple-800 rounded-lg p-6">
				<div class="flex items-center justify-between">
					<div>
						<p class="text-sm font-medium text-purple-600 dark:text-purple-400">Billing Period</p>
						<p class="text-lg font-semibold text-purple-900 dark:text-purple-100">
							{subscriptionData.current_month.billing_month}
						</p>
						<p class="text-xs text-purple-700 dark:text-purple-300 mt-1">
							Days in month: {subscriptionData.current_month.days_in_month}
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- User Details Table -->
		<div class="mb-6">
			<h4 class="text-md font-medium mb-3">User Billing Details</h4>
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
								Days Remaining
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
									{formatPercentage(userDetail.billing_proportion)}
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
		<p class="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
			{$i18n.t('No subscription billing data available.')}
		</p>
	{/if}
</div>