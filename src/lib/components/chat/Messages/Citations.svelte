<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import {
		buildCitationEntries,
		buildTextFragmentUrl,
		getCitationListLabel,
		getSafeCitationUrl,
		parseCitationIdentifier,
		selectCitationEntry,
		type CitationEntry,
		type SourceEntry
	} from '$lib/utils/citations';
	import CitationSourceIcon from './Citations/CitationSourceIcon.svelte';

	const i18n =
		getContext<Writable<{ t: (key: string, options?: Record<string, unknown>) => string }>>('i18n');

	export let id = '';
	export let sources: SourceEntry[] = [];

	let citations: CitationEntry[] = [];
	let showCitations = false;

	export const openSource = (sourceId: string | number) => {
		const { sourceIndex } = parseCitationIdentifier(sourceId);
		const citation = citations[sourceIndex];
		if (citation) {
			const selection = selectCitationEntry(citation, sourceId);
			const externalUrl = getSafeCitationUrl(
				buildTextFragmentUrl({
					source: selection.source,
					metadata: selection.metadata[0],
					document: selection.document[0]
				})
			);
			if (externalUrl) {
				const opened = window.open(externalUrl, '_blank', 'noopener,noreferrer');
				if (opened) opened.opener = null;
			}
		}
	};

	$: {
		citations = buildCitationEntries(sources);
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch {
			return str;
		}
	};
</script>

{#if citations.length > 0}
	{@const urlCitations = citations.filter((citation) => citation.source?.url)}
	<div class=" py-1 -mx-0.5 w-full flex gap-1 items-center flex-wrap">
		<button
			class="text-xs font-normal text-gray-600 dark:text-gray-300 px-3.5 h-8 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center gap-1 border border-gray-50 dark:border-gray-850/30"
			aria-label={citations.length === 1
				? $i18n.t('Toggle 1 source')
				: $i18n.t('Toggle {{COUNT}} sources', { COUNT: citations.length })}
			aria-expanded={showCitations}
			on:click={() => {
				showCitations = !showCitations;
			}}
		>
			{#if citations.length === 1}
				<CitationSourceIcon
					source={citations[0].source}
					metadata={citations[0].metadata[0]}
					size={16}
					imageClass="rounded-full border border-white bg-white dark:border-gray-850 dark:bg-gray-900"
				/>
			{:else if urlCitations.length > 0}
				<div class="flex -space-x-1 items-center">
					{#each urlCitations.slice(0, 3) as citation}
						<CitationSourceIcon
							source={citation.source}
							metadata={citation.metadata[0]}
							size={16}
							imageClass="rounded-full border border-white bg-white dark:border-gray-850 dark:bg-gray-900"
						/>
					{/each}
					{#if citations.length > 3}
						<div
							class="size-4 rounded-full shrink-0 border border-white dark:border-gray-850 bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-[0.5rem] font-normal text-gray-500 dark:text-gray-400 whitespace-nowrap tracking-tighter"
							aria-hidden="true"
						>
							+{citations.length - Math.min(urlCitations.length, 3)}
						</div>
					{/if}
				</div>
			{/if}
			<div>
				{#if citations.length === 1}
					{$i18n.t('1 Source')}
				{:else}
					{$i18n.t('{{COUNT}} Sources', {
						COUNT: citations.length
					})}
				{/if}
			</div>
		</button>
	</div>
{/if}

{#if showCitations}
	<div class="py-1.5">
		<div class="text-xs gap-2 flex flex-col">
			{#each citations as citation, idx}
				{@const label = decodeString(getCitationListLabel(citation.source, citation.metadata[0]))}
				{@const externalUrl = getSafeCitationUrl(
					buildTextFragmentUrl({
						source: citation.source,
						metadata: citation.metadata[0],
						document: citation.document[0]
					})
				)}
				{#if externalUrl}
					<a
						id={`source-${id}-${idx + 1}`}
						href={externalUrl}
						target="_blank"
						rel="nofollow noopener noreferrer"
						referrerpolicy="no-referrer"
						aria-label={$i18n.t('Open source: {{name}}', {
							name: label
						})}
						class="no-toggle outline-hidden flex dark:text-gray-300 bg-transparent text-gray-600 rounded-xl gap-1.5 items-center !no-underline hover:!no-underline visited:!no-underline focus-visible:!no-underline"
					>
						<div class="font-normal bg-gray-50 dark:bg-gray-850 rounded-md px-1">
							{idx + 1}
						</div>
						<CitationSourceIcon
							source={citation.source}
							metadata={citation.metadata[0]}
							size={14}
						/>
						<div
							class="flex-1 truncate hover:text-black dark:text-white/60 dark:hover:text-white transition text-left"
						>
							{label}
						</div>
					</a>
				{:else}
					<div class="flex dark:text-gray-300 text-gray-600 gap-1.5 items-center">
						<div class="font-normal bg-gray-50 dark:bg-gray-850 rounded-md px-1">
							{idx + 1}
						</div>
						<CitationSourceIcon
							source={citation.source}
							metadata={citation.metadata[0]}
							size={14}
						/>
						<div class="flex-1 truncate">
							{label}
						</div>
					</div>
				{/if}
			{/each}
		</div>
	</div>
{/if}
