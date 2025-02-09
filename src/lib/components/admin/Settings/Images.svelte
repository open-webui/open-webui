<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { config as backendConfig, user } from '$lib/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		getImageGenerationModels,
		getConfig,
		updateConfig,
		verifyConfigUrl
	} from '$lib/apis/images';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AccessControl from '../../workspace/common/AccessControl.svelte';

	interface ImageModel {
		id: string;
		name: string;
		model: string;
		is_default: boolean;
		enabled: boolean;
		image_size: string;
		image_steps: number;
		access_control: {
			read: { group_ids: string[] };
			write: { group_ids: string[] };
		} | null;
		workflow?: string;
		workflow_nodes?: any[];
		cfg_scale?: number;
		sampler?: string;
		scheduler?: string;
	}

	interface ImageConfig {
		enabled: boolean;
		prompt_generation: boolean;
		default_engine: 'openai' | 'comfyui' | 'automatic1111';
		openai: {
			api_base_url: string;
			api_key: string;
			model_wrappers: ImageModel[];
		};
		comfyui: {
			base_url: string;
			api_key: string;
			model_wrappers: ImageModel[];
		};
		automatic1111: {
			base_url: string;
			api_auth: string;
			model_wrappers: ImageModel[];
		};
	}

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let loading = false;

	let config: ImageConfig | null = null;

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

	let availableModels: {id: string, name: string}[] = [];

	const getModels = async (engine: string) => {
		return await getImageGenerationModels(localStorage.token, engine).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const updateConfigHandler = async () => {
		try {
			const res = await updateConfig(localStorage.token, config);
			if (res) {
				config = res;
				if (config?.enabled) {
					await backendConfig.set(await getBackendConfig());
				}
			}
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	const validateJSON = (json: string): boolean => {
		try {
			const obj = JSON.parse(json);
			return obj && typeof obj === 'object';
		} catch (e) {
			return false;
		}
	};

	const saveHandler = async () => {
		if (!config) return;

		loading = true;

		const validConfig = {
			enabled: config.enabled,
			prompt_generation: config.prompt_generation,
			default_engine: config.default_engine,
			openai: {
				api_base_url: config.openai?.api_base_url || '',
				api_key: config.openai?.api_key || '',
				model_wrappers: (config.openai?.model_wrappers || []).map(model_wrapper => ({
					id: model_wrapper.id,
					name: model_wrapper.name,
					model: model_wrapper.model,
					is_default: model_wrapper.is_default,
					enabled: model_wrapper.enabled,
					image_size: model_wrapper.image_size,
					image_steps: model_wrapper.image_steps,
					access_control: model_wrapper.access_control,
				}))
			},
			automatic1111: {
				base_url: config.automatic1111?.base_url || '',
				api_auth: config.automatic1111?.api_auth || '',
				model_wrappers: (config.automatic1111?.model_wrappers || []).map(model_wrapper => ({
					id: model_wrapper.id,
					name: model_wrapper.name,
					model: model_wrapper.model,
					is_default: model_wrapper.is_default,
					enabled: model_wrapper.enabled,
					image_size: model_wrapper.image_size,
					image_steps: model_wrapper.image_steps,
					access_control: model_wrapper.access_control,
					cfg_scale: model_wrapper.cfg_scale,
					sampler: model_wrapper.sampler,
					scheduler: model_wrapper.scheduler
				}))
			},
			comfyui: {
				base_url: config.comfyui?.base_url || '',
				api_key: config.comfyui?.api_key || '',
				model_wrappers: (config.comfyui?.model_wrappers || []).map(model_wrapper => ({
					id: model_wrapper.id,
					name: model_wrapper.name,
					model: model_wrapper.model,
					is_default: model_wrapper.is_default,
					enabled: model_wrapper.enabled,
					image_size: model_wrapper.image_size,
					image_steps: model_wrapper.image_steps,
					access_control: model_wrapper.access_control,
					workflow: model_wrapper.workflow,
					workflow_nodes: model_wrapper.workflow_nodes
				}))
			}
		};

		if (validConfig.comfyui.model_wrappers) {
			for (const model_wrapper of validConfig.comfyui.model_wrappers) {
				if (model_wrapper.workflow && !validateJSON(model_wrapper.workflow)) {
					toast.error(`Invalid JSON format for ComfyUI Workflow in model ${model_wrapper.name}`);
					loading = false;
					return;
				}

                const missingNodeIds = model_wrapper.workflow_nodes.find(node =>
                    !node.node_ids || node.node_ids.length === 0
                );

                if (missingNodeIds) {
                    toast.error(`Missing node IDs in workflow configuration for model ${model_wrapper.name}`);
                    loading = false;
                    return;
                }
			}
		}

		try {
			await updateConfig(localStorage.token, validConfig);
			config = validConfig;
			dispatch('save');
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			const res = await getConfig(localStorage.token).catch((error: Error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				config = res;

				if (config.comfyui.model_wrappers) {
					config.comfyui.model_wrappers = config.comfyui.model_wrappers.map(model_wrapper => ({
						...model_wrapper,
						workflow: model_wrapper.workflow ? JSON.stringify(JSON.parse(model_wrapper.workflow), null, 2) : undefined
					}));
				}
			}
		}
	});

	const generateId = (name: string): string => {
		const timestamp = Date.now().toString(36);
		const sanitizedName = name
			.toLowerCase()
			.replace(/\s+/g, '-')
			.replace(/[^a-z0-9-]+/g, '')
			.replace(/^-+|-+$/g, '');
		return `${sanitizedName}-${timestamp}`;
	};

	const addNewModelWrapper = async (engine: 'openai' | 'comfyui' | 'automatic1111') => {
		if (!config) return;

		try {
			const urlValid = await verifyConfigUrl(localStorage.token, engine);
			if (!urlValid) {
				toast.error(`Invalid ${engine} configuration URL`);
				return;
			}
		} catch (error) {
			toast.error(`Failed to add model wrapper: ${error}`);
			return;
		}

		try {
			availableModels = await getModels(engine);
			if (!availableModels) {
				toast.error('Failed to fetch available models');
			}
		} catch (error) {
			toast.error(`Failed to fetch models: ${error}`);
		}

		let shouldBeDefault = false;
		switch (engine) {
			case 'openai':
				shouldBeDefault = !config.openai.model_wrappers?.length;
				break;
			case 'automatic1111':
				shouldBeDefault = !config.automatic1111.model_wrappers?.length;
				break;
			case 'comfyui':
				shouldBeDefault = !config.comfyui.model_wrappers?.length;
				break;
		}

		const defaultName = {
			openai: 'New OpenAI model wrapper',
			automatic1111: 'New Automatic1111 model wrapper',
			comfyui: 'New ComfyUI model wrapper'
		}[engine];

		const newModel: ImageModel = {
			id: generateId(defaultName),
			name: defaultName,
			model: '',
			is_default: shouldBeDefault,
			enabled: true,
			image_size: '512x512',
			image_steps: 50,
			access_control: null,
		};

		if (engine === 'automatic1111') {
			newModel.cfg_scale = 7.0;
			newModel.sampler = '';
			newModel.scheduler = '';
		} else if (engine === 'comfyui') {
			newModel.workflow = '';
			newModel.workflow_nodes = [];
		}

		switch (engine) {
			case 'openai':
				if (!config.openai.model_wrappers) config.openai.model_wrappers = [];
				config.openai.model_wrappers = [...config.openai.model_wrappers, newModel];
				break;
			case 'automatic1111':
				if (!config.automatic1111.model_wrappers) config.automatic1111.model_wrappers = [];
				config.automatic1111.model_wrappers = [...config.automatic1111.model_wrappers, newModel];
				break;
			case 'comfyui':
				if (!config.comfyui.model_wrappers) config.comfyui.model_wrappers = [];
				config.comfyui.model_wrappers = [...config.comfyui.model_wrappers, newModel];
				break;
		}
	};

</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={saveHandler}
>
	<div class="space-y-3 overflow-y-scroll scrollbar-hidden pr-2">
		{#if config}
			<div class="space-y-4">
				<div class="mb-1 text-sm font-medium">{$i18n.t('Image Settings')}</div>

				<div class="py-1 flex w-full justify-between">
					<div class="self-center text-xs font-medium">
						{$i18n.t('Image Generation (Experimental)')}
					</div>
					<div class="px-1">
						<Switch
							bind:state={config.enabled}
							on:change={updateConfigHandler}
						/>
					</div>
				</div>

				{#if config.enabled}
					<div class="py-1 flex w-full justify-between">
						<div class="self-center text-xs font-medium">{$i18n.t('Image Prompt Generation')}</div>
						<div class="px-1">
							<Switch bind:state={config.prompt_generation} />
						</div>
					</div>
				{/if}

				<div class="py-1 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Default Image Generation Engine')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
							bind:value={config.default_engine}
							on:change={updateConfigHandler}
						>
							<option value="openai">{$i18n.t('Default (Open AI)')}</option>
							<option value="comfyui">{$i18n.t('ComfyUI')}</option>
							<option value="automatic1111">{$i18n.t('Automatic1111')}</option>
						</select>
					</div>
				</div>
			</div>

			<hr class="dark:border-gray-850" />

			<div class="space-y-4">
				<div>
					<div class="mb-2 text-sm font-medium">{$i18n.t('OpenAI Settings')}</div>
					<div class="flex gap-2 mb-4">
						<input
							class="flex-1 rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('API Base URL')}
							bind:value={config.openai.api_base_url}
						/>
						<SensitiveInput
							placeholder={$i18n.t('API Key')}
							bind:value={config.openai.api_key}
							required={false}
						/>
					</div>

					<div class="space-y-4 mt-4">
						<div class="flex justify-between items-center">
							<div class="text-sm font-medium">{$i18n.t('OpenAI Model Wrapper')}</div>
							<button
								type="button"
								class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition"
								on:click={() => addNewModelWrapper('openai')}
							>
								{$i18n.t('Add model wrapper')}
							</button>
						</div>
						{#if config.openai.model_wrappers?.length}
							{#each config.openai.model_wrappers as model_wrapper, i}
								<div class="border dark:border-gray-850 rounded-lg p-4">
									<div class="flex justify-between mb-4">
										<div class="flex items-center gap-4">
											<h3 class="text-sm font-medium">{model_wrapper.name || 'New model wrapper'}</h3>
											<div class="flex items-center gap-2">
												<Switch
													bind:state={model_wrapper.enabled}
												/>
												<label class="text-xs text-gray-500">{model_wrapper.enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}</label>
											</div>
										</div>
										<button
											type="button"
											class="text-red-500 hover:text-red-600"
											on:click={() => {
												if (!config) return;
												config.openai.model_wrappers = config.openai.model_wrappers.filter((_, index) => index !== i);
											}}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
											</svg>
										</button>
									</div>

									<div class="space-y-4">
										<div class="grid grid-cols-2 gap-4">
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Model wrapper name')}</label>
												<input
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.name}
													placeholder="e.g. SDXL 1.0"
													on:input={(e) => {
														model_wrapper.id = generateId(e.currentTarget.value || 'New OpenAI model wrapper');
													}}
												/>
											</div>
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Model')}</label>
												<div class="relative">
													<input
														list="model-list"
														class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
														bind:value={model_wrapper.model}
														placeholder="Select a model"
														required
													/>

													<datalist id="model-list">
														{#each availableModels ?? [] as availableModel}
															<option value={availableModel.id}>{availableModel.name}</option>
														{/each}
													</datalist>
												</div>
											</div>
										</div>

										<div class="grid grid-cols-2 gap-4">
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Image Size')}</label>
												<input
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.image_size}
													placeholder="e.g. 1024x1024"
												/>
											</div>
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Steps')}</label>
												<input
													type="number"
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.image_steps}
													placeholder="e.g. 50"
												/>
											</div>
										</div>

										<div class="flex items-center space-x-2">
											<Switch
												bind:state={model_wrapper.is_default}
												on:change={() => {
													if (model_wrapper.is_default) {
														config.openai.model_wrappers.forEach((m, index) => {
															if (index !== i) m.is_default = false;
														});
													}
												}}
											/>
											<label class="text-sm">{$i18n.t('Default model wrapper')}</label>
										</div>

										<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
											<AccessControl
												bind:accessControl={model_wrapper.access_control}
												accessRoles={['read', 'write']}
											/>
										</div>
									</div>
								</div>
							{/each}
						{:else}
							<div class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
								{$i18n.t('No OpenAI model wrappers configured')}
							</div>
						{/if}
					</div>
				</div>

				<div>
					<div class="mb-2 text-sm font-medium">{$i18n.t('Automatic1111 Settings')}</div>
					<div class="flex gap-2 mb-4">
						<input
							class="flex-1 rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('Base URL')}
							bind:value={config.automatic1111.base_url}
						/>
						<SensitiveInput
							placeholder={$i18n.t('API Auth')}
							bind:value={config.automatic1111.api_auth}
							required={false}
						/>
					</div>

					<div class="space-y-4 mt-4">
						<div class="flex justify-between items-center">
							<div class="text-sm font-medium">{$i18n.t('Automatic1111 model wrappers')}</div>
							<button
								type="button"
								class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition"
								on:click={() => addNewModelWrapper('automatic1111')}
							>
								{$i18n.t('Add model wrapper')}
							</button>
						</div>
						{#if config.automatic1111.model_wrappers?.length}
							{#each config.automatic1111.model_wrappers as model_wrapper, i}
								<div class="border dark:border-gray-850 rounded-lg p-4">
									<div class="flex justify-between mb-4">
										<div class="flex items-center gap-4">
											<h3 class="text-sm font-medium">{model_wrapper.name || 'New model wrapper'}</h3>
											<div class="flex items-center gap-2">
												<Switch
													bind:state={model_wrapper.enabled}
												/>
												<label class="text-xs text-gray-500">{model_wrapper.enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}</label>
											</div>
										</div>
										<button
											type="button"
											class="text-red-500 hover:text-red-600"
											on:click={() => {
												if (!config) return;
												config.automatic1111.model_wrappers = config.automatic1111.model_wrappers.filter((_, index) => index !== i);
											}}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
											</svg>
										</button>
									</div>

									<div class="space-y-4">
										<div class="grid grid-cols-2 gap-4">
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Model wrapper name')}</label>
												<input
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.name}
													placeholder="e.g. SDXL 1.0"
													on:input={(e) => {
														model_wrapper.id = generateId(e.currentTarget.value || 'New Automatic1111 model wrapper');
													}}
												/>
											</div>
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Model')}</label>
												<div class="relative">
													<input
														list="model-list"
														class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
														bind:value={model_wrapper.model}
														placeholder="Select a model"
														required
													/>

													<datalist id="model-list">
														{#each availableModels ?? [] as availableModel}
															<option value={availableModel.id}>{availableModel.name}</option>
														{/each}
													</datalist>
												</div>
											</div>
										</div>

										<div class="grid grid-cols-2 gap-4">
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Image Size')}</label>
												<input
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.image_size}
													placeholder="e.g. 1024x1024"
												/>
											</div>
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Steps')}</label>
												<input
													type="number"
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.image_steps}
													placeholder="e.g. 50"
												/>
											</div>
										</div>

										<div class="flex items-center space-x-2">
											<Switch
												bind:state={model_wrapper.is_default}
												on:change={() => {
													if (model_wrapper.is_default) {
														config.automatic1111.model_wrappers.forEach((m, index) => {
															if (index !== i) m.is_default = false;
														});
													}
												}}
											/>
											<label class="text-sm">{$i18n.t('Default model wrapper')}</label>
										</div>

										<div class="space-y-4">
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Sampler')}</label>
												<input
													list="sampler-list"
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.sampler}
													placeholder={$i18n.t('e.g. Euler a')}
												/>
												<datalist id="sampler-list">
													{#each samplers as sampler}
														<option value={sampler} />
													{/each}
												</datalist>
											</div>

											<div>
												<label class="block text-xs mb-1">{$i18n.t('Scheduler')}</label>
												<input
													list="scheduler-list"
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.scheduler}
													placeholder={$i18n.t('e.g. Karras')}
												/>
												<datalist id="scheduler-list">
													{#each schedulers as scheduler}
														<option value={scheduler} />
													{/each}
												</datalist>
											</div>

											<div>
												<label class="block text-xs mb-1">{$i18n.t('CFG Scale')}</label>
												<input
													type="number"
													step="0.1"
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.cfg_scale}
													placeholder="7.0"
												/>
											</div>
										</div>

										<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
											<AccessControl
												bind:accessControl={model_wrapper.access_control}
												accessRoles={['read', 'write']}
											/>
										</div>
									</div>
								</div>
							{/each}
						{:else}
							<div class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
								{$i18n.t('No Automatic1111 model wrappers configured')}
							</div>
						{/if}
					</div>
				</div>

				<div>
					<div class="mb-2 text-sm font-medium">{$i18n.t('ComfyUI Settings')}</div>
					<div class="flex gap-2 mb-4">
						<input
							class="flex-1 rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('Base URL')}
							bind:value={config.comfyui.base_url}
						/>
						<SensitiveInput
							placeholder={$i18n.t('API Key')}
							bind:value={config.comfyui.api_key}
							required={false}
						/>
					</div>

					<div class="space-y-4 mt-4">
						<div class="flex justify-between items-center">
							<div class="text-sm font-medium">{$i18n.t('ComfyUI model wrappers')}</div>
							<button
								type="button"
								class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition"
								on:click={() => addNewModelWrapper('comfyui')}
							>
								{$i18n.t('Add model wrapper')}
							</button>
						</div>
						{#if config.comfyui.model_wrappers?.length}
							{#each config.comfyui.model_wrappers as model_wrapper, i}
								<div class="border dark:border-gray-850 rounded-lg p-4">
									<div class="flex justify-between mb-4">
										<div class="flex items-center gap-4">
											<h3 class="text-sm font-medium">{model_wrapper.name || 'New model wraper'}</h3>
											<div class="flex items-center gap-2">
												<Switch
													bind:state={model_wrapper.enabled}
												/>
												<label class="text-xs text-gray-500">{model_wrapper.enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}</label>
											</div>
										</div>
										<button
											type="button"
											class="text-red-500 hover:text-red-600"
											on:click={() => {
												if (!config) return;
												config.comfyui.model_wrappers = config.comfyui.model_wrappers.filter((_, index) => index !== i);
											}}
										>
											<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
												<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
											</svg>
										</button>
									</div>

									<div class="space-y-4">
										<div class="grid grid-cols-2 gap-4">
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Model wrapper name')}</label>
												<input
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.name}
													placeholder="e.g. SDXL 1.0"
													on:input={(e) => {
														model_wrapper.id = generateId(e.currentTarget.value || 'New ComfyUI model wrapper');
													}}
												/>
											</div>
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Model')}</label>
												<div class="relative">
													<input
														list="model-list"
														class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
														bind:value={model_wrapper.model}
														placeholder="Select a model"
														required
													/>

													<datalist id="model-list">
														{#each availableModels ?? [] as availableModel}
															<option value={availableModel.id}>{availableModel.name}</option>
														{/each}
													</datalist>
												</div>
											</div>
										</div>

										<div class="grid grid-cols-2 gap-4">
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Image Size')}</label>
												<input
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.image_size}
													placeholder="e.g. 1024x1024"
												/>
											</div>
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Steps')}</label>
												<input
													type="number"
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
													bind:value={model_wrapper.image_steps}
													placeholder="e.g. 50"
												/>
											</div>
										</div>

										<div class="flex items-center space-x-2">
											<Switch
												bind:state={model_wrapper.is_default}
												on:change={() => {
													if (model_wrapper.is_default) {
														config.comfyui.model_wrappers.forEach((m, index) => {
															if (index !== i) m.is_default = false;
														});
													}
												}}
											/>
											<label class="text-sm">{$i18n.t('Default model wrapper')}</label>
										</div>

										<div class="space-y-4">
											<div>
												<label class="block text-xs mb-1">{$i18n.t('Workflow')}</label>
												<textarea
													class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none resize-y"
													rows="10"
													bind:value={model_wrapper.workflow}
													placeholder={$i18n.t('Paste ComfyUI workflow JSON here')}
												/>
											</div>
										</div>
										{#if model_wrapper.workflow}
											<div class="">
												<div class="mb-2 text-sm font-medium">{$i18n.t('ComfyUI Workflow Nodes')}</div>

												<div class="text-xs flex flex-col gap-1.5">
													{#if !model_wrapper.workflow_nodes || model_wrapper.workflow_nodes.length === 0}
														{@const _ = model_wrapper.workflow_nodes = requiredWorkflowNodes.map(node => ({
															type: node.type,
															key: node.key || '',
															node_ids: ''
														}))}
													{/if}

													{#each requiredWorkflowNodes as templateNode, index}
														<div class="flex w-full items-center border dark:border-gray-850 rounded-lg">
															<div class="flex-shrink-0">
																<div class="capitalize line-clamp-1 font-medium px-3 py-1 w-20 text-center rounded-l-lg bg-green-500/10 text-green-700 dark:text-green-200">
																	{templateNode.type}{templateNode.type === 'prompt' ? '*' : ''}
																</div>
															</div>
															<div class="">
																<Tooltip content="Input Key (e.g. text, unet_name, steps)">
																	<input
																		class="py-1 px-3 w-24 text-xs text-center bg-transparent outline-none border-r dark:border-gray-850"
																		placeholder="Key"
																		bind:value={model_wrapper.workflow_nodes[index].key}
																		required
																	/>
																</Tooltip>
															</div>

															<div class="w-full">
																<Tooltip
																	content="Comma separated Node Ids (e.g. 1 or 1,2)"
																	placement="top-start"
																>
																	<input
																		class="w-full py-1 px-4 rounded-r-lg text-xs bg-transparent outline-none"
																		placeholder="Node Ids"
																		bind:value={model_wrapper.workflow_nodes[index].node_ids}
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

										<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
											<AccessControl
												bind:accessControl={model_wrapper.access_control}
												accessRoles={['read', 'write']}
											/>
										</div>
									</div>
								</div>
							{/each}
						{:else}
							<div class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
								{$i18n.t('No ComfyUI model wrappers configured')}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center space-x-2"
			type="submit"
			disabled={loading}
		>
			<span>{$i18n.t('Save')}</span>
			{#if loading}
				<div class="ml-2 self-center">
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
			{/if}
		</button>
	</div>
</form>
