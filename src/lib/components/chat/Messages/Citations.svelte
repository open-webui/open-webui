<script lang="ts">
	import { getContext } from 'svelte';
	import CitationsModal from './CitationsModal.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';

	const i18n = getContext('i18n');

	export let citations = [];

	let _citations = [];

	let showCitationModal = false;
	let selectedCitation = null;
	let isCollapsibleOpen = false;

	$: _citations = citations.reduce((acc, citation) => {
		citation.document.forEach((document, index) => {
			const metadata = citation.metadata?.[index];
			const distance = citation.distances?.[index];
			const id = metadata?.source ?? 'N/A';
			let source = citation?.source;

			if (metadata?.name) {
				source = { ...source, name: metadata.name };
			}

			// Check if ID looks like a URL
			if (id.startsWith('http://') || id.startsWith('https://')) {
				source = { name: id };
			}

			const existingSource = acc.find((item) => item.id === id);

			if (existingSource) {
				existingSource.document.push(document);
				existingSource.metadata.push(metadata);
				if (distance !== undefined) existingSource.distances.push(distance);
			} else {
				acc.push({
					id: id,
					source: source,
					document: [document],
					metadata: metadata ? [metadata] : [],
					distances: distance !== undefined ? [distance] : undefined
				});
			}
		});
		return acc;
	}, []);

	$: if (_citations.every((citation) => citation.distances !== undefined)) {
		// Sort citations by distance (relevance)
		_citations = _citations.sort((a, b) => {
			const aMinDistance = Math.min(...(a.distances ?? []));
			const bMinDistance = Math.min(...(b.distances ?? []));
			return aMinDistance - bMinDistance;
		});
	}
</script>

<CitationsModal bind:show={showCitationModal} citation={selectedCitation} />

{#if _citations.length > 0}
	<div class="mt-1 mb-2 w-full flex gap-1 items-center flex-wrap">
		{#if _citations.length <= 3}
			{#each _citations as citation, idx}
				<div class="flex gap-1 text-xs font-semibold">
					<button
						class="no-toggle flex dark:text-gray-300 py-1 px-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-xl max-w-96"
						on:click={() => {
							showCitationModal = true;
							selectedCitation = citation;
						}}
					>
						{#if _citations.every((c) => c.distances !== undefined)}
							<div class="bg-white dark:bg-gray-700 rounded-full size-4">
								{idx + 1}
							</div>
						{/if}
						<div class="flex-1 mx-2 line-clamp-1">
							{citation.source.name}
						</div>
					</button>
				</div>
			{/each}
		{:else}
			<Collapsible bind:open={isCollapsibleOpen} className="w-full">
				<div
					class="flex items-center gap-2 text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 transition cursor-pointer"
				>
					<span>{$i18n.t('References from')}</span>
					{#each _citations.slice(0, 2) as citation, idx}
						<div class="flex gap-1 text-xs font-semibold">
							<button
								class="no-toggle flex dark:text-gray-300 py-1 px-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-xl max-w-96"
								on:click={() => {
									showCitationModal = true;
									selectedCitation = citation;
								}}
							>
								{#if _citations.every((c) => c.distances !== undefined)}
									<div class="bg-white dark:bg-gray-700 rounded-full size-4">
										{idx + 1}
									</div>
								{/if}
								<div class="flex-1 mx-2 line-clamp-1">
									{citation.source.name}
								</div>
							</button>
						</div>
						{#if idx === 0}
							<span class="-ml-2">,</span>
						{/if}
					{/each}
					<span>{$i18n.t('and')}</span>
					<div class="text-gray-600 dark:text-gray-400">
						{_citations.length - 2}
					</div>
					<span>{$i18n.t('more')}</span>
					{#if isCollapsibleOpen}
						<ChevronUp strokeWidth="3.5" className="size-3.5" />
					{:else}
						<ChevronDown strokeWidth="3.5" className="size-3.5" />
					{/if}
				</div>
				<div slot="content" class="mt-2">
					<div class="flex flex-wrap gap-2">
						{#each _citations as citation, idx}
							<div class="flex gap-1 text-xs font-semibold">
								<button
									class="no-toggle flex dark:text-gray-300 py-1 px-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-xl max-w-96"
									on:click={() => {
										showCitationModal = true;
										selectedCitation = citation;
									}}
								>
									{#if _citations.every((c) => c.distances !== undefined)}
										<div class="bg-white dark:bg-gray-700 rounded-full size-4">
											{idx + 1}
										</div>
									{/if}
									<div class="flex-1 mx-2 line-clamp-1">
										{citation.source.name}
									</div>
								</button>
							</div>
						{/each}
					</div>
				</div>
			</Collapsible>
		{/if}
	</div>
{/if}
