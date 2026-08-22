<script lang="ts">
	import { getContext } from 'svelte';
	const i18n: any = getContext('i18n');
	export let items: any[] = [];
	export let label = '';
	export let onDelete: (id: string) => void = () => {};
	export let onEdit: (id: string) => void = () => {};
</script>

<div>
	<h2 class="mb-2 text-xs uppercase text-gray-500">{label}</h2>
	{#if items.length === 0}
		<p class="py-10 text-center text-sm text-gray-500">{$i18n.t('Nothing here yet')}</p>
	{:else}
		<div class="grid gap-2 sm:grid-cols-2">
			{#each items as item}
				<div
					class="flex items-center justify-between rounded-xl border border-gray-100 px-3 py-3 dark:border-gray-800"
				>
					<span class="truncate font-mono text-xs">{item.resource_id}</span>
					<div class="ml-3 flex shrink-0 gap-3">
						<button class="text-xs hover:underline" on:click={() => onEdit(item.resource_id)}
							>{$i18n.t('Edit')}</button
						>
						<button
							class="text-xs text-red-600 hover:underline"
							on:click={() => onDelete(item.resource_id)}>{$i18n.t('Delete')}</button
						>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
