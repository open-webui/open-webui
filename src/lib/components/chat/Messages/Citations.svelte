<script lang="ts">
	import CitationsModal from './CitationsModal.svelte';

	export let citations = [];

	let showCitationModal = false;
	let selectedCitation = null;
</script>

<CitationsModal bind:show={showCitationModal} citation={selectedCitation} />

<div class="mt-1 mb-2 w-full flex gap-1 items-center flex-wrap">
	{#each citations.reduce((acc, citation) => {
		citation.document.forEach((document, index) => {
			const metadata = citation.metadata?.[index];
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
			} else {
				acc.push( { id: id, source: source, document: [document], metadata: metadata ? [metadata] : [] } );
			}
		});
		return acc;
	}, []) as citation, idx}
		<div class="flex gap-1 text-xs font-semibold">
			<button
				class="flex dark:text-gray-300 py-1 px-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-xl"
				on:click={() => {
					showCitationModal = true;
					selectedCitation = citation;
				}}
			>
				<div class="bg-white dark:bg-gray-700 rounded-full size-4">
					{idx + 1}
				</div>
				<div class="flex-1 mx-2 line-clamp-1">
					{citation.source.name}
				</div>
			</button>
		</div>
	{/each}
</div>
