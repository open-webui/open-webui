<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	const i18n = getContext('i18n');

	export let show = false;
	export let citation: any[];

	let mergedDocuments = [];

	onMount(async () => {
		console.log(citation);
		// Merge the document with its metadata
		mergedDocuments = citation.document?.map((c, i) => {
			return {
				document: c,
				metadata: citation.metadata?.[i]
			};
		});
	});
</script>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4">
			<div class=" text-lg font-medium self-center capitalize">
				{$i18n.t('Citation')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<div class="flex flex-col w-full px-5 py-4 dark:text-gray-200 overflow-y-scroll max-h-[22rem]">
			{#each mergedDocuments as document, documentIdx}
				<div class="flex flex-col w-full">
					<div class=" font-medium dark:text-gray-300">
						{$i18n.t('Source')}
					</div>
					<div class="text-sm dark:text-gray-400">
						{document.metadata?.source ?? $i18n.t('No source available')}
					</div>
				</div>
				<div class="flex flex-col w-full">
					<div class=" font-medium dark:text-gray-300">
						{$i18n.t('Content')}
					</div>
					<pre class="text-sm dark:text-gray-400">
						{document.document}
					</pre>
				</div>

				{#if documentIdx !== mergedDocuments.length - 1}
					<hr class=" dark:border-gray-850" />
				{/if}
			{/each}
		</div>
	</div>
</Modal>
