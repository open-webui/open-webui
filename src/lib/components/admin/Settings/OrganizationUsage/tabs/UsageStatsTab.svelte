<script>
	import { getContext } from 'svelte';
	import { formatNumber, formatDualCurrency } from '../utils/formatters.js';
	
	export let usageData = {};
	
	const i18n = getContext('i18n');
</script>

<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
	<h3 class="text-lg font-medium mb-4">{$i18n.t('Usage Statistics')}</h3>
	
	<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
		<div>
			<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Today vs Month')}</h4>
			<div class="space-y-2">
				<div class="flex justify-between">
					<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Today Tokens')}:</span>
					<span class="text-sm font-medium">{formatNumber(usageData.today?.tokens)}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Month Total')}:</span>
					<span class="text-sm font-medium">{formatNumber(usageData.this_month?.tokens)}</span>
				</div>
			</div>
		</div>
		
		<div>
			<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{$i18n.t('Cost Analysis')}</h4>
			<div class="space-y-2">
				<div class="flex justify-between">
					<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Today Cost')}:</span>
					<span class="text-sm font-medium">{formatDualCurrency(usageData.today?.cost, usageData.today?.cost_pln)}</span>
				</div>
				<div class="flex justify-between">
					<span class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Month Total')}:</span>
					<span class="text-sm font-medium">{formatDualCurrency(usageData.this_month?.cost, usageData.this_month?.cost_pln)}</span>
				</div>
			</div>
		</div>
	</div>
</div>