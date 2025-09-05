<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let sources: Array<{
		title: string;
		content: string;
		url: string;
		score: number;
		language?: string;
		fallback_reason?: string;
	}> = [];
	export let count: number = 0;

	$: displayCount = count || sources.length;
	let state = false;
</script>

<div class="flex flex-col justify-center -space-y-0.5">
	<Collapsible bind:open={state} className="w-full space-y-1">
		<div
			class="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
		>
			<BookOpen className="size-4" />
			<span>{$i18n.t('Enhanced with {{COUNT}} sources', { COUNT: displayCount })}</span>

			{#if state}
				<ChevronUp strokeWidth="3.5" className="size-3.5" />
			{:else}
				<ChevronDown strokeWidth="3.5" className="size-3.5" />
			{/if}
		</div>

		<div
			class="text-sm border border-gray-300/30 dark:border-gray-700/50 rounded-xl mb-1.5"
			slot="content"
		>
			{#each sources as source, idx}
				<a
					href={source.url}
					target="_blank"
					rel="noopener noreferrer"
					class="flex w-full items-start p-3 px-4 {idx === sources.length - 1
						? ''
						: 'border-b border-gray-300/30 dark:border-gray-700/50'} group/item justify-between font-normal text-gray-800 dark:text-gray-300"
				>
					<div class="flex-1 min-w-0">
						<h4 class="font-medium text-gray-900 dark:text-gray-100 text-sm mb-1 line-clamp-2">
							{source.title}
						</h4>
						{#if source.content}
							<p class="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
								{source.content}
							</p>
						{/if}
					</div>

					<div class="flex items-center gap-2 ml-2 flex-shrink-0">
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
						{#if source.score}
							<span
								class="text-xs text-gray-500 bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded whitespace-nowrap"
							>
								{$i18n.t('Relevance')}: {Math.round(source.score * 100)}%
							</span>
						{/if}
						<div
							class="text-white dark:text-gray-900 group-hover/item:text-gray-600 dark:group-hover/item:text-white transition"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-4"
							>
								<path
									fill-rule="evenodd"
									d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</div>
				</a>
			{/each}
		</div>
	</Collapsible>
</div>
