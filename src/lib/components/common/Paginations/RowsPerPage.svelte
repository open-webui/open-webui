<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	import { getContext } from 'svelte';

	export let dataHandler: DataHandler;

	const i18n = getContext('i18n');
	const rowsPerPage = dataHandler.getRowsPerPage();
	const options = [5, 10, 20, 50, 100];
</script>

<div class=" flex justify-end w-full mb-3">
	<div class="flex space-x-2">
		{$i18n.t('Show')}
		<select
			class="dark:bg-gray-900 w-fit pr-8 rounded bg-transparent outline-none text-right"
			bind:value={$rowsPerPage}
		>
			{#each options as option}
				<option value={option}>
					{option}
				</option>
			{/each}
		</select>
		{$i18n.t('Entries')}
	</div>
</div>
