<script lang="ts">
	import { getContext } from 'svelte';
	import NoticeCard from './shared/NoticeCard.svelte';
	import type { SubscriptionData } from '../types';
	
	export let subscriptionData: SubscriptionData | null;
	export let clientOrgIdValidated: boolean;
	
	const i18n = getContext('i18n');
</script>

<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
	<h3 class="text-lg font-medium mb-4">{$i18n.t('Subscription Billing')}</h3>
	
	{#if !clientOrgIdValidated}
		<NoticeCard type="warning" title="Organization data unavailable. Subscription billing cannot be displayed.">
			<br>
			<span class="text-xs">{$i18n.t('Please refresh the page or contact your administrator.')}</span>
		</NoticeCard>
	{:else if subscriptionData}
		<!-- Current Month Summary -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
			<!-- Total Users -->
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
			
			<!-- Current Tier -->
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
			
			<!-- Monthly Total -->
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