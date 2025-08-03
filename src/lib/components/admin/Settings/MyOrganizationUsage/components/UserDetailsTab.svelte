<script lang="ts">
	import { getContext } from 'svelte';
	import { FormatterService } from '../services/formatters';
	import DataTable from './shared/DataTable.svelte';
	import NoticeCard from './shared/NoticeCard.svelte';
	import type { UserUsage } from '../types';
	
	export let userUsageData: UserUsage[];
	export let clientOrgIdValidated: boolean;
	
	const i18n = getContext('i18n');
	
	const tableHeaders = [
		$i18n.t('Email'),
		$i18n.t('Total Tokens'),
		$i18n.t('Cost'),
		$i18n.t('Days Active')
	];
</script>

<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
	<h3 class="text-lg font-medium mb-4">{$i18n.t('Usage by User')}</h3>
	
	{#if !clientOrgIdValidated}
		<NoticeCard type="warning" title="Organization data unavailable. User usage cannot be displayed.">
			<br>
			<span class="text-xs">{$i18n.t('Please refresh the page or contact your administrator.')}</span>
		</NoticeCard>
	{:else}
		<DataTable 
			headers={tableHeaders} 
			data={userUsageData || []} 
			emptyMessage="{$i18n.t('No user usage data available.')}"
		>
			<svelte:fragment slot="default" let:data>
				{#each data as userUsage}
					<tr>
						<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
							{userUsage.user_email}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm">
							{FormatterService.formatNumber(userUsage.total_tokens)}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm font-medium">
							{FormatterService.formatDualCurrency(userUsage.markup_cost, userUsage.cost_pln)}
						</td>
						<td class="px-4 py-3 whitespace-nowrap text-sm">
							{userUsage.days_active}
						</td>
					</tr>
				{/each}
			</svelte:fragment>
		</DataTable>
	{/if}
</div>