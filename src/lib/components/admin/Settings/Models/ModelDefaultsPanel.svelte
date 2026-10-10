<script>
	import { getContext, onMount, tick } from 'svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ModelSettingsLabel from '$lib/components/workspace/Models/ModelSettingsLabel.svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	import { config as appConfig } from '$lib/stores';
	import { DEFAULT_CAPABILITIES } from '$lib/constants';
	import { getModelsConfig, setModelsConfig, setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { getBackendConfig } from '$lib/apis';
	import { getLanguages } from '$lib/i18n';
	import { resolveLocalizedPromptSuggestions } from '$lib/utils/localizedContent';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import LanguageModeSelect from '$lib/components/common/LanguageModeSelect.svelte';
	import LocalizedPromptSuggestions from '$lib/components/workspace/Models/LocalizedPromptSuggestions.svelte';

	export let initHandler = () => {};
	export let dirty = false;

	let config = null;
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
	let useDefaultPromptSuggestions = false;
	let promptSuggestionsI18n = {};
	let languages = [];
	let editingLocale = '';

	$: configuredParams = Object.entries(defaultParams ?? {}).filter(
		([_, value]) => value !== null && value !== '' && value !== undefined
	);
	$: enabledCapabilities = Object.entries(defaultCapabilities ?? {}).filter(([_, value]) => value);
	$: translatedPromptLocales = Object.entries(promptSuggestionsI18n ?? {})
		.filter(([_, value]) => Array.isArray(value?.suggestion_prompts))
		.map(([locale]) => locale);
	$: editingLocaleLabel = languages.find((language) => language.code === editingLocale)?.title;

	const getSnapshot = () =>
		JSON.stringify({
			defaultCapabilities,
			defaultFeatureIds,
			defaultParams: Object.fromEntries(configuredParams),
			builtinTools,
			promptSuggestions: useDefaultPromptSuggestions
				? null
				: promptSuggestions.filter((p) => p.content !== ''),
			promptSuggestionsI18n
		});

	const updateDirty = async () => {
		await tick();
		dirty = savedSnapshot !== '' && getSnapshot() !== savedSnapshot;
	};

	const resetPromptSuggestions = () => {
		useDefaultPromptSuggestions = true;
		promptSuggestions = resolveLocalizedPromptSuggestions(null, {});
		updateDirty();
	};

	const init = async () => {
		loading = true;
		config = await getModelsConfig(localStorage.token);

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
		useDefaultPromptSuggestions = $appConfig?.default_prompt_suggestions == null;
		promptSuggestions = resolveLocalizedPromptSuggestions(
			$appConfig?.default_prompt_suggestions,
			{}
		);
		promptSuggestionsI18n = $appConfig?.default_prompt_suggestions_i18n ?? {};
		languages = await getLanguages();
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

		config = await getModelsConfig(localStorage.token);

		const res = await setModelsConfig(localStorage.token, {
			DEFAULT_MODELS: config?.DEFAULT_MODELS ?? null,
			DEFAULT_PINNED_MODELS: config?.DEFAULT_PINNED_MODELS ?? null,
			MODEL_ORDER_LIST: config?.MODEL_ORDER_LIST ?? [],
			DEFAULT_MODEL_METADATA: metadata,
			DEFAULT_MODEL_PARAMS: Object.fromEntries(configuredParams)
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			config = res;
			promptSuggestions = promptSuggestions.filter((p) => p.content !== '');
			const suggestionsRes = await setDefaultPromptSuggestions(
				localStorage.token,
				useDefaultPromptSuggestions ? null : promptSuggestions,
				promptSuggestionsI18n
			);
			promptSuggestions = suggestionsRes?.suggestions ?? promptSuggestions;
			promptSuggestionsI18n = suggestionsRes?.i18n ?? promptSuggestionsI18n;
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
	<button
		class="flex w-full items-center justify-between gap-2 rounded-md px-1 py-1.5 text-left text-xs font-normal text-gray-600 focus-visible:outline focus-visible:outline-2 dark:text-gray-400"
		type="button"
		aria-expanded={expanded}
		on:click={() => (expanded = !expanded)}
	>
		<ModelSettingsLabel
			label={$i18n.t('settings.admin.models.defaults.modelDefaults.label')}
			description={$i18n.t(
				'Set default capabilities, parameters, and prompt suggestions for models. Individual model settings can override these defaults.'
			)}
		/>
		<ChevronRight
			className={`size-3 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
		/>
	</button>

	{#if expanded}
		{#if loading}
			<div class="py-1 text-xs text-gray-400 dark:text-gray-600">{$i18n.t('Loading...')}</div>
		{:else}
			<div class="space-y-0 pl-3">
				<div>
					<button
						class="flex w-full items-center justify-between gap-2 rounded-md px-1 py-1.5 text-left font-normal focus-visible:outline focus-visible:outline-2"
						type="button"
						aria-expanded={showCapabilities}
						on:click={() => {
							showCapabilities = !showCapabilities;
						}}
					>
						<span class="text-xs text-gray-600 dark:text-gray-400">
							<ModelSettingsLabel
								label={$i18n.t('settings.admin.models.defaults.modelCapabilities.label')}
								description={$i18n.t(
									'Set default capabilities, enabled features, and built-in tools for models. Individual models can override these settings.'
								)}
							/>
						</span>
						<ChevronRight
							className={`size-3 text-gray-400 transition-transform ${showCapabilities ? 'rotate-90' : ''}`}
						/>
					</button>

					{#if showCapabilities}
						<div
							class="max-h-[24rem] overflow-y-auto pb-2 pl-3 pr-1 scrollbar-hover"
							on:click={updateDirty}
							on:change={updateDirty}
						>
							<Capabilities
								bind:capabilities={defaultCapabilities}
								bind:defaultFeatureIds
								bind:builtinTools
							/>
						</div>
					{/if}
				</div>

				<div>
					<button
						class="flex w-full items-center justify-between gap-2 rounded-md px-1 py-1.5 text-left font-normal focus-visible:outline focus-visible:outline-2"
						type="button"
						aria-expanded={showParameters}
						on:click={() => {
							showParameters = !showParameters;
						}}
					>
						<span class="text-xs text-gray-600 dark:text-gray-400">
							<ModelSettingsLabel
								label={$i18n.t('settings.admin.models.defaults.modelParameters.label')}
								description={$i18n.t(
									'Set default generation parameters for models, such as temperature and token limits. Individual models can override these settings.'
								)}
							/>
						</span>
						<ChevronRight
							className={`size-3 text-gray-400 transition-transform ${showParameters ? 'rotate-90' : ''}`}
						/>
					</button>

					{#if showParameters}
						<div
							class="max-h-[24rem] overflow-y-auto pb-2 pl-3 pr-1 scrollbar-hover"
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
						class="flex w-full items-center justify-between gap-2 rounded-md px-1 py-1.5 text-left font-normal focus-visible:outline focus-visible:outline-2"
						type="button"
						aria-expanded={showPromptSuggestions}
						on:click={() => {
							showPromptSuggestions = !showPromptSuggestions;
						}}
					>
						<span class="text-xs text-gray-600 dark:text-gray-400">
							<ModelSettingsLabel
								label={$i18n.t('settings.admin.models.defaults.promptSuggestions.label')}
								description={$i18n.t(
									'Set the starter prompts shown in new chats when a model uses default prompt suggestions.'
								)}
							/>
						</span>
						<ChevronRight
							className={`size-3 text-gray-400 transition-transform ${showPromptSuggestions ? 'rotate-90' : ''}`}
						/>
					</button>

					{#if showPromptSuggestions}
						<div
							class="max-h-[24rem] space-y-2 overflow-y-auto pb-2 pl-3 pr-1 scrollbar-hover"
							on:click={updateDirty}
							on:change={updateDirty}
							on:input={updateDirty}
						>
							<LocalizedPromptSuggestions
								bind:promptSuggestions
								bind:localizedPromptSuggestions={promptSuggestionsI18n}
								locale={editingLocale}
								localeLabel={editingLocaleLabel}
								onChange={() => {
									if (!editingLocale) useDefaultPromptSuggestions = false;
									updateDirty();
								}}
							>
								<svelte:fragment slot="label">
									{#if !editingLocale && !useDefaultPromptSuggestions}
										<button
											type="button"
											class="shrink-0 px-1 py-0.5 text-xs text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
											on:click={resetPromptSuggestions}
										>
											{$i18n.t('Reset to Defaults')}
										</button>
									{/if}
								</svelte:fragment>
								<LanguageModeSelect
									slot="language"
									bind:value={editingLocale}
									{languages}
									translatedLocales={translatedPromptLocales}
									className="w-fit max-w-[10rem]"
								/>
							</LocalizedPromptSuggestions>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>
