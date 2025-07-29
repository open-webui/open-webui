<script lang="ts">
	import { getContext } from 'svelte';
	import { FormatterService } from '../services/formatters';
	import { PricingService } from '../services/pricingService';
	import LoadingState from './shared/LoadingState.svelte';
	import NoticeCard from './shared/NoticeCard.svelte';
	import DataTable from './shared/DataTable.svelte';
	import type { ModelPricing, LoadingState as LoadingStateType } from '../types';
	
	export let modelPricingData: ModelPricing[];
	export let loading: LoadingStateType;
	
	const i18n = getContext('i18n');
	
	// Debug reactive statements
	$: {
		console.log('[DEBUG] ModelPricingTab: Received modelPricingData count:', modelPricingData?.length);
		console.log('[DEBUG] ModelPricingTab: Loading state:', loading);
		console.log('[DEBUG] ModelPricingTab: Data sample:', modelPricingData?.[0]);
	}
	
	const tableHeaders = [
		$i18n.t('Model'),
		$i18n.t('Provider'),
		$i18n.t('Input (per 1M tokens)'),
		$i18n.t('Output (per 1M tokens)'),
		$i18n.t('Context Length'),
		$i18n.t('Category')
	];
	
	const categories = PricingService.getCategories();
</script>

<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
	<div class="mb-4">
		<h3 class="text-lg font-medium">{$i18n.t('Available Models & Pricing')}</h3>
		<div class="text-sm text-gray-500 dark:text-gray-400">
			{#if loading.loading}
				{$i18n.t('Loading pricing information...')}
			{:else}
				{$i18n.t('Prices updated daily at 13:00 CET')}
			{/if}
		</div>
	</div>
	
	<NoticeCard type="info" title="Pricing Information">
		<p>• All prices are per 1 million tokens in USD</p>
		<p>• Input and output tokens are priced separately</p>
		<p>• Context length shows maximum input size per request</p>
	</NoticeCard>
	
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
		<!-- Category filters -->
		<div class="flex flex-wrap gap-2">
			{#each categories as category}
				<span class="px-2 py-1 text-xs rounded-full {PricingService.getCategoryColorClass(category)}">
					{category}
				</span>
			{/each}
		</div>
		<div class="text-right text-sm text-gray-600 dark:text-gray-400">
			{modelPricingData.length} models available
		</div>
	</div>
	
	{#if loading.loading}
		<LoadingState message="{$i18n.t('Loading model pricing...')}" />
	{:else}
		<DataTable 
			headers={tableHeaders} 
			data={modelPricingData} 
			emptyMessage="No pricing data available"
		>
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
						{FormatterService.formatNumber(model.context_length)} tokens
					</td>
					<td class="px-4 py-3 whitespace-nowrap">
						<span class="px-2 py-1 text-xs rounded-full {PricingService.getCategoryColorClass(model.category)}">
							{model.category}
						</span>
					</td>
				</tr>
			{/each}
		</DataTable>
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
			<p class="text-gray-600 dark:text-gray-400 mb-1">{modelPricingData.length} premium AI models available</p>
			<p class="text-xs text-gray-500">Choose the best model for your task</p>
		</div>
	</div>
</div>