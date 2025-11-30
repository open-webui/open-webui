<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { config as backendConfig, user } from '$lib/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		getImageGenerationModels,
		getImageGenerationConfig,
		updateImageGenerationConfig,
		getConfig,
		updateConfig,
		verifyConfigUrl
	} from '$lib/apis/images';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import CodeEditorModal from '$lib/components/common/CodeEditorModal.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let loading = false;

	let models = null;
	let config = null;

	let showComfyUIWorkflowEditor = false;
	let REQUIRED_WORKFLOW_NODES = [
		{
			type: 'prompt',
			key: 'text',
			node_ids: ''
		},
		{
			type: 'model',
			key: 'ckpt_name',
			node_ids: ''
		},
		{
			type: 'width',
			key: 'width',
			node_ids: ''
		},
		{
			type: 'height',
			key: 'height',
			node_ids: ''
		},
		{
			type: 'steps',
			key: 'steps',
			node_ids: ''
		},
		{
			type: 'seed',
			key: 'seed',
			node_ids: ''
		}
	];

	let showComfyUIEditWorkflowEditor = false;
	let REQUIRED_EDIT_WORKFLOW_NODES = [
		{
			type: 'image',
			key: 'image',
			node_ids: ''
		},
		{
			type: 'prompt',
			key: 'prompt',
			node_ids: ''
		},
		{
			type: 'model',
			key: 'unet_name',
			node_ids: ''
		},
		{
			type: 'width',
			key: 'width',
			node_ids: ''
		},
		{
			type: 'height',
			key: 'height',
			node_ids: ''
		}
	];

	const getModels = async () => {
		models = await getImageGenerationModels(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const updateConfigHandler = async () => {
		if (
			config.IMAGE_GENERATION_ENGINE === 'automatic1111' &&
			config.AUTOMATIC1111_BASE_URL === ''
		) {
			toast.error($i18n.t('AUTOMATIC1111 Base URL is required.'));
			config.ENABLE_IMAGE_GENERATION = false;

			return null;
		} else if (config.IMAGE_GENERATION_ENGINE === 'comfyui' && config.COMFYUI_BASE_URL === '') {
			toast.error($i18n.t('ComfyUI Base URL is required.'));
			config.ENABLE_IMAGE_GENERATION = false;

			return null;
		} else if (config.IMAGE_GENERATION_ENGINE === 'openai' && config.IMAGES_OPENAI_API_KEY === '') {
			toast.error($i18n.t('OpenAI API Key is required.'));
			config.ENABLE_IMAGE_GENERATION = false;

			return null;
		} else if (config.IMAGE_GENERATION_ENGINE === 'gemini' && config.IMAGES_GEMINI_API_KEY === '') {
			toast.error($i18n.t('Gemini API Key is required.'));
			config.ENABLE_IMAGE_GENERATION = false;

			return null;
		}

		const res = await updateConfig(localStorage.token, {
			...config,
			AUTOMATIC1111_PARAMS:
				typeof config.AUTOMATIC1111_PARAMS === 'string' && config.AUTOMATIC1111_PARAMS.trim() !== ''
					? JSON.parse(config.AUTOMATIC1111_PARAMS)
					: {},
			IMAGES_OPENAI_API_PARAMS:
				typeof config.IMAGES_OPENAI_API_PARAMS === 'string' &&
				config.IMAGES_OPENAI_API_PARAMS.trim() !== ''
					? JSON.parse(config.IMAGES_OPENAI_API_PARAMS)
					: {}
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			if (res.ENABLE_IMAGE_GENERATION) {
				backendConfig.set(await getBackendConfig());
				getModels();
			}

			return res;
		}

		return null;
	};

	const validateJSON = (json) => {
		try {
			const obj = JSON.parse(json);

			if (obj && typeof obj === 'object') {
				return true;
			}
		} catch (e) {}
		return false;
	};

	const saveHandler = async () => {
		loading = true;

		if (config?.COMFYUI_WORKFLOW) {
			if (!validateJSON(config?.COMFYUI_WORKFLOW)) {
				toast.error($i18n.t('Invalid JSON format for ComfyUI Workflow.'));
				loading = false;
				return;
			}

			config.COMFYUI_WORKFLOW_NODES = REQUIRED_WORKFLOW_NODES.map((node) => {
				return {
					type: node.type,
					key: node.key,
					node_ids:
						node.node_ids.trim() === '' ? [] : node.node_ids.split(',').map((id) => id.trim())
				};
			});
		}

		if (config?.IMAGES_EDIT_COMFYUI_WORKFLOW) {
			if (!validateJSON(config?.IMAGES_EDIT_COMFYUI_WORKFLOW)) {
				toast.error($i18n.t('Invalid JSON format for ComfyUI Edit Workflow.'));
				loading = false;
				return;
			}

			config.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES = REQUIRED_EDIT_WORKFLOW_NODES.map((node) => {
				return {
					type: node.type,
					key: node.key,
					node_ids:
						node.node_ids.trim() === '' ? [] : node.node_ids.split(',').map((id) => id.trim())
				};
			});
		}

		const res = await updateConfigHandler();
		if (res) {
			dispatch('save');
		}

		loading = false;
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			const res = await getConfig(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				config = res;
			}

			if (config.ENABLE_IMAGE_GENERATION) {
				getModels();
			}

			if (config.COMFYUI_WORKFLOW) {
				try {
					config.COMFYUI_WORKFLOW = JSON.stringify(JSON.parse(config.COMFYUI_WORKFLOW), null, 2);
				} catch (e) {
					console.error(e);
				}
			}

			REQUIRED_WORKFLOW_NODES = REQUIRED_WORKFLOW_NODES.map((node) => {
				const n = config.COMFYUI_WORKFLOW_NODES.find((n) => n.type === node.type) ?? node;
				console.debug(n);

				return {
					type: n.type,
					key: n.key,
					node_ids: typeof n.node_ids === 'string' ? n.node_ids : n.node_ids.join(',')
				};
			});

			if (config.IMAGES_EDIT_COMFYUI_WORKFLOW) {
				try {
					config.IMAGES_EDIT_COMFYUI_WORKFLOW = JSON.stringify(
						JSON.parse(config.IMAGES_EDIT_COMFYUI_WORKFLOW),
						null,
						2
					);
				} catch (e) {
					console.error(e);
				}
			}

			config.IMAGES_OPENAI_API_PARAMS =
				typeof config.IMAGES_OPENAI_API_PARAMS === 'object'
					? JSON.stringify(config.IMAGES_OPENAI_API_PARAMS ?? {}, null, 2)
					: config.IMAGES_OPENAI_API_PARAMS;

			config.AUTOMATIC1111_PARAMS =
				typeof config.AUTOMATIC1111_PARAMS === 'object'
					? JSON.stringify(config.AUTOMATIC1111_PARAMS ?? {}, null, 2)
					: config.AUTOMATIC1111_PARAMS;

			REQUIRED_EDIT_WORKFLOW_NODES = REQUIRED_EDIT_WORKFLOW_NODES.map((node) => {
				const n =
					config.IMAGES_EDIT_COMFYUI_WORKFLOW_NODES.find((n) => n.type === node.type) ?? node;
				console.debug(n);

				return {
					type: n.type,
					key: n.key,
					node_ids: typeof n.node_ids === 'string' ? n.node_ids : n.node_ids.join(',')
				};
			});
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden pr-2">
		{#if config}
			<div>
				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="">
									{$i18n.t('Image Generation')}
								</div>
							</div>

							<Switch bind:state={config.ENABLE_IMAGE_GENERATION} />
						</div>
					</div>
				</div>

				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Create Image')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					{#if config.ENABLE_IMAGE_GENERATION}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2">
									<div class="shrink-0">
										{$i18n.t('Model')}
									</div>
								</div>

								<Tooltip content={$i18n.t('Enter Model ID')} placement="top-start">
									<input
										list="model-list"
										class=" text-right text-sm bg-transparent outline-hidden max-w-full w-52"
										bind:value={config.IMAGE_GENERATION_MODEL}
										placeholder={$i18n.t('Select a model')}
										required
									/>

									<datalist id="model-list">
										{#each models ?? [] as model}
											<option value={model.id}>{model.name}</option>
										{/each}
									</datalist>
								</Tooltip>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2">
									<div class="shrink-0">
										{$i18n.t('Image Size')}
									</div>
								</div>

								<Tooltip content={$i18n.t('Enter Image Size (e.g. 512x512)')} placement="top-start">
									<input
										class="  text-right text-sm bg-transparent outline-hidden max-w-full w-52"
										placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
										bind:value={config.IMAGE_SIZE}
									/>
								</Tooltip>
							</div>
						</div>

						{#if ['comfyui', 'automatic1111', ''].includes(config?.IMAGE_GENERATION_ENGINE)}
							<div class="mb-2.5">
								<div class="flex w-full justify-between items-center">
									<div class="text-xs pr-2">
										<div class="">
											{$i18n.t('Steps')}
										</div>
									</div>

									<Tooltip
										content={$i18n.t('Enter Number of Steps (e.g. 50)')}
										placement="top-start"
									>
										<input
											class=" text-right text-sm bg-transparent outline-hidden"
											placeholder={$i18n.t('Enter Number of Steps (e.g. 50)')}
											bind:value={config.IMAGE_STEPS}
											required
										/>
									</Tooltip>
								</div>
							</div>
						{/if}

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2">
									<div class="">
										{$i18n.t('Image Prompt Generation')}
									</div>
								</div>

								<Switch bind:state={config.ENABLE_IMAGE_PROMPT_GENERATION} />
							</div>
						</div>
					{/if}

					<div class="mb-2.5">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="">
									{$i18n.t('Image Generation Engine')}
								</div>
							</div>

							<select
								class=" dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
								bind:value={config.IMAGE_GENERATION_ENGINE}
								placeholder={$i18n.t('Select Engine')}
							>
								<option value="openai">{$i18n.t('Default (Open AI)')}</option>
								<option value="comfyui">{$i18n.t('ComfyUI')}</option>
								<option value="automatic1111">{$i18n.t('Automatic1111')}</option>
								<option value="gemini">{$i18n.t('Gemini')}</option>
							</select>
						</div>
					</div>

					{#if config?.IMAGE_GENERATION_ENGINE === 'openai'}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('OpenAI API Base URL')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('API Base URL')}
											bind:value={config.IMAGES_OPENAI_API_BASE_URL}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('OpenAI API Key')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											inputClassName="text-right w-full"
											placeholder={$i18n.t('API Key')}
											bind:value={config.IMAGES_OPENAI_API_KEY}
											required={false}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('OpenAI API Version')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('API Version')}
											bind:value={config.IMAGES_OPENAI_API_VERSION}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('Additional Parameters')}
									</div>
								</div>
							</div>
							<div class="mt-1.5 flex w-full">
								<div class="flex-1 mr-2">
									<Textarea
										className="rounded-lg w-full py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={config.IMAGES_OPENAI_API_PARAMS}
										placeholder={$i18n.t('Enter additional parameters in JSON format')}
										minSize={100}
									/>
								</div>
							</div>
						</div>
					{:else if (config?.IMAGE_GENERATION_ENGINE ?? 'automatic1111') === 'automatic1111'}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('AUTOMATIC1111 Base URL')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1 mr-2">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
											bind:value={config.AUTOMATIC1111_BASE_URL}
										/>
									</div>
									<button
										class="  transition"
										type="button"
										aria-label="verify connection"
										on:click={async () => {
											await updateConfigHandler();
											const res = await verifyConfigUrl(localStorage.token).catch((error) => {
												toast.error(`${error}`);
												return null;
											});

											if (res) {
												toast.success($i18n.t('Server connection verified'));
											}
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							</div>

							<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('Include `--api` flag when running stable-diffusion-webui')}
								<a
									class=" text-gray-300 font-medium"
									href="https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/3734"
									target="_blank"
								>
									{$i18n.t('(e.g. `sh webui.sh --api`)')}
								</a>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('AUTOMATIC1111 Api Auth String')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											inputClassName="text-right w-full"
											placeholder={$i18n.t('Enter api auth string (e.g. username:password)')}
											bind:value={config.AUTOMATIC1111_API_AUTH}
											required={false}
										/>
									</div>
								</div>
							</div>

							<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('Include `--api-auth` flag when running stable-diffusion-webui')}
								<a
									class=" text-gray-300 font-medium"
									href="https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/13993"
									target="_blank"
								>
									{$i18n
										.t('(e.g. `sh webui.sh --api --api-auth username_password`)')
										.replace('_', ':')}
								</a>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('Additional Parameters')}
									</div>
								</div>
							</div>
							<div class="mt-1.5 flex w-full">
								<div class="flex-1 mr-2">
									<Textarea
										className="rounded-lg w-full py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={config.AUTOMATIC1111_PARAMS}
										placeholder={$i18n.t('Enter additional parameters in JSON format')}
										minSize={100}
									/>
								</div>
							</div>
						</div>
					{:else if config?.IMAGE_GENERATION_ENGINE === 'comfyui'}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('ComfyUI Base URL')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1 mr-2">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
											bind:value={config.COMFYUI_BASE_URL}
										/>
									</div>
									<button
										class="  rounded-lg transition"
										type="button"
										aria-label="verify connection"
										on:click={async () => {
											await updateConfigHandler();
											const res = await verifyConfigUrl(localStorage.token).catch((error) => {
												toast.error(`${error}`);
												return null;
											});

											if (res) {
												toast.success($i18n.t('Server connection verified'));
											}
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('ComfyUI API Key')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											inputClassName="text-right w-full"
											placeholder={$i18n.t('sk-1234')}
											bind:value={config.COMFYUI_API_KEY}
											required={false}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<input
								id="upload-comfyui-workflow-input"
								hidden
								type="file"
								accept=".json"
								on:change={(e) => {
									const file = e.target.files[0];
									const reader = new FileReader();

									reader.onload = (e) => {
										config.COMFYUI_WORKFLOW = e.target.result;
										e.target.value = null;
									};

									reader.readAsText(file);
								}}
							/>
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('ComfyUI Workflow')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1 mr-2 justify-end flex gap-1">
										{#if config.COMFYUI_WORKFLOW}
											<button
												class="text-xs text-gray-700 dark:text-gray-400 underline"
												type="button"
												aria-label={$i18n.t('Edit workflow.json content')}
												on:click={() => {
													// open code editor modal
													showComfyUIWorkflowEditor = true;
												}}
											>
												{$i18n.t('Edit')}
											</button>
										{/if}

										<Tooltip content={$i18n.t('Click here to upload a workflow.json file.')}>
											<button
												class="text-xs text-gray-700 dark:text-gray-400 underline"
												type="button"
												aria-label={$i18n.t('Click here to upload a workflow.json file.')}
												on:click={() => {
													document.getElementById('upload-comfyui-workflow-input')?.click();
												}}
											>
												{$i18n.t('Upload')}
											</button>
										</Tooltip>
									</div>
								</div>
							</div>

							<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
								<CodeEditorModal
									bind:show={showComfyUIWorkflowEditor}
									value={config.COMFYUI_WORKFLOW}
									lang="json"
									onChange={(e) => {
										config.COMFYUI_WORKFLOW = e;
									}}
									onSave={() => {
										console.log('Saved');
									}}
								/>
								<!-- {#if config.COMFYUI_WORKFLOW}
									<Textarea
										class="w-full rounded-lg my-1 py-2 px-3 text-xs bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden disabled:text-gray-600 resize-none"
										rows="10"
										bind:value={config.COMFYUI_WORKFLOW}
										required
									/>
								{/if} -->
								{$i18n.t('Make sure to export a workflow.json file as API format from ComfyUI.')}
							</div>
						</div>

						{#if config.COMFYUI_WORKFLOW}
							<div class="mb-2.5">
								<div class="flex w-full justify-between items-center">
									<div class="text-xs pr-2 shrink-0">
										<div class="">
											{$i18n.t('ComfyUI Workflow Nodes')}
										</div>
									</div>
								</div>

								<div class="mt-1 text-xs flex flex-col gap-1.5">
									{#each REQUIRED_WORKFLOW_NODES as node}
										<div class="flex w-full flex-col">
											<div class="shrink-0">
												<div class=" capitalize line-clamp-1 w-20 text-gray-400 dark:text-gray-500">
													{node.type}{node.type === 'prompt' ? '*' : ''}
												</div>
											</div>

											<div class="flex mt-0.5 items-center">
												<div class="">
													<Tooltip content={$i18n.t('Input Key (e.g. text, unet_name, steps)')}>
														<input
															class="py-1 w-24 text-xs bg-transparent outline-hidden"
															placeholder={$i18n.t('Key')}
															bind:value={node.key}
															required
														/>
													</Tooltip>
												</div>

												<div class="px-2 text-gray-400 dark:text-gray-500">:</div>

												<div class="w-full">
													<Tooltip
														content={$i18n.t('Comma separated Node Ids (e.g. 1 or 1,2)')}
														placement="top-start"
													>
														<input
															class="w-full py-1 text-xs bg-transparent outline-hidden"
															placeholder={$i18n.t('Node Ids')}
															bind:value={node.node_ids}
														/>
													</Tooltip>
												</div>
											</div>
										</div>
									{/each}
								</div>

								<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t('*Prompt node ID(s) are required for image generation')}
								</div>
							</div>
						{/if}
					{:else if config?.IMAGE_GENERATION_ENGINE === 'gemini'}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('Gemini Base URL')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('API Base URL')}
											bind:value={config.IMAGES_GEMINI_API_BASE_URL}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('Gemini API Key')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											inputClassName="text-right w-full"
											placeholder={$i18n.t('API Key')}
											bind:value={config.IMAGES_GEMINI_API_KEY}
											required={true}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2">
									<div class="">
										{$i18n.t('Gemini Endpoint Method')}
									</div>
								</div>

								<select
									class=" dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
									bind:value={config.IMAGES_GEMINI_ENDPOINT_METHOD}
									placeholder={$i18n.t('Select Method')}
								>
									<option value="predict">predict</option>
									<option value="generateContent">generateContent</option>
								</select>
							</div>
						</div>
					{/if}
				</div>

				<div class="mb-3">
					<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Edit Image')}</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

					<div class="mb-2.5">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="">
									{$i18n.t('Image Edit')}
								</div>
							</div>

							<Switch bind:state={config.ENABLE_IMAGE_EDIT} />
						</div>
					</div>

					{#if config?.ENABLE_IMAGE_GENERATION && config?.ENABLE_IMAGE_EDIT}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2">
									<div class="shrink-0">
										{$i18n.t('Model')}
									</div>
								</div>

								<Tooltip content={$i18n.t('Enter Model ID')} placement="top-start">
									<input
										list="model-list"
										class="text-right text-sm bg-transparent outline-hidden max-w-full w-52"
										bind:value={config.IMAGE_EDIT_MODEL}
										placeholder={$i18n.t('Select a model')}
									/>

									<datalist id="model-list">
										{#each models ?? [] as model}
											<option value={model.id}>{model.name}</option>
										{/each}
									</datalist>
								</Tooltip>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2">
									<div class="shrink-0">
										{$i18n.t('Image Size')}
									</div>
								</div>

								<Tooltip content={$i18n.t('Enter Image Size (e.g. 512x512)')} placement="top-start">
									<input
										class="text-right text-sm bg-transparent outline-hidden max-w-full w-52"
										placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
										bind:value={config.IMAGE_EDIT_SIZE}
									/>
								</Tooltip>
							</div>
						</div>
					{/if}

					<div class="mb-2.5">
						<div class="flex w-full justify-between items-center">
							<div class="text-xs pr-2">
								<div class="">
									{$i18n.t('Image Edit Engine')}
								</div>
							</div>

							<select
								class=" dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded-sm px-2 text-xs bg-transparent outline-hidden text-right"
								bind:value={config.IMAGE_EDIT_ENGINE}
								placeholder={$i18n.t('Select Engine')}
							>
								<option value="openai">{$i18n.t('Default (Open AI)')}</option>
								<option value="comfyui">{$i18n.t('ComfyUI')}</option>
								<option value="gemini">{$i18n.t('Gemini')}</option>
							</select>
						</div>
					</div>

					{#if config?.IMAGE_EDIT_ENGINE === 'openai'}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('OpenAI API Base URL')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('API Base URL')}
											bind:value={config.IMAGES_EDIT_OPENAI_API_BASE_URL}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('OpenAI API Key')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											inputClassName="text-right w-full"
											placeholder={$i18n.t('API Key')}
											bind:value={config.IMAGES_EDIT_OPENAI_API_KEY}
											required={false}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('OpenAI API Version')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('API Version')}
											bind:value={config.IMAGES_EDIT_OPENAI_API_VERSION}
										/>
									</div>
								</div>
							</div>
						</div>
					{:else if config?.IMAGE_EDIT_ENGINE === 'comfyui'}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('ComfyUI Base URL')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1 mr-2">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
											bind:value={config.IMAGES_EDIT_COMFYUI_BASE_URL}
										/>
									</div>
									<button
										class="  transition"
										type="button"
										aria-label="verify connection"
										on:click={async () => {
											await updateConfigHandler();
											const res = await verifyConfigUrl(localStorage.token).catch((error) => {
												toast.error(`${error}`);
												return null;
											});

											if (res) {
												toast.success($i18n.t('Server connection verified'));
											}
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('ComfyUI API Key')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											inputClassName="text-right w-full"
											placeholder={$i18n.t('sk-1234')}
											bind:value={config.IMAGES_EDIT_COMFYUI_API_KEY}
											required={false}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<input
								id="upload-comfyui-edit-workflow-input"
								hidden
								type="file"
								accept=".json"
								on:change={(e) => {
									const file = e.target.files[0];
									const reader = new FileReader();

									reader.onload = (e) => {
										config.IMAGES_EDIT_COMFYUI_WORKFLOW = e.target.result;
										e.target.value = null;
									};

									reader.readAsText(file);
								}}
							/>
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('ComfyUI Workflow')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1 mr-2 justify-end flex gap-1">
										{#if config.IMAGES_EDIT_COMFYUI_WORKFLOW}
											<button
												class="text-xs text-gray-700 dark:text-gray-400 underline"
												type="button"
												aria-label={$i18n.t('Edit workflow.json content')}
												on:click={() => {
													// open code editor modal
													showComfyUIEditWorkflowEditor = true;
												}}
											>
												{$i18n.t('Edit')}
											</button>
										{/if}

										<Tooltip content={$i18n.t('Click here to upload a workflow.json file.')}>
											<button
												class="text-xs text-gray-700 dark:text-gray-400 underline"
												type="button"
												aria-label={$i18n.t('Click here to upload a workflow.json file.')}
												on:click={() => {
													document.getElementById('upload-comfyui-edit-workflow-input')?.click();
												}}
											>
												{$i18n.t('Upload')}
											</button>
										</Tooltip>
									</div>
								</div>
							</div>

							<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
								<CodeEditorModal
									bind:show={showComfyUIEditWorkflowEditor}
									value={config.IMAGES_EDIT_COMFYUI_WORKFLOW}
									lang="json"
									onChange={(e) => {
										config.IMAGES_EDIT_COMFYUI_WORKFLOW = e;
									}}
									onSave={() => {
										console.log('Saved');
									}}
								/>
								{$i18n.t('Make sure to export a workflow.json file as API format from ComfyUI.')}
							</div>
						</div>

						{#if config.IMAGES_EDIT_COMFYUI_WORKFLOW}
							<div class="mb-2.5">
								<div class="flex w-full justify-between items-center">
									<div class="text-xs pr-2 shrink-0">
										<div class="">
											{$i18n.t('ComfyUI Workflow Nodes')}
										</div>
									</div>
								</div>

								<div class="mt-1 text-xs flex flex-col gap-1.5">
									{#each REQUIRED_EDIT_WORKFLOW_NODES as node}
										<div class="flex w-full flex-col">
											<div class="shrink-0">
												<div class=" capitalize line-clamp-1 w-20 text-gray-400 dark:text-gray-500">
													{node.type}{['prompt', 'image'].includes(node.type) ? '*' : ''}
												</div>
											</div>

											<div class="flex mt-0.5 items-center">
												<div class="">
													<Tooltip content={$i18n.t('Input Key (e.g. text, unet_name, steps)')}>
														<input
															class="py-1 w-24 text-xs bg-transparent outline-hidden"
															placeholder={$i18n.t('Key')}
															bind:value={node.key}
															required
														/>
													</Tooltip>
												</div>

												<div class="px-2 text-gray-400 dark:text-gray-500">:</div>

												<div class="w-full">
													<Tooltip
														content={$i18n.t('Comma separated Node Ids (e.g. 1 or 1,2)')}
														placement="top-start"
													>
														<input
															class="w-full py-1 text-xs bg-transparent outline-hidden"
															placeholder={$i18n.t('Node Ids')}
															bind:value={node.node_ids}
														/>
													</Tooltip>
												</div>
											</div>
										</div>
									{/each}
								</div>

								<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t('*Prompt node ID(s) are required for image generation')}
								</div>
							</div>
						{/if}
					{:else if config?.IMAGE_EDIT_ENGINE === 'gemini'}
						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('Gemini Base URL')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full text-sm bg-transparent outline-hidden text-right"
											placeholder={$i18n.t('API Base URL')}
											bind:value={config.IMAGES_EDIT_GEMINI_API_BASE_URL}
										/>
									</div>
								</div>
							</div>
						</div>

						<div class="mb-2.5">
							<div class="flex w-full justify-between items-center">
								<div class="text-xs pr-2 shrink-0">
									<div class="">
										{$i18n.t('Gemini API Key')}
									</div>
								</div>

								<div class="flex w-full">
									<div class="flex-1">
										<SensitiveInput
											inputClassName="text-right w-full"
											placeholder={$i18n.t('API Key')}
											bind:value={config.IMAGES_EDIT_GEMINI_API_KEY}
											required={true}
										/>
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
				? ' cursor-not-allowed'
				: ''}"
			type="submit"
			disabled={loading}
		>
			{$i18n.t('Save')}

			{#if loading}
				<div class="ml-2 self-center">
					<Spinner />
				</div>
			{/if}
		</button>
	</div>
</form>
