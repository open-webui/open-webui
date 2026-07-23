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
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';

	const i18n = getContext('i18n');

	let updateEmbeddingModelLoading = false;
	let updateRerankingModelLoading = false;

	let showResetConfirm = false;
	let showResetUploadDirConfirm = false;
	let showReindexConfirm = false;
	let showExternalDocumentLoaderHeadersHint = false;

	let RAG_EMBEDDING_ENGINE = '';
	let RAG_EMBEDDING_MODEL = '';
	let RAG_EMBEDDING_BATCH_SIZE = 1;
	let ENABLE_ASYNC_EMBEDDING = true;
	let RAG_EMBEDDING_CONCURRENT_REQUESTS = 0;

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
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const actionButtonClass =
		'shrink-0 text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const embeddingModelUpdateHandler = async () => {
		if (RAG_EMBEDDING_ENGINE === '' && RAG_EMBEDDING_MODEL.split('/').length - 1 > 1) {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}
		if (RAG_EMBEDDING_ENGINE === 'ollama' && RAG_EMBEDDING_MODEL === '') {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}

		if (RAG_EMBEDDING_ENGINE === 'openai' && RAG_EMBEDDING_MODEL === '') {
			toast.error(
				$i18n.t(
					'Model filesystem path detected. Model shortname is required for update, cannot continue.'
				)
			);
			return;
		}

		if (
			RAG_EMBEDDING_ENGINE === 'azure_openai' &&
			(AzureOpenAIKey === '' || AzureOpenAIUrl === '' || AzureOpenAIVersion === '')
		) {
			toast.error($i18n.t('OpenAI URL/Key required.'));
			return;
		}

		console.debug('Update embedding model attempt:', {
			RAG_EMBEDDING_ENGINE,
			RAG_EMBEDDING_MODEL,
			RAG_EMBEDDING_BATCH_SIZE,
			ENABLE_ASYNC_EMBEDDING,
			RAG_EMBEDDING_CONCURRENT_REQUESTS
		});

		updateEmbeddingModelLoading = true;
		const res = await updateEmbeddingConfig(localStorage.token, {
			RAG_EMBEDDING_ENGINE: RAG_EMBEDDING_ENGINE,
			RAG_EMBEDDING_MODEL: RAG_EMBEDDING_MODEL,
			RAG_EMBEDDING_BATCH_SIZE: RAG_EMBEDDING_BATCH_SIZE,
			ENABLE_ASYNC_EMBEDDING: ENABLE_ASYNC_EMBEDDING,
			RAG_EMBEDDING_CONCURRENT_REQUESTS: RAG_EMBEDDING_CONCURRENT_REQUESTS,
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
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'external' &&
			RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS
		) {
			try {
				const headers = JSON.parse(RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS);
				if (headers === null || typeof headers !== 'object' || Array.isArray(headers)) {
					throw new Error('Headers must be a valid JSON object');
				}
				RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS = JSON.stringify(headers, null, 2);
			} catch (error) {
				toast.error($i18n.t('Headers must be a valid JSON object'));
				return;
			}
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
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'datalab_marker' &&
			RAGConfig.DATALAB_MARKER_ADDITIONAL_CONFIG &&
			RAGConfig.DATALAB_MARKER_ADDITIONAL_CONFIG.trim() !== ''
		) {
			try {
				JSON.parse(RAGConfig.DATALAB_MARKER_ADDITIONAL_CONFIG);
			} catch (e) {
				toast.error($i18n.t('Invalid JSON format in Additional Config'));
				return;
			}
		}

		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'document_intelligence' &&
			RAGConfig.DOCUMENT_INTELLIGENCE_ENDPOINT === ''
		) {
			toast.error($i18n.t('Document Intelligence endpoint required.'));
			return;
		}
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mistral_ocr' &&
			RAGConfig.MISTRAL_OCR_API_KEY === ''
		) {
			toast.error($i18n.t('Mistral OCR API Key required.'));
			return;
		}
		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'paddleocr_vl' &&
			RAGConfig.PADDLEOCR_VL_BASE_URL === ''
		) {
			toast.error($i18n.t('PaddleOCR-vl API URL required.'));
			return;
		}

		if (
			RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mineru' &&
			RAGConfig.MINERU_API_MODE === 'cloud' &&
			RAGConfig.MINERU_API_KEY === ''
		) {
			toast.error($i18n.t('MinerU API Key required for Cloud API mode.'));
			return;
		}

		if (!RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL) {
			await embeddingModelUpdateHandler();
		}

		if (RAGConfig.DOCLING_PARAMS) {
			try {
				JSON.parse(RAGConfig.DOCLING_PARAMS);
			} catch (e) {
				toast.error(
					$i18n.t('Invalid JSON format in {{NAME}}', {
						NAME: $i18n.t('Docling Parameters')
					})
				);
				return;
			}
		}
		if (RAGConfig.MINERU_PARAMS) {
			try {
				JSON.parse(RAGConfig.MINERU_PARAMS);
			} catch (e) {
				toast.error($i18n.t('Invalid JSON format in MinerU Parameters'));
				return;
			}
		}

		const res = await updateRAGConfig(localStorage.token, {
			...RAGConfig,
			// Convert null (from cleared number inputs) to empty string so the backend
			// can distinguish "clear this field" from "don't change this field"
			FILE_MAX_SIZE: RAGConfig.FILE_MAX_SIZE ?? '',
			FILE_MAX_COUNT: RAGConfig.FILE_MAX_COUNT ?? '',
			FILE_IMAGE_COMPRESSION_WIDTH: RAGConfig.FILE_IMAGE_COMPRESSION_WIDTH ?? '',
			FILE_IMAGE_COMPRESSION_HEIGHT: RAGConfig.FILE_IMAGE_COMPRESSION_HEIGHT ?? '',
			ALLOWED_FILE_EXTENSIONS: RAGConfig.ALLOWED_FILE_EXTENSIONS.split(',')
				.map((ext) => ext.trim())
				.filter((ext) => ext !== ''),
			DOCLING_PARAMS:
				typeof RAGConfig.DOCLING_PARAMS === 'string' && RAGConfig.DOCLING_PARAMS.trim() !== ''
					? JSON.parse(RAGConfig.DOCLING_PARAMS)
					: {},
			EXTERNAL_DOCUMENT_LOADER_HEADERS:
				typeof RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS === 'string' &&
				RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS.trim() !== ''
					? JSON.parse(RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS)
					: {},
			MINERU_PARAMS:
				typeof RAGConfig.MINERU_PARAMS === 'string' && RAGConfig.MINERU_PARAMS.trim() !== ''
					? JSON.parse(RAGConfig.MINERU_PARAMS)
					: {},
			MINERU_FILE_EXTENSIONS: RAGConfig.MINERU_FILE_EXTENSIONS.split(',')
				.map((ext) => ext.trim())
				.filter((ext) => ext !== '')
		});
		dispatch('save');
	};

	const setEmbeddingConfig = async () => {
		const embeddingConfig = await getEmbeddingConfig(localStorage.token);

		if (embeddingConfig) {
			RAG_EMBEDDING_ENGINE = embeddingConfig.RAG_EMBEDDING_ENGINE;
			RAG_EMBEDDING_MODEL = embeddingConfig.RAG_EMBEDDING_MODEL;
			RAG_EMBEDDING_BATCH_SIZE = embeddingConfig.RAG_EMBEDDING_BATCH_SIZE ?? 1;
			ENABLE_ASYNC_EMBEDDING = embeddingConfig.ENABLE_ASYNC_EMBEDDING ?? true;
			RAG_EMBEDDING_CONCURRENT_REQUESTS = embeddingConfig.RAG_EMBEDDING_CONCURRENT_REQUESTS ?? 0;

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

		config.DOCLING_PARAMS =
			typeof config.DOCLING_PARAMS === 'object'
				? JSON.stringify(config.DOCLING_PARAMS ?? {}, null, 2)
				: config.DOCLING_PARAMS;

		config.MINERU_PARAMS =
			typeof config.MINERU_PARAMS === 'object'
				? JSON.stringify(config.MINERU_PARAMS ?? {}, null, 2)
				: config.MINERU_PARAMS;

		config.EXTERNAL_DOCUMENT_LOADER_HEADERS =
			typeof config.EXTERNAL_DOCUMENT_LOADER_HEADERS === 'object'
				? Object.keys(config.EXTERNAL_DOCUMENT_LOADER_HEADERS ?? {}).length > 0
					? JSON.stringify(config.EXTERNAL_DOCUMENT_LOADER_HEADERS, null, 2)
					: ''
				: config.EXTERNAL_DOCUMENT_LOADER_HEADERS;

		config.MINERU_FILE_EXTENSIONS = (config?.MINERU_FILE_EXTENSIONS ?? ['pdf']).join(', ');
		config.RAG_TOKENIZER_MODEL = config?.RAG_TOKENIZER_MODEL ?? '';

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
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Documents')}</h2>

	{#if RAGConfig}
		<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
			<AdminSettingSection title={$i18n.t('Content Extraction')} first>
				<AdminSettingRow
					label={$i18n.t('Content Extraction Engine')}
					description={$i18n.t('Choose how uploaded documents are parsed before indexing.')}
				>
					<SettingsSelect bind:value={RAGConfig.CONTENT_EXTRACTION_ENGINE}>
						<option value="">{$i18n.t('Default')}</option>
						<option value="external">{$i18n.t('External')}</option>
						<option value="tika">{$i18n.t('Tika')}</option>
						<option value="docling">{$i18n.t('Docling')}</option>
						<option value="datalab_marker">{$i18n.t('Datalab Marker API')}</option>
						<option value="document_intelligence">{$i18n.t('Document Intelligence')}</option>
						<option value="mistral_ocr">{$i18n.t('Mistral OCR')}</option>
						<option value="paddleocr_vl">{$i18n.t('PaddleOCR-vl')}</option>
						<option value="mineru">{$i18n.t('MinerU')}</option>
					</SettingsSelect>
				</AdminSettingRow>

				{#if RAGConfig.CONTENT_EXTRACTION_ENGINE === ''}
					<AdminSettingRow
						label={$i18n.t('PDF Extract Images (OCR)')}
						description={$i18n.t('Extract images from PDFs so OCR can process image-only pages.')}
					>
						<Switch bind:state={RAGConfig.PDF_EXTRACT_IMAGES} />
					</AdminSettingRow>

					<AdminSettingRow
						label={$i18n.t('PDF Loader Mode')}
						description={$i18n.t(
							'Page mode creates one document per page. Single mode keeps pages together for chunking across boundaries.'
						)}
					>
						<SettingsSelect bind:value={RAGConfig.PDF_LOADER_MODE}>
							<option value="page">{$i18n.t('Page')}</option>
							<option value="single">{$i18n.t('Single')}</option>
						</SettingsSelect>
					</AdminSettingRow>
				{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'datalab_marker'}
					<AdminSettingField
						label={$i18n.t('API Base URL')}
						description={$i18n.t('Datalab Marker service endpoint used for document parsing.')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Enter Datalab Marker API Base URL')}
							bind:value={RAGConfig.DATALAB_MARKER_API_BASE_URL}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('API Key')}
						description={$i18n.t('API key used to authenticate with Datalab Marker.')}
					>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('Enter Datalab Marker API Key')}
							required={false}
							bind:value={RAGConfig.DATALAB_MARKER_API_KEY}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('Additional Config')}
						description={$i18n.t('JSON options passed to Marker for advanced parsing behavior.')}
					>
						<Tooltip
							content={$i18n.t(
								'Additional configuration options for marker. This should be a JSON string with key-value pairs. For example, \'{"key": "value"}\'. Supported keys include: disable_links, keep_pageheader_in_output, keep_pagefooter_in_output, filter_blank_pages, drop_repeated_text, layout_coverage_threshold, merge_threshold, height_tolerance, gap_threshold, image_threshold, min_line_length, level_count, default_level'
							)}
							placement="top-start"
							className="w-full"
						>
							<Textarea
								className={textareaClass}
								bind:value={RAGConfig.DATALAB_MARKER_ADDITIONAL_CONFIG}
								placeholder={$i18n.t('Enter JSON config (e.g., {"disable_links": true})')}
							/>
						</Tooltip>
					</AdminSettingField>

					<AdminSettingRow
						label={$i18n.t('Use LLM')}
						description={$i18n.t(
							'Use an LLM to improve tables, forms, math, and layout detection.'
						)}
					>
						<Switch bind:state={RAGConfig.DATALAB_MARKER_USE_LLM} />
					</AdminSettingRow>
					<AdminSettingRow
						label={$i18n.t('Skip Cache')}
						description={$i18n.t('Skip cached Marker results and rerun inference.')}
					>
						<Switch bind:state={RAGConfig.DATALAB_MARKER_SKIP_CACHE} />
					</AdminSettingRow>
					<AdminSettingRow
						label={$i18n.t('Force OCR')}
						description={$i18n.t('Run OCR on all PDF pages, even pages with embedded text.')}
					>
						<Switch bind:state={RAGConfig.DATALAB_MARKER_FORCE_OCR} />
					</AdminSettingRow>
					<AdminSettingRow
						label={$i18n.t('Paginate')}
						description={$i18n.t('Separate output by page with page markers.')}
					>
						<Switch bind:state={RAGConfig.DATALAB_MARKER_PAGINATE} />
					</AdminSettingRow>
					<AdminSettingRow
						label={$i18n.t('Strip Existing OCR')}
						description={$i18n.t('Remove existing OCR text and rerun OCR when Force OCR is off.')}
					>
						<Switch bind:state={RAGConfig.DATALAB_MARKER_STRIP_EXISTING_OCR} />
					</AdminSettingRow>
					<AdminSettingRow
						label={$i18n.t('Disable Image Extraction')}
						description={$i18n.t('Do not extract images from PDFs during Marker processing.')}
					>
						<Switch bind:state={RAGConfig.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION} />
					</AdminSettingRow>
					<AdminSettingRow
						label={$i18n.t('Format Lines')}
						description={$i18n.t('Format lines to detect inline math and styles.')}
					>
						<Switch bind:state={RAGConfig.DATALAB_MARKER_FORMAT_LINES} />
					</AdminSettingRow>
					<AdminSettingRow
						label={$i18n.t('Output Format')}
						description={$i18n.t('Text output format returned by Marker.')}
					>
						<SettingsSelect bind:value={RAGConfig.DATALAB_MARKER_OUTPUT_FORMAT}>
							<option value="markdown">{$i18n.t('Markdown')}</option>
							<option value="json">{$i18n.t('JSON')}</option>
							<option value="html">{$i18n.t('HTML')}</option>
						</SettingsSelect>
					</AdminSettingRow>
				{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'external'}
					<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
						<AdminSettingField
							label={$i18n.t('Document Loader URL')}
							description={$i18n.t('External service endpoint used to load document content.')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter External Document Loader URL')}
								bind:value={RAGConfig.EXTERNAL_DOCUMENT_LOADER_URL}
							/>
						</AdminSettingField>
						<AdminSettingField
							label={$i18n.t('API Key')}
							description={$i18n.t('API key sent to the external document loader.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('Enter External Document Loader API Key')}
								required={false}
								bind:value={RAGConfig.EXTERNAL_DOCUMENT_LOADER_API_KEY}
							/>
						</AdminSettingField>
					</div>

					<AdminSettingField
						label={$i18n.t('Headers')}
						description={$i18n.t('Additional JSON headers sent to the external document loader.')}
					>
						<Tooltip
							content={$i18n.t(
								'Enter additional headers in JSON format (e.g. {"X-Custom-Header": "value"}'
							)}
						>
							<Textarea
								className={textareaClass}
								bind:value={RAGConfig.EXTERNAL_DOCUMENT_LOADER_HEADERS}
								placeholder={$i18n.t('Enter additional headers in JSON format')}
								required={false}
							/>
						</Tooltip>
						<button
							type="button"
							class="mt-1 text-[0.6875rem] text-gray-400 transition-colors hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
							on:click={() =>
								(showExternalDocumentLoaderHeadersHint = !showExternalDocumentLoaderHeadersHint)}
						>
							{$i18n.t('Header variables')}
						</button>
						{#if showExternalDocumentLoaderHeadersHint}
							<div class="mt-1 text-[0.6875rem] leading-5 text-gray-500 dark:text-gray-400">
								<div>{$i18n.t('No additional headers are sent unless configured.')}</div>
								<div>
									{$i18n.t('Example')}:
									<code class="text-gray-700 dark:text-gray-300"
										>{'{"X-OpenWebUI-File-Id": "{{FILE_ID}}"}'}</code
									>
								</div>
								<div>
									{$i18n.t('Available variables')}:
									<code class="text-gray-700 dark:text-gray-300">{'{{FILE_ID}}'}</code>,
									<code class="text-gray-700 dark:text-gray-300">{'{{FILE_NAME}}'}</code>,
									<code class="text-gray-700 dark:text-gray-300">{'{{FILE_CONTENT_TYPE}}'}</code>
								</div>
							</div>
						{/if}
					</AdminSettingField>
				{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'tika'}
					<AdminSettingField
						label={$i18n.t('Tika Server URL')}
						description={$i18n.t('Tika server endpoint used for content extraction.')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Enter Tika Server URL')}
							bind:value={RAGConfig.TIKA_SERVER_URL}
						/>
					</AdminSettingField>
				{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'docling'}
					<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
						<AdminSettingField
							label={$i18n.t('Docling Server URL')}
							description={$i18n.t('Docling service endpoint used for parsing.')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter Docling Server URL')}
								bind:value={RAGConfig.DOCLING_SERVER_URL}
							/>
						</AdminSettingField>
						<AdminSettingField
							label={$i18n.t('API Key')}
							description={$i18n.t('API key sent to Docling.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('Enter Docling API Key')}
								bind:value={RAGConfig.DOCLING_API_KEY}
								required={false}
							/>
						</AdminSettingField>
					</div>

					<AdminSettingField
						label={$i18n.t('Parameters')}
						description={$i18n.t('Additional Docling parameters in JSON format.')}
					>
						<Textarea
							className={textareaClass}
							bind:value={RAGConfig.DOCLING_PARAMS}
							placeholder={$i18n.t('Enter additional parameters in JSON format')}
							minSize={100}
						/>
					</AdminSettingField>
				{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'document_intelligence'}
					<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
						<AdminSettingField
							label={$i18n.t('Endpoint')}
							description={$i18n.t('Document Intelligence endpoint used for parsing.')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter Document Intelligence Endpoint')}
								bind:value={RAGConfig.DOCUMENT_INTELLIGENCE_ENDPOINT}
							/>
						</AdminSettingField>
						<AdminSettingField
							label={$i18n.t('Key')}
							description={$i18n.t('Credential used for Document Intelligence.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('Enter Document Intelligence Key')}
								bind:value={RAGConfig.DOCUMENT_INTELLIGENCE_KEY}
								required={false}
							/>
						</AdminSettingField>
					</div>

					<AdminSettingField
						label={$i18n.t('Document Intelligence Model')}
						description={$i18n.t('Model name used by Document Intelligence.')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('Enter Document Intelligence Model')}
							bind:value={RAGConfig.DOCUMENT_INTELLIGENCE_MODEL}
						/>
					</AdminSettingField>
				{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mistral_ocr'}
					<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
						<AdminSettingField
							label={$i18n.t('API Base URL')}
							description={$i18n.t('Mistral OCR service endpoint.')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter Mistral API Base URL')}
								bind:value={RAGConfig.MISTRAL_OCR_API_BASE_URL}
							/>
						</AdminSettingField>
						<AdminSettingField
							label={$i18n.t('API Key')}
							description={$i18n.t('API key sent to Mistral OCR.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('Enter Mistral API Key')}
								bind:value={RAGConfig.MISTRAL_OCR_API_KEY}
							/>
						</AdminSettingField>
					</div>
					<AdminSettingRow
						label={$i18n.t('Use Base64')}
						description={$i18n.t('Send PDFs as base64 data URLs instead of uploading first.')}
					>
						<Switch bind:state={RAGConfig.MISTRAL_OCR_USE_BASE64} />
					</AdminSettingRow>
				{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'paddleocr_vl'}
					<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
						<AdminSettingField
							label={$i18n.t('API Base URL')}
							description={$i18n.t('PaddleOCR-vl service endpoint.')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter PaddleOCR-vl API Base URL')}
								bind:value={RAGConfig.PADDLEOCR_VL_BASE_URL}
							/>
						</AdminSettingField>
						<AdminSettingField
							label={$i18n.t('API Token')}
							description={$i18n.t('API token sent to PaddleOCR-vl.')}
						>
							<SensitiveInput
								variant="settings"
								placeholder={$i18n.t('Enter PaddleOCR-vl API Token')}
								bind:value={RAGConfig.PADDLEOCR_VL_TOKEN}
								required={false}
							/>
						</AdminSettingField>
					</div>
				{:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'mineru'}
					<AdminSettingRow
						label={$i18n.t('API Mode')}
						description={$i18n.t('Choose the local or cloud MinerU API mode.')}
					>
						<SettingsSelect
							bind:value={RAGConfig.MINERU_API_MODE}
							on:change={() => {
								const cloudUrl = 'https://mineru.net/api/v4';
								const localUrl = 'http://localhost:8000';

								if (RAGConfig.MINERU_API_MODE === 'cloud') {
									if (!RAGConfig.MINERU_API_URL || RAGConfig.MINERU_API_URL === localUrl) {
										RAGConfig.MINERU_API_URL = cloudUrl;
									}
								} else {
									if (!RAGConfig.MINERU_API_URL || RAGConfig.MINERU_API_URL === cloudUrl) {
										RAGConfig.MINERU_API_URL = localUrl;
									}
								}
							}}
						>
							<option value="local">{$i18n.t('local')}</option>
							<option value="cloud">{$i18n.t('cloud')}</option>
						</SettingsSelect>
					</AdminSettingRow>

					<AdminSettingField
						label={$i18n.t('API URL')}
						description={$i18n.t('MinerU API endpoint for the selected mode.')}
					>
						<input
							class={inputClass}
							placeholder={RAGConfig.MINERU_API_MODE === 'cloud'
								? $i18n.t('https://mineru.net/api/v4')
								: $i18n.t('http://localhost:8000')}
							bind:value={RAGConfig.MINERU_API_URL}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('API Key')}
						description={$i18n.t('API key used for MinerU cloud mode.')}
					>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('Enter MinerU API Key')}
							bind:value={RAGConfig.MINERU_API_KEY}
						/>
					</AdminSettingField>

					<AdminSettingRow
						label={$i18n.t('API Timeout')}
						description={$i18n.t('Maximum time in seconds to wait for MinerU API responses.')}
					>
						<input
							class="w-16 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-right text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
							type="number"
							min="1"
							bind:value={RAGConfig.MINERU_API_TIMEOUT}
							placeholder="60"
						/>
					</AdminSettingRow>

					<AdminSettingField
						label={$i18n.t('Parameters')}
						description={$i18n.t('Advanced MinerU parsing parameters in JSON format.')}
					>
						<Textarea
							className={textareaClass}
							bind:value={RAGConfig.MINERU_PARAMS}
							placeholder={`{\n  "enable_ocr": false,\n  "enable_formula": true,\n  "enable_table": true,\n  "language": "en",\n  "model_version": "pipeline",\n  "page_ranges": ""\n}`}
							minSize={100}
						/>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('File Extensions')}
						description={$i18n.t('Comma-separated extensions MinerU should handle.')}
					>
						<input
							class={inputClass}
							placeholder={$i18n.t('pdf, docx, pptx, xlsx')}
							bind:value={RAGConfig.MINERU_FILE_EXTENSIONS}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('Bypass Embedding and Retrieval')}
					description={RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL
						? $i18n.t('Inject the entire content as context for comprehensive processing.')
						: $i18n.t('Use segmented retrieval for focused and relevant context.')}
				>
					<Switch bind:state={RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL} />
				</AdminSettingRow>

				{#if !RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL}
					<AdminSettingRow
						label={$i18n.t('Text Splitter')}
						description={$i18n.t('Choose how extracted text is split before indexing.')}
					>
						<SettingsSelect bind:value={RAGConfig.TEXT_SPLITTER}>
							<option value="">{$i18n.t('Default')} ({$i18n.t('Character')})</option>
							<option value="token">{$i18n.t('Token')} ({$i18n.t('Tiktoken')})</option>
							<option value="token_transformers">
								{$i18n.t('Token')} ({$i18n.t('Transformers')})
							</option>
						</SettingsSelect>
					</AdminSettingRow>

					{#if RAGConfig.TEXT_SPLITTER === 'token_transformers'}
						<AdminSettingField
							label={$i18n.t('Tokenizer Model')}
							description={$i18n.t('Tokenizer model used for transformer token splitting.')}
						>
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter Tokenizer Model')}
								bind:value={RAGConfig.RAG_TOKENIZER_MODEL}
								autocomplete="off"
								required={RAG_EMBEDDING_ENGINE !== ''}
							/>
						</AdminSettingField>
					{/if}

					<AdminSettingRow
						label={$i18n.t('Markdown Header Text Splitter')}
						description={$i18n.t(
							'Split documents by markdown headers before character or token splitting.'
						)}
					>
						<Switch bind:state={RAGConfig.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER} />
					</AdminSettingRow>

					<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
						<AdminSettingField
							label={$i18n.t('Chunk Size')}
							description={$i18n.t('Maximum size for each text chunk.')}
						>
							<input
								class={inputClass}
								type="number"
								placeholder={$i18n.t('Enter Chunk Size')}
								bind:value={RAGConfig.CHUNK_SIZE}
								autocomplete="off"
								min="0"
							/>
						</AdminSettingField>
						<AdminSettingField
							label={$i18n.t('Chunk Overlap')}
							description={$i18n.t('Overlap preserved between neighboring chunks.')}
						>
							<input
								class={inputClass}
								type="number"
								placeholder={$i18n.t('Enter Chunk Overlap')}
								bind:value={RAGConfig.CHUNK_OVERLAP}
								autocomplete="off"
								min="0"
							/>
						</AdminSettingField>
					</div>

					{#if RAGConfig.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER}
						<AdminSettingField
							label={$i18n.t('Chunk Min Size Target')}
							description={$i18n.t(
								'Merge chunks smaller than this threshold when possible. Set to 0 to disable merging.'
							)}
						>
							<input
								class={inputClass}
								type="number"
								placeholder={$i18n.t('Enter Chunk Min Size Target')}
								bind:value={RAGConfig.CHUNK_MIN_SIZE_TARGET}
								autocomplete="off"
								min="0"
							/>
						</AdminSettingField>
					{/if}
				{/if}
			</AdminSettingSection>

			{#if !RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL}
				<AdminSettingSection title={$i18n.t('Embedding')}>
					<AdminSettingRow
						label={$i18n.t('Embedding Model Engine')}
						description={$i18n.t('Provider used to generate document embeddings.')}
					>
						<SettingsSelect
							bind:value={RAG_EMBEDDING_ENGINE}
							placeholder={$i18n.t('Select an embedding model engine')}
							on:change={(e) => {
								if (e.target.value === 'ollama') {
									RAG_EMBEDDING_MODEL = '';
								} else if (e.target.value === 'openai') {
									RAG_EMBEDDING_MODEL = 'text-embedding-3-small';
								} else if (e.target.value === 'azure_openai') {
									RAG_EMBEDDING_MODEL = 'text-embedding-3-small';
								} else if (e.target.value === '') {
									RAG_EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2';
								}
							}}
						>
							<option value="">{$i18n.t('Default (SentenceTransformers)')}</option>
							<option value="ollama">{$i18n.t('Ollama')}</option>
							<option value="openai">{$i18n.t('OpenAI')}</option>
							<option value="azure_openai">{$i18n.t('Azure OpenAI')}</option>
						</SettingsSelect>
					</AdminSettingRow>

					{#if RAG_EMBEDDING_ENGINE === 'openai'}
						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('API Base URL')}
								description={$i18n.t('OpenAI-compatible embeddings endpoint.')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('API Base URL')}
									bind:value={OpenAIUrl}
									required
								/>
							</AdminSettingField>
							<AdminSettingField
								label={$i18n.t('API Key')}
								description={$i18n.t('API key for embedding requests.')}
							>
								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('API Key')}
									bind:value={OpenAIKey}
									required={false}
								/>
							</AdminSettingField>
						</div>
					{:else if RAG_EMBEDDING_ENGINE === 'ollama'}
						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('API Base URL')}
								description={$i18n.t('Ollama endpoint used for embeddings.')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('API Base URL')}
									bind:value={OllamaUrl}
									required
								/>
							</AdminSettingField>
							<AdminSettingField
								label={$i18n.t('API Key')}
								description={$i18n.t('Optional API key for Ollama requests.')}
							>
								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('API Key')}
									bind:value={OllamaKey}
									required={false}
								/>
							</AdminSettingField>
						</div>
					{:else if RAG_EMBEDDING_ENGINE === 'azure_openai'}
						<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
							<AdminSettingField
								label={$i18n.t('API Base URL')}
								description={$i18n.t('Azure OpenAI endpoint used for embeddings.')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('API Base URL')}
									bind:value={AzureOpenAIUrl}
									required
								/>
							</AdminSettingField>
							<AdminSettingField
								label={$i18n.t('API Key')}
								description={$i18n.t('Azure OpenAI API key.')}
							>
								<SensitiveInput
									variant="settings"
									placeholder={$i18n.t('API Key')}
									bind:value={AzureOpenAIKey}
								/>
							</AdminSettingField>
							<AdminSettingField
								label={$i18n.t('Version')}
								description={$i18n.t('Azure OpenAI API version.')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('Version')}
									bind:value={AzureOpenAIVersion}
									required
								/>
							</AdminSettingField>
						</div>
					{/if}

					<AdminSettingField
						label={$i18n.t('Embedding Model')}
						description={$i18n.t(
							'Model used to generate embeddings. Reindex knowledge after changing this.'
						)}
					>
						<div class="flex w-full gap-2">
							<input
								class={inputClass}
								placeholder={RAG_EMBEDDING_ENGINE === 'ollama'
									? $i18n.t('Set embedding model')
									: $i18n.t('Set embedding model (e.g. {{model}})', {
											model: RAG_EMBEDDING_MODEL.slice(-40)
										})}
								bind:value={RAG_EMBEDDING_MODEL}
								required={RAG_EMBEDDING_ENGINE === 'ollama'}
							/>

							{#if RAG_EMBEDDING_ENGINE === ''}
								<button
									class="flex size-7 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-500 dark:hover:bg-white/5 dark:hover:text-white"
									type="button"
									on:click={() => {
										embeddingModelUpdateHandler();
									}}
									disabled={updateEmbeddingModelLoading}
									aria-label={$i18n.t('Update embedding model')}
								>
									{#if updateEmbeddingModelLoading}
										<Spinner />
									{:else}
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="size-4"
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
						<div class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t(
								'After changing the embedding model, reindex the knowledge base for changes to take effect.'
							)}
						</div>
					</AdminSettingField>

					<AdminSettingRow
						label={$i18n.t('Embedding Batch Size')}
						description={$i18n.t('Number of items processed per embedding batch.')}
					>
						<input
							bind:value={RAG_EMBEDDING_BATCH_SIZE}
							type="number"
							class="w-14 bg-transparent text-center text-xs outline-none"
							min="-2"
							max="16000"
							step="1"
						/>
					</AdminSettingRow>

					{#if RAG_EMBEDDING_ENGINE === 'ollama' || RAG_EMBEDDING_ENGINE === 'openai' || RAG_EMBEDDING_ENGINE === 'azure_openai'}
						<AdminSettingRow
							label={$i18n.t('Async Embedding Processing')}
							description={$i18n.t('Run embedding tasks concurrently to speed up processing.')}
						>
							<Switch bind:state={ENABLE_ASYNC_EMBEDDING} />
						</AdminSettingRow>
						<AdminSettingRow
							label={$i18n.t('Embedding Concurrent Requests')}
							description={$i18n.t(
								'Maximum concurrent embedding requests. Set to 0 for unlimited.'
							)}
						>
							<input
								bind:value={RAG_EMBEDDING_CONCURRENT_REQUESTS}
								type="number"
								class="w-14 bg-transparent text-center text-xs outline-none"
								min="0"
								step="1"
							/>
						</AdminSettingRow>
					{/if}
				</AdminSettingSection>
			{/if}

			<AdminSettingSection title={$i18n.t('Retrieval')}>
				{#if !RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL}
					<AdminSettingRow
						label={$i18n.t('Full Context Mode')}
						description={RAGConfig.RAG_FULL_CONTEXT
							? $i18n.t('Inject entire documents as context for comprehensive processing.')
							: $i18n.t('Use segmented retrieval for focused context.')}
					>
						<Switch bind:state={RAGConfig.RAG_FULL_CONTEXT} />
					</AdminSettingRow>

					{#if !RAGConfig.RAG_FULL_CONTEXT}
						<AdminSettingRow
							label={$i18n.t('Hybrid Search')}
							description={$i18n.t('Combine semantic and keyword retrieval.')}
						>
							<Switch bind:state={RAGConfig.ENABLE_RAG_HYBRID_SEARCH} />
						</AdminSettingRow>

						{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
							<AdminSettingRow
								label={$i18n.t('Enrich Hybrid Search Text')}
								description={$i18n.t(
									'Add filenames, titles, sections, and snippets to improve lexical recall.'
								)}
							>
								<Switch bind:state={RAGConfig.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS} />
							</AdminSettingRow>

							<AdminSettingRow
								label={$i18n.t('Reranking Engine')}
								description={$i18n.t('Provider used to rerank hybrid search results.')}
							>
								<SettingsSelect
									bind:value={RAGConfig.RAG_RERANKING_ENGINE}
									placeholder={$i18n.t('Select a reranking model engine')}
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
								</SettingsSelect>
							</AdminSettingRow>

							{#if RAGConfig.RAG_RERANKING_ENGINE === 'external'}
								<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
									<AdminSettingField
										label={$i18n.t('API Base URL')}
										description={$i18n.t('External reranker endpoint.')}
									>
										<input
											class={inputClass}
											placeholder={$i18n.t('API Base URL')}
											bind:value={RAGConfig.RAG_EXTERNAL_RERANKER_URL}
											required
										/>
									</AdminSettingField>
									<AdminSettingField
										label={$i18n.t('API Key')}
										description={$i18n.t('API key sent to the external reranker.')}
									>
										<SensitiveInput
											variant="settings"
											placeholder={$i18n.t('API Key')}
											bind:value={RAGConfig.RAG_EXTERNAL_RERANKER_API_KEY}
											required={false}
										/>
									</AdminSettingField>
								</div>
							{/if}

							<AdminSettingField
								label={$i18n.t('Reranking Model')}
								description={$i18n.t('Model used to rerank retrieved results.')}
							>
								<input
									class={inputClass}
									placeholder={$i18n.t('Set reranking model (e.g. {{model}})', {
										model: 'BAAI/bge-reranker-v2-m3'
									})}
									bind:value={RAGConfig.RAG_RERANKING_MODEL}
								/>
							</AdminSettingField>
						{/if}

						<AdminSettingRow
							label={$i18n.t('Reranking Batch Size')}
							description={$i18n.t('Number of results processed per reranking batch.')}
						>
							<input
								bind:value={RAGConfig.RAG_RERANKING_BATCH_SIZE}
								type="number"
								class="w-14 bg-transparent text-center text-xs outline-none"
								min="1"
								max="16000"
								step="1"
							/>
						</AdminSettingRow>

						<AdminSettingField
							label={$i18n.t('Top K')}
							description={$i18n.t('Maximum number of retrieved chunks returned to the model.')}
						>
							<input
								class={inputClass}
								type="number"
								placeholder={$i18n.t('Enter Top K')}
								bind:value={RAGConfig.TOP_K}
								autocomplete="off"
								min="0"
							/>
						</AdminSettingField>

						{#if RAGConfig.ENABLE_RAG_HYBRID_SEARCH === true}
							<AdminSettingField
								label={$i18n.t('Top K Reranker')}
								description={$i18n.t('Maximum number of hybrid results sent to the reranker.')}
							>
								<input
									class={inputClass}
									type="number"
									placeholder={$i18n.t('Enter Top K Reranker')}
									bind:value={RAGConfig.TOP_K_RERANKER}
									autocomplete="off"
									min="0"
								/>
							</AdminSettingField>

							<AdminSettingField
								label={$i18n.t('Relevance Threshold')}
								description={$i18n.t(
									'Only return documents with a score greater than or equal to this value.'
								)}
							>
								<input
									class={inputClass}
									type="number"
									step="0.01"
									placeholder={$i18n.t('Enter Score')}
									bind:value={RAGConfig.RELEVANCE_THRESHOLD}
									autocomplete="off"
									min="0.0"
									title={$i18n.t('The score should be a value between 0.0 (0%) and 1.0 (100%).')}
								/>
							</AdminSettingField>

							<AdminSettingRow
								label={$i18n.t('BM25 Weight')}
								description={$i18n.t('Balance semantic and lexical weighting for hybrid search.')}
							>
								<button
									class={actionButtonClass}
									type="button"
									on:click={() => {
										RAGConfig.HYBRID_BM25_WEIGHT =
											(RAGConfig?.HYBRID_BM25_WEIGHT ?? null) === null ? 0.5 : null;
									}}
								>
									{(RAGConfig?.HYBRID_BM25_WEIGHT ?? null) === null
										? $i18n.t('Default')
										: $i18n.t('Custom')}
								</button>
							</AdminSettingRow>

							{#if (RAGConfig?.HYBRID_BM25_WEIGHT ?? null) !== null}
								<div class="flex items-center gap-2">
									<div class="flex-1">
										<input
											id="steps-range"
											type="range"
											min="0"
											max="1"
											step="0.05"
											bind:value={RAGConfig.HYBRID_BM25_WEIGHT}
											class="h-2 w-full cursor-pointer appearance-none rounded-lg dark:bg-gray-700"
										/>
										<div
											class="flex justify-between py-0.5 text-[0.6875rem] text-gray-400 dark:text-gray-600"
										>
											<div>{$i18n.t('semantic')}</div>
											<div>{$i18n.t('lexical')}</div>
										</div>
									</div>
									<input
										bind:value={RAGConfig.HYBRID_BM25_WEIGHT}
										type="number"
										class="w-14 bg-transparent text-center text-xs outline-none"
										min="0"
										max="1"
										step="any"
									/>
								</div>
							{/if}
						{/if}
					{/if}
				{/if}

				<AdminSettingField
					label={$i18n.t('RAG Template')}
					description={$i18n.t('Prompt template used when retrieved context is injected.')}
				>
					<Tooltip
						content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
						placement="top-start"
						className="w-full"
					>
						<Textarea
							className={textareaClass}
							bind:value={RAGConfig.RAG_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>

					{#if RAGConfig.RAG_TEMPLATE && (RAGConfig.RAG_TEMPLATE.match(/\[context\]/g) || []).length + (RAGConfig.RAG_TEMPLATE.match(/\{\{CONTEXT\}\}/g) || []).length > 1}
						<div class="mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{$i18n.t(
								'This template contains multiple context placeholders ([context] or {{CONTEXT}}). Context will be injected at each occurrence.'
							)}
						</div>
					{/if}
				</AdminSettingField>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Files')}>
				<AdminSettingField
					label={$i18n.t('Allowed File Extensions')}
					description={$i18n.t(
						'Comma-separated upload extensions. Leave empty for all file types.'
					)}
				>
					<input
						class={inputClass}
						type="text"
						placeholder={$i18n.t('e.g. pdf, docx, txt')}
						bind:value={RAGConfig.ALLOWED_FILE_EXTENSIONS}
						autocomplete="off"
					/>
				</AdminSettingField>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Max Upload Size')}
						description={$i18n.t('Maximum file size in MB. Leave empty for unlimited.')}
					>
						<input
							class={inputClass}
							type="number"
							placeholder={$i18n.t('Leave empty for unlimited')}
							bind:value={RAGConfig.FILE_MAX_SIZE}
							autocomplete="off"
							min="0"
						/>
					</AdminSettingField>
					<AdminSettingField
						label={$i18n.t('Max Upload Count')}
						description={$i18n.t('Maximum number of files that can be used at once in chat.')}
					>
						<input
							class={inputClass}
							type="number"
							placeholder={$i18n.t('Leave empty for unlimited')}
							bind:value={RAGConfig.FILE_MAX_COUNT}
							autocomplete="off"
							min="0"
						/>
					</AdminSettingField>
				</div>

				<div class="grid grid-cols-1 gap-x-3 gap-y-2.5 sm:grid-cols-2">
					<AdminSettingField
						label={$i18n.t('Image Compression Width')}
						description={$i18n.t(
							'Width in pixels to compress images to. Leave empty for no compression.'
						)}
					>
						<input
							class={inputClass}
							type="number"
							placeholder={$i18n.t('Leave empty for no compression')}
							bind:value={RAGConfig.FILE_IMAGE_COMPRESSION_WIDTH}
							autocomplete="off"
							min="0"
						/>
					</AdminSettingField>
					<AdminSettingField
						label={$i18n.t('Image Compression Height')}
						description={$i18n.t(
							'Height in pixels to compress images to. Leave empty for no compression.'
						)}
					>
						<input
							class={inputClass}
							type="number"
							placeholder={$i18n.t('Leave empty for no compression')}
							bind:value={RAGConfig.FILE_IMAGE_COMPRESSION_HEIGHT}
							autocomplete="off"
							min="0"
						/>
					</AdminSettingField>
				</div>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Integration')}>
				<AdminSettingRow
					label={$i18n.t('Google Drive')}
					description={$i18n.t('Allow Google Drive as a document source.')}
				>
					<Switch bind:state={RAGConfig.ENABLE_GOOGLE_DRIVE_INTEGRATION} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('OneDrive')}
					description={$i18n.t('Allow OneDrive as a document source.')}
				>
					<Switch bind:state={RAGConfig.ENABLE_ONEDRIVE_INTEGRATION} />
				</AdminSettingRow>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('Danger Zone')}>
				<AdminSettingRow
					label={$i18n.t('Reset Upload Directory')}
					description={$i18n.t('Delete uploaded files from the upload directory.')}
				>
					<button
						class={actionButtonClass}
						type="button"
						on:click={() => {
							showResetUploadDirConfirm = true;
						}}
					>
						{$i18n.t('Reset')}
					</button>
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('Reset Vector Storage/Knowledge')}
					description={$i18n.t('Clear vector storage and knowledge indexing data.')}
				>
					<button
						class={actionButtonClass}
						type="button"
						on:click={() => {
							showResetConfirm = true;
						}}
					>
						{$i18n.t('Reset')}
					</button>
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('Reindex Knowledge Base Vectors')}
					description={$i18n.t('Rebuild vectors for existing knowledge files.')}
				>
					<button
						class={actionButtonClass}
						type="button"
						on:click={() => {
							showReindexConfirm = true;
						}}
					>
						{$i18n.t('Reindex')}
					</button>
				</AdminSettingRow>
			</AdminSettingSection>
		</div>

		<div class="flex justify-end pt-6 text-sm font-normal">
			<button
				class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
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
