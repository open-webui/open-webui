<script lang="ts">
	import { getContext } from 'svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';

	const i18n = getContext('i18n');

	export let sources: Array<{
		title: string;
		content: string;
		url: string;
		score: number;
		language?: string;
		fallback_reason?: string;
	}> = [];

	let open = false;
</script>

{#if sources && sources.length > 0}
	<div class="mt-2">
		<Collapsible bind:open className="w-full space-y-1">
			<div
				class="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
			>
				<BookOpen className="size-4" />
				<span>{$i18n.t('Wikipedia Sources')} ({sources.length})</span>
				{#if open}
					<ChevronUp strokeWidth="3.5" className="size-3.5" />
				{:else}
					<ChevronDown strokeWidth="3.5" className="size-3.5" />
				{/if}
			</div>
			<div
				slot="content"
				class="text-sm border border-gray-300/30 dark:border-gray-700/50 rounded-xl mb-1.5 space-y-2 p-3"
			>
				{#each sources as source}
					<div
						class="border rounded-lg p-3 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
					>
						<div class="flex items-start justify-between gap-2">
							<div class="flex-1">
								<div class="flex items-center gap-2 mb-1">
									<h4 class="font-semibold text-sm text-gray-800 dark:text-gray-200">
										<a
											href={source.url}
											target="_blank"
											rel="noopener noreferrer"
											class="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
										>
											{source.title}
										</a>
									</h4>
									{#if source.language}
										<span
											class="text-xs px-1.5 py-0.5 rounded {source.language === 'fr'
												? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
												: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'}"
										>
											{source.language === 'fr' ? '🇫🇷 FR' : '🇬🇧 EN'}
										</span>
									{/if}
									{#if source.fallback_reason === 'french_equivalent_not_found'}
										<span
											class="text-xs px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300"
											title={$i18n.t('French equivalent not found')}
										>
											⚠️
										</span>
									{/if}
								</div>
								{#if source.content}
									<p class="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-3">
										{source.content}
									</p>
								{/if}
							</div>
							<div class="flex flex-col gap-1 flex-shrink-0">
								{#if source.score}
									<span
										class="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded"
									>
										{$i18n.t('Relevance')}: {(source.score * 100).toFixed(0)}%
									</span>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		</Collapsible>
	</div>
{/if}
