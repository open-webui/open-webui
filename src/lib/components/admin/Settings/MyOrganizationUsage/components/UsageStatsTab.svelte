<script lang="ts">
	import { getContext } from 'svelte';
	import { FormatterService } from '../services/formatters';
	import DataTable from './shared/DataTable.svelte';
	import NoticeCard from './shared/NoticeCard.svelte';
	import type { UsageData } from '../types';
	
	export let usageData: UsageData;
	
	const i18n = getContext('i18n');
	
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
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-medium">{$i18n.t('Monthly Summary')}</h3>
			<NoticeCard type="info" title="Daily Batch Calculated" showIcon={true}>
				<div slot="actions" class="text-xs bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded">
					Business Intelligence
				</div>
			</NoticeCard>
		</div>
		
		<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
			<!-- Usage Averages -->
			<div>
				<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Usage Averages')} 📊</h4>
				<div class="space-y-2">
					<div class="flex justify-between">
						<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Daily Average')}:</span>
						<span class="text-sm font-medium">{FormatterService.formatNumber(usageData.monthly_summary?.average_daily_tokens || 0)} tokens</span>
					</div>
					<div class="flex justify-between">
						<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Usage Day Average')}:</span>
						<span class="text-sm font-medium">{FormatterService.formatNumber(usageData.monthly_summary?.average_usage_day_tokens || 0)} tokens</span>
					</div>
				</div>
			</div>
			
			<!-- Peak Usage -->
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
			
			<!-- Most Used -->
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
			<NoticeCard type="success" title="Updated at 00:00 Daily" showIcon={true} />
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
				<p class="text-gray-500 dark:text-gray-500 text-sm mt-2">Data is processed daily at 00:00. Usage will appear after first API calls.</p>
			</div>
		{/if}
	</div>
</div>