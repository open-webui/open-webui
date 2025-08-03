<script lang="ts">
	export let headers: string[];
	export let data: any[];
	export let emptyMessage: string = 'No data available';
	export let formatters: Record<string, (value: any) => string> = {};
	
	function formatValue(value: any, column: string): string {
		if (formatters[column]) {
			return formatters[column](value);
		}
		return value?.toString() || 'N/A';
	}
</script>

{#if data && data.length > 0}
	<div class="overflow-x-auto">
		<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
			<thead>
				<tr>
					{#each headers as header}
						<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							{header}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
				<slot {data} {formatValue} />
			</tbody>
		</table>
	</div>
{:else}
	<div class="text-center py-8">
		<svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
		</svg>
		<p class="text-gray-600 dark:text-gray-400 text-lg font-medium">{emptyMessage}</p>
	</div>
{/if}