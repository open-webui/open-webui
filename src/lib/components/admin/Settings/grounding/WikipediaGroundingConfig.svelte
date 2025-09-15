<script lang="ts">
	import { getRAGConfig } from '$lib/apis/retrieval';
	import Switch from '$lib/components/common/Switch.svelte';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let config = { enabled: false, maxConcurrent: 1 };

	let loading = false;

	onMount(async () => {
		loading = true;
		const res = await getRAGConfig(localStorage.token);
		if (res) {
			config.enabled = res?.enable_wikipedia_grounding ?? true;
			config.maxConcurrent = res?.wikipedia_grounding_max_concurrent ?? 1;
		}
		loading = false;
	});
</script>

<div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
	<div class="space-y-4">
		<!-- Header -->
		<div class="flex items-center justify-between">
			<div>
				<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
					{$i18n.t('Wikipedia Grounding')}
				</h3>
				<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
					{$i18n.t('Enhance responses with Wikipedia knowledge')}
				</p>
			</div>
			<Switch bind:state={config.enabled} aria-labelledby="wikipedia-grounding-label" />
		</div>

		<!-- Description when enabled -->
		{#if config.enabled}
			<div class="space-y-4">
				<!-- Max Concurrent Setting -->
				<div>
					<label
						for="wikipedia-max-concurrent"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
					>
						{$i18n.t('Maximum Concurrent Operations')}
					</label>
					<div class="flex items-center space-x-3">
						<input
							id="wikipedia-max-concurrent"
							type="number"
							min="1"
							max="10"
							bind:value={config.maxConcurrent}
							class="w-20 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
						/>
						<span class="text-sm text-gray-600 dark:text-gray-400">
							{$i18n.t('Controls memory usage and prevents system overload under high load')}
						</span>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						{$i18n.t(
							'Recommended: 2-4 for typical deployments. Higher values may cause memory issues.'
						)}
					</p>
				</div>

				<!-- Description -->
				<div
					class="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-md p-3"
				>
					<div class="font-medium text-gray-800 dark:text-gray-200 mb-2">
						{$i18n.t('How Wikipedia Grounding works:')}
					</div>
					<ul class="list-disc list-inside space-y-1">
						<li>{$i18n.t('Uses semantic search over Wikipedia content for factual questions')}</li>
						<li>
							{$i18n.t('For French queries: translates to English → searches → provides results')}
						</li>
						<li>
							{$i18n.t('Provides current, accurate information without disrupting web search')}
						</li>
						<li>
							{$i18n.t(
								'Covers global knowledge including people, places, government, and general topics'
							)}
						</li>
					</ul>
				</div>
			</div>
		{/if}
	</div>
</div>
