<script lang="ts">
	import { getDocs } from '$lib/apis/documents';
	import {
		getRAGConfig,
		updateRAGConfig,
		getQuerySettings,
		scanDocs,
		updateQuerySettings
	} from '$lib/apis/rag';
	import { documents } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let loading = false;

	let chunkSize = 0;
	let chunkOverlap = 0;
	let pdfExtractImages = true;

	let querySettings = {
		template: '',
		k: 4
	};

	const scanHandler = async () => {
		loading = true;
		const res = await scanDocs(localStorage.token);
		loading = false;

		if (res) {
			await documents.set(await getDocs(localStorage.token));
			toast.success($i18n.t('Scan complete!'));
		}
	};

	const submitHandler = async () => {
		const res = await updateRAGConfig(localStorage.token, {
			pdf_extract_images: pdfExtractImages,
			chunk: {
				chunk_overlap: chunkOverlap,
				chunk_size: chunkSize
			}
		});
		querySettings = await updateQuerySettings(localStorage.token, querySettings);
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);

		if (res) {
			pdfExtractImages = res.pdf_extract_images;

			chunkSize = res.chunk.chunk_size;
			chunkOverlap = res.chunk.chunk_overlap;
		}

		querySettings = await getQuerySettings(localStorage.token);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
		saveHandler();
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-80">
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('General Settings')}</div>

			<div class="  flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Scan for documents from {{path}}', { path: '/data/docs' })}
				</div>

				<button
					class=" self-center text-xs p-1 px-3 bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded flex flex-row space-x-1 items-center {loading
						? ' cursor-not-allowed'
						: ''}"
					on:click={() => {
						scanHandler();
						console.log('check');
					}}
					type="button"
					disabled={loading}
				>
					<div class="self-center font-medium">{$i18n.t('Scan')}</div>

					<!-- <svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-3 h-3"
					>
						<path
							fill-rule="evenodd"
							d="M13.836 2.477a.75.75 0 0 1 .75.75v3.182a.75.75 0 0 1-.75.75h-3.182a.75.75 0 0 1 0-1.5h1.37l-.84-.841a4.5 4.5 0 0 0-7.08.932.75.75 0 0 1-1.3-.75 6 6 0 0 1 9.44-1.242l.842.84V3.227a.75.75 0 0 1 .75-.75Zm-.911 7.5A.75.75 0 0 1 13.199 11a6 6 0 0 1-9.44 1.241l-.84-.84v1.371a.75.75 0 0 1-1.5 0V9.591a.75.75 0 0 1 .75-.75H5.35a.75.75 0 0 1 0 1.5H3.98l.841.841a4.5 4.5 0 0 0 7.08-.932.75.75 0 0 1 1.025-.273Z"
							clip-rule="evenodd"
						/>
					</svg> -->

					{#if loading}
						<div class="ml-3 self-center">
							<svg
								class=" w-3 h-3"
								viewBox="0 0 24 24"
								fill="currentColor"
								xmlns="http://www.w3.org/2000/svg"
								><style>
									.spinner_ajPY {
										transform-origin: center;
										animation: spinner_AtaB 0.75s infinite linear;
									}
									@keyframes spinner_AtaB {
										100% {
											transform: rotate(360deg);
										}
									}
								</style><path
									d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
									opacity=".25"
								/><path
									d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
									class="spinner_ajPY"
								/></svg
							>
						</div>
					{/if}
				</button>
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		<div class=" ">
			<div class=" text-sm font-medium">{$i18n.t('Chunk Params')}</div>

			<div class=" flex">
				<div class="  flex w-full justify-between">
					<div class="self-center text-xs font-medium min-w-fit">{$i18n.t('Chunk Size')}</div>

					<div class="self-center p-3">
						<input
							class=" w-full rounded py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none border border-gray-100 dark:border-gray-600"
							type="number"
							placeholder={$i18n.t('Enter Chunk Size')}
							bind:value={chunkSize}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>

				<div class="flex w-full">
					<div class=" self-center text-xs font-medium min-w-fit">{$i18n.t('Chunk Overlap')}</div>

					<div class="self-center p-3">
						<input
							class="w-full rounded py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none border border-gray-100 dark:border-gray-600"
							type="number"
							placeholder={$i18n.t('Enter Chunk Overlap')}
							bind:value={chunkOverlap}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>
			</div>

			<div>
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

		<div>
			<div class=" text-sm font-medium">{$i18n.t('Query Params')}</div>

			<div class=" flex">
				<div class="  flex w-full justify-between">
					<div class="self-center text-xs font-medium flex-1">{$i18n.t('Top K')}</div>

					<div class="self-center p-3">
						<input
							class=" w-full rounded py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none border border-gray-100 dark:border-gray-600"
							type="number"
							placeholder={$i18n.t('Enter Top K')}
							bind:value={querySettings.k}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>

				<!-- <div class="flex w-full">
						<div class=" self-center text-xs font-medium min-w-fit">Chunk Overlap</div>
	
						<div class="self-center p-3">
							<input
								class="w-full rounded py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none border border-gray-100 dark:border-gray-600"
								type="number"
								placeholder="Enter Chunk Overlap"
								bind:value={chunkOverlap}
								autocomplete="off"
								min="0"
							/>
						</div>
					</div> -->
			</div>

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('RAG Template')}</div>
				<textarea
					bind:value={querySettings.template}
					class="w-full rounded p-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none resize-none"
					rows="4"
				/>
			</div>
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
