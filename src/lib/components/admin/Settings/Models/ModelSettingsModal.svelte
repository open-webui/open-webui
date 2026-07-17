<script>
	import { toast } from 'svelte-sonner';

	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { config as _config } from '$lib/stores';
	import { DEFAULT_CAPABILITIES } from '$lib/constants';
	import { getModelsConfig, setModelsConfig, setDefaultPromptSuggestions } from '$lib/apis/configs';
	import { getBackendConfig } from '$lib/apis';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';

	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import DefaultFeatures from '$lib/components/workspace/Models/DefaultFeatures.svelte';
	import BuiltinTools from '$lib/components/workspace/Models/BuiltinTools.svelte';
	import PromptSuggestions from '$lib/components/workspace/Models/PromptSuggestions.svelte';

	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';

	export let show = false;
	export let initHandler = () => {};

	let config = null;

	let modelIds = [];

	let loading = false;
	let showDefaultCapabilities = false;
	let showDefaultParams = false;
	let showDefaultPromptSuggestions = false;

	let defaultCapabilities = {};
	let defaultFeatureIds = [];
	let defaultParams = {};
	let builtinTools = {};
	let promptSuggestions = [];

	$: if (show) {
		init();
	}
	const init = async () => {
		config = await getModelsConfig(localStorage.token);

		modelIds = config.MODEL_ORDER_LIST || [];

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

		promptSuggestions = $_config?.default_prompt_suggestions ?? [];
	};
	const submitHandler = async () => {
		loading = true;

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
			DEFAULT_MODEL_PARAMS: Object.fromEntries(
				Object.entries(defaultParams).filter(([_, v]) => v !== null && v !== '' && v !== undefined)
			)
		});

		if (res) {
			promptSuggestions = promptSuggestions.filter((p) => p.content !== '');
			promptSuggestions = await setDefaultPromptSuggestions(localStorage.token, promptSuggestions);
			await _config.set(await getBackendConfig());

			toast.success($i18n.t('Models configuration saved successfully'));
			initHandler();
			show = false;
		} else {
			toast.error($i18n.t('Failed to save models configuration'));
		}

		loading = false;
	};

	onMount(async () => {
		init();
	});
</script>

<Modal size="lg" bind:show className="bg-white dark:bg-gray-900 rounded-4xl">
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-4 pt-3 pb-1">
			<div class=" text-sm font-medium self-center">
				{$i18n.t('Settings')}
			</div>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				{#if config}
					<form
						class="flex flex-col w-full"
						on:submit|preventDefault={() => {
							submitHandler();
						}}
					>
						<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
							<div
								id="admin-settings-tabs-container"
								class="tabs flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-normal text-left scrollbar-none"
							>
								<button
									class="px-0.5 py-1 max-w-fit w-fit rounded-lg flex-1 lg:flex-none flex text-right transition"
									type="button"
								>
									<div class=" self-center mr-2">
										<AdjustmentsHorizontal />
									</div>
									<div class=" self-center">{$i18n.t('Defaults')}</div>
								</button>
							</div>

							<div class="flex-1 mt-1 lg:mt-1 lg:h-[30rem] lg:max-h-[30rem] flex flex-col min-w-0">
								<div class="w-full h-full overflow-y-auto overflow-x-hidden scrollbar-hidden">
									<div>
										<button
											class="flex w-full justify-between items-center"
											type="button"
											on:click={() => {
												showDefaultPromptSuggestions = !showDefaultPromptSuggestions;
											}}
										>
											<div class="text-xs text-gray-500 font-normal">
												{$i18n.t('Prompt Suggestions')}
											</div>
											<div>
												{#if showDefaultPromptSuggestions}
													<ChevronUp className="size-3" />
												{:else}
													<ChevronDown className="size-3" />
												{/if}
											</div>
										</button>

										{#if showDefaultPromptSuggestions}
											<div class="mt-2">
												<PromptSuggestions bind:promptSuggestions />

												{#if promptSuggestions.length > 0}
													<div class="text-xs text-left w-full mt-2 text-gray-500">
														{$i18n.t(
															'Adjusting these settings will apply changes universally to all users.'
														)}
													</div>
												{/if}
											</div>
										{/if}
									</div>

									<hr class=" border-gray-50 dark:border-gray-800/10 my-2.5 w-full" />

									<div>
										<button
											class="flex w-full justify-between items-center"
											type="button"
											on:click={() => {
												showDefaultCapabilities = !showDefaultCapabilities;
											}}
										>
											<div class="text-xs text-gray-500 font-normal">
												{$i18n.t('Model Capabilities')}
											</div>
											<div>
												{#if showDefaultCapabilities}
													<ChevronUp className="size-3" />
												{:else}
													<ChevronDown className="size-3" />
												{/if}
											</div>
										</button>

										{#if showDefaultCapabilities}
											<div class="mt-2">
												<Capabilities bind:capabilities={defaultCapabilities} />

												{#if Object.keys(defaultCapabilities).filter((key) => defaultCapabilities[key]).length > 0}
													{@const availableFeatures = Object.entries(defaultCapabilities)
														.filter(
															([key, value]) =>
																value &&
																['web_search', 'code_interpreter', 'image_generation'].includes(key)
														)
														.map(([key, value]) => key)}

													{#if availableFeatures.length > 0}
														<div class="mt-4">
															<DefaultFeatures
																{availableFeatures}
																bind:featureIds={defaultFeatureIds}
															/>
														</div>
													{/if}
												{/if}

												{#if defaultCapabilities.builtin_tools}
													<div class="mt-4">
														<BuiltinTools bind:builtinTools />
													</div>
												{/if}
											</div>
										{/if}
									</div>

									<hr class=" border-gray-50 dark:border-gray-800/10 my-2.5 w-full" />

									<div>
										<button
											class="flex w-full justify-between items-center"
											type="button"
											on:click={() => {
												showDefaultParams = !showDefaultParams;
											}}
										>
											<div class="text-xs text-gray-500 font-normal">
												{$i18n.t('Model Parameters')}
											</div>
											<div>
												{#if showDefaultParams}
													<ChevronUp className="size-3" />
												{:else}
													<ChevronDown className="size-3" />
												{/if}
											</div>
										</button>

										{#if showDefaultParams}
											<div class="mt-2">
												<AdvancedParams admin={true} custom={true} bind:params={defaultParams} />
											</div>
										{/if}
									</div>
								</div>

								<div class="flex justify-end items-center pt-3 text-sm font-normal gap-1.5">
									<button
										class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 whitespace-nowrap {loading
											? ' cursor-not-allowed'
											: ''}"
										type="submit"
										disabled={loading}
									>
										{$i18n.t('Save')}

										{#if loading}
											<span class="shrink-0">
												<Spinner />
											</span>
										{/if}
									</button>
								</div>
							</div>
						</div>
					</form>
				{:else}
					<div>
						<Spinner className="size-5" />
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
