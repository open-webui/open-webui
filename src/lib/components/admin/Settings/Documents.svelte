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
		getRAGConfig,
		updateRAGConfig
	} from '$lib/apis/retrieval';

	import { reindexKnowledgeFiles } from '$lib/apis/knowledge';
	import { deleteAllFiles } from '$lib/apis/files';

	import ResetUploadDirConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ResetVectorDBConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ReindexKnowledgeFilesConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let updateEmbeddingModelLoading = false;
	let updateRerankingModelLoading = false;

	let showResetConfirm = false;
	let showResetUploadDirConfirm = false;
	let showReindexConfirm = false;

	let embeddingEngine = '';
	let embeddingModel = '';
	let embeddingBatchSize = 1;
	let rerankingModel = '';

	let OpenAIUrl = '';
	let OpenAIKey = '';

	let AzureOpenAIUrl = '';
	let AzureOpenAIKey = '';
	let AzureOpenAIVersion = '';

	let OllamaUrl = '';
	let OllamaKey = '';

	let querySettings = {
		template: '',
		r: 0.0,
		k: 4,
		k_reranker: 4,
		hybrid: false
	};

	let RAGConfig = null;

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

		if (
			embeddingEngine === 'azure_openai' &&
			(AzureOpenAIKey === '' || AzureOpenAIUrl === '' || AzureOpenAIVersion === '')
		) {
			toast.error($i18n.t('OpenAI URL/Key required.'));
			return;
		}

		console.debug('Update embedding model attempt:', embeddingModel);

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
			},
			azure_openai_config: {
				key: AzureOpenAIKey,
				url: AzureOpenAIUrl,
				version: AzureOpenAIVersion
			}
		}).catch(async (error) => {
			toast.error(`${error}`);
			await setEmbeddingConfig();
			return null;
		});
		updateEmbeddingModelLoading = false;

		if (res) {
			console.debug('embeddingModelUpdateHandler:', res);
			if (res.status === true) {
				toast.success($i18n.t('Embedding model set to "{{embedding_model}}"', res), {
					duration: 1000 * 10
				});
			}
		}
	};

	const submitHandler = async () => {
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'external' &&
			RAGConfig.EXTERNAL_DOCUMENT_LOADER_URL === ''
		) {
			toast.error($i18n.t('External Document Loader URL required.'));
			return;
		}
		if (RAGConfig.CONTENT_EXTRACTION_ENGINE === 'tika' && RAGConfig.TIKA_SERVER_URL === '') {
			toast.error($i18n.t('Tika Server URL required.'));
			return;
		}
		if (RAGConfig.CONTENT_EXTRACTION_ENGINE === 'docling' && RAGConfig.DOCLING_SERVER_URL === '') {
			toast.error($i18n.t('Docling Server URL required.'));
			return;
		}
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'docling' &&
			((RAGConfig.DOCLING_OCR_ENGINE === '' && RAGConfig.DOCLING_OCR_LANG !== '') ||
				(RAGConfig.DOCLING_OCR_ENGINE !== '' && RAGConfig.DOCLING_OCR_LANG === ''))
		) {
			toast.error(
				$i18n.t('Both Docling OCR Engine and Language(s) must be provided or both left empty.')
			);
			return;
		}

		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'datalab_marker' &&
			!RAGConfig.DATALAB_MARKER_API_KEY
		) {
			toast.error($i18n.t('Datalab Marker API Key required.'));
			return;
		}

		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'document_intelligence' &&
			(RAGConfig.DOCUMENT_INTELLIGENCE_ENDPOINT === '' ||
				RAGConfig.DOCUMENT_INTELLIGENCE_KEY === '')
		) {
			toast.error($i18n.t('Document Intelligence endpoint and key required.'));
			return;
		}
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mistral_ocr' &&
			RAGConfig.MISTRAL_OCR_API_KEY === ''
		) {
			toast.error($i18n.t('Mistral OCR API Key required.'));
			return;
		}

		if (!RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL) {
			await embeddingModelUpdateHandler();
		}

		const res = await updateRAGConfig(localStorage.token, {
			...RAGConfig,
			ALLOWED_FILE_EXTENSIONS: RAGConfig.ALLOWED_FILE_EXTENSIONS.split(',')
				.map((ext) => ext.trim())
				.filter((ext) => ext !== ''),
			DATALAB_MARKER_LANGS: RAGConfig.DATALAB_MARKER_LANGS.split(',')
				.map((code) => code.trim())
				.filter((code) => code !== '')
				.join(', '),
			DOCLING_PICTURE_DESCRIPTION_LOCAL: JSON.parse(
				RAGConfig.DOCLING_PICTURE_DESCRIPTION_LOCAL || '{}'
			),
			DOCLING_PICTURE_DESCRIPTION_API: JSON.parse(RAGConfig.DOCLING_PICTURE_DESCRIPTION_API || '{}')
		});
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

			AzureOpenAIKey = embeddingConfig.azure_openai_config.key;
			AzureOpenAIUrl = embeddingConfig.azure_openai_config.url;
			AzureOpenAIVersion = embeddingConfig.azure_openai_config.version;
		}
	};
	onMount(async () => {
		await setEmbeddingConfig();

		const config = await getRAGConfig(localStorage.token);
		config.ALLOWED_FILE_EXTENSIONS = (config?.ALLOWED_FILE_EXTENSIONS ?? []).join(', ');

		config.DOCLING_PICTURE_DESCRIPTION_LOCAL = JSON.stringify(
			config.DOCLING_PICTURE_DESCRIPTION_LOCAL ?? {},
			null,
			2
		);
		config.DOCLING_PICTURE_DESCRIPTION_API = JSON.stringify(
			config.DOCLING_PICTURE_DESCRIPTION_API ?? {},
			null,
			2
		);

		RAGConfig = config;
	});
</script>

<ResetUploadDirConfirmDialog
	bind:show={showResetUploadDirConfirm}
	on:confirm={async () => {
		const res = await deleteAllFiles(localStorage.token).catch((error) => {
			toast.error(`${error}`);
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
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Success'));
		}
	}}
/>

<ReindexKnowledgeFilesConfirmDialog
	bind:show={showReindexConfirm}
	on:confirm={async () => {
		const res = await reindexKnowledgeFiles(localStorage.token).catch((error) => {
			toast.error(`${error}`);
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
	{#if RAGConfig}
		<div class=" space-y-2.5 overflow-y-scroll scrollbar-hidden h-full pr-1.5">
			<div class="">
				<div class="mb-3">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="mb-2.5 flex flex-col w-full justify-between">
						<div class="flex w-full justify-between mb-1">
							<div class="self-center text-xs font-medium">
								{$i18n.t('Content Extraction Engine')}
							</div>
							<div class="">
								<select
									class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
									bind:value={RAGConfig.CONTENT_EXTRACTION_ENGINE}
								>
									<option value="">{$i18n.t('Default')}</option>
									<option value="external">{$i18n.t('External')}</option>
									<option value="tika">{$i18n.t('Tika')}</option>
									<option value="docling">{$i18n.t('Docling')}</option>
									<option value="datalab_marker">{$i18n.t('Datalab Marker API')}</option>
									<option value="document_intelligence">{$i18n.t('Document Intelligence')}</option>
									<option value="mistral_ocr">{$i18n.t('Mistral OCR')}</option>
								</select>
							</div>
						</div>

						{#if RAGConfig.CONTENT_EXTRACTION_ENGINE === ''}
							<div class="flex w-full mt-1">
								<div class="flex-1 flex justify-between">
									<div class=" self-center text-xs font-medium">
										{$i18n.t('PDF Extract Images (OCR)')}
									</div>
									<div class="flex items-center relative">
										<Switch bind:state={RAGConfig.PDF_EXTRACT_IMAGES} />
									</div>
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'datalab_marker'}
							<div class="my-0.5 flex gap-2 pr-2">
								<SensitiveInput
									placeholder={$i18n.t('Enter Datalab Marker API Key')}
									required={false}
									bind:value={RAGConfig.DATALAB_MARKER_API_KEY}
								/>
							</div>

							<div class="flex justify-between w-full mt-2">
								<div class="text-xs font-medium">
									{$i18n.t('Languages')}
								</div>

								<input
									class="text-sm bg-transparent outline-hidden"
									type="text"
									bind:value={RAGConfig.DATALAB_MARKER_LANGS}
									placeholder={$i18n.t('e.g.) en,fr,de')}
								/>
							</div>

							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Significantly improves accuracy by using an LLM to enhance tables, forms, inline math, and layout detection. Will increase latency. Defaults to True.'
										)}
										placement="top-start"
									>
										{$i18n.t('Use LLM')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_USE_LLM} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t('Skip the cache and re-run the inference. Defaults to False.')}
										placement="top-start"
									>
										{$i18n.t('Skip Cache')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_SKIP_CACHE} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Force OCR on all pages of the PDF. This can lead to worse results if you have good text in your PDFs. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Force OCR')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_FORCE_OCR} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Whether to paginate the output. Each page will be separated by a horizontal rule and page number. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Paginate')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_PAGINATE} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Strip existing OCR text from the PDF and re-run OCR. Ignored if Force OCR is enabled. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Strip Existing OCR')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_STRIP_EXISTING_OCR} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											'Disable image extraction from the PDF. If Use LLM is enabled, images will be automatically captioned. Defaults to False.'
										)}
										placement="top-start"
									>
										{$i18n.t('Disable Image Extraction')}
									</Tooltip>
								</div>
								<div class="flex items-center">
									<Switch bind:state={RAGConfig.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION} />
								</div>
							</div>
							<div class="flex justify-between w-full mt-2">
								<div class="self-center text-xs font-medium">
									<Tooltip
										content={$i18n.t(
											"The output format for the text. Can be 'json', 'markdown', or 'html'. Defaults to 'markdown'."
										)}
										placement="top-start"
									>
										{$i18n.t('Output Format')}
									</Tooltip>
								</div>
								<div class="">
									<select
										class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
										bind:value={RAGConfig.DATALAB_MARKER_OUTPUT_FORMAT}
									>
										<option value="markdown">{$i18n.t('Markdown')}</option>
										<option value="json">{$i18n.t('JSON')}</option>
										<option value="html">{$i18n.t('HTML')}</option>
									</select>
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'external'}
							<div class="my-0.5 flex gap-2 pr-2">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter External Document Loader URL')}
									bind:value={RAGConfig.EXTERNAL_DOCUMENT_LOADER_URL}
								/>
								<SensitiveInput
									placeholder={$i18n.t('Enter External Document Loader API Key')}
									required={false}
									bind:value={RAGConfig.EXTERNAL_DOCUMENT_LOADER_API_KEY}
								/>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'tika'}
							<div class="flex w-full mt-1">
								<div class="flex-1 mr-2">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										placeholder={$i18n.t('Enter Tika Server URL')}
										bind:value={RAGConfig.TIKA_SERVER_URL}
									/>
								</div>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'docling'}
							<div class="flex w-full mt-1">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter Docling Server URL')}
									bind:value={RAGConfig.DOCLING_SERVER_URL}
								/>
							</div>
							<div class="flex w-full mt-2">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter Docling OCR Engine')}
									bind:value={RAGConfig.DOCLING_OCR_ENGINE}
								/>
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter Docling OCR Language(s)')}
									bind:value={RAGConfig.DOCLING_OCR_LANG}
								/>
							</div>

							<div class="flex w-full mt-2">
								<div class="flex-1 flex justify-between">
									<div class=" self-center text-xs font-medium">
										{$i18n.t('Describe Pictures in Documents')}
									</div>
									<div class="flex items-center relative">
										<Switch bind:state={RAGConfig.DOCLING_DO_PICTURE_DESCRIPTION} />
									</div>
								</div>
							</div>
							{#if RAGConfig.DOCLING_DO_PICTURE_DESCRIPTION}
								<div class="flex justify-between w-full mt-2">
									<div class="self-center text-xs font-medium">
										<Tooltip content={''} placement="top-start">
											{$i18n.t('Picture Description Mode')}
										</Tooltip>
									</div>
									<div class="">
										<select
											class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
											bind:value={RAGConfig.DOCLING_PICTURE_DESCRIPTION_MODE}
										>
											<option value="">{$i18n.t('Default')}</option>
											<option value="local">{$i18n.t('Local')}</option>
											<option value="api">{$i18n.t('API')}</option>
										</select>
									</div>
								</div>

								{#if RAGConfig.DOCLING_PICTURE_DESCRIPTION_MODE === 'local'}
									<div class="flex flex-col gap-2 mt-2">
										<div class=" flex flex-col w-full justify-between">
											<div class=" mb-1 text-xs font-medium">
												{$i18n.t('Picture Description Local Config')}
											</div>
											<div class="flex w-full items-center relative">
												<Tooltip
													content={$i18n.t(
														'Options for running a local vision-language model in the picture description. The parameters refer to a model hosted on Hugging Face. This parameter is mutually exclusive with picture_description_api.'
													)}
													placement="top-start"
													className="w-full"
												>
													<Textarea
														bind:value={RAGConfig.DOCLING_PICTURE_DESCRIPTION_LOCAL}
														placeholder={$i18n.t('Enter Config in JSON format')}
													/>
												</Tooltip>
											</div>
										</div>
									</div>
								{:else if RAGConfig.DOCLING_PICTURE_DESCRIPTION_MODE === 'api'}
									<div class="flex flex-col gap-2 mt-2">
										<div class=" flex flex-col w-full justify-between">
											<div class=" mb-1 text-xs font-medium">
												{$i18n.t('Picture Description API Config')}
											</div>
											<div class="flex w-full items-center relative">
												<Tooltip
													content={$i18n.t(
														'API details for using a vision-language model in the picture description. This parameter is mutually exclusive with picture_description_local.'
													)}
													placement="top-start"
													className="w-full"
												>
													<Textarea
														bind:value={RAGConfig.DOCLING_PICTURE_DESCRIPTION_API}
														placeholder={$i18n.t('Enter Config in JSON format')}
													/>
												</Tooltip>
											</div>
										</div>
									</div>
								{/if}
							{/if}
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'document_intelligence'}
							<div class="my-0.5 flex gap-2 pr-2">
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									placeholder={$i18n.t('Enter Document Intelligence Endpoint')}
									bind:value={RAGConfig.DOCUMENT_INTELLIGENCE_ENDPOINT}
								/>
								<SensitiveInput
									placeholder={$i18n.t('Enter Document Intelligence Key')}
									bind:value={RAGConfig.DOCUMENT_INTELLIGENCE_KEY}
								/>
							</div>
						{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mistral_ocr'}
							<div class="my-0.5 flex gap-2 pr-2">
								<SensitiveInput
									placeholder={$i18n.t('Enter Mistral API Key')}
									bind:value={RAGConfig.MISTRAL_OCR_API_KEY}
								/>
							</div>
						{/if}
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							<Tooltip content={$i18n.t('Full Context Mode')} placement="top-start">
								{$i18n.t('Bypass Embedding and Retrieval')}
							</Tooltip>
						</div>
						<div class="flex items-center relative">
							<Tooltip
								content={RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL
									? $i18n.t(
											'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
										)
									: $i18n.t(
											'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
										)}
							>
								<Switch bind:state={RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL} />
							</Tooltip>
						</div>
					</div>

					{#if !RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL}
						<div class="  mb-2.5 flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Text Splitter')}</div>
							<div class="flex items-center relative">
								<select
									class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
									bind:value={RAGConfig.TEXT_SPLITTER}
								>
									<option value="">{$i18n.t('Default')} ({$i18n.t('Character')})</option>
									<option value="token">{$i18n.t('Token')} ({$i18n.t('Tiktoken')})</option>
									<option value="markdown_header">{$i18n.t('Markdown (Header)')}</option>
								</select>
							</div>
						</div>

						<div class="  mb-2.5 flex w-full justify-between">
							<div class=" flex gap-1.5 w-full">
								<div class="  w-full justify-between">
									<div class="self-center text-xs font-medium min-w-fit mb-1">
										{$i18n.t('Chunk Size')}
									</div>
									<div class="self-center">
										<input
											class=" w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											type="number"
											placeholder={$i18n.t('Enter Chunk Size')}
											bind:value={RAGConfig.CHUNK_SIZE}
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
											class="w-full rounded-lg py-1.5 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											type="number"
											placeholder={$i18n.t('Enter Chunk Overlap')}
											bind:value={RAGConfig.CHUNK_OVERLAP}
											autocomplete="off"
											min="0"
										/>
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>

				{#if !RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL}
					<div class="mb-3">
						<div class=" mb-2.5 text-base font-medium">{$i18n.t('Embedding')}</div>

						<hr class=" border-gray-100 dark:border-gray-850 my-2" />

						<div class="  mb-2.5 flex flex-col w-full justify-between">
							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Embedding Model Engine')}
								</div>
								<div class="flex items-center relative">
									<select
										class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
										bind:value={embeddingEngine}
										placeholder="Select an embedding model engine"
										on:change={(e) => {
											if (e.target.value === 'ollama') {
												embeddingModel = '';
											} else if (e.target.value === 'openai') {
												embeddingModel = 'text-embedding-3-small';
											} else if (e.target.value === 'azure_openai') {
												embeddingModel = 'text-embedding-3-small';
											} else if (e.target.value === '') {
												embeddingModel = 'sentence-transformers/all-MiniLM-L6-v2';
											}
										}}
									>
										<option value="">{$i18n.t('Default (SentenceTransformers)')}</option>
										<option value="ollama">{$i18n.t('Ollama')}</option>
										<option value="openai">{$i18n.t('OpenAI')}</option>
										<option value="azure_openai">Azure OpenAI</option>
									</select>
								</div>
							</div>

							{#if embeddingEngine === 'openai'}
								<div class="my-0.5 flex gap-2 pr-2">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										placeholder={$i18n.t('API Base URL')}
										bind:value={OpenAIUrl}
										required
									/>

									<SensitiveInput
										placeholder={$i18n.t('API Key')}
										bind:value={OpenAIKey}
										required={false}
									/>
								</div>
							{:else if embeddingEngine === 'ollama'}
								<div class="my-0.5 flex gap-2 pr-2">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
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
							{:else if embeddingEngine === 'azure_openai'}
								<div class="my-0.5 flex flex-col gap-2 pr-2 w-full">
									<div class="flex gap-2">
										<input
											class="flex-1 w-full text-sm bg-transparent outline-hidden"
											placeholder={$i18n.t('API Base URL')}
											bind:value={AzureOpenAIUrl}
											required
										/>
										<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={AzureOpenAIKey} />
									</div>
									<div class="flex gap-2">
										<input
											class="flex-1 w-full text-sm bg-transparent outline-hidden"
											placeholder="Version"
											bind:value={AzureOpenAIVersion}
											required
										/>
									</div>
								</div>
							{/if}
						</div>

						<div class="  mb-2.5 flex flex-col w-full">
							<div class=" mb-1 text-xs font-medium">{$i18n.t('Embedding Model')}</div>

							<div class="">
								{#if embeddingEngine === 'ollama'}
									<div class="flex w-full">
										<div class="flex-1 mr-2">
											<input
												class="flex-1 w-full text-sm bg-transparent outline-hidden"
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
												class="flex-1 w-full text-sm bg-transparent outline-hidden"
												placeholder={$i18n.t('Set embedding model (e.g. {{model}})', {
													model: embeddingModel.slice(-40)
												})}
												bind:value={embeddingModel}
											/>
										</div>

										{#if embeddingEngine === ''}
											<button
												class="px-2.5 bg-transparent text-gray-800 dark:bg-transparent dark:text-gray-100 rounded-lg transition"
												on:click={() => {
													embeddingModelUpdateHandler();
												}}
												disabled={updateEmbeddingModelLoading}
											>
												{#if updateEmbeddingModelLoading}
													<div class="self-center">
														<Spinner />
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
							</div>

							<div class="mt-1 mb-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t(
									'Warning: If you update or change your embedding model, you will need to re-import all documents.'
								)}
							</div>
						</div>

						{#if embeddingEngine === 'ollama' || embeddingEngine === 'openai' || embeddingEngine === 'azure_openai'}
							<div class="  mb-2.5 flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Embedding Batch Size')}
								</div>

								<div class="">
									<input
										bind:value={embeddingBatchSize}
										type="number"
										class=" bg-transparent text-center w-14 outline-none"
										min="-2"
										max="16000"
										step="1"
									/>
								</div>
							</div>
						{/if}
					</div>

					<div class="mb-3">
						<div class=" mb-2.5 text-base font-medium">{$i18n.t('Retrieval')}</div>

						<hr class=" border-gray-100 dark:border-gray-850 my-2" />

						<div class="  mb-2.5 flex w-full justify-between">
							<div class=" self-center text-xs font-medium">{$i18n.t('Full Context Mode')}</div>
							<div class="flex items-center relative">
								<Tooltip
									content={RAGConfig.RAG_FULL_CONTEXT
										? $i18n.t(
												'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
											)
										: $i18n.t(
												'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
											)}
								>
									<Switch bind:state={RAGConfig.RAG_FULL_CONTEXT} />
								</Tooltip>
							</div>
						</div>

						{#if !RAGConfig.RAG_FULL_CONTEXT}
							<div class="  mb-2.5 flex w-full justify-between">
								<div class=" self-center text-xs font-medium">{$i18n.t('Hybrid Search')}</div>
								<div class="flex items-center relative">
									<Switch bind:state={RAGConfig.ENABLE_RAG_HYBRID_SEARCH} />
								</div>
							</div>

							{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
								<div class="  mb-2.5 flex flex-col w-full justify-between">
									<div class="flex w-full justify-between">
										<div class=" self-center text-xs font-medium">
											{$i18n.t('Reranking Engine')}
										</div>
										<div class="flex items-center relative">
											<select
												class="dark:bg-gray-900 w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
												bind:value={RAGConfig.RAG_RERANKING_ENGINE}
												placeholder="Select a reranking model engine"
												on:change={(e) => {
													if (e.target.value === 'external') {
														RAGConfig.RAG_RERANKING_MODEL = '';
													} else if (e.target.value === '') {
														RAGConfig.RAG_RERANKING_MODEL = 'BAAI/bge-reranker-v2-m3';
													}
												}}
											>
												<option value="">{$i18n.t('Default (SentenceTransformers)')}</option>
												<option value="external">{$i18n.t('External')}</option>
											</select>
										</div>
									</div>

									{#if RAGConfig.RAG_RERANKING_ENGINE === 'external'}
										<div class="my-0.5 flex gap-2 pr-2">
											<input
												class="flex-1 w-full text-sm bg-transparent outline-hidden"
												placeholder={$i18n.t('API Base URL')}
												bind:value={RAGConfig.RAG_EXTERNAL_RERANKER_URL}
												required
											/>

											<SensitiveInput
												placeholder={$i18n.t('API Key')}
												bind:value={RAGConfig.RAG_EXTERNAL_RERANKER_API_KEY}
												required={false}
											/>
										</div>
									{/if}
								</div>

								<div class="  mb-2.5 flex flex-col w-full">
									<div class=" mb-1 text-xs font-medium">{$i18n.t('Reranking Model')}</div>

									<div class="">
										<div class="flex w-full">
											<div class="flex-1 mr-2">
												<input
													class="flex-1 w-full text-sm bg-transparent outline-hidden"
													placeholder={$i18n.t('Set reranking model (e.g. {{model}})', {
														model: 'BAAI/bge-reranker-v2-m3'
													})}
													bind:value={RAGConfig.RAG_RERANKING_MODEL}
												/>
											</div>
										</div>
									</div>
								</div>
							{/if}

							<div class="  mb-2.5 flex w-full justify-between">
								<div class=" self-center text-xs font-medium">{$i18n.t('Top K')}</div>
								<div class="flex items-center relative">
									<input
										class="flex-1 w-full text-sm bg-transparent outline-hidden"
										type="number"
										placeholder={$i18n.t('Enter Top K')}
										bind:value={RAGConfig.TOP_K}
										autocomplete="off"
										min="0"
									/>
								</div>
							</div>

							{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
								<div class="mb-2.5 flex w-full justify-between">
									<div class="self-center text-xs font-medium">{$i18n.t('Top K Reranker')}</div>
									<div class="flex items-center relative">
										<input
											class="flex-1 w-full text-sm bg-transparent outline-hidden"
											type="number"
											placeholder={$i18n.t('Enter Top K Reranker')}
											bind:value={RAGConfig.TOP_K_RERANKER}
											autocomplete="off"
											min="0"
										/>
									</div>
								</div>
							{/if}

							{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
								<div class="  mb-2.5 flex flex-col w-full justify-between">
									<div class=" flex w-full justify-between">
										<div class=" self-center text-xs font-medium">
											{$i18n.t('Relevance Threshold')}
										</div>
										<div class="flex items-center relative">
											<input
												class="flex-1 w-full text-sm bg-transparent outline-hidden"
												type="number"
												step="0.01"
												placeholder={$i18n.t('Enter Score')}
												bind:value={RAGConfig.RELEVANCE_THRESHOLD}
												autocomplete="off"
												min="0.0"
												title={$i18n.t(
													'The score should be a value between 0.0 (0%) and 1.0 (100%).'
												)}
											/>
										</div>
									</div>
									<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
										{$i18n.t(
											'Note: If you set a minimum score, the search will only return documents with a score greater than or equal to the minimum score.'
										)}
									</div>
								</div>
							{/if}

							{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
								<div class="mb-2.5 flex w-full justify-between">
									<div class="self-center text-xs font-medium">
										{$i18n.t('Weight of BM25 Retrieval')}
									</div>
									<div class="flex items-center relative">
										<input
											class="flex-1 w-full text-sm bg-transparent outline-hidden"
											type="number"
											step="0.01"
											placeholder={$i18n.t('Enter BM25 Weight')}
											bind:value={RAGConfig.HYBRID_BM25_WEIGHT}
											autocomplete="off"
											min="0.0"
											max="1.0"
										/>
									</div>
								</div>
							{/if}
						{/if}

						<div class="  mb-2.5 flex flex-col w-full justify-between">
							<div class=" mb-1 text-xs font-medium">{$i18n.t('RAG Template')}</div>
							<div class="flex w-full items-center relative">
								<Tooltip
									content={$i18n.t(
										'Leave empty to use the default prompt, or enter a custom prompt'
									)}
									placement="top-start"
									className="w-full"
								>
									<Textarea
										bind:value={RAGConfig.RAG_TEMPLATE}
										placeholder={$i18n.t(
											'Leave empty to use the default prompt, or enter a custom prompt'
										)}
									/>
								</Tooltip>
							</div>
						</div>
					</div>
				{/if}

				<div class="mb-3">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('Files')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Allowed File Extensions')}</div>
						<div class="flex items-center relative">
							<Tooltip
								content={$i18n.t(
									'Allowed file extensions for upload. Separate multiple extensions with commas. Leave empty for all file types.'
								)}
								placement="top-start"
							>
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									type="text"
									placeholder={$i18n.t('e.g. pdf, docx, txt')}
									bind:value={RAGConfig.ALLOWED_FILE_EXTENSIONS}
									autocomplete="off"
								/>
							</Tooltip>
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Max Upload Size')}</div>
						<div class="flex items-center relative">
							<Tooltip
								content={$i18n.t(
									'The maximum file size in MB. If the file size exceeds this limit, the file will not be uploaded.'
								)}
								placement="top-start"
							>
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									type="number"
									placeholder={$i18n.t('Leave empty for unlimited')}
									bind:value={RAGConfig.FILE_MAX_SIZE}
									autocomplete="off"
									min="0"
								/>
							</Tooltip>
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Max Upload Count')}</div>
						<div class="flex items-center relative">
							<Tooltip
								content={$i18n.t(
									'The maximum number of files that can be used at once in chat. If the number of files exceeds this limit, the files will not be uploaded.'
								)}
								placement="top-start"
							>
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									type="number"
									placeholder={$i18n.t('Leave empty for unlimited')}
									bind:value={RAGConfig.FILE_MAX_COUNT}
									autocomplete="off"
									min="0"
								/>
							</Tooltip>
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Image Compression Width')}</div>
						<div class="flex items-center relative">
							<Tooltip
								content={$i18n.t(
									'The width in pixels to compress images to. Leave empty for no compression.'
								)}
								placement="top-start"
							>
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									type="number"
									placeholder={$i18n.t('Leave empty for no compression')}
									bind:value={RAGConfig.FILE_IMAGE_COMPRESSION_WIDTH}
									autocomplete="off"
									min="0"
								/>
							</Tooltip>
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Image Compression Height')}
						</div>
						<div class="flex items-center relative">
							<Tooltip
								content={$i18n.t(
									'The height in pixels to compress images to. Leave empty for no compression.'
								)}
								placement="top-start"
							>
								<input
									class="flex-1 w-full text-sm bg-transparent outline-hidden"
									type="number"
									placeholder={$i18n.t('Leave empty for no compression')}
									bind:value={RAGConfig.FILE_IMAGE_COMPRESSION_HEIGHT}
									autocomplete="off"
									min="0"
								/>
							</Tooltip>
						</div>
					</div>
				</div>

				<div class="mb-3">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('Integration')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Google Drive')}</div>
						<div class="flex items-center relative">
							<Switch bind:state={RAGConfig.ENABLE_GOOGLE_DRIVE_INTEGRATION} />
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('OneDrive')}</div>
						<div class="flex items-center relative">
							<Switch bind:state={RAGConfig.ENABLE_ONEDRIVE_INTEGRATION} />
						</div>
					</div>
				</div>

				<div class="mb-3">
					<div class=" mb-2.5 text-base font-medium">{$i18n.t('Danger Zone')}</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-2" />

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Reset Upload Directory')}</div>
						<div class="flex items-center relative">
							<button
								class="text-xs"
								on:click={() => {
									showResetUploadDirConfirm = true;
								}}
							>
								{$i18n.t('Reset')}
							</button>
						</div>
					</div>

					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Reset Vector Storage/Knowledge')}
						</div>
						<div class="flex items-center relative">
							<button
								class="text-xs"
								on:click={() => {
									showResetConfirm = true;
								}}
							>
								{$i18n.t('Reset')}
							</button>
						</div>
					</div>
					<div class="  mb-2.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Reindex Knowledge Base Vectors')}
						</div>
						<div class="flex items-center relative">
							<button
								class="text-xs"
								on:click={() => {
									showReindexConfirm = true;
								}}
							>
								{$i18n.t('Reindex')}
							</button>
						</div>
					</div>
				</div>
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
	{:else}
		<div class="flex items-center justify-center h-full">
			<Spinner className="size-5" />
		</div>
	{/if}
</form>
