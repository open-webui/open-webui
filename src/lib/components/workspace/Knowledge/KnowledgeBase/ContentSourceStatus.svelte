<script lang="ts">
	import { getContext } from 'svelte';
	import type { KnowledgeDataWithContentSource } from '$lib/types';
	import { 
		hasContentSourceSync, 
		getConfiguredProvider, 
		getSyncStatus, 
		formatLastSync,
		getProviderDisplayName,
		getProviderIcon
	} from '$lib/utils/content-sources';

	const i18n = getContext('i18n');

	export let knowledgeData: KnowledgeDataWithContentSource;

	$: hasSync = hasContentSourceSync(knowledgeData);
	$: provider = getConfiguredProvider(knowledgeData);
	$: syncStatus = getSyncStatus(knowledgeData);
	$: providerIcon = provider ? getProviderIcon(provider) : null;
</script>
{#if hasSync && provider}
	<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
		{#if providerIcon}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path d={providerIcon} />
			</svg>
		{/if}
		<span>
			{getProviderDisplayName(provider)}
			{#if syncStatus.sourceId}
				• {$i18n.t('Last sync')}: {formatLastSync(syncStatus.lastSync, $i18n)}
			{/if}
		</span>
	</div>
{/if}