<script>
	import { getContext } from 'svelte';
	import { formatNumber, formatDualCurrency } from '../utils/formatters.js';
	
	export let modelUsageData = [];
	export let clientOrgIdValidated = false;
	export let loading = false;
	
	const i18n = getContext('i18n');
</script>

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
	{:else if loading}
		<div class="flex items-center justify-center py-8">
			<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900 dark:border-white"></div>
			<span class="ml-2 text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Loading model data...')}</span>
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
		<p class="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
			{$i18n.t('No model usage data available for this period.')}
		</p>
	{/if}
</div>