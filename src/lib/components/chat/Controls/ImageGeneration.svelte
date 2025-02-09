<script lang="ts">
	import { getContext, onMount, createEventDispatcher } from 'svelte';
	import { user } from '$lib/stores';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import { getConfig, getImageGenerationModels } from '$lib/apis/images';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	interface ImageModelWrapper {
		id: string;
		name: string;
		model: string;
		is_default?: boolean;
		image_size?: string;
		image_steps?: number;
		enabled?: boolean;
	}

	interface ImageConfig {
		enabled: boolean;
		default_engine: string;
		openai: { model_wrappers: ImageModelWrapper[] };
		automatic1111: { model_wrappers: ImageModelWrapper[] };
		comfyui: { model_wrappers: ImageModelWrapper[] };
	}

	export let show = false;
	export let params = {
		engine: '',
		model_wrapper_id: '',
		model: '',
		size: '',
		steps: 0
	};

	let loading = false;
	let configLoaded = false;
	let config: ImageConfig | null = null;
	let engines: string[] = [];
	let modelWrappersByEngine: Record<string, ImageModelWrapper[]> = {};
	let availableModels: { id: string; name: string }[] = [];

	$: if (params) {
		dispatch('change', params);
	}

	$: currentModelWrapper = (params.engine &&
		modelWrappersByEngine[params.engine]?.find(
			(m) => m.id === params.model_wrapper_id
		)) as ImageModelWrapper | null;

	function updateModelWrapperDefaults(model_wrapper: ImageModelWrapper | null) {
		if (!model_wrapper) return;

		if (model_wrapper.model) {
			params.model = model_wrapper.model;
		}
		if (model_wrapper.image_size) {
			params.size = model_wrapper.image_size;
		}
		if (model_wrapper.image_steps) {
			params.steps = model_wrapper.image_steps;
		}
	}

	async function fetchAvailableModels(engine: string) {
		try {
			const models = await getImageGenerationModels(localStorage.token, engine);
			if (models) {
				availableModels = models;
			}
		} catch (error) {
			console.error('Error fetching available models:', error);
		}
	}

	function handleEngineChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		const newEngine = select.value;

		if (newEngine !== params.engine) {
			params.engine = newEngine;
			fetchAvailableModels(newEngine);

			if (modelWrappersByEngine[newEngine]?.length > 0) {
				const defaultWrapper =
					modelWrappersByEngine[newEngine].find((m) => m.is_default) ||
					modelWrappersByEngine[newEngine][0];
				params.model_wrapper_id = defaultWrapper.id;
			}
		}
	}

	function handleModelWrapperChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		const newModelWrapperId = select.value;

		if (newModelWrapperId !== params.model_wrapper_id) {
			params.model_wrapper_id = newModelWrapperId;
			const newModelWrapper =
				modelWrappersByEngine[params.engine]?.find((m) => m.id === newModelWrapperId) || null;
			updateModelWrapperDefaults(newModelWrapper);
		}
	}

	async function fetchConfig() {
		try {
			loading = true;
			config = await getConfig(localStorage.token);

			if (!config || !config?.enabled) {
				configLoaded = false;
				return;
			}

			engines = ['openai', 'automatic1111', 'comfyui'].filter((engine) =>
				config[engine]?.model_wrappers?.some((m) => m.enabled)
			);

			if (engines.length === 0) {
				configLoaded = false;
				return;
			}

			if (config.openai?.model_wrappers)
				modelWrappersByEngine.openai = config.openai.model_wrappers;
			if (config.automatic1111?.model_wrappers)
				modelWrappersByEngine.automatic1111 = config.automatic1111.model_wrappers;
			if (config.comfyui?.model_wrappers)
				modelWrappersByEngine.comfyui = config.comfyui.model_wrappers;

			if (!params.engine) {
				params.engine = config.default_engine || engines[0];

				fetchAvailableModels(params.engine);

				if (modelWrappersByEngine[params.engine]?.length > 0) {
					const defaultWrapper =
						modelWrappersByEngine[params.engine].find((m) => m.is_default) ||
						modelWrappersByEngine[params.engine][0];
					params.model_wrapper_id = defaultWrapper.id;

					updateModelWrapperDefaults(defaultWrapper);
				}
			}

			configLoaded = true;
		} catch (error) {
			configLoaded = false;
			console.error('Error fetching config:', error);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		if (!configLoaded) {
			fetchConfig();
		}
	});
</script>

{#if show && config && configLoaded}
	<div class="flex flex-col gap-3">
		<div>
			<label class="text-xs mb-1.5 block">{$i18n.t('Engine')}</label>
			<select
				value={params.engine}
				on:change={handleEngineChange}
				class="w-full bg-transparent border border-input rounded-md px-2 py-1.5 text-sm"
				disabled={loading}
			>
				{#each engines as engine}
					<option value={engine}>
						{engine.toUpperCase()}
						{config?.default_engine === engine ? '(Default)' : ''}
					</option>
				{/each}
			</select>
		</div>

		{#if params.engine && modelWrappersByEngine[params.engine]}
			<div>
				<label class="text-xs mb-1.5 block">{$i18n.t('Model wrapper')}</label>
				<select
					value={params.model_wrapper_id}
					on:change={handleModelWrapperChange}
					class="w-full bg-transparent border border-input rounded-md px-2 py-1.5 text-sm"
					disabled={loading}
				>
					{#each modelWrappersByEngine[params.engine] as model_wrapper}
						<option value={model_wrapper.id}>
							{model_wrapper.name}
							{model_wrapper.is_default ? '(Default)' : ''}
						</option>
					{/each}
				</select>
			</div>

			{#if $user.role === 'admin'}
				<Collapsible title={$i18n.t('Advanced Settings')} buttonClassName="w-full">
					<div class="mt-2 space-y-3" slot="content">
						<div>
							<label class="text-xs mb-1.5 block">{$i18n.t('Model')}</label>
							<div class="relative">
								<input
									list="model-list"
									type="text"
									bind:value={params.model}
									class="w-full bg-transparent border border-input rounded-md px-2 py-1.5 text-sm"
								/>

								<datalist id="model-list">
									{#each availableModels ?? [] as availableModel}
										<option value={availableModel.id}>{availableModel.name}</option>
									{/each}
								</datalist>
								{#if currentModelWrapper?.model && currentModelWrapper.model !== params.model}
									<p class="text-xs text-yellow-500 mt-1">
										{$i18n.t('Default model for this model wrapper is')}
										{currentModelWrapper.model}
									</p>
								{/if}
							</div>
						</div>

						<div>
							<label class="text-xs mb-1.5 block">{$i18n.t('Image Size')}</label>
							<select
								bind:value={params.size}
								class="w-full bg-transparent border border-input rounded-md px-2 py-1.5 text-sm"
							>
								<option value="256x256">256x256</option>
								<option value="512x512">512x512</option>
								<option value="1024x1024">1024x1024</option>
							</select>
							{#if currentModelWrapper?.image_size && currentModelWrapper.image_size !== params.size}
								<p class="text-xs text-yellow-500 mt-1">
									{$i18n.t('Default size for this model wrapper is')}
									{currentModelWrapper.image_size}
								</p>
							{/if}
						</div>

						<div>
							<label class="text-xs mb-1.5 block">{$i18n.t('Steps')}</label>
							<input
								type="number"
								bind:value={params.steps}
								min="1"
								max="150"
								class="w-full bg-transparent border border-input rounded-md px-2 py-1.5 text-sm"
							/>
							{#if currentModelWrapper?.image_steps && currentModelWrapper.image_steps !== params.steps}
								<p class="text-xs text-yellow-500 mt-1">
									{$i18n.t('Default steps for this model wrapper is')}
									{currentModelWrapper.image_steps}
								</p>
							{/if}
						</div>
					</div>
				</Collapsible>
			{/if}
		{/if}
	</div>
{/if}
