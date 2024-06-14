<script lang="ts">
	import { getDocs } from '$lib/apis/documents';
	import {
		getQuerySettings,
		scanDocs,
		updateQuerySettings,
		resetVectorDB,
		getEmbeddingConfig,
		updateEmbeddingConfig,
		getRerankingConfig,
		updateRerankingConfig,
		resetUploadDir,
		getRAGConfig,
		updateRAGConfig
	} from '$lib/apis/rag';

	import { documents, models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let scanDirLoading = false;
	let updateEmbeddingModelLoading = false;
	let updateRerankingModelLoading = false;

	let showResetConfirm = false;
	let showResetUploadDirConfirm = false;

	let embeddingEngine = '';
	let embeddingModel = '';
	let rerankingModel = '';

	let chunkSize = 0;
	let chunkOverlap = 0;
	let pdfExtractImages = true;

	let OpenAIKey = '';
	let OpenAIUrl = '';
	let OpenAIBatchSize = 1;

	let querySettings = {
		template: '',
		r: 0.0,
		k: 4,
		hybrid: false
	};

	const scanHandler = async () => {
		scanDirLoading = true;
		const res = await scanDocs(localStorage.token);
		scanDirLoading = false;

		if (res) {
			await documents.set(await getDocs(localStorage.token));
			toast.success($i18n.t('Scan complete!'));
		}
	};

	const embeddingModelUpdateHandler = async () => {
		if (embeddingEngine === '' && embeddingModel.split('/').length - 1 > 1) {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}
		if (embeddingEngine === 'ollama' && embeddingModel === '') {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}

		if (embeddingEngine === 'openai' && embeddingModel === '') {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}

		if ((embeddingEngine === 'openai' && OpenAIKey === '') || OpenAIUrl === '') {
			toast.error($i18n.t('OpenAI URL/Key required.'));
			return;
		}

		console.log('Update embedding model attempt:', embeddingModel);

		updateEmbeddingModelLoading = true;
		const res = await updateEmbeddingConfig(localStorage.token, {
			embedding_engine: embeddingEngine,
			embedding_model: embeddingModel,
			...(embeddingEngine === 'openai'
				? {
						openai_config: {
							key: OpenAIKey,
							url: OpenAIUrl,
							batch_size: OpenAIBatchSize
						}
				  }
				: {})
		}).catch(async (error) => {
			toast.error(error);
			await setEmbeddingConfig();
			return null;
		});
		updateEmbeddingModelLoading = false;

		if (res) {
			console.log('embeddingModelUpdateHandler:', res);
			if (res.status === true) {
				toast.success($i18n.t('Embedding model set to "{{embedding_model}}"', res), {
					duration: 1000 * 10
				});
			}
		}
	};

	const rerankingModelUpdateHandler = async () => {
		console.log('Update reranking model attempt:', rerankingModel);

		updateRerankingModelLoading = true;
		const res = await updateRerankingConfig(localStorage.token, {
			reranking_model: rerankingModel
		}).catch(async (error) => {
			toast.error(error);
			await setRerankingConfig();
			return null;
		});
		updateRerankingModelLoading = false;

		if (res) {
			console.log('rerankingModelUpdateHandler:', res);
			if (res.status === true) {
				if (rerankingModel === '') {
					toast.success($i18n.t('Reranking model disabled', res), {
						duration: 1000 * 10
					});
				} else {
					toast.success($i18n.t('Reranking model set to "{{reranking_model}}"', res), {
						duration: 1000 * 10
					});
				}
			}
		}
	};

	const submitHandler = async () => {
		embeddingModelUpdateHandler();

		if (querySettings.hybrid) {
			rerankingModelUpdateHandler();
		}

		const res = await updateRAGConfig(localStorage.token, {
			pdf_extract_images: pdfExtractImages,
			chunk: {
				chunk_overlap: chunkOverlap,
				chunk_size: chunkSize
			}
		});

		await updateQuerySettings(localStorage.token, querySettings);
	};

	const setEmbeddingConfig = async () => {
		const embeddingConfig = await getEmbeddingConfig(localStorage.token);

		if (embeddingConfig) {
			embeddingEngine = embeddingConfig.embedding_engine;
			embeddingModel = embeddingConfig.embedding_model;

			OpenAIKey = embeddingConfig.openai_config.key;
			OpenAIUrl = embeddingConfig.openai_config.url;
			OpenAIBatchSize = embeddingConfig.openai_config.batch_size ?? 1;
		}
	};

	const setRerankingConfig = async () => {
		const rerankingConfig = await getRerankingConfig(localStorage.token);

		if (rerankingConfig) {
			rerankingModel = rerankingConfig.reranking_model;
		}
	};

	const toggleHybridSearch = async () => {
		querySettings.hybrid = !querySettings.hybrid;
		querySettings = await updateQuerySettings(localStorage.token, querySettings);
	};

	onMount(async () => {
		await setEmbeddingConfig();
		await setRerankingConfig();

		querySettings = await getQuerySettings(localStorage.token);

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
	<div class=" space-y-2.5 overflow-y-scroll scrollbar-hidden h-full">
		<div class="flex flex-col gap-0.5">
			<div class=" mb-0.5 text-sm font-medium">{$i18n.t('General Settings')}</div>

			<div class="  flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Scan for documents from {{path}}', { path: 'DOCS_DIR (/data/docs)' })}
				</div>

				<button
					class=" self-center text-xs p-1 px-3 bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg flex flex-row space-x-1 items-center {scanDirLoading
						? ' cursor-not-allowed'
						: ''}"
					on:click={() => {
						scanHandler();
						console.log('check');
					}}
					type="button"
					disabled={scanDirLoading}
				>
					<div class="self-center font-medium">{$i18n.t('Scan')}</div>

					{#if scanDirLoading}
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

			<div class=" flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Embedding Model Engine')}</div>
				<div class="flex items-center relative">
					<select
						class="dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
						bind:value={embeddingEngine}
						placeholder="Select an embedding model engine"
						on:change={(e) => {
							if (e.target.value === 'ollama') {
								embeddingModel = '';
							} else if (e.target.value === 'openai') {
								embeddingModel = 'text-embedding-3-small';
							} else if (e.target.value === '') {
								embeddingModel = 'sentence-transformers/all-MiniLM-L6-v2';
							}
						}}
					>
						<option value="">{$i18n.t('Default (SentenceTransformers)')}</option>
						<option value="ollama">{$i18n.t('Ollama')}</option>
						<option value="openai">{$i18n.t('OpenAI')}</option>
					</select>
				</div>
			</div>

			{#if embeddingEngine === 'openai'}
				<div class="my-0.5 flex gap-2">
					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('API Base URL')}
						bind:value={OpenAIUrl}
						required
					/>

					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('API Key')}
						bind:value={OpenAIKey}
						required
					/>
				</div>
				<div class="flex mt-0.5 space-x-2">
					<div class=" self-center text-xs font-medium">{$i18n.t('Embedding Batch Size')}</div>
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="1"
							max="2048"
							step="1"
							bind:value={OpenAIBatchSize}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div class="">
						<input
							bind:value={OpenAIBatchSize}
							type="number"
							class=" bg-transparent text-center w-14"
							min="-2"
							max="16000"
							step="1"
						/>
					</div>
				</div>
			{/if}

			<div class=" flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Hybrid Search')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleHybridSearch();
					}}
					type="button"
				>
					{#if querySettings.hybrid === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>
		</div>

		<hr class=" dark:border-gray-850 my-1" />

		<div class="space-y-2" />
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('Embedding Model')}</div>

			{#if embeddingEngine === 'ollama'}
				<div class="flex w-full">
					<div class="flex-1 mr-2">
						<select
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={embeddingModel}
							placeholder={$i18n.t('Select a model')}
							required
						>
							{#if !embeddingModel}
								<option value="" disabled selected>{$i18n.t('Select a model')}</option>
							{/if}
							{#each $models.filter((m) => m.id && m.ollama && !(m?.preset ?? false)) as model}
								<option value={model.id} class="bg-gray-100 dark:bg-gray-700">{model.name}</option>
							{/each}
						</select>
					</div>
				</div>
			{:else}
				<div class="flex w-full">
					<div class="flex-1 mr-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('Set embedding model (e.g. {{model}})', {
								model: embeddingModel.slice(-40)
							})}
							bind:value={embeddingModel}
						/>
					</div>

					{#if embeddingEngine === ''}
						<button
							class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
							on:click={() => {
								embeddingModelUpdateHandler();
							}}
							disabled={updateEmbeddingModelLoading}
						>
							{#if updateEmbeddingModelLoading}
								<div class="self-center">
									<svg
										class=" w-4 h-4"
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
							{:else}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										d="M8.75 2.75a.75.75 0 0 0-1.5 0v5.69L5.03 6.22a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 0 0-1.06-1.06L8.75 8.44V2.75Z"
									/>
									<path
										d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
									/>
								</svg>
							{/if}
						</button>
					{/if}
				</div>
			{/if}

			<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t(
					'Warning: If you update or change your embedding model, you will need to re-import all documents.'
				)}
			</div>

			{#if querySettings.hybrid === true}
				<div class=" ">
					<div class=" mb-2 text-sm font-medium">{$i18n.t('Reranking Model')}</div>

					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('Set reranking model (e.g. {{model}})', {
									model: 'BAAI/bge-reranker-v2-m3'
								})}
								bind:value={rerankingModel}
							/>
						</div>
						<button
							class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
							on:click={() => {
								rerankingModelUpdateHandler();
							}}
							disabled={updateRerankingModelLoading}
						>
							{#if updateRerankingModelLoading}
								<div class="self-center">
									<svg
										class=" w-4 h-4"
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
							{:else}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										d="M8.75 2.75a.75.75 0 0 0-1.5 0v5.69L5.03 6.22a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 0 0-1.06-1.06L8.75 8.44V2.75Z"
									/>
									<path
										d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
									/>
								</svg>
							{/if}
						</button>
					</div>
				</div>
			{/if}
		</div>

		<hr class=" dark:border-gray-850" />

		<div class=" ">
			<div class=" text-sm font-medium">{$i18n.t('Query Params')}</div>

			<div class=" flex">
				<div class="  flex w-full justify-between">
					<div class="self-center text-xs font-medium min-w-fit">{$i18n.t('Top K')}</div>

					<div class="self-center p-3">
						<input
							class=" w-full rounded-lg py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="number"
							placeholder={$i18n.t('Enter Top K')}
							bind:value={querySettings.k}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>

				{#if querySettings.hybrid === true}
					<div class="flex w-full">
						<div class=" self-center text-xs font-medium min-w-fit">
							{$i18n.t('Minimum Score')}
						</div>

						<div class="self-center p-3">
							<input
								class=" w-full rounded-lg py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								type="number"
								step="0.01"
								placeholder={$i18n.t('Enter Score')}
								bind:value={querySettings.r}
								autocomplete="off"
								min="0.0"
								title={$i18n.t('The score should be a value between 0.0 (0%) and 1.0 (100%).')}
							/>
						</div>
					</div>
				{/if}
			</div>

			{#if querySettings.hybrid === true}
				<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t(
						'Note: If you set a minimum score, the search will only return documents with a score greater than or equal to the minimum score.'
					)}
				</div>

				<hr class=" dark:border-gray-850 my-3" />
			{/if}

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('RAG Template')}</div>
				<textarea
					bind:value={querySettings.template}
					class="w-full rounded-lg px-4 py-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none resize-none"
					rows="4"
				/>
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div class=" ">
			<div class=" text-sm font-medium">{$i18n.t('Chunk Params')}</div>

			<div class=" my-2 flex gap-1.5">
				<div class="  w-full justify-between">
					<div class="self-center text-xs font-medium min-w-fit mb-1">{$i18n.t('Chunk Size')}</div>
					<div class="self-center">
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

				<div class="w-full">
					<div class=" self-center text-xs font-medium min-w-fit mb-1">
						{$i18n.t('Chunk Overlap')}
					</div>

					<div class="self-center">
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

			<div class="my-3">
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

		<hr class=" dark:border-gray-850" />

		<div>
			{#if showResetUploadDirConfirm}
				<div class="flex justify-between rounded-md items-center py-2 px-3.5 w-full transition">
					<div class="flex items-center space-x-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="currentColor"
							class="size-4"
						>
							<path
								fill-rule="evenodd"
								d="M5.625 1.5H9a3.75 3.75 0 0 1 3.75 3.75v1.875c0 1.036.84 1.875 1.875 1.875H16.5a3.75 3.75 0 0 1 3.75 3.75v7.875c0 1.035-.84 1.875-1.875 1.875H5.625a1.875 1.875 0 0 1-1.875-1.875V3.375c0-1.036.84-1.875 1.875-1.875ZM9.75 14.25a.75.75 0 0 0 0 1.5H15a.75.75 0 0 0 0-1.5H9.75Z"
								clip-rule="evenodd"
							/>
							<path
								d="M14.25 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 16.5 7.5h-1.875a.375.375 0 0 1-.375-.375V5.25Z"
							/>
						</svg>
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div class="flex space-x-1.5 items-center">
						<button
							class="hover:text-white transition"
							on:click={() => {
								const res = resetUploadDir(localStorage.token).catch((error) => {
									toast.error(error);
									return null;
								});

								if (res) {
									toast.success($i18n.t('Success'));
								}

								showResetUploadDirConfirm = false;
							}}
							type="button"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									fill-rule="evenodd"
									d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						<button
							class="hover:text-white transition"
							type="button"
							on:click={() => {
								showResetUploadDirConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
								/>
							</svg>
						</button>
					</div>
				</div>
			{:else}
				<button
					class=" flex rounded-xl py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showResetUploadDirConfirm = true;
					}}
					type="button"
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="currentColor"
							class="size-4"
						>
							<path
								fill-rule="evenodd"
								d="M5.625 1.5H9a3.75 3.75 0 0 1 3.75 3.75v1.875c0 1.036.84 1.875 1.875 1.875H16.5a3.75 3.75 0 0 1 3.75 3.75v7.875c0 1.035-.84 1.875-1.875 1.875H5.625a1.875 1.875 0 0 1-1.875-1.875V3.375c0-1.036.84-1.875 1.875-1.875ZM9.75 14.25a.75.75 0 0 0 0 1.5H15a.75.75 0 0 0 0-1.5H9.75Z"
								clip-rule="evenodd"
							/>
							<path
								d="M14.25 5.25a5.23 5.23 0 0 0-1.279-3.434 9.768 9.768 0 0 1 6.963 6.963A5.23 5.23 0 0 0 16.5 7.5h-1.875a.375.375 0 0 1-.375-.375V5.25Z"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Reset Upload Directory')}</div>
				</button>
			{/if}

			{#if showResetConfirm}
				<div class="flex justify-between rounded-md items-center py-2 px-3.5 w-full transition">
					<div class="flex items-center space-x-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M3.5 2A1.5 1.5 0 0 0 2 3.5v9A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 12.5 4H9.621a1.5 1.5 0 0 1-1.06-.44L7.439 2.44A1.5 1.5 0 0 0 6.38 2H3.5Zm6.75 7.75a.75.75 0 0 0 0-1.5h-4.5a.75.75 0 0 0 0 1.5h4.5Z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div class="flex space-x-1.5 items-center">
						<button
							class="hover:text-white transition"
							on:click={() => {
								const res = resetVectorDB(localStorage.token).catch((error) => {
									toast.error(error);
									return null;
								});

								if (res) {
									toast.success($i18n.t('Success'));
								}

								showResetConfirm = false;
							}}
							type="button"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									fill-rule="evenodd"
									d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						<button
							class="hover:text-white transition"
							on:click={() => {
								showResetConfirm = false;
							}}
							type="button"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
								/>
							</svg>
						</button>
					</div>
				</div>
			{:else}
				<button
					class=" flex rounded-xl py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showResetConfirm = true;
					}}
					type="button"
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M3.5 2A1.5 1.5 0 0 0 2 3.5v9A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 12.5 4H9.621a1.5 1.5 0 0 1-1.06-.44L7.439 2.44A1.5 1.5 0 0 0 6.38 2H3.5Zm6.75 7.75a.75.75 0 0 0 0-1.5h-4.5a.75.75 0 0 0 0 1.5h4.5Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Reset Vector Storage')}</div>
				</button>
			{/if}
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
