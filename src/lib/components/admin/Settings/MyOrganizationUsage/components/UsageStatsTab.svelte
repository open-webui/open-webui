<script lang="ts">
	import { getContext } from 'svelte';
	import { FormatterService } from '../services/formatters';
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
		console.log('🔍 UsageStatsTab - total_unique_users:', usageData?.monthly_summary?.total_unique_users);
	}
	
	const tableHeaders = [
		$i18n.t('Date'),
		$i18n.t('Day'),
		$i18n.t('Tokens'),
		$i18n.t('Cost'),
		$i18n.t('Requests'),
		$i18n.t('Primary Model'),
		$i18n.t('Last Activity')
	];
	
	const formatters = {
		tokens: FormatterService.formatNumber,
		cost: (value: any) => FormatterService.formatDualCurrency(value?.cost || 0, value?.cost_pln || 0),
		requests: FormatterService.formatNumber
	};
</script>

<div class="space-y-6">
	<!-- Monthly Summary Insights -->
	<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
		<div class="mb-4">
			<h3 class="text-lg font-medium">{$i18n.t('Monthly Summary')}</h3>
		</div>
		
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
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
			
			<!-- Active Users -->
			<div>
				<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Active Users')} 👥</h4>
				<div class="space-y-2">
					<div class="flex justify-between">
						<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Aktywni użytkownicy')}:</span>
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
			<NoticeCard type="success" title="Updated daily at 13:00 CET" showIcon={true} />
		</div>
		
		<DataTable 
			headers={tableHeaders} 
			data={usageData.daily_breakdown || []} 
			emptyMessage="{$i18n.t('No usage data available for this month.')}"
			{formatters}
		>
			{#each data as day}
				<tr>
					<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
						{day?.date || 'N/A'}
					</td>
					<td class="px-4 py-3 whitespace-nowrap text-sm">
						{day?.day_name || 'N/A'}
					</td>
					<td class="px-4 py-3 whitespace-nowrap text-sm">
						{FormatterService.formatNumber(day?.tokens || 0)}
					</td>
					<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
						{FormatterService.formatDualCurrency(day?.cost || 0, day?.cost_pln || 0)}
					</td>
					<td class="px-4 py-3 whitespace-nowrap text-sm">
						{FormatterService.formatNumber(day?.requests || 0)}
					</td>
					<td class="px-4 py-3 whitespace-nowrap text-sm">
						{day?.primary_model || 'N/A'}
					</td>
					<td class="px-4 py-3 whitespace-nowrap text-sm">
						{day?.last_activity || 'N/A'}
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