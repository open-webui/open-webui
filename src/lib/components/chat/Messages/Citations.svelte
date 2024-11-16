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
	let showRelevance = true;

	let showCitationModal = false;
	let selectedCitation: any = null;
	let isCollapsibleOpen = false;

	function calculateShowRelevance(citations: any[]) {
		const distances = citations.flatMap((citation) => citation.distances ?? []);
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

	function shouldShowPercentage(citations: any[]) {
		const distances = citations.flatMap((citation) => citation.distances ?? []);
		return distances.every((d) => d !== undefined && d >= -1 && d <= 1);
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
					source = { ...source, name: id, url: id };
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

		showRelevance = calculateShowRelevance(_citations);
		showPercentage = shouldShowPercentage(_citations);
	}
</script>

<CitationsModal
	bind:show={showCitationModal}
	citation={selectedCitation}
	{showPercentage}
	{showRelevance}
/>

{#if _citations.length > 0}
	<div class=" py-0.5 -mx-0.5 w-full flex gap-1 items-center flex-wrap">
		{#if _citations.length <= 3}
			<div class="flex text-xs font-medium">
				{#each _citations as citation, idx}
					<button
						class="no-toggle outline-none flex dark:text-gray-300 p-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition rounded-xl max-w-96"
						on:click={() => {
							showCitationModal = true;
							selectedCitation = citation;
						}}
					>
						{#if _citations.every((c) => c.distances !== undefined)}
							<div class="bg-gray-50 dark:bg-gray-800 rounded-full size-4">
								{idx + 1}
							</div>
						{/if}
						<div class="flex-1 mx-1 line-clamp-1 truncate">
							{citation.source.name}
						</div>
					</button>
				{/each}
			</div>
		{:else}
			<Collapsible bind:open={isCollapsibleOpen} className="w-full">
				<div
					class="flex items-center gap-2 text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 transition cursor-pointer"
				>
					<div class="flex-grow flex items-center gap-1 overflow-hidden">
						<span class="whitespace-nowrap hidden sm:inline">{$i18n.t('References from')}</span>
						<div class="flex items-center">
							<div class="flex text-xs font-medium items-center">
								{#each _citations.slice(0, 2) as citation, idx}
									<button
										class="no-toggle outline-none flex dark:text-gray-300 p-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition rounded-xl max-w-96"
										on:click={() => {
											showCitationModal = true;
											selectedCitation = citation;
										}}
										on:pointerup={(e) => {
											e.stopPropagation();
										}}
									>
										{#if _citations.every((c) => c.distances !== undefined)}
											<div class="bg-gray-50 dark:bg-gray-800 rounded-full size-4">
												{idx + 1}
											</div>
										{/if}
										<div class="flex-1 mx-1 line-clamp-1 truncate">
											{citation.source.name}
										</div>
									</button>
								{/each}
							</div>
						</div>
						<div class="flex items-center gap-1 whitespace-nowrap">
							<span class="hidden sm:inline">{$i18n.t('and')}</span>
							{_citations.length - 2}
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
				<div slot="content">
					<div class="flex text-xs font-medium">
						{#each _citations as citation, idx}
							<button
								class="no-toggle outline-none flex dark:text-gray-300 p-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition rounded-xl max-w-96"
								on:click={() => {
									showCitationModal = true;
									selectedCitation = citation;
								}}
							>
								{#if _citations.every((c) => c.distances !== undefined)}
									<div class="bg-gray-50 dark:bg-gray-800 rounded-full size-4">
										{idx + 1}
									</div>
								{/if}
								<div class="flex-1 mx-1 line-clamp-1 truncate">
									{citation.source.name}
								</div>
							</button>
						{/each}
					</div>
				</div>
			</Collapsible>
		{/if}
	</div>
{/if}
