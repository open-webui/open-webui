<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	const i18n = getContext('i18n');

	export let show = false;
	export let citation;

	let mergedDocuments = [];

	$: if (citation) {
		mergedDocuments = citation.document?.map((c, i) => {
			return {
				source: citation.source,
				document: c,
				metadata: citation.metadata?.[i]
			};
		});
	}
</script>

<Modal size="lg" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
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

		<div class="flex flex-col md:flex-row w-full px-6 pb-5 md:space-x-4">
			<div
				class="flex flex-col w-full dark:text-gray-200 overflow-y-scroll max-h-[22rem] scrollbar-hidden"
			>
				{#each mergedDocuments as document, documentIdx}
					<div class="flex flex-col w-full">
						<div class="text-sm font-medium dark:text-gray-300">
							{$i18n.t('Source')}
						</div>

						{#if document.source?.name}
							<div class="text-sm dark:text-gray-400">
								<a
									href={document?.metadata?.file_id
										? `/api/v1/files/${document?.metadata?.file_id}/content`
										: document.source.name.includes('http')
										? document.source.name
										: `#`}
									target="_blank"
								>
									{document?.metadata?.name ?? document.source.name}
								</a>
							</div>
						{:else}
							<div class="text-sm dark:text-gray-400">
								{$i18n.t('No source available')}
							</div>
						{/if}
					</div>
					<div class="flex flex-col w-full">
						<div class=" text-sm font-medium dark:text-gray-300">
							{$i18n.t('Content')}
						</div>
						<pre class="text-sm dark:text-gray-400 whitespace-pre-line">
							{document.document}
						</pre>
					</div>

					{#if documentIdx !== mergedDocuments.length - 1}
						<hr class=" dark:border-gray-850 my-3" />
					{/if}
				{/each}
			</div>
		</div>
	</div>
</Modal>
