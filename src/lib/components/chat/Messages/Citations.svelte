<script lang="ts">
	import { getContext } from 'svelte';
	import CitationsModal from './CitationsModal.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';

	const i18n = getContext('i18n');

	export let citations = [];

	let _citations = [];
	let showPercentage = false;

	let showCitationModal = false;
	let selectedCitation: any = null;
	let isCollapsibleOpen = false;

	function shouldShowPercentage(citations: any[]) {
		return citations.every(
			(citation) =>
				citation.distances &&
				citation.distances.length > 0 &&
				citation.distances.every((d: number) => d !== undefined && d >= -1 && d <= 1)
		);
	}

	$: {
		_citations = citations.reduce((acc, citation) => {
			citation.document.forEach((document, index) => {
				const metadata = citation.metadata?.[index];
				const distance = citation.distances?.[index];
				const id = metadata?.source ?? 'N/A';
				let source = citation?.source;

				if (metadata?.name) {
					source = { ...source, name: metadata.name };
				}

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

		showPercentage = shouldShowPercentage(_citations);
	}
</script>

<CitationsModal bind:show={showCitationModal} citation={selectedCitation} {showPercentage} />

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
					class="flex items-center gap-1 text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 transition cursor-pointer"
				>
					<div class="flex-grow flex flex-wrap items-center gap-1">
						<span class="whitespace-nowrap hidden sm:inline">{$i18n.t('References from')}</span>
						<div class="flex flex-wrap items-center">
							{#each _citations.slice(0, 2) as citation, idx}
								<div class="flex items-center">
									<button
										class="no-toggle flex dark:text-gray-300 py-1 px-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-xl max-w-96 text-xs font-semibold"
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
									{#if idx === 0}
										<span class="mr-1">,</span>
									{/if}
								</div>
							{/each}
						</div>
						<div class="flex items-center gap-1 whitespace-nowrap">
							<span class="hidden sm:inline">{$i18n.t('and')}</span>
							<span class="text-gray-600 dark:text-gray-400">
								{_citations.length - 2}
							</span>
							<span>{$i18n.t('more')}</span>
						</div>
					</div>
					<div class="flex-shrink-0">
						{#if isCollapsibleOpen}
							<ChevronUp strokeWidth="3.5" className="size-3.5" />
						{:else}
							<ChevronDown strokeWidth="3.5" className="size-3.5" />
						{/if}
					</div>
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
