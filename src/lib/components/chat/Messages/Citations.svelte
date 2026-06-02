<script lang="ts">
	import { getContext } from 'svelte';
	import { embed, showControls, showEmbeds } from '$lib/stores';

	import CitationModal from './Citations/CitationModal.svelte';

	const i18n = getContext('i18n');

	export let id = '';
	export let chatId = '';

	export let sources = [];
	export let content = ''; // Message content to extract cited indices
	export let readOnly = false;

	let citations = [];
	let showPercentage = false;
	let showRelevance = true;

	// Extract all citation indices from the message content (e.g., [1], [2,3], [4#section])
	function extractCitedIndices(text: string): Set<number> {
		const indices = new Set<number>();
		// Match citation patterns like [1], [1,2], [1#foo], etc.
		const regex = /\[(\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\]/g;
		let match;
		while ((match = regex.exec(text)) !== null) {
			// Split by comma and extract numbers
			const parts = match[1].split(',').map((p) => p.trim());
			parts.forEach((part) => {
				const numMatch = /^(\d+)/.exec(part);
				if (numMatch) {
					indices.add(parseInt(numMatch[1], 10));
				}
			});
		}
		return indices;
	}

	let citationModal = null;

	let showCitations = false;
	let showCitationModal = false;

	let selectedCitation: any = null;

	export const showSourceModal = (sourceId) => {
		let index;
		let suffix = null;

		if (typeof sourceId === 'string') {
			const output = sourceId.split('#');
			index = parseInt(output[0]) - 1;

			if (output.length > 1) {
				suffix = output[1];
			}
		} else {
			index = sourceId - 1;
		}

		if (citations[index]) {
			console.log('Showing citation modal for:', citations[index]);

			if (citations[index]?.source?.embed_url) {
				const embedUrl = citations[index].source.embed_url;
				if (embedUrl) {
					if (readOnly) {
						// Open in new tab if readOnly
						window.open(embedUrl, '_blank');
						return;
					} else {
						showControls.set(true);
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

	function calculateShowRelevance(sources: any[]) {
		const distances = sources.flatMap((citation) => citation.distances ?? []);
		const inRange = distances.filter((d) => d !== undefined && d >= -1 && d <= 1).length;
		const outOfRange = distances.filter((d) => d !== undefined && (d < -1 || d > 1)).length;

		if (distances.length === 0) {
			return false;
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
		const distances = sources.flatMap((citation) => citation.distances ?? []);
		return distances.every((d) => d !== undefined && d >= -1 && d <= 1);
	}

	$: {
		// Extract which source indices are actually cited in the message content
		const citedIndices = extractCitedIndices(content);

		// Build a flat list of all source chunks with their original indices
		// Each source in 'sources' array contains document chunks - we need to track the overall index
		let allChunks: { sourceIdx: number; chunkIdx: number; source: any }[] = [];
		let chunkIndex = 0;
		sources.forEach((source, sourceIdx) => {
			if (Object.keys(source).length === 0) return;
			const docCount = source?.document?.length ?? 0;
			for (let i = 0; i < docCount; i++) {
				allChunks.push({
					sourceIdx,
					chunkIdx: i,
					source,
					overallIndex: chunkIndex + 1 // 1-based index for citation matching
				});
				chunkIndex++;
			}
		});

		// If content has citations, filter to only show cited sources
		// Otherwise show all (for backward compatibility or when content is empty)
		let filteredSources = sources;
		if (citedIndices.size > 0) {
			// Get the set of source indices that were cited
			const citedSourceIndices = new Set<number>();
			allChunks.forEach((chunk) => {
				if (citedIndices.has(chunk.overallIndex)) {
					citedSourceIndices.add(chunk.sourceIdx);
				}
			});
			filteredSources = sources.filter((_, idx) => citedSourceIndices.has(idx));
		}

		// Group citations by document (source.id) rather than by chunk
		// This ensures multiple chunks from the same document appear as a single entry
		citations = filteredSources.reduce((acc, source) => {
			if (Object.keys(source).length === 0) {
				return acc;
			}

			// Use source.id as the grouping key (document level)
			const documentId = source?.source?.id ?? 'N/A';
			const existingSource = acc.find((item) => item.id === documentId);

			if (existingSource) {
				// Add documents and metadata from this source to existing entry
				source?.document?.forEach((document, index) => {
					const metadata = source?.metadata?.[index];
					const distance = source?.distances?.[index];

					existingSource.document.push(document);
					if (metadata) existingSource.metadata.push(metadata);
					if (distance !== undefined) existingSource.distances.push(distance);
				});
			} else {
				// Create new entry for this document
				let _source = source?.source ?? {};

				// Collect all documents and metadata from this source
				const documents: string[] = [];
				const metadatas: any[] = [];
				const distances: number[] = [];

				source?.document?.forEach((document, index) => {
					const metadata = source?.metadata?.[index];
					const distance = source?.distances?.[index];

					documents.push(document);
					if (metadata) metadatas.push(metadata);
					if (distance !== undefined) distances.push(distance);
				});

				acc.push({
					id: documentId,
					source: _source,
					document: documents,
					metadata: metadatas,
					distances: distances
				});
			}

			return acc;
		}, []);
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
			class="text-xs font-medium text-gray-600 dark:text-gray-300 px-3.5 h-8 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center gap-1 border border-gray-50 dark:border-gray-850/30"
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
							class="size-4 rounded-full shrink-0 border border-white dark:border-gray-850 bg-white dark:bg-gray-900"
							on:error={(e) => {
								e.target.src = '/favicon.png';
							}}
						/>
					{/each}
					{#if citations.length > 3}
						<div
							class="size-4 rounded-full shrink-0 border border-white dark:border-gray-850 bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-[8px] font-semibold text-gray-500 dark:text-gray-400 whitespace-nowrap tracking-tighter"
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
						name: decodeString(citation.source.name)
					})}
					class="no-toggle outline-hidden flex dark:text-gray-300 bg-transparent text-gray-600 rounded-xl gap-1.5 items-center"
					on:click={() => {
						// Open document URL in new tab if available, otherwise show modal
						if (citation?.source?.url) {
							window.open(citation.source.url, '_blank');
						} else {
							showCitationModal = true;
							selectedCitation = citation;
						}
					}}
				>
					<div class=" font-medium bg-gray-50 dark:bg-gray-850 rounded-md px-1">
						{idx + 1}
					</div>
					<div
						class="flex-1 truncate hover:text-black dark:text-white/60 dark:hover:text-white transition text-left"
					>
						{decodeString(citation.source.name)}
					</div>
				</button>
			{/each}
		</div>
	</div>
{/if}
