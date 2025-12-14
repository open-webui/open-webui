<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	import WebSearchResults from '../WebSearchResults.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import { t } from 'i18next';

	export let status = null;
	export let done = false;
</script>

{#if !status?.hidden}
	<div class="status-description flex items-center gap-2 py-0.5 w-full text-left">
		{#if status?.action === 'web_search' && (status?.urls || status?.items)}
			<WebSearchResults {status}>
				<div class="flex flex-col justify-center -space-y-0.5">
					<div
						class="{(done || status?.done) === false
							? 'shimmer'
							: ''} text-base line-clamp-1 text-wrap"
					>
						<!-- $i18n.t("Generating search query") -->
						<!-- $i18n.t("No search query generated") -->
						<!-- $i18n.t('Searched {{count}} sites') -->
						{#if status?.description?.includes('{{count}}')}
							{$i18n.t(status?.description, {
								count: (status?.urls || status?.items).length
							})}
						{:else if status?.description === 'No search query generated'}
							{$i18n.t('No search query generated')}
						{:else if status?.description === 'Generating search query'}
							{$i18n.t('Generating search query')}
						{:else}
							{status?.description}
						{/if}
					</div>
				</div>
			</WebSearchResults>
		{:else if status?.action === 'web_search_queries_generated' && status?.queries}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{$i18n.t(`Searching`)}
				</div>

				<div class=" flex gap-1 flex-wrap mt-2">
					{#each status.queries as query, idx (query)}
						<div
							class="bg-gray-50 dark:bg-gray-850 flex rounded-lg py-1 px-2 items-center gap-1 text-xs"
						>
							<div>
								<Search className="size-3" />
							</div>

							<span class="line-clamp-1">
								{query}
							</span>
						</div>
					{/each}
				</div>
			</div>
		{:else if status?.action === 'queries_generated' && status?.queries}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{$i18n.t(`Querying`)}
				</div>

				<div class=" flex gap-1 flex-wrap mt-2">
					{#each status.queries as query, idx (query)}
						<div
							class="bg-gray-50 dark:bg-gray-850 flex rounded-lg py-1 px-2 items-center gap-1 text-xs"
						>
							<div>
								<Search className="size-3" />
							</div>

							<span class="line-clamp-1">
								{query}
							</span>
						</div>
					{/each}
				</div>
			</div>
		{:else if status?.action === 'sources_retrieved' && status?.count !== undefined}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					{#if status.count === 0}
						{$i18n.t('No sources found')}
					{:else if status.count === 1}
						{$i18n.t('Retrieved 1 source')}
					{:else}
						<!-- {$i18n.t('Source')} -->
						<!-- {$i18n.t('No source available')} -->
						<!-- {$i18n.t('No distance available')} -->
						<!-- {$i18n.t('Retrieved {{count}} sources')} -->
						{$i18n.t('Retrieved {{count}} sources', {
							count: status.count
						})}
					{/if}
				</div>
			</div>
		{:else if status?.action === '🖼️'}
			<div class="flex flex-col justify-center -space-y-0.5 w-full">
				{#if status?.done && (status.vision_prompt || status.vision_response)}
					<Collapsible
						title={status?.description}
						open={false}
						className="w-full"
						buttonClassName="text-gray-500 dark:text-gray-500"
					>
						<div slot="content" class="mt-2 space-y-2 text-sm px-2">
							{#if status.vision_prompt}
								<div><strong>System Prompt:</strong></div>
								<pre class="p-2 bg-gray-50 dark:bg-gray-850 rounded text-xs overflow-auto max-h-32 whitespace-pre-wrap">{status.vision_prompt}</pre>
							{/if}
							{#if status.vision_response}
								<div><strong>Vision Model Response:</strong></div>
								<pre class="p-2 bg-gray-50 dark:bg-gray-850 rounded text-xs overflow-auto max-h-48 whitespace-pre-wrap">{status.vision_response}</pre>
							{/if}
							{#if status.error}
								<div class="text-red-600"><strong>Error:</strong> {status.error}</div>
							{/if}
						</div>
					</Collapsible>
				{:else}
					<div class="{(done || status?.done) === false ? 'shimmer' : ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap">
						{status?.description}
					</div>
				{/if}
			</div>
		{:else if status?.action === '📄' || status?.action === '📄❌'}
			<div class="flex flex-col justify-center -space-y-0.5 w-full">
				{#if status?.done && (status.vision_prompt || status.vision_response)}
					<Collapsible
						title={status?.description}
						open={false}
						className="w-full"
						buttonClassName="text-gray-500 dark:text-gray-500"
					>
						<div slot="content" class="mt-2 space-y-2 text-sm px-2">
							{#if status.vision_prompt}
								<div><strong>System Prompt:</strong></div>
								<pre class="p-2 bg-gray-50 dark:bg-gray-850 rounded text-xs overflow-auto max-h-32 whitespace-pre-wrap">{status.vision_prompt}</pre>
							{/if}
							{#if status.vision_response}
								<div><strong>PDF Vision Analysis:</strong></div>
								<pre class="p-2 bg-gray-50 dark:bg-gray-850 rounded text-xs overflow-auto max-h-64 whitespace-pre-wrap">{status.vision_response}</pre>
							{/if}
							{#if status.error}
								<div class="text-red-600"><strong>Error:</strong> {status.error}</div>
							{/if}
						</div>
					</Collapsible>
				{:else}
					<div class="{(done || status?.done) === false ? 'shimmer' : ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap">
						{status?.description}
					</div>
				{/if}
			</div>
		{:else}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{(done || status?.done) === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
				>
					<!-- $i18n.t(`Searching "{{searchQuery}}"`) -->
					{#if status?.description?.includes('{{searchQuery}}')}
						{$i18n.t(status?.description, {
							searchQuery: status?.query
						})}
					{:else if status?.description === 'No search query generated'}
						{$i18n.t('No search query generated')}
					{:else if status?.description === 'Generating search query'}
						{$i18n.t('Generating search query')}
					{:else if status?.description === 'Searching the web'}
						{$i18n.t('Searching the web')}
					{:else}
						{status?.description}
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}
