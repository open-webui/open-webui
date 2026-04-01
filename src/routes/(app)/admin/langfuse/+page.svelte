<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getLangfuseMetrics, type MetricRow } from '$lib/apis/langfuse';

	const i18n = getContext('i18n');

	const PERIODS = [
		{ value: 'today', label: 'Today' },
		{ value: 'day', label: 'Yesterday' },
		{ value: 'week', label: 'Last Week' },
		{ value: 'month', label: 'Last Month' },
		{ value: 'custom', label: 'Custom Days' }
	];

	let period = 'week';
	let customDays = 7;
	let rows: MetricRow[] = [];
	let loading = false;

	const loadMetrics = async () => {
		loading = true;
		try {
			rows = await getLangfuseMetrics(
				localStorage.token,
				period,
				period === 'custom' ? customDays : undefined
			);
		} catch (e) {
			toast.error(String(e) || 'Failed to fetch Langfuse metrics');
			rows = [];
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		loadMetrics();
	});

	const totalTokens = (data: MetricRow[]) => data.reduce((s, r) => s + r.tokens, 0);
	const totalCost = (data: MetricRow[]) => data.reduce((s, r) => s + r.cost, 0);
</script>

<div class="w-full px-4 py-6 space-y-4">
	<div class="flex items-center justify-between">
		<h2 class="text-xl font-semibold">{$i18n.t('Langfuse Metrics')}</h2>
	</div>

	<div class="flex flex-wrap items-end gap-3">
		<div class="flex flex-col gap-1">
			<label class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Period')}</label>
			<select
				bind:value={period}
				class="text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5"
			>
				{#each PERIODS as p}
					<option value={p.value}>{$i18n.t(p.label)}</option>
				{/each}
			</select>
		</div>

		{#if period === 'custom'}
			<div class="flex flex-col gap-1">
				<label class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Days')}</label>
				<input
					type="number"
					min="1"
					bind:value={customDays}
					class="w-24 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5"
				/>
			</div>
		{/if}

		<button
			on:click={loadMetrics}
			disabled={loading}
			class="px-4 py-1.5 rounded-lg text-sm bg-black text-white dark:bg-white dark:text-black hover:opacity-80 transition disabled:opacity-50"
		>
			{loading ? $i18n.t('Loading...') : $i18n.t('Refresh')}
		</button>
	</div>

	{#if loading}
		<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
	{:else if rows.length === 0}
		<div class="text-sm text-gray-500 dark:text-gray-400">
			{$i18n.t('No data for the selected period.')}
		</div>
	{:else}
		<div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
			<table class="w-full text-sm">
				<thead class="bg-gray-50 dark:bg-gray-850 text-gray-500 dark:text-gray-400">
					<tr>
						<th class="text-left px-4 py-2 font-medium">{$i18n.t('User')}</th>
						<th class="text-left px-4 py-2 font-medium">{$i18n.t('Model')}</th>
						<th class="text-right px-4 py-2 font-medium">{$i18n.t('Tokens')}</th>
						<th class="text-right px-4 py-2 font-medium">{$i18n.t('Cost')}</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-100 dark:divide-gray-800">
					{#each rows as row}
						<tr class="hover:bg-gray-50 dark:hover:bg-gray-850 transition">
							<td class="px-4 py-2 font-mono text-xs">{row.user}</td>
							<td class="px-4 py-2 text-gray-600 dark:text-gray-300">{row.model}</td>
							<td class="px-4 py-2 text-right">{row.tokens.toLocaleString()}</td>
							<td class="px-4 py-2 text-right">${row.cost.toFixed(4)}</td>
						</tr>
					{/each}
				</tbody>
				<tfoot class="bg-gray-50 dark:bg-gray-850 font-medium">
					<tr>
						<td class="px-4 py-2 text-gray-500 dark:text-gray-400" colspan="2"
							>{$i18n.t('Total')}</td
						>
						<td class="px-4 py-2 text-right">{totalTokens(rows).toLocaleString()}</td>
						<td class="px-4 py-2 text-right">${totalCost(rows).toFixed(4)}</td>
					</tr>
				</tfoot>
			</table>
		</div>
	{/if}
</div>
