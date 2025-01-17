<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import {
		getQuerySettings,
		updateQuerySettings,
		resetVectorDB,
		getEmbeddingConfig,
		updateEmbeddingConfig,
		getRerankingConfig,
		updateRerankingConfig,
		resetUploadDir,
		getRAGConfig,
		updateRAGConfig
	} from '$lib/apis/retrieval';

	import { knowledge, models } from '$lib/stores';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { uploadDir, deleteAllFiles, deleteFileById } from '$lib/apis/files';

	import ResetUploadDirConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ResetVectorDBConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import { text } from '@sveltejs/kit';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	let scanDirLoading = false;
	let updateEmbeddingModelLoading = false;
	let updateRerankingModelLoading = false;

	let showResetConfirm = false;
	let showResetUploadDirConfirm = false;

	let embeddingEngine = '';
	let embeddingModel = '';
	let embeddingBatchSize = 1;
	let rerankingModel = '';

	let fileMaxSize = null;
	let fileMaxCount = null;

	let contentExtractionEngine = 'default';
	let tikaServerUrl = '';
	let showTikaServerUrl = false;

	let textSplitter = '';
	let chunkSize = 0;
	let chunkOverlap = 0;
	let pdfExtractImages = true;

	let enableGoogleDriveIntegration = false;

	let OpenAIUrl = '';
	let OpenAIKey = '';

	let OllamaUrl = '';
	let OllamaKey = '';

	let querySettings = {
		template: '',
		r: 0.0,
		k: 4,
		hybrid: false
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
			embedding_batch_size: embeddingBatchSize,
			ollama_config: {
				key: OllamaKey,
				url: OllamaUrl
			},
			openai_config: {
				key: OpenAIKey,
				url: OpenAIUrl
			}
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
		await embeddingModelUpdateHandler();

		if (querySettings.hybrid) {
			await rerankingModelUpdateHandler();
		}

		if (contentExtractionEngine === 'tika' && tikaServerUrl === '') {
			toast.error($i18n.t('Tika Server URL required.'));
			return;
		}
		const res = await updateRAGConfig(localStorage.token, {
			pdf_extract_images: pdfExtractImages,
			enable_google_drive_integration: enableGoogleDriveIntegration,
			file: {
				max_size: fileMaxSize === '' ? null : fileMaxSize,
				max_count: fileMaxCount === '' ? null : fileMaxCount
			},
			chunk: {
				text_splitter: textSplitter,
				chunk_overlap: chunkOverlap,
				chunk_size: chunkSize
			},
			content_extraction: {
				engine: contentExtractionEngine,
				tika_server_url: tikaServerUrl
			}
		});

		await updateQuerySettings(localStorage.token, querySettings);

		dispatch('save');
	};

	const setEmbeddingConfig = async () => {
		const embeddingConfig = await getEmbeddingConfig(localStorage.token);

		if (embeddingConfig) {
			embeddingEngine = embeddingConfig.embedding_engine;
			embeddingModel = embeddingConfig.embedding_model;
			embeddingBatchSize = embeddingConfig.embedding_batch_size ?? 1;

			OpenAIKey = embeddingConfig.openai_config.key;
			OpenAIUrl = embeddingConfig.openai_config.url;

			OllamaKey = embeddingConfig.ollama_config.key;
			OllamaUrl = embeddingConfig.ollama_config.url;
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

			textSplitter = res.chunk.text_splitter;
			chunkSize = res.chunk.chunk_size;
			chunkOverlap = res.chunk.chunk_overlap;

			contentExtractionEngine = res.content_extraction.engine;
			tikaServerUrl = res.content_extraction.tika_server_url;
			showTikaServerUrl = contentExtractionEngine === 'tika';

			fileMaxSize = res?.file.max_size ?? '';
			fileMaxCount = res?.file.max_count ?? '';

			enableGoogleDriveIntegration = res.enable_google_drive_integration;
		}
	});
</script>

<ResetUploadDirConfirmDialog
	bind:show={showResetUploadDirConfirm}
	on:confirm={async () => {
		const res = await deleteAllFiles(localStorage.token).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Success'));
		}
	}}
/>

<ResetVectorDBConfirmDialog
	bind:show={showResetConfirm}
	on:confirm={() => {
		const res = resetVectorDB(localStorage.token).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Success'));
		}
	}}
/>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
	}}
>
	<div class=" space-y-2.5 overflow-y-scroll scrollbar-hidden h-full pr-1.5">
		<div class="flex flex-col gap-0.5">
			<div class=" mb-0.5 text-sm font-medium">{$i18n.t('General Settings')}</div>

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
				<div class="my-0.5 flex gap-2 pr-2">
					<input
						class="flex-1 w-full rounded-lg text-sm bg-transparent outline-none"
						placeholder={$i18n.t('API Base URL')}
						bind:value={OpenAIUrl}
						required
					/>

					<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={OpenAIKey} />
				</div>
			{:else if embeddingEngine === 'ollama'}
				<div class="my-0.5 flex gap-2 pr-2">
					<input
						class="flex-1 w-full rounded-lg text-sm bg-transparent outline-none"
						placeholder={$i18n.t('API Base URL')}
						bind:value={OllamaUrl}
						required
					/>

					<SensitiveInput
						placeholder={$i18n.t('API Key')}
						bind:value={OllamaKey}
						required={false}
					/>
				</div>
			{/if}

			{#if embeddingEngine === 'ollama' || embeddingEngine === 'openai'}
				<div class="flex mt-0.5 space-x-2">
					<div class=" self-center text-xs font-medium">{$i18n.t('Embedding Batch Size')}</div>
					<div class=" flex-1">
						<input
							id="steps-range"
							type="range"
							min="1"
							max="2048"
							step="1"
							bind:value={embeddingBatchSize}
							class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						/>
					</div>
					<div class="">
						<input
							bind:value={embeddingBatchSize}
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

		<hr class="dark:border-gray-850" />

		<div class="space-y-2" />
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('Embedding Model')}</div>

			{#if embeddingEngine === 'ollama'}
				<div class="flex w-full">
					<div class="flex-1 mr-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={embeddingModel}
							placeholder={$i18n.t('Set embedding model')}
							required
						/>
					</div>
				</div>
			{:else}
				<div class="flex w-full">
					<div class="flex-1 mr-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('Set embedding model (e.g. {{model}})', {
								model: embeddingModel.slice(-40)
							})}
							bind:value={embeddingModel}
						/>
					</div>

					{#if embeddingEngine === ''}
						<button
							class="px-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
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
									>
										<style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}

											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style>
										<path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/>
										<path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/>
									</svg>
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
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('Set reranking model (e.g. {{model}})', {
									model: 'BAAI/bge-reranker-v2-m3'
								})}
								bind:value={rerankingModel}
							/>
						</div>
						<button
							class="px-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
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
									>
										<style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}

											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style>
										<path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/>
										<path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/>
									</svg>
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

		<div class="">
			<div class="text-sm font-medium mb-1">{$i18n.t('Content Extraction')}</div>

			<div class="flex w-full justify-between">
				<div class="self-center text-xs font-medium">{$i18n.t('Engine')}</div>
				<div class="flex items-center relative">
					<select
						class="dark:bg-gray-900 w-fit pr-8 rounded px-2 text-xs bg-transparent outline-none text-right"
						bind:value={contentExtractionEngine}
						on:change={(e) => {
							showTikaServerUrl = e.target.value === 'tika';
						}}
					>
						<option value="">{$i18n.t('Default')} </option>
						<option value="tika">{$i18n.t('Tika')}</option>
					</select>
				</div>
			</div>

			{#if showTikaServerUrl}
				<div class="flex w-full mt-1">
					<div class="flex-1 mr-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('Enter Tika Server URL')}
							bind:value={tikaServerUrl}
						/>
					</div>
				</div>
			{/if}
		</div>

		<hr class=" dark:border-gray-850" />

		<div class="text-sm font-medium mb-1">{$i18n.t('Google Drive')}</div>

		<div class="">
			<div class="flex justify-between items-center text-xs">
				<div class="text-xs font-medium">{$i18n.t('Enable Google Drive')}</div>
				<div>
					<Switch bind:state={enableGoogleDriveIntegration} />
				</div>
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div class=" ">
			<div class=" text-sm font-medium mb-1">{$i18n.t('Query Params')}</div>

			<div class=" flex gap-1.5">
				<div class="flex flex-col w-full gap-1">
					<div class=" text-xs font-medium w-full">{$i18n.t('Top K')}</div>

					<div class="w-full">
						<input
							class=" w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="number"
							placeholder={$i18n.t('Enter Top K')}
							bind:value={querySettings.k}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>

				{#if querySettings.hybrid === true}
					<div class=" flex flex-col w-full gap-1">
						<div class="text-xs font-medium w-full">
							{$i18n.t('Minimum Score')}
						</div>

						<div class="w-full">
							<input
								class=" w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
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
				<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t(
						'Note: If you set a minimum score, the search will only return documents with a score greater than or equal to the minimum score.'
					)}
				</div>
			{/if}

			<div class="mt-2">
				<div class=" mb-1 text-xs font-medium">{$i18n.t('RAG Template')}</div>
				<Tooltip
					content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
					placement="top-start"
				>
					<Textarea
						bind:value={querySettings.template}
						placeholder={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
					/>
				</Tooltip>
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div class=" ">
			<div class="mb-1 text-sm font-medium">{$i18n.t('Chunk Params')}</div>

			<div class="flex w-full justify-between mb-1.5">
				<div class="self-center text-xs font-medium">{$i18n.t('Text Splitter')}</div>
				<div class="flex items-center relative">
					<select
						class="dark:bg-gray-900 w-fit pr-8 rounded px-2 text-xs bg-transparent outline-none text-right"
						bind:value={textSplitter}
					>
						<option value="">{$i18n.t('Default')} ({$i18n.t('Character')})</option>
						<option value="token">{$i18n.t('Token')} ({$i18n.t('Tiktoken')})</option>
					</select>
				</div>
			</div>

			<div class=" flex gap-1.5">
				<div class="  w-full justify-between">
					<div class="self-center text-xs font-medium min-w-fit mb-1">
						{$i18n.t('Chunk Size')}
					</div>
					<div class="self-center">
						<input
							class=" w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
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
							class="w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="number"
							placeholder={$i18n.t('Enter Chunk Overlap')}
							bind:value={chunkOverlap}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>
			</div>

			<div class="my-2">
				<div class="flex justify-between items-center text-xs">
					<div class=" text-xs font-medium">{$i18n.t('PDF Extract Images (OCR)')}</div>

					<div>
						<Switch bind:state={pdfExtractImages} />
					</div>
				</div>
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div class="">
			<div class="text-sm font-medium mb-1">{$i18n.t('Files')}</div>

			<div class=" flex gap-1.5">
				<div class="w-full">
					<div class=" self-center text-xs font-medium min-w-fit mb-1">
						{$i18n.t('Max Upload Size')}
					</div>

					<div class="self-center">
						<Tooltip
							content={$i18n.t(
								'The maximum file size in MB. If the file size exceeds this limit, the file will not be uploaded.'
							)}
							placement="top-start"
						>
							<input
								class="w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
								type="number"
								placeholder={$i18n.t('Leave empty for unlimited')}
								bind:value={fileMaxSize}
								autocomplete="off"
								min="0"
							/>
						</Tooltip>
					</div>
				</div>

				<div class="  w-full">
					<div class="self-center text-xs font-medium min-w-fit mb-1">
						{$i18n.t('Max Upload Count')}
					</div>
					<div class="self-center">
						<Tooltip
							content={$i18n.t(
								'The maximum number of files that can be used at once in chat. If the number of files exceeds this limit, the files will not be uploaded.'
							)}
							placement="top-start"
						>
							<input
								class=" w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
								type="number"
								placeholder={$i18n.t('Leave empty for unlimited')}
								bind:value={fileMaxCount}
								autocomplete="off"
								min="0"
							/>
						</Tooltip>
					</div>
				</div>
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div>
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
				<div class=" self-center text-sm font-medium">
					{$i18n.t('Reset Vector Storage/Knowledge')}
				</div>
			</button>
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
