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
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let loading = false;

	let config = null;
	let imageGenerationConfig = null;

	let models = null;

	let samplers = [
		'DPM++ 2M',
		'DPM++ SDE',
		'DPM++ 2M SDE',
		'DPM++ 2M SDE Heun',
		'DPM++ 2S a',
		'DPM++ 3M SDE',
		'Euler a',
		'Euler',
		'LMS',
		'Heun',
		'DPM2',
		'DPM2 a',
		'DPM fast',
		'DPM adaptive',
		'Restart',
		'DDIM',
		'DDIM CFG++',
		'PLMS',
		'UniPC'
	];

	let schedulers = [
		'Automatic',
		'Uniform',
		'Karras',
		'Exponential',
		'Polyexponential',
		'SGM Uniform',
		'KL Optimal',
		'Align Your Steps',
		'Simple',
		'Normal',
		'DDIM',
		'Beta'
	];

	let requiredWorkflowNodes = [
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

	const getModels = async () => {
		models = await getImageGenerationModels(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const updateConfigHandler = async () => {
		const res = await updateConfig(localStorage.token, config)
			.catch((error) => {
				toast.error(`${error}`);
				return null;
			})
			.catch((error) => {
				toast.error(`${error}`);
				return null;
			});

		if (res) {
			config = res;
		}

		if (config.enabled) {
			backendConfig.set(await getBackendConfig());
			getModels();
		}
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

		if (config?.comfyui?.COMFYUI_WORKFLOW) {
			if (!validateJSON(config.comfyui.COMFYUI_WORKFLOW)) {
				toast.error($i18n.t('Invalid JSON format for ComfyUI Workflow.'));
				loading = false;
				return;
			}
		}

		if (config?.comfyui?.COMFYUI_WORKFLOW) {
			config.comfyui.COMFYUI_WORKFLOW_NODES = requiredWorkflowNodes.map((node) => {
				return {
					type: node.type,
					key: node.key,
					node_ids:
						node.node_ids.trim() === '' ? [] : node.node_ids.split(',').map((id) => id.trim())
				};
			});
		}

		await updateConfig(localStorage.token, config).catch((error) => {
			toast.error(`${error}`);
			loading = false;
			return null;
		});

		await updateImageGenerationConfig(localStorage.token, imageGenerationConfig).catch((error) => {
			toast.error(`${error}`);
			loading = false;
			return null;
		});

		getModels();
		dispatch('save');
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

			if (config.enabled) {
				getModels();
			}

			if (config.comfyui.COMFYUI_WORKFLOW) {
				try {
					config.comfyui.COMFYUI_WORKFLOW = JSON.stringify(
						JSON.parse(config.comfyui.COMFYUI_WORKFLOW),
						null,
						2
					);
				} catch (e) {
					console.error(e);
				}
			}

			requiredWorkflowNodes = requiredWorkflowNodes.map((node) => {
				const n = config.comfyui.COMFYUI_WORKFLOW_NODES.find((n) => n.type === node.type) ?? node;

				console.debug(n);

				return {
					type: n.type,
					key: n.key,
					node_ids: typeof n.node_ids === 'string' ? n.node_ids : n.node_ids.join(',')
				};
			});

			const imageConfigRes = await getImageGenerationConfig(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (imageConfigRes) {
				imageGenerationConfig = imageConfigRes;
			}
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
		{#if config && imageGenerationConfig}
			<div>
				<div class=" mb-1 text-sm font-medium">{$i18n.t('Image Settings')}</div>

				<div>
					<div class=" py-1 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Image Generation (Experimental)')}
						</div>

						<div class="px-1">
							<Switch
								bind:state={config.enabled}
								on:change={(e) => {
									const enabled = e.detail;

									if (enabled) {
										if (
											config.engine === 'automatic1111' &&
											config.automatic1111.AUTOMATIC1111_BASE_URL === ''
										) {
											toast.error($i18n.t('AUTOMATIC1111 Base URL is required.'));
											config.enabled = false;
										} else if (
											config.engine === 'comfyui' &&
											config.comfyui.COMFYUI_BASE_URL === ''
										) {
											toast.error($i18n.t('ComfyUI Base URL is required.'));
											config.enabled = false;
										} else if (config.engine === 'openai' && config.openai.OPENAI_API_KEY === '') {
											toast.error($i18n.t('OpenAI API Key is required.'));
											config.enabled = false;
										} else if (config.engine === 'gemini' && config.gemini.GEMINI_API_KEY === '') {
											toast.error($i18n.t('Gemini API Key is required.'));
											config.enabled = false;
										}
									}

									updateConfigHandler();
								}}
							/>
						</div>
					</div>
				</div>

				{#if config.enabled}
					<div class=" py-1 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">{$i18n.t('Image Prompt Generation')}</div>
						<div class="px-1">
							<Switch bind:state={config.prompt_generation} />
						</div>
					</div>
				{/if}

				<div class=" py-1 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Image Generation Engine')}</div>
					<div class="flex items-center relative">
						<select
							class=" dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
							bind:value={config.engine}
							placeholder={$i18n.t('Select Engine')}
							on:change={async () => {
								updateConfigHandler();
							}}
						>
							<option value="openai">{$i18n.t('Default (Open AI)')}</option>
							<option value="comfyui">{$i18n.t('ComfyUI')}</option>
							<option value="automatic1111">{$i18n.t('Automatic1111')}</option>
							<option value="gemini">{$i18n.t('Gemini')}</option>
						</select>
					</div>
				</div>
			</div>
			<hr class=" border-gray-100 dark:border-gray-850" />

			<div class="flex flex-col gap-2">
				{#if (config?.engine ?? 'automatic1111') === 'automatic1111'}
					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('AUTOMATIC1111 Base URL')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
									bind:value={config.automatic1111.AUTOMATIC1111_BASE_URL}
								/>
							</div>
							<button
								class="px-2.5 bg-gray-50 hover:bg-gray-100 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								type="button"
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

						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
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

					<div>
						<div class=" mb-2 text-sm font-medium">
							{$i18n.t('AUTOMATIC1111 Api Auth String')}
						</div>
						<SensitiveInput
							placeholder={$i18n.t('Enter api auth string (e.g. username:password)')}
							bind:value={config.automatic1111.AUTOMATIC1111_API_AUTH}
							required={false}
						/>

						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
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

					<!---Sampler-->
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Sampler')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<Tooltip content={$i18n.t('Enter Sampler (e.g. Euler a)')} placement="top-start">
									<input
										list="sampler-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Enter Sampler (e.g. Euler a)')}
										bind:value={config.automatic1111.AUTOMATIC1111_SAMPLER}
									/>

									<datalist id="sampler-list">
										{#each samplers ?? [] as sampler}
											<option value={sampler}>{sampler}</option>
										{/each}
									</datalist>
								</Tooltip>
							</div>
						</div>
					</div>
					<!---Scheduler-->
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Scheduler')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<Tooltip content={$i18n.t('Enter Scheduler (e.g. Karras)')} placement="top-start">
									<input
										list="scheduler-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Enter Scheduler (e.g. Karras)')}
										bind:value={config.automatic1111.AUTOMATIC1111_SCHEDULER}
									/>

									<datalist id="scheduler-list">
										{#each schedulers ?? [] as scheduler}
											<option value={scheduler}>{scheduler}</option>
										{/each}
									</datalist>
								</Tooltip>
							</div>
						</div>
					</div>
					<!---CFG scale-->
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set CFG Scale')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<Tooltip content={$i18n.t('Enter CFG Scale (e.g. 7.0)')} placement="top-start">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Enter CFG Scale (e.g. 7.0)')}
										bind:value={config.automatic1111.AUTOMATIC1111_CFG_SCALE}
									/>
								</Tooltip>
							</div>
						</div>
					</div>
				{:else if config?.engine === 'comfyui'}
					<div class="">
						<div class=" mb-2 text-sm font-medium">{$i18n.t('ComfyUI Base URL')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
									bind:value={config.comfyui.COMFYUI_BASE_URL}
								/>
							</div>
							<button
								class="px-2.5 bg-gray-50 hover:bg-gray-100 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								type="button"
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

					<div class="">
						<div class=" mb-2 text-sm font-medium">{$i18n.t('ComfyUI API Key')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<SensitiveInput
									placeholder={$i18n.t('sk-1234')}
									bind:value={config.comfyui.COMFYUI_API_KEY}
									required={false}
								/>
							</div>
						</div>
					</div>

					<div class="">
						<div class=" mb-2 text-sm font-medium">{$i18n.t('ComfyUI Workflow')}</div>

						{#if config.comfyui.COMFYUI_WORKFLOW}
							<Textarea
								class="w-full rounded-lg mb-1 py-2 px-4 text-xs bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden disabled:text-gray-600 resize-none"
								rows="10"
								bind:value={config.comfyui.COMFYUI_WORKFLOW}
								required
							/>
						{/if}

						<div class="flex w-full">
							<div class="flex-1">
								<input
									id="upload-comfyui-workflow-input"
									hidden
									type="file"
									accept=".json"
									on:change={(e) => {
										const file = e.target.files[0];
										const reader = new FileReader();

										reader.onload = (e) => {
											config.comfyui.COMFYUI_WORKFLOW = e.target.result;
											e.target.value = null;
										};

										reader.readAsText(file);
									}}
								/>

								<button
									class="w-full text-sm font-medium py-2 bg-transparent hover:bg-gray-50 border border-dashed border-gray-50 dark:border-gray-850 dark:hover:bg-gray-850 text-center rounded-xl"
									type="button"
									on:click={() => {
										document.getElementById('upload-comfyui-workflow-input')?.click();
									}}
								>
									{$i18n.t('Click here to upload a workflow.json file.')}
								</button>
							</div>
						</div>

						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Make sure to export a workflow.json file as API format from ComfyUI.')}
						</div>
					</div>

					{#if config.comfyui.COMFYUI_WORKFLOW}
						<div class="">
							<div class=" mb-2 text-sm font-medium">{$i18n.t('ComfyUI Workflow Nodes')}</div>

							<div class="text-xs flex flex-col gap-1.5">
								{#each requiredWorkflowNodes as node}
									<div class="flex w-full items-center">
										<div class="shrink-0">
											<div
												class=" capitalize line-clamp-1 font-medium px-3 py-1 w-20 text-center bg-green-500/10 text-green-700 dark:text-green-200"
											>
												{node.type}{node.type === 'prompt' ? '*' : ''}
											</div>
										</div>
										<div class="">
											<Tooltip content={$i18n.t('Input Key (e.g. text, unet_name, steps)')}>
												<input
													class="py-1 px-3 w-24 text-xs text-center bg-transparent outline-hidden border-r border-gray-50 dark:border-gray-850"
													placeholder={$i18n.t('Key')}
													bind:value={node.key}
													required
												/>
											</Tooltip>
										</div>

										<div class="w-full">
											<Tooltip
												content={$i18n.t('Comma separated Node Ids (e.g. 1 or 1,2)')}
												placement="top-start"
											>
												<input
													class="w-full py-1 px-4 text-xs bg-transparent outline-hidden"
													placeholder={$i18n.t('Node Ids')}
													bind:value={node.node_ids}
												/>
											</Tooltip>
										</div>
									</div>
								{/each}
							</div>

							<div class="mt-2 text-xs text-right text-gray-400 dark:text-gray-500">
								{$i18n.t('*Prompt node ID(s) are required for image generation')}
							</div>
						</div>
					{/if}
				{:else if config?.engine === 'openai'}
					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('OpenAI API Config')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('API Base URL')}
									bind:value={config.openai.OPENAI_API_BASE_URL}
									required
								/>
							</div>
						</div>
					</div>

					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('API Key')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<SensitiveInput
									placeholder={$i18n.t('API Key')}
									bind:value={config.openai.OPENAI_API_KEY}
									required
								/>
							</div>
						</div>
					</div>

					<div>
						<div class=" mb-2 text-sm font-medium">{$i18n.t('API Version')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('API Version')}
									bind:value={config.openai.OPENAI_API_VERSION}
								/>
							</div>
						</div>
					</div>
				{:else if config?.engine === 'gemini'}
					<div>
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('Gemini API Config')}</div>

						<div class="flex gap-2 mb-1">
							<input
								class="flex-1 w-full text-sm bg-transparent outline-none"
								placeholder={$i18n.t('API Base URL')}
								bind:value={config.gemini.GEMINI_API_BASE_URL}
								required
							/>

							<SensitiveInput
								placeholder={$i18n.t('API Key')}
								bind:value={config.gemini.GEMINI_API_KEY}
							/>
						</div>
					</div>
				{/if}
			</div>

			{#if config?.enabled}
				<hr class=" border-gray-100 dark:border-gray-850" />

				<div>
					<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Default Model')}</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<div class="flex w-full">
								<div class="flex-1">
									<Tooltip content={$i18n.t('Enter Model ID')} placement="top-start">
										<input
											list="model-list"
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={imageGenerationConfig.MODEL}
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
						</div>
					</div>
				</div>

				<div>
					<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Image Size')}</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<Tooltip content={$i18n.t('Enter Image Size (e.g. 512x512)')} placement="top-start">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
									bind:value={imageGenerationConfig.IMAGE_SIZE}
									required
								/>
							</Tooltip>
						</div>
					</div>
				</div>

				{#if ['comfyui', 'automatic1111', ''].includes(config?.engine)}
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Steps')}</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<Tooltip content={$i18n.t('Enter Number of Steps (e.g. 50)')} placement="top-start">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Enter Number of Steps (e.g. 50)')}
										bind:value={imageGenerationConfig.IMAGE_STEPS}
										required
									/>
								</Tooltip>
							</div>
						</div>
					</div>
				{/if}
			{/if}
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
