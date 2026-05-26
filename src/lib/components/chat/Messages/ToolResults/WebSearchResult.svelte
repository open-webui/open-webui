<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { copyToClipboard } from '$lib/utils';
	import {
		formatCount,
		parseWebSearchResult,
		previewText,
		truncateMiddle,
		type ParsedWebSearchResult,
		type WebSearchItem
	} from '$lib/utils/toolResults';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let id = '';
	export let resultRaw: unknown = '';
	export let argsRaw: unknown = '';

	const PAGE_SIZE = 8;

	let filter = '';
	let visibleCount = PAGE_SIZE;
	let parsed: ParsedWebSearchResult | null = null;
	let parseGeneration = 0;
	let parseFrame: number | null = null;
	let parseTimeout: ReturnType<typeof setTimeout> | null = null;

	const clearScheduledParse = () => {
		if (parseFrame !== null) {
			window.cancelAnimationFrame(parseFrame);
			parseFrame = null;
		}
		if (parseTimeout !== null) {
			clearTimeout(parseTimeout);
			parseTimeout = null;
		}
	};

	const scheduleParse = () => {
		clearScheduledParse();
		parsed = null;
		const generation = ++parseGeneration;

		if (typeof window === 'undefined') {
			parsed = parseWebSearchResult(resultRaw, argsRaw);
			return;
		}

		// Let the expand click paint first. The parse is usually quick, but doing
		// it in the same frame as the pointerup makes the row feel sticky.
		parseFrame = window.requestAnimationFrame(() => {
			parseFrame = null;
			parseTimeout = setTimeout(() => {
				parseTimeout = null;
				if (generation === parseGeneration) {
					parsed = parseWebSearchResult(resultRaw, argsRaw);
				}
			}, 0);
		});
	};

	$: {
		resultRaw;
		argsRaw;
		scheduleParse();
	}
	$: normalizedFilter = filter.trim().toLowerCase();
	$: filteredResults = parsed
		? normalizedFilter
			? parsed.results.filter((result) => searchResultMatches(result, normalizedFilter))
			: parsed.results
		: [];
	$: visibleResults = filteredResults.slice(0, visibleCount);

	onDestroy(() => {
		clearScheduledParse();
		parseGeneration += 1;
	});

	const searchResultMatches = (result: WebSearchItem, query: string) => {
		return [result.title, result.url, result.domain, result.snippet]
			.filter(Boolean)
			.some((value) => value.toLowerCase().includes(query));
	};

	const resetVisibleCount = () => {
		visibleCount = PAGE_SIZE;
	};

	const showMore = () => {
		visibleCount += PAGE_SIZE;
	};

	const copy = async (text: string) => {
		if (await copyToClipboard(text)) {
			toast.success($i18n.t('Copied to clipboard'));
		}
	};
</script>

{#if parsed === null}
	<div class="space-y-3" {id}>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
			<div class="min-w-0 space-y-2">
				<div class="h-4 w-32 rounded bg-gray-100 dark:bg-gray-800"></div>
				<div class="h-3 w-56 rounded bg-gray-100 dark:bg-gray-800"></div>
			</div>
		</div>
		<div class="space-y-2">
			<div class="h-20 rounded-2xl bg-gray-100 dark:bg-gray-800"></div>
			<div class="h-20 rounded-2xl bg-gray-100 dark:bg-gray-800"></div>
		</div>
	</div>
{:else if parsed.ok}
	<div class="space-y-3" {id}>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
			<div class="min-w-0">
				<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
					{$i18n.t('Search Results')}
				</div>
				<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
					{#if parsed.query}
						<span class="break-words">“{parsed.query}”</span>
						<span class="mx-1 text-gray-300 dark:text-gray-600">•</span>
					{/if}
					<span>{formatCount(parsed.declaredCount ?? parsed.results.length, 'result')}</span>
				</div>
			</div>

			{#if parsed.results.length > PAGE_SIZE}
				<div class="shrink-0 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Showing')}
					{visibleResults.length}
					{$i18n.t('of')}
					{filteredResults.length}
				</div>
			{/if}
		</div>

		{#if parsed.results.length > 5}
			<label class="block">
				<span class="sr-only">{$i18n.t('Filter results')}</span>
				<input
					class="w-full rounded-xl border border-gray-100 bg-white px-3 py-2 text-xs text-gray-800 outline-hidden transition placeholder:text-gray-400 focus:border-gray-300 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-gray-700"
					placeholder={$i18n.t('Filter results by title, domain, URL, or snippet')}
					bind:value={filter}
					on:input={resetVisibleCount}
				/>
			</label>
		{/if}

		{#if filteredResults.length === 0}
			<div
				class="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400"
			>
				{$i18n.t('No results match your filter.')}
			</div>
		{:else}
			<div class="space-y-2">
				{#each visibleResults as result (result.index)}
					<article
						class="group rounded-2xl border border-gray-100 bg-white p-3 transition hover:border-gray-200 hover:bg-gray-50/70 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700 dark:hover:bg-gray-850"
					>
						<div class="flex gap-3">
							<div
								class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-gray-100 text-[11px] font-semibold text-gray-500 dark:bg-gray-800 dark:text-gray-400"
							>
								{result.index}
							</div>

							<div class="min-w-0 flex-1">
								<div
									class="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-start sm:justify-between"
								>
									<div class="min-w-0">
										<div class="break-words text-sm font-semibold text-gray-900 dark:text-gray-100">
											{result.title}
										</div>
										{#if result.url}
											<div class="mt-0.5 truncate text-xs text-gray-500 dark:text-gray-500">
												{result.domain || truncateMiddle(result.url, 88)}
											</div>
										{/if}
									</div>

									{#if result.url}
										<div
											class="flex shrink-0 gap-1.5 sm:opacity-70 sm:transition sm:group-hover:opacity-100"
										>
											<a
												class="rounded-lg border border-gray-100 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
												href={result.url}
												target="_blank"
												rel="noreferrer noopener"
											>
												{$i18n.t('Open')}
											</a>
											<button
												class="rounded-lg border border-gray-100 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
												type="button"
												on:click={() => copy(result.url)}
											>
												{$i18n.t('Copy URL')}
											</button>
										</div>
									{/if}
								</div>

								{#if result.snippet}
									<p class="mt-2 text-xs leading-relaxed text-gray-600 dark:text-gray-400">
										{previewText(result.snippet, 420)}
									</p>
								{/if}
							</div>
						</div>
					</article>
				{/each}
			</div>

			{#if visibleResults.length < filteredResults.length}
				<button
					class="w-full rounded-xl border border-gray-100 bg-white px-3 py-2 text-xs font-medium text-gray-600 transition hover:bg-gray-50 hover:text-gray-900 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-850 dark:hover:text-white"
					type="button"
					on:click={showMore}
				>
					{$i18n.t('Show more results')} ({Math.min(
						PAGE_SIZE,
						filteredResults.length - visibleResults.length
					)})
				</button>
			{/if}
		{/if}
	</div>
{:else}
	<div
		class="rounded-2xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-900 dark:border-yellow-900/50 dark:bg-yellow-950/30 dark:text-yellow-200"
	>
		<div class="font-medium">{$i18n.t('Could not parse web_search results.')}</div>
		<div class="mt-1 text-xs opacity-80">
			{$i18n.t('Use the Raw tab to inspect the original tool output.')}
		</div>
	</div>
{/if}
