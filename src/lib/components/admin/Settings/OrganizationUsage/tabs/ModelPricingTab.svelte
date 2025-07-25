<script>
	import { getContext } from 'svelte';
	import { formatCurrency, formatNumber } from '../utils/formatters.js';
	
	export let modelPricingData = [];
	export let loadingPricing = false;
	
	const i18n = getContext('i18n');
	
	const getCategoryColor = (category) => {
		const colors = {
			'Budget': 'bg-green-100 text-green-800',
			'Standard': 'bg-blue-100 text-blue-800',
			'Premium': 'bg-purple-100 text-purple-800',
			'Fast': 'bg-orange-100 text-orange-800',
			'Reasoning': 'bg-red-100 text-red-800'
		};
		return colors[category] || 'bg-gray-100 text-gray-800';
	};
</script>

<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
	<div class="flex items-center justify-between mb-4">
		<h3 class="text-lg font-medium">{$i18n.t('Available Models & Pricing')}</h3>
		<div class="text-sm text-gray-500 dark:text-gray-400">
			{#if loadingPricing}
				{$i18n.t('Loading pricing information...')}
			{:else}
				{$i18n.t('Current pricing rates')}
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
						{$i18n.t('Context')}
					</th>
					<th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
						{$i18n.t('Category')}
					</th>
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
				{#each modelPricingData as model}
					<tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
						<td class="px-4 py-3 whitespace-nowrap">
							<div class="text-sm font-medium text-gray-900 dark:text-white">
								{model.name}
							</div>
							<div class="text-xs text-gray-500">
								{model.id}
							</div>
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
							{model.provider}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
							{formatCurrency(model.price_per_million_input)}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
							{formatCurrency(model.price_per_million_output)}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white">
							{formatNumber(model.context_length)}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-center">
							<span class="px-2 py-1 text-xs rounded-full {getCategoryColor(model.category)}">
								{model.category}
							</span>
						</td>
					</tr>
				{/each}
			</tbody>
			</table>
		</div>
		
		<div class="mt-4 text-xs text-gray-500 dark:text-gray-400">
			<p><strong>Note:</strong> Prices shown are base costs before mAI markup (typically 1.3x)</p>
		</div>
	{/if}
</div>