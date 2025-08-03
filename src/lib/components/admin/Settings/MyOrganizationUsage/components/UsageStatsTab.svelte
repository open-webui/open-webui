<script lang="ts">
	import { getContext } from 'svelte';
	import { FormatterService } from '../services/formatters';
	import { DateHelperService } from '../services/dateHelpers';
	import DataTable from './shared/DataTable.svelte';
	import NoticeCard from './shared/NoticeCard.svelte';
	import type { UsageData } from '../types';
	
	export let usageData: UsageData;
	
	const i18n = getContext('i18n');
	
	// Debug: Log usage data to console
	$: {
		console.log('🔍 UsageStatsTab - usageData:', usageData);
		console.log('🔍 UsageStatsTab - monthly_summary:', usageData?.monthly_summary);
		console.log('🔍 UsageStatsTab - top_models:', usageData?.monthly_summary?.top_models);
	}
	
	const tableHeaders = [
		$i18n.t('Date'),
		$i18n.t('Tokens'),
		$i18n.t('Cost')
	];
	
	const formatters = {
		tokens: FormatterService.formatNumber,
		cost: (value: any) => FormatterService.formatDualCurrency(value?.cost || 0, value?.cost_pln || 0)
	};
</script>

<div class="space-y-6">
	<!-- Monthly Summary Insights -->
	<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
		<div class="mb-4">
			<h3 class="text-lg font-medium">{$i18n.t('Monthly Summary')}</h3>
		</div>
		
		<div class="grid grid-cols-1 gap-6">
			<!-- Top Models -->
			<div>
				<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Top 3 Models')} ⭐</h4>
				<div class="space-y-2">
					{#if usageData.monthly_summary?.top_models && usageData.monthly_summary.top_models.length > 0}
						{#each usageData.monthly_summary.top_models as model, index}
							<div class="flex justify-between">
								<span class="text-sm text-gray-600 dark:text-gray-400">{index + 1}. {model.model_name}:</span>
								<span class="text-sm font-medium">{FormatterService.formatNumber(model.total_tokens)} tokens</span>
							</div>
						{/each}
					{:else}
						<div class="flex justify-between">
							<span class="text-sm text-gray-600 dark:text-gray-400">No models:</span>
							<span class="text-sm font-medium">N/A</span>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Daily Breakdown Table -->
	<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-medium">{$i18n.t('Daily Breakdown')} - {usageData.current_month?.month || 'Current Month'}</h3>
			<NoticeCard type="success" title="Updated daily at 13:00 CET" showIcon={true} />
		</div>
		
		<DataTable 
			headers={tableHeaders} 
			data={usageData.daily_breakdown || []} 
			emptyMessage="{$i18n.t('No usage data available for this month.')}"
			{formatters}
			let:data
		>
			{#each data as day}
				<tr class="{DateHelperService.isLiveData(day?.date) ? 'bg-blue-50 dark:bg-blue-900/20' : ''}">
					<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
						{#if DateHelperService.isLiveData(day?.date)}
							<span class="flex items-center" title="Estimated live data - updates throughout the day">
								{DateHelperService.formatDateWithLiveIndicator(day?.date)}
								<svg class="w-3 h-3 ml-1 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
								</svg>
							</span>
						{:else}
							{FormatterService.formatDate(day?.date || 'N/A')}
						{/if}
					</td>
					<td class="px-4 py-3 whitespace-nowrap text-sm">
						{FormatterService.formatNumber(day?.tokens || 0)}
					</td>
					<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
						{#if DateHelperService.isLiveData(day?.date)}
							<span title="Estimated live cost - may change throughout the day">
								~{FormatterService.formatDualCurrency(day?.cost || 0, day?.cost_pln || 0)}
							</span>
						{:else}
							{FormatterService.formatDualCurrency(day?.cost || 0, day?.cost_pln || 0)}
						{/if}
					</td>
				</tr>
			{/each}
		</DataTable>
		
		{#if !usageData.daily_breakdown || usageData.daily_breakdown.length === 0}
			<div class="text-center py-8">
				<p class="text-gray-500 dark:text-gray-500 text-sm mt-2">Data is processed daily at 13:00 CET using current NBP exchange rate. Usage will appear after first API calls.</p>
			</div>
		{/if}
	</div>
</div>