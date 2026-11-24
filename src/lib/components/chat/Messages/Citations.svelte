<script lang="ts">
	import { getContext } from 'svelte';
	import { embed, showTabs, showEmbeds } from '$lib/stores';
	import { isValidHttpUrl } from '$lib/utils';
	import { getCitations } from '$lib/utils/citations';

	import CitationModal from './Citations/CitationModal.svelte';

	const i18n = getContext('i18n');

	export let id = '';
	export let chatId = '';

	export let sources = [];
	export let readOnly = false;

	let citations = [];
	let showPercentage = false;
	let showRelevance = true;

	let citationModal = null;

	let showCitations = false;
	let showCitationModal = false;

	let selectedCitation: any = null;

	export const showSourceModal = (sourceId) => {
		// "2#page" and 2 both name citation number 2
		const number = typeof sourceId === 'string' ? parseInt(sourceId.split('#')[0]) : sourceId;
		const index = citations.findIndex((citation) => citation.number === number);

		if (citations[index]) {
			console.log('Showing citation modal for:', citations[index]);

			// A cited file opens beside the chat, at the cited page when one is known. Web pages,
			// and files that cannot be previewed, show their retrieved text in the popup.
			const metadata = citations[index].metadata?.[0];
			const fileName = String(metadata?.name ?? citations[index].source?.name ?? '');
			if (
				!readOnly &&
				metadata?.file_id &&
				!metadata.external &&
				!['note', 'chat'].includes(citations[index].source?.type) &&
				!isValidHttpUrl(fileName) &&
				!/\.(doc|ppt|odt|ods|odp|rtf|epub|msg)$/i.test(fileName)
			) {
				showTabs.set(true);
				showEmbeds.set(true);
				embed.set({
					file: {
						id: metadata.file_id,
						page: Number.isInteger(metadata.page) ? metadata.page + 1 : null,
						// The cited passages of this file, each with its page and relevance
						passages: (citations[index].document ?? [])
							.map((text, i) => ({
								text,
								metadata: citations[index].metadata?.[i],
								distance: showRelevance ? citations[index].distances?.[i] : undefined
							}))
							.filter((passage) => passage.metadata?.file_id === metadata.file_id)
							.map(({ text, metadata, distance }) => ({
								text,
								page: Number.isInteger(metadata?.page) ? metadata.page + 1 : null,
								distance
							})),
						showPercentage
					},
					title: fileName,
					chatId: chatId
				});
				return;
			}

			if (citations[index]?.source?.embed_url) {
				const embedUrl = citations[index].source.embed_url;
				// The embed panel renders anything it cannot read as a URL as raw HTML
				if (
					typeof embedUrl === 'string' &&
					(isValidHttpUrl(embedUrl) || embedUrl.startsWith('//'))
				) {
					if (readOnly) {
						// Open in new tab if readOnly
						window.open(embedUrl, '_blank');
						return;
					} else {
						showTabs.set(true);
						showEmbeds.set(true);
						embed.set({
							url: embedUrl,
							title: citations[index]?.source?.name || 'Embedded Content',
							source: citations[index],
							chatId: chatId,
							messageId: id,
							sourceId: sourceId
						});
					}
				} else {
					selectedCitation = citations[index];
					showCitationModal = true;
				}
			} else {
				selectedCitation = citations[index];
				showCitationModal = true;
			}
		}
	};

	// Passages read rather than searched for have no distance
	const getDistances = (sources: any[]): number[] =>
		sources
			.flatMap((citation) => citation.distances ?? [])
			.filter((distance) => typeof distance === 'number');

	function calculateShowRelevance(sources: any[]) {
		const distances = getDistances(sources);
		const inRange = distances.filter((d) => d >= -1 && d <= 1).length;
		const outOfRange = distances.length - inRange;

		if (distances.length === 0) {
			return false;
		}

		// A single distance cannot be an outlier
		if (distances.length === 1) {
			return true;
		}

		if (
			(inRange === distances.length - 1 && outOfRange === 1) ||
			(outOfRange === distances.length - 1 && inRange === 1)
		) {
			return false;
		}

		return true;
	}

	function shouldShowPercentage(sources: any[]) {
		return getDistances(sources).every((d) => d >= -1 && d <= 1);
	}

	$: {
		citations = getCitations(sources);
		console.log('citations', citations);

		showRelevance = calculateShowRelevance(citations);
		showPercentage = shouldShowPercentage(citations);
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

<CitationModal
	bind:show={showCitationModal}
	citation={selectedCitation}
	{showPercentage}
	{showRelevance}
/>

{#if citations.length > 0}
	{@const urlCitations = citations.filter((c) => c?.source?.name?.startsWith('http'))}
	<div class=" py-1 -mx-0.5 w-full flex gap-1 items-center flex-wrap">
		<button
			class="text-xs font-normal text-base-600 dark:text-base-300 px-3.5 h-8 rounded-full hover:bg-base-100 dark:hover:bg-base-800 transition flex items-center gap-1 border border-base-50 dark:border-base-850/30"
			aria-label={citations.length === 1
				? $i18n.t('Toggle 1 source')
				: $i18n.t('Toggle {{COUNT}} sources', { COUNT: citations.length })}
			aria-expanded={showCitations}
			on:click={() => {
				showCitations = !showCitations;
			}}
		>
			{#if urlCitations.length > 0}
				<div class="flex -space-x-1 items-center">
					{#each urlCitations.slice(0, 3) as citation, idx}
						<img
							src="https://www.google.com/s2/favicons?sz=32&domain={citation.source.name}"
							alt="favicon"
							class="size-4 rounded-full shrink-0 border border-base-0 dark:border-base-850 bg-base-0 dark:bg-base-900"
							on:error={(e) => {
								// LICENSE covers this Open WebUI fallback logo.
								// Do not alter, remove, obscure, or replace it except as LICENSE permits:
								// https://docs.openwebui.com/license.
								e.target.src = '/favicon.png';
							}}
						/>
					{/each}
					{#if citations.length > 3}
						<div
							class="size-4 rounded-full shrink-0 border border-base-0 dark:border-base-850 bg-base-100 dark:bg-base-800 flex items-center justify-center text-[0.5rem] font-normal text-base-500 dark:text-base-400 whitespace-nowrap tracking-tighter"
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
				<button
					id={`source-${id}-${idx + 1}`}
					aria-label={$i18n.t('View source: {{name}}', {
						name: `${idx + 1} ${decodeString(citation.source.name)}`
					})}
					class="no-toggle outline-hidden flex dark:text-base-300 bg-transparent text-base-600 rounded-xl gap-1.5 items-center"
					on:click={() => showSourceModal(citation.number)}
				>
					<div class=" font-normal bg-base-50 dark:bg-base-850 rounded-md px-1">
						{idx + 1}
					</div>
					<div
						class="flex-1 truncate hover:text-base-1000 dark:text-base-0/60 dark:hover:text-base-0 transition text-left"
					>
						{decodeString(citation.source.name)}
					</div>
				</button>
			{/each}
		</div>
	</div>
{/if}
