<script>
    import { goto } from '$app/navigation';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
    import { toast } from 'svelte-sonner';
    import Switch from '$lib/components/common/Switch.svelte';
    import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
    import Tooltip from '$lib/components/common/Tooltip.svelte';

    import { createNewKnowledge, getKnowledgeBases } from '$lib/apis/knowledge';
    import { knowledge, user } from '$lib/stores';
    import AccessControl from '../common/AccessControl.svelte';


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

	import Textarea from '$lib/components/common/Textarea.svelte';
	import resourcesToBackend from 'i18next-resources-to-backend';

    const i18n = getContext('i18n');

    let loading = false;
    let name = '';
    let description = '';
    let accessControl = {};
	
	let updateEmbeddingModelLoading = false;

	let embeddingEngine = '';
	let embeddingModel = '';
	let embeddingBatchSize = 1;

	let OpenAIUrl = '';
	let OpenAIKey = '';

	let OllamaUrl = '';
	let OllamaKey = '';

	let querySettings = {
		template: '',
		r: 0.0,
		k: 4,
		k_reranker: 4,
		hybrid: false
	};

	let enableIndividualRagConfig = false;

    let RAGConfig = null;

	const embeddingModelUpdateHandler = async (knowledgeId) => {

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
			},
            knowledge_id: knowledgeId
		}).catch(async (error) => {
			toast.error(`${error}`);
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


    const submitHandler = async () => {
		loading = true;

        if (name.trim() === '' || description.trim() === '') {
            toast.error($i18n.t('Please fill in all fields.'));
            loading = false;
            return;
        }

		if (enableIndividualRagConfig) {
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
		}

        const res = await createNewKnowledge(localStorage.token, 
            name, 
            description, 
            accessControl,
            RAGConfig
        ).catch((e) => {
            toast.error(`${e}`);
        });

        if (res) {
            toast.success($i18n.t('Knowledge base created successfully.'));
            knowledge.set(await getKnowledgeBases(localStorage.token));
            goto(`/workspace/knowledge/${res.id}`);
        }
        if (enableIndividualRagConfig) {
			if (!RAGConfig.BYPASS_EMBEDDING_AND_RETRIEVAL) {
				await embeddingModelUpdateHandler(res.id);

				if (RAGConfig.ENABLE_RAG_HYBRID_SEARCH) {
                    const { 
                        embedding_engine, 
                        embedding_model, 
                        embedding_batch_size, 
                        openai_config, 
                        ollama_config, 
                        LOADED_EMBEDDING_MODELS,
                        DOWNLOADED_EMBEDDING_MODELS,
                        LOADED_RERANKING_MODELS,
                        DOWNLOADED_RERANKING_MODELS, 
                        ...filteredRAGConfig 
                    } = RAGConfig;

                    // update ragconfig to load reranker
                    const backendRAGConfig = { ...filteredRAGConfig, knowledge_id: res.id };

                    await updateRAGConfig(localStorage.token, backendRAGConfig);
				}
			}
        }
        loading = false;
    };

    onMount(async () => {
		await setEmbeddingConfig();

		RAGConfig = await getRAGConfig(localStorage.token);

	});
</script>

<div class="w-full max-h-full">
    <button
        class="flex space-x-1"
        on:click={() => {
            goto('/workspace/knowledge');
        }}
    >
        <div class="self-center">
            <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                class="w-4 h-4"
            >
                <path
                    fill-rule="evenodd"
                    d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
                    clip-rule="evenodd"
                />
            </svg>
        </div>
        <div class="self-center font-medium text-sm">{$i18n.t('Back')}</div>
    </button>

    <form
        class="flex flex-col max-w-lg mx-auto mt-10 mb-10"
        on:submit|preventDefault={() => {
			submitHandler();
		}}
    >
        <div class="w-full flex flex-col justify-center">
            <div class="text-2xl font-medium font-primary mb-2.5">
                {$i18n.t('Create a knowledge base')}
            </div>

            <div class="w-full flex flex-col gap-2.5">
                <div class="w-full">
                    <div class="text-sm mb-2">{$i18n.t('What are you working on?')}</div>

                    <div class="w-full mt-1">
                        <input
                            class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
                            type="text"
                            bind:value={name}
                            placeholder={$i18n.t('Name your knowledge base')}
                            required
                        />
                    </div>
                </div>

                <div>
                    <div class="text-sm mb-2">{$i18n.t('What are you trying to achieve?')}</div>

                    <div class="w-full mt-1">
                        <textarea
                            class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
                            rows="4"
                            bind:value={description}
                            placeholder={$i18n.t('Describe your knowledge base and objectives')}
                            required
                        ></textarea>
                    </div>
                </div>
            </div>
        </div>

		<div class="mt-2">
			<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
				<AccessControl
					bind:accessControl
					accessRoles={['read', 'write']}
					allowPublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
				/>
			</div>
		</div>

        <div class="mt-4">
            <div class="block text-sm font-medium mb-1">
				{$i18n.t('Enable Individual RAG Configuration')}
			<Switch 
				bind:state={enableIndividualRagConfig} 
				on:change={() => {
					RAGConfig.DEFAULT_RAG_SETTINGS = !enableIndividualRagConfig;
				}} 
			/>
			</div>
        </div>

        {#if enableIndividualRagConfig}
            <div class="flex w-full justify-between">
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
                        <option value="document_intelligence">{$i18n.t('Document Intelligence')}</option>
                        <option value="mistral_ocr">{$i18n.t('Mistral OCR')}</option>
                    </select>
                </div>
            </div>
            <div class="space-y-4 mt-4">
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
                                class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
                                placeholder={$i18n.t('Enter Tika Server URL')}
                                bind:value={RAGConfig.TIKA_SERVER_URL}
                            />
                        </div>
                    </div>
                {:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'docling'}
                    <div class="flex w-full mt-1">
                        <input
                            class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
                            placeholder={$i18n.t('Enter Docling Server URL')}
                            bind:value={RAGConfig.DOCLING_SERVER_URL}
                        />
                    </div>
                {:else if RAGConfig.CONTENT_EXTRACTION_ENGINE === 'document_intelligence'}
                    <div class="my-0.5 flex gap-2 pr-2">
                        <input
                            class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
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
                                class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
                                placeholder={$i18n.t('API Base URL')}
                                bind:value={OpenAIUrl}
                                required
                            />

                            <SensitiveInput placeholder={$i18n.t('API Key')} bind:value={OpenAIKey} />
                        </div>
                    {:else if embeddingEngine === 'ollama'}
                        <div class="my-0.5 flex gap-2 pr-2">
                            <input
                                class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
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
                </div>

                <div class="  mb-2.5 flex flex-col w-full">
                    <div class=" mb-1 text-xs font-medium">{$i18n.t('Embedding Model')}</div>
                    {#if $user?.role === 'admin'}
                        <div class="">
                            {#if embeddingEngine === 'ollama'}
                                <div class="flex w-full">
                                    <div class="flex-1 mr-2">
                                        <input
                                            class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
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
                                            class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
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
                        </div>
                    {/if}
                    <div class="flex w-full">
                            <div class="flex-1 mr-2">
                                <select
                                    class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden p-2 border border-gray-300"
                                    bind:value={embeddingModel}
                                    required
                                >
                                    <option value="" disabled selected>{$i18n.t('Select embedding model')}</option>
                                    <!-- Always show the current value first if it's not empty -->
                                    {#if embeddingModel && embeddingModel.trim() !== ''}
                                        <option value={embeddingModel} class="py-1 font-semibold">
                                            {embeddingModel} 
                                            {#if embeddingEngine && 
                                                RAGConfig.DOWNLOADED_EMBEDDING_MODELS[embeddingEngine] && 
                                                !RAGConfig.DOWNLOADED_EMBEDDING_MODELS[embeddingEngine]?.includes(embeddingModel)}
                                                (custom)
                                            {/if}
                                        </option>
                                    {/if}
                                    
                                    <!-- Then show all downloaded models from the selected engine -->
                                    {#if embeddingEngine && RAGConfig.DOWNLOADED_EMBEDDING_MODELS[embeddingEngine]}
                                        {#each RAGConfig.DOWNLOADED_EMBEDDING_MODELS[embeddingEngine] as model}
                                            {#if model !== embeddingModel} <!-- Skip the current model as it's already shown -->
                                                <option value={model} class="py-1">{model}</option>
                                            {/if}
                                        {/each}
                                    {/if}
                                </select>
                            </div>
                        </div>
                    <div class="mt-1 mb-1 text-xs text-gray-400 dark:text-gray-500">
                        {$i18n.t(
                            'Warning: If you update or change your embedding model, you will need to re-import all documents.'
                        )}
                    </div>
                </div>

                {#if embeddingEngine === 'ollama' || embeddingEngine === 'openai'}
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
                            <Switch
                                bind:state={RAGConfig.ENABLE_RAG_HYBRID_SEARCH}
                                on:change={() => {
                                    if (!RAGConfig.ENABLE_RAG_HYBRID_SEARCH) {
                                        RAGConfig.RAG_RERANKING_MODEL = "";
                                    }
                                }}
                            />
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
                            {#if $user?.role === 'admin'}
                                <div class="">
                                    <div class="flex w-full">
                                        <div class="flex-1 mr-2">
                                            <input
                                                class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
                                                placeholder={$i18n.t('Set reranking model (e.g. {{model}})', {
                                                    model: 'BAAI/bge-reranker-v2-m3'
                                                })}
                                                bind:value={RAGConfig.RAG_RERANKING_MODEL}
                                                on:input={() => {
                                                }}
                                            />
                                        </div>  
                                    </div>
                                </div>
                            {/if}
                            <div class="flex w-full">
                                <div class="flex-1 mr-2">
                                    <select
                                        class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden p-2 border border-gray-300"
                                        bind:value={RAGConfig.RAG_RERANKING_MODEL}
                                        required
                                    >
                                        <option value="" disabled selected>{$i18n.t('Select reranking model')}</option>
                                        <!-- Always show the current value first if it's not empty -->
                                        {#if RAGConfig.RAG_RERANKING_MODEL && RAGConfig.RAG_RERANKING_MODEL.trim() !== ''}
                                            <option value={RAGConfig.RAG_RERANKING_MODEL} class="py-1 font-semibold">
                                                {RAGConfig.RAG_RERANKING_MODEL} 
                                                {#if RAGConfig.RAG_RERANKING_ENGINE !== undefined &&
                                                    RAGConfig.DOWNLOADED_RERANKING_MODELS[RAGConfig.RAG_RERANKING_ENGINE] &&
                                                    !RAGConfig.DOWNLOADED_RERANKING_MODELS[RAGConfig.RAG_RERANKING_ENGINE]?.some(model => model.RAG_RERANKING_MODEL === RAGConfig.RAG_RERANKING_MODEL)}
                                                    (custom)
                                                {/if}
                                            </option>
                                        {/if}
                                        
                                        <!-- Then show all downloaded models from the selected engine -->
                                        {#if RAGConfig.RAG_RERANKING_ENGINE !== undefined && RAGConfig.DOWNLOADED_RERANKING_MODELS[RAGConfig.RAG_RERANKING_ENGINE]}
                                            {#each RAGConfig.DOWNLOADED_RERANKING_MODELS[RAGConfig.RAG_RERANKING_ENGINE] as model}
                                                {#if model !== RAGConfig.RAG_RERANKING_MODEL} <!-- Skip the current model as it's already shown -->
                                                    <option value={model} class="py-1">{model}</option>
                                                {/if}
                                            {/each}
                                        {/if}
                                    </select>
                                </div>
                            </div>
                        </div>
                    {/if}

                    <div class="  mb-2.5 flex w-full justify-between">
                        <div class=" self-center text-xs font-medium">{$i18n.t('Top K')}</div>
                        <div class="flex items-center relative">
                            <input
                                class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
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
                                    class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
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
                                        class="flex-1 w-full rounded-lg text-sm bg-transparent outline-hidden"
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
    {/if}

        <div class="flex justify-end mt-6">
            <button
                class="text-sm px-4 py-2 transition rounded-lg {loading
                    ? 'cursor-not-allowed bg-gray-100 dark:bg-gray-800'
                    : 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800'} flex"
                type="submit"
                disabled={loading}
            >
                <div class="self-center font-medium">{$i18n.t('Create Knowledge')}</div>

                {#if loading}
                    <div class="ml-1.5 self-center">
                        <svg
                            class="w-4 h-4"
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
    </form>
</div>
    