<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import {
		buildTextFragmentUrl,
		formatCitationDate,
		getSafeCitationUrl,
		getCitationThumbnailUrl,
		getCitationTitle,
		selectCitationEntry,
		type CitationEntry
	} from '$lib/utils/citations';
	import CitationSourceIcon from './CitationSourceIcon.svelte';

	const i18n = getContext<
		Writable<{
			t: (key: string, options?: Record<string, unknown>) => string;
			resolvedLanguage?: string;
			language?: string;
		}>
	>('i18n');

	export let entry: CitationEntry;
	export let identifier: string | number;
	export let position = 0;
	export let count = 1;
	export let onPrevious: () => void = () => {};
	export let onNext: () => void = () => {};
	export let onNavigateKey: (event: KeyboardEvent) => void = () => {};

	let failedThumbnailUrl: string | null = null;
	$: selected = selectCitationEntry(entry, identifier);
	$: metadata = selected.metadata[0];
	$: document = selected.document[0] ?? '';
	$: title = getCitationTitle(selected.source, metadata);
	$: thumbnailUrl = getCitationThumbnailUrl(metadata);
	$: snippetUrl = buildTextFragmentUrl({
		source: selected.source,
		metadata,
		document
	});
	$: externalUrl = getSafeCitationUrl(snippetUrl);
	$: formattedDate = formatCitationDate(
		metadata?.date_published,
		$i18n.resolvedLanguage ?? $i18n.language
	);
	$: byline = [...(metadata?.author ?? []), ...(metadata?.publisher ?? []), formattedDate]
		.filter(Boolean)
		.join(' · ');
</script>

<article
	class="w-[280px] max-w-[80vw] rounded-2xl border border-gray-100 bg-white p-3 shadow-lg dark:border-gray-800 dark:bg-gray-850 dark:text-white"
>
	<div class="flex gap-2.5">
		{#if thumbnailUrl && failedThumbnailUrl !== thumbnailUrl}
			<img
				src={thumbnailUrl}
				alt=""
				crossorigin="anonymous"
				referrerpolicy="no-referrer"
				class="mt-0.5 size-10 shrink-0 rounded-lg border border-gray-100 bg-gray-50 object-cover dark:border-gray-800 dark:bg-gray-900"
				on:error={(event) => {
					failedThumbnailUrl = (event.currentTarget as HTMLImageElement).src;
				}}
			/>
		{:else}
			<div class="mt-0.5 flex size-10 shrink-0 items-center justify-center">
				<CitationSourceIcon source={selected.source} {metadata} size={24} />
			</div>
		{/if}
		<div class="min-w-0 flex-1">
			{#if externalUrl}
				<a
					href={externalUrl}
					target="_blank"
					rel="nofollow noopener noreferrer"
					referrerpolicy="no-referrer"
					class="line-clamp-2 rounded-sm text-sm font-medium leading-snug text-gray-900 underline-offset-2 transition hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 dark:text-white"
					on:keydown={onNavigateKey}
				>
					{title}
				</a>
			{:else}
				<div class="line-clamp-2 text-sm font-medium leading-snug">{title}</div>
			{/if}
			{#if byline}
				<div class="mt-0.5 line-clamp-1 text-[11px] text-gray-500 dark:text-gray-400">
					{byline}
				</div>
			{/if}
		</div>
	</div>

	{#if document.trim() || metadata?.description}
		<blockquote
			class="mt-2 line-clamp-4 border-l-2 border-gray-200 pl-2 text-xs leading-relaxed text-gray-600 dark:border-gray-700 dark:text-gray-300"
		>
			{document.trim() || metadata.description}
		</blockquote>
	{/if}

	{#if count > 1}
		<div
			class="mt-2 flex items-center justify-end gap-1 border-t border-gray-100 pt-2 dark:border-gray-800"
		>
			<button
				type="button"
				aria-label="Previous citation"
				disabled={position <= 0}
				class="flex size-6 items-center justify-center rounded-md text-sm text-gray-600 transition hover:bg-gray-100 disabled:cursor-default disabled:opacity-30 dark:text-gray-300 dark:hover:bg-gray-800"
				on:keydown={onNavigateKey}
				on:click={onPrevious}>←</button
			>
			<span class="min-w-10 text-center text-[11px] tabular-nums text-gray-500 dark:text-gray-400">
				{position + 1} / {count}
			</span>
			<button
				type="button"
				aria-label="Next citation"
				disabled={position >= count - 1}
				class="flex size-6 items-center justify-center rounded-md text-sm text-gray-600 transition hover:bg-gray-100 disabled:cursor-default disabled:opacity-30 dark:text-gray-300 dark:hover:bg-gray-800"
				on:keydown={onNavigateKey}
				on:click={onNext}>→</button
			>
		</div>
	{/if}
</article>
