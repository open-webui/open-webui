<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { copyToClipboard } from '$lib/utils';
	import {
		formatCharacterCount,
		formatCount,
		parseWebFetchResult,
		previewText,
		truncateMiddle,
		type ParsedWebFetchResult,
		type WebFetchPage
	} from '$lib/utils/toolResults';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let id = '';
	export let resultRaw: unknown = '';

	const PREVIEW_CHARS = 1100;

	let filter = '';
	let expandedPage: number | null = null;
	let parsed: ParsedWebFetchResult | null = null;
	let parseGeneration = 0;
	let parseFrame: number | null = null;
	let parseTimeout: ReturnType<typeof setTimeout> | null = null;
	let parseIdle: number | null = null;

	const clearScheduledParse = () => {
		const idleWindow = typeof window !== 'undefined' ? (window as any) : null;
		if (parseFrame !== null) {
			window.cancelAnimationFrame(parseFrame);
			parseFrame = null;
		}
		if (parseTimeout !== null) {
			clearTimeout(parseTimeout);
			parseTimeout = null;
		}
		if (parseIdle !== null && idleWindow?.cancelIdleCallback) {
			idleWindow.cancelIdleCallback(parseIdle);
			parseIdle = null;
		}
	};

	const scheduleParse = () => {
		clearScheduledParse();
		parsed = null;
		expandedPage = null;
		const generation = ++parseGeneration;

		if (typeof window === 'undefined') {
			parsed = parseWebFetchResult(resultRaw);
			return;
		}

		// web_fetch can be very large. Paint the opened shell first, then parse
		// during idle time so the click/expand interaction stays smooth.
		parseFrame = window.requestAnimationFrame(() => {
			parseFrame = null;
			const idleWindow = window as any;
			const run = () => {
				parseIdle = null;
				parseTimeout = null;
				if (generation === parseGeneration) {
					parsed = parseWebFetchResult(resultRaw);
				}
			};

			if (typeof idleWindow.requestIdleCallback === 'function') {
				parseIdle = idleWindow.requestIdleCallback(run, { timeout: 450 });
			} else {
				parseTimeout = setTimeout(run, 0);
			}
		});
	};

	$: {
		resultRaw;
		scheduleParse();
	}

	const pageMatches = (page: WebFetchPage, query: string) => {
		const preview = previewText(page.content, 2200);
		return [
			page.title,
			page.url,
			page.domain,
			page.published,
			page.author,
			page.description,
			preview
		]
			.filter(Boolean)
			.some((value) => value.toLowerCase().includes(query));
	};

	const togglePage = (pageIndex: number) => {
		expandedPage = expandedPage === pageIndex ? null : pageIndex;
	};

	const copy = async (text: string) => {
		if (await copyToClipboard(text)) {
			toast.success($i18n.t('Copied to clipboard'));
		}
	};

	$: normalizedFilter = filter.trim().toLowerCase();
	$: filteredPages = parsed
		? normalizedFilter
			? parsed.pages.filter((page) => pageMatches(page, normalizedFilter))
			: parsed.pages
		: [];

	onDestroy(() => {
		clearScheduledParse();
		parseGeneration += 1;
	});
</script>

{#if parsed === null}
	<div class="space-y-3" {id}>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
			<div class="min-w-0 space-y-2">
				<div class="h-4 w-32 rounded bg-gray-100 dark:bg-gray-800"></div>
				<div class="h-3 w-44 rounded bg-gray-100 dark:bg-gray-800"></div>
			</div>
		</div>
		<div class="space-y-2">
			<div class="h-24 rounded-2xl bg-gray-100 dark:bg-gray-800"></div>
			<div class="h-24 rounded-2xl bg-gray-100 dark:bg-gray-800"></div>
		</div>
	</div>
{:else if parsed.ok}
	<div class="space-y-3" {id}>
		<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
			<div class="min-w-0">
				<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
					{$i18n.t('Fetched Pages')}
				</div>
				<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
					<span>{formatCount(parsed.declaredCount ?? parsed.pages.length, 'page')}</span>
					<span class="mx-1 text-gray-300 dark:text-gray-600">•</span>
					<span>{formatCharacterCount(parsed.totalCharacters)}</span>
				</div>
			</div>

			{#if expandedPage !== null}
				<button
					class="shrink-0 rounded-lg border border-gray-100 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
					type="button"
					on:click={() => (expandedPage = null)}
				>
					{$i18n.t('Collapse all')}
				</button>
			{/if}
		</div>

		{#if parsed.pages.length > 2}
			<label class="block">
				<span class="sr-only">{$i18n.t('Filter fetched pages')}</span>
				<input
					class="w-full rounded-xl border border-gray-100 bg-white px-3 py-2 text-xs text-gray-800 outline-hidden transition placeholder:text-gray-400 focus:border-gray-300 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-gray-700"
					placeholder={$i18n.t('Filter pages by title, domain, URL, author, or preview text')}
					bind:value={filter}
				/>
			</label>
		{/if}

		{#if filteredPages.length === 0}
			<div
				class="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400"
			>
				{$i18n.t('No fetched pages match your filter.')}
			</div>
		{:else}
			<div class="space-y-2">
				{#each filteredPages as page (page.index)}
					<article
						class="rounded-2xl border border-gray-100 bg-white p-3 transition dark:border-gray-800 dark:bg-gray-900"
					>
						<div class="flex gap-3">
							<button
								class="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-gray-100 text-[11px] font-semibold text-gray-500 transition hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
								type="button"
								on:click={() => togglePage(page.index)}
								aria-label={$i18n.t('Toggle page content')}
							>
								{expandedPage === page.index ? '−' : page.index}
							</button>

							<div class="min-w-0 flex-1">
								<div
									class="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-start sm:justify-between"
								>
									<div class="min-w-0">
										<div class="break-words text-sm font-semibold text-gray-900 dark:text-gray-100">
											{page.title}
										</div>
										<div
											class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500 dark:text-gray-500"
										>
											{#if page.url}
												<span class="truncate">{page.domain || truncateMiddle(page.url, 88)}</span>
											{/if}
											<span>{formatCharacterCount(page.characters)}</span>
											{#if page.published}
												<span>{page.published}</span>
											{/if}
											{#if page.author}
												<span>{page.author}</span>
											{/if}
										</div>
									</div>

									<div class="flex shrink-0 flex-wrap gap-1.5">
										{#if page.url}
											<a
												class="rounded-lg border border-gray-100 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
												href={page.url}
												target="_blank"
												rel="noreferrer noopener"
											>
												{$i18n.t('Open')}
											</a>
											<button
												class="rounded-lg border border-gray-100 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
												type="button"
												on:click={() => copy(page.url)}
											>
												{$i18n.t('Copy URL')}
											</button>
										{/if}
										<button
											class="rounded-lg border border-gray-100 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 hover:text-gray-900 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white"
											type="button"
											on:click={() => copy(page.content)}
										>
											{$i18n.t('Copy page')}
										</button>
									</div>
								</div>

								{#if page.description}
									<p class="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-500">
										{page.description}
									</p>
								{/if}

								{#if expandedPage !== page.index}
									<p class="mt-2 text-xs leading-relaxed text-gray-600 dark:text-gray-400">
										{previewText(page.content, PREVIEW_CHARS)}
									</p>
									{#if page.content.length > PREVIEW_CHARS}
										<button
											class="mt-2 text-xs font-medium text-gray-600 underline decoration-gray-300 underline-offset-2 transition hover:text-gray-900 dark:text-gray-300 dark:decoration-gray-700 dark:hover:text-white"
											type="button"
											on:click={() => togglePage(page.index)}
										>
											{$i18n.t('Show full content')}
										</button>
									{/if}
								{:else}
									<div
										class="mt-3 overflow-hidden rounded-xl border border-gray-100 bg-gray-50 dark:border-gray-800 dark:bg-gray-950/40"
									>
										<div
											class="flex items-center justify-between gap-2 border-b border-gray-100 bg-white px-3 py-2 text-xs dark:border-gray-800 dark:bg-gray-900"
										>
											<span class="font-medium text-gray-700 dark:text-gray-300">
												{$i18n.t('Full page content')}
											</span>
											<button
												class="text-gray-500 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
												type="button"
												on:click={() => togglePage(page.index)}
											>
												{$i18n.t('Collapse')}
											</button>
										</div>
										<div
											class="max-h-[60vh] overflow-y-auto whitespace-pre-wrap px-3 py-3 text-sm leading-relaxed text-gray-800 dark:text-gray-200"
										>
											{page.content || $i18n.t('No content returned for this page.')}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</article>
				{/each}
			</div>
		{/if}
	</div>
{:else}
	<div
		class="rounded-2xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-sm text-yellow-900 dark:border-yellow-900/50 dark:bg-yellow-950/30 dark:text-yellow-200"
	>
		<div class="font-medium">{$i18n.t('Could not parse web_fetch results.')}</div>
		<div class="mt-1 text-xs opacity-80">
			{$i18n.t('Use the Raw tab to inspect the original tool output.')}
		</div>
	</div>
{/if}
