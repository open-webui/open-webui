<script lang="ts">
	import { getDocs } from '$lib/apis/documents';
	import {
		getRAGConfig,
		updateRAGConfig,
		getQuerySettings,
		scanDocs,
		updateQuerySettings,
		resetVectorDB,
		getEmbeddingConfig,
		updateEmbeddingConfig,
		getRerankingConfig,
		updateRerankingConfig
	} from '$lib/apis/rag';

	import { documents, models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let scanDirLoading = false;
	let updateEmbeddingModelLoading = false;
	let updateRerankingModelLoading = false;

	let showResetConfirm = false;

	let chunkSize = 0;
	let chunkOverlap = 0;
	let pdfExtractImages = true;

	const submitHandler = async () => {
		const res = await updateRAGConfig(localStorage.token, {
			pdf_extract_images: pdfExtractImages,
			chunk: {
				chunk_overlap: chunkOverlap,
				chunk_size: chunkSize
			}
		});
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);

		if (res) {
			pdfExtractImages = res.pdf_extract_images;

			chunkSize = res.chunk.chunk_size;
			chunkOverlap = res.chunk.chunk_overlap;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
		saveHandler();
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll h-full max-h-[22rem]">
		<div class=" ">
			<div class=" text-sm font-medium">{$i18n.t('Chunk Params')}</div>

			<div class=" flex">
				<div class="  flex w-full justify-between">
					<div class="self-center text-xs font-medium min-w-fit">{$i18n.t('Chunk Size')}</div>

					<div class="self-center p-3">
						<input
							class=" w-full rounded-lg py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="number"
							placeholder={$i18n.t('Enter Chunk Size')}
							bind:value={chunkSize}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>

				<div class="flex w-full">
					<div class=" self-center text-xs font-medium min-w-fit">
						{$i18n.t('Chunk Overlap')}
					</div>

					<div class="self-center p-3">
						<input
							class="w-full rounded-lg py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="number"
							placeholder={$i18n.t('Enter Chunk Overlap')}
							bind:value={chunkOverlap}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>
			</div>

			<div class="pr-2">
				<div class="flex justify-between items-center text-xs">
					<div class=" text-xs font-medium">{$i18n.t('PDF Extract Images (OCR)')}</div>

					<button
						class=" text-xs font-medium text-gray-500"
						type="button"
						on:click={() => {
							pdfExtractImages = !pdfExtractImages;
						}}>{pdfExtractImages ? $i18n.t('On') : $i18n.t('Off')}</button
					>
				</div>
			</div>
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
