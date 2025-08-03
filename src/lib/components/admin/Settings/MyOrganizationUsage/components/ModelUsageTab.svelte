<script lang="ts">
	import { getContext } from 'svelte';
	import { FormatterService } from '../services/formatters';
	import DataTable from './shared/DataTable.svelte';
	import NoticeCard from './shared/NoticeCard.svelte';
	import type { ModelUsage } from '../types';
	
	export let modelUsageData: ModelUsage[];
	export let clientOrgIdValidated: boolean;
	
	const i18n = getContext('i18n');
	
	const tableHeaders = [
		$i18n.t('Model'),
		$i18n.t('Provider'),
		$i18n.t('Total Tokens'),
		$i18n.t('Cost'),
		$i18n.t('Days Used')
	];
</script>

<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
	<h3 class="text-lg font-medium mb-4">{$i18n.t('Usage by Model')}</h3>
	
	{#if !clientOrgIdValidated}
		<NoticeCard type="warning" title="Organization data unavailable. Model usage cannot be displayed.">
			<br>
			<span class="text-xs">{$i18n.t('Please refresh the page or contact your administrator.')}</span>
		</NoticeCard>
	{:else}
		<DataTable 
			headers={tableHeaders} 
			data={modelUsageData || []} 
			emptyMessage="{$i18n.t('No model usage data available.')}"
		>
			<svelte:fragment slot="default" let:data>
				{#each data as modelUsage}
					<tr>
						<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
							{modelUsage.model_name}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm">
							{modelUsage.provider || 'N/A'}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm">
							{FormatterService.formatNumber(modelUsage.total_tokens)}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
							{FormatterService.formatDualCurrency(modelUsage.markup_cost, modelUsage.cost_pln)}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm">
							{modelUsage.days_used}
						</td>
					</tr>
				{/each}
			</svelte:fragment>
		</DataTable>
	{/if}
</div>