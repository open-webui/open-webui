<script>
	import { getContext, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	import { config as appConfig } from '$lib/stores';
	import { DEFAULT_CAPABILITIES } from '$lib/constants';
	import { getModelsConfig, setModelsConfig, setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { getBackendConfig } from '$lib/apis';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import DefaultFeatures from '$lib/components/workspace/Models/DefaultFeatures.svelte';
	import BuiltinTools from '$lib/components/workspace/Models/BuiltinTools.svelte';
	import PromptSuggestions from '$lib/components/workspace/Models/PromptSuggestions.svelte';

	export let initHandler = () => {};
	export let dirty = false;

	let config = null;
	let modelIds = [];
	let loading = false;
	let expanded = false;
	let showCapabilities = false;
	let showParameters = false;
	let showPromptSuggestions = false;
	let savedSnapshot = '';

	let defaultCapabilities = {};
	let defaultFeatureIds = [];
	let defaultParams = {};
	let builtinTools = {};
	let promptSuggestions = [];

	$: configuredParams = Object.entries(defaultParams ?? {}).filter(
		([_, value]) => value !== null && value !== '' && value !== undefined
	);
	$: enabledCapabilities = Object.entries(defaultCapabilities ?? {}).filter(([_, value]) => value);
	$: availableFeatures = enabledCapabilities
		.filter(([key]) => ['web_search', 'code_interpreter', 'image_generation'].includes(key))
		.map(([key]) => key);

	const getSnapshot = () =>
		JSON.stringify({
			defaultCapabilities,
			defaultFeatureIds,
			defaultParams: Object.fromEntries(configuredParams),
			builtinTools,
			promptSuggestions: promptSuggestions.filter((p) => p.content !== '')
		});

	const updateDirty = async () => {
		await tick();
		dirty = savedSnapshot !== '' && getSnapshot() !== savedSnapshot;
	};

	const init = async () => {
		loading = true;
		config = await getModelsConfig(localStorage.token);

		modelIds = config?.MODEL_ORDER_LIST || [];

		const savedMeta = config?.DEFAULT_MODEL_METADATA;
		if (savedMeta && Object.keys(savedMeta).length > 0) {
			defaultCapabilities = savedMeta.capabilities ?? { ...DEFAULT_CAPABILITIES };
			defaultFeatureIds = savedMeta.defaultFeatureIds ?? [];
			builtinTools = savedMeta.builtinTools ?? {};
		} else {
			defaultCapabilities = { ...DEFAULT_CAPABILITIES };
			defaultFeatureIds = [];
			builtinTools = {};
		}

		defaultParams = config?.DEFAULT_MODEL_PARAMS ?? {};
		promptSuggestions = $appConfig?.default_prompt_suggestions ?? [];
		savedSnapshot = getSnapshot();
		dirty = false;
		loading = false;
	};

	export const save = async () => {
		if (loading || !dirty) {
			return true;
		}

		const metadata = {
			capabilities: defaultCapabilities,
			...(defaultFeatureIds.length > 0 ? { defaultFeatureIds } : {}),
			...(Object.keys(builtinTools).length > 0 ? { builtinTools } : {})
		};

		const res = await setModelsConfig(localStorage.token, {
			DEFAULT_MODELS: config?.DEFAULT_MODELS ?? null,
			DEFAULT_PINNED_MODELS: config?.DEFAULT_PINNED_MODELS ?? null,
			MODEL_ORDER_LIST: modelIds,
			DEFAULT_MODEL_METADATA: metadata,
			DEFAULT_MODEL_PARAMS: Object.fromEntries(configuredParams)
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			config = res;
			promptSuggestions = promptSuggestions.filter((p) => p.content !== '');
			promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
			await appConfig.set(await getBackendConfig());
			savedSnapshot = getSnapshot();
			dirty = false;

			toast.success($i18n.t('Models configuration saved successfully'));
			initHandler();
			return true;
		} else {
			toast.error($i18n.t('Failed to save models configuration'));
			return false;
		}
	};

	onMount(async () => {
		await init();
	});
</script>

<div class="shrink-0">
	<div class="flex items-center justify-between gap-4 py-0.5">
		<button
			class="min-w-0 flex-1 text-left text-xs text-gray-600 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
			type="button"
			on:click={() => {
				expanded = !expanded;
			}}
		>
			{$i18n.t('Model Defaults')}
		</button>

		<button
			class="shrink-0 text-[0.6875rem] text-gray-400 transition hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
			type="button"
			on:click={() => {
				expanded = !expanded;
			}}
		>
			{expanded ? $i18n.t('Close') : $i18n.t('Configure')}
		</button>
	</div>

	{#if expanded}
		{#if loading}
			<div class="py-1 text-xs text-gray-400 dark:text-gray-600">{$i18n.t('Loading...')}</div>
		{:else}
			<div class="space-y-1 mt-0.5">
				<div>
					<button
						class="flex w-full items-center justify-between gap-4 py-0.5 text-left"
						type="button"
						on:click={() => {
							showCapabilities = !showCapabilities;
						}}
					>
						<span class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Model Capabilities')}
						</span>
						<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{showCapabilities ? $i18n.t('Close') : $i18n.t('Configure')}
						</span>
					</button>

					{#if showCapabilities}
						<div class="pb-2" on:click={updateDirty} on:change={updateDirty}>
							<Capabilities bind:capabilities={defaultCapabilities} />

							{#if availableFeatures.length > 0}
								<div class="mt-4">
									<DefaultFeatures {availableFeatures} bind:featureIds={defaultFeatureIds} />
								</div>
							{/if}

							{#if defaultCapabilities.builtin_tools}
								<div class="mt-4">
									<BuiltinTools bind:builtinTools />
								</div>
							{/if}
						</div>
					{/if}
				</div>

				<div>
					<button
						class="flex w-full items-center justify-between gap-4 py-0.5 text-left"
						type="button"
						on:click={() => {
							showParameters = !showParameters;
						}}
					>
						<span class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Model Parameters')}
						</span>
						<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{showParameters ? $i18n.t('Close') : $i18n.t('Configure')}
						</span>
					</button>

					{#if showParameters}
						<div
							class="max-h-[24rem] overflow-y-auto pb-2 pr-1 scrollbar-hover"
							on:click={updateDirty}
							on:change={updateDirty}
							on:input={updateDirty}
						>
							<AdvancedParams admin={true} custom={true} bind:params={defaultParams} />
						</div>
					{/if}
				</div>

				<div>
					<button
						class="flex w-full items-center justify-between gap-4 py-0.5 text-left"
						type="button"
						on:click={() => {
							showPromptSuggestions = !showPromptSuggestions;
						}}
					>
						<span class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Prompt Suggestions')}
						</span>
						<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
							{showPromptSuggestions ? $i18n.t('Close') : $i18n.t('Configure')}
						</span>
					</button>

					{#if showPromptSuggestions}
						<div class="pb-2" on:click={updateDirty} on:change={updateDirty} on:input={updateDirty}>
							<PromptSuggestions bind:promptSuggestions />
						</div>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>
