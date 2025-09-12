<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';

	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import CitationModal from './CitationModal.svelte';

	export let id = '';
	export let show = false;
	export let citations = [];
	export let showPercentage = false;
	export let showRelevance = true;

	let showCitationModal = false;
	let selectedCitation: any = null;

	export const showCitation = (citation) => {
		selectedCitation = citation;
		showCitationModal = true;
	};

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

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center capitalize">
				{$i18n.t('Citations')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-6 pb-5 md:space-x-4">
			<div
				class="flex flex-col w-full dark:text-gray-200 overflow-y-scroll max-h-[22rem] scrollbar-hidden text-left text-sm gap-2"
			>
				{#each citations as citation, idx}
					<button
						id={`source-${id}-${idx + 1}`}
						class="no-toggle outline-hidden flex dark:text-gray-300 bg-white dark:bg-gray-900 rounded-xl gap-1.5 items-center"
						on:click={() => {
							showCitationModal = true;
							selectedCitation = citation;
						}}
					>
						<div class=" font-medium">
							{idx + 1}.
						</div>
						<div
							class="flex-1 truncate text-black/60 hover:text-black dark:text-white/60 dark:hover:text-white transition text-left"
						>
							{decodeString(citation.source.name)}
						</div>
					</button>
				{/each}
			</div>
		</div>
	</div>
</Modal>
