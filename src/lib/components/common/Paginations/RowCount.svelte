<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	import { getContext } from 'svelte';

	export let dataHandler: DataHandler;

	const i18n = getContext('i18n');
	const rowCount = dataHandler.getRowCount();
</script>

<div>
	{#if $rowCount.total > 0}
		{$i18n.t(`Showing {{countStart}} to {{countEnd}} of {{countTotal}} users`, {
			countStart: $rowCount.start,
			countEnd: $rowCount.end,
			countTotal: $rowCount.total
		})}
	{:else}
		{$i18n.t('No entries found')}
	{/if}
</div>
