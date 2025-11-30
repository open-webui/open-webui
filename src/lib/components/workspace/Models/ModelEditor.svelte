<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick, onDestroy } from 'svelte';
	import { models, tools, functions, knowledge as knowledgeCollections, user } from '$lib/stores';
	import { applyModelAccent, setModelAccentIntensity } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import { getTools } from '$lib/apis/tools';
	import { getFunctions } from '$lib/apis/functions';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';
	import FiltersSelector from '$lib/components/workspace/Models/FiltersSelector.svelte';
	import ActionsSelector from '$lib/components/workspace/Models/ActionsSelector.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import DefaultFiltersSelector from './DefaultFiltersSelector.svelte';
	import DefaultFeatures from './DefaultFeatures.svelte';
	import PromptSuggestions from './PromptSuggestions.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';

	const i18n = getContext('i18n');

	export let onSubmit: Function;
	export let onBack: null | Function = null;

	export let model = null;
	export let edit = false;

	export let preset = true;

	let loading = false;
	let success = false;

	let filesInputElement;
	let inputFiles;

	let showAdvanced = false;
	let showPreview = false;
	let showAccessControlModal = false;

	let loaded = false;

	// ///////////
	// model
	// ///////////

	let id = '';
	let name = '';

	let info = {
		id: '',
		base_model_id: null,
		name: '',
		params: {
			system: ''
		},
		meta: {
			profile_image_url: '',
			description: '',
			capabilities: null,
			model_config: {},

			suggestion_prompts: null,
			tags: [],

			accent_color: null,
			accent_intensity: null
		}
	};

	let params = {};

	let capabilities = {
		vision: true,
		usage: false,
		citations: false,
		user_code_execution: false,
		tooling: false,
		web_search: false,
		image_generation: false
	};

	let knowledge = [];
	let toolIds = [];
	let filterIds = [];
	let actionIds = [];
	let defaultFilterIds = [];
	let defaultFeatureIds = [];

	let enableDescription = false;

	let accessControl = null;

	const addUsage = (modelId) => {
		const _model = $models.find((m) => m.id === modelId);

		if (_model) {
			if (_model?.info?.meta?.capabilities) {
				capabilities = { ...capabilities, ..._model.info.meta.capabilities };
			}
		}
	};

	const submitHandler = async () => {
		loading = true;

		info.id = id;
		info.name = name;

		if (Object.keys(params).length > 0) {
			info.params = params;
		}

		info.meta.capabilities = capabilities;
		info.meta.filterIds = defaultFilterIds;
		info.meta.featureIds = defaultFeatureIds;

		if (knowledge.length > 0) {
			info.meta.knowledge = knowledge;
		} else {
			if (info.meta.knowledge) {
				delete info.meta.knowledge;
			}
		}

		if (toolIds.length > 0) {
			info.meta.toolIds = toolIds;
		} else {
			if (info.meta.toolIds) {
				delete info.meta.toolIds;
			}
		}

		if (filterIds.length > 0) {
			info.meta.filterIds = filterIds;
		} else {
			if (info.meta.filterIds) {
				delete info.meta.filterIds;
			}
		}

		if (actionIds.length > 0) {
			info.meta.actionIds = actionIds;
		} else {
			if (info.meta.actionIds) {
				delete info.meta.actionIds;
			}
		}

		console.log(info);

		const res = await onSubmit(info, accessControl);

		if (res) {
			success = true;
		}

		loading = false;
	};

	onMount(async () => {
		await tools.set(await getTools(localStorage.token));
		await functions.set(await getFunctions(localStorage.token));
		await knowledgeCollections.set(await getKnowledgeBases(localStorage.token));

		if (model) {
			console.log(model);

			id = model.id;
			name = model.name ?? model.id;

			if (model.info) {
				info = { ...info, ...model.info };

				if (model.info.base_model_id) {
					info.base_model_id = model.info.base_model_id;
				}

				params = { ...params, ...(model.info.params ?? {}) };

				if (model.info?.meta?.capabilities) {
					capabilities = { ...capabilities, ...model.info.meta.capabilities };
				}

				if (model.info?.meta?.knowledge) {
					knowledge = [...model.info.meta.knowledge];
				}

				if (model.info?.meta?.toolIds) {
					toolIds = [...model.info.meta.toolIds];
				}

				if (model.info?.meta?.filterIds) {
					filterIds = [...model.info.meta.filterIds];
				}

				if (model.info?.meta?.actionIds) {
					actionIds = [...model.info.meta.actionIds];
				}

				if (model.info?.meta?.filterIds) {
					defaultFilterIds = [...model.info.meta.filterIds];
				}

				if (model.info?.meta?.featureIds) {
					defaultFeatureIds = [...model.info.meta.featureIds];
				}

				if (model.info?.meta?.description) {
					enableDescription = true;
				}
			}

			if (model?.access_control) {
				accessControl = model.access_control;
			}

			console.log(model);
		}

		loaded = true;
	});
</script>

{#if loaded}
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessControl
		accessRoles={['read', 'write']}
		share={$user?.permissions?.sharing?.models || $user?.role === 'admin'}
		sharePublic={$user?.permissions?.sharing?.public_models || $user?.role === 'admin'}
	/>

	{#if onBack}
		<button
			class="flex space-x-1"
			on:click={() => {
				onBack();
			}}
		>
			<div class=" self-center">
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
			<div class=" self-center font-medium text-sm">{$i18n.t('Back')}</div>
		</button>
	{/if}

	<div class="w-full flex flex-col max-w-2xl mx-auto my-10">
		{#if success}
			<div class="w-full flex flex-col items-center justify-center py-20">
				<div
					class="bg-green-500/20 text-green-500 rounded-full size-10 flex items-center justify-center"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="size-6"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
					</svg>
				</div>
				<div class="text-lg font-medium mt-3">
					{$i18n.t('Model {{name}} has been updated successfully', { name: name })}
				</div>
				<button
					class="mt-3 underline text-xs"
					on:click={() => {
						success = false;
					}}
				>
					{$i18n.t('Click here to go back')}
				</button>
			</div>
		{:else}
			<form
				class="flex flex-col"
				on:submit|preventDefault={() => {
					submitHandler();
				}}
			>
				<div class="flex flex-col sm:flex-row sm:gap-4">
					<div class="">
						<input
							bind:this={filesInputElement}
							bind:files={inputFiles}
							type="file"
							hidden
							accept="image/*"
							on:change={() => {
								let reader = new FileReader();
								reader.onload = (event) => {
									let originalImageUrl = `${event.target.result}`;

									info.meta.profile_image_url = originalImageUrl;
								};

								if (
									inputFiles &&
									inputFiles.length > 0 &&
									['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(
										inputFiles[0]['type']
									)
								) {
									reader.readAsDataURL(inputFiles[0]);
								} else {
									console.log(`Unsupported File Type '${inputFiles[0]['type']}'.`);
									inputFiles = null;
								}
							}}
						/>
						<button
							class="group relative rounded-xl w-full sm:size-60 shrink-0 overflow-hidden bg-gray-100 dark:bg-gray-850"
							type="button"
							on:click={() => {
								filesInputElement.click();
							}}
						>
							{#if info.meta.profile_image_url}
								<img
									src={info.meta.profile_image_url}
									alt="model profile"
									class="rounded-xl sm:size-60 size-max object-cover shrink-0"
								/>
							{:else}
								<img
									src="{WEBUI_BASE_URL}/static/favicon.png"
									alt="model profile"
									class=" rounded-xl sm:size-60 size-max object-cover shrink-0"
								/>
							{/if}

							<div class="absolute bottom-0 right-0 z-10">
								<div class="m-1.5">
									<div
										class="shadow-xl p-1 rounded-full border-2 border-white bg-gray-800 text-white group-hover:bg-gray-600 transition dark:border-black dark:bg-white dark:group-hover:bg-gray-200 dark:text-black"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-4"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
											/>
										</svg>
									</div>
								</div>
							</div>
						</button>

						<div class="flex justify-end mt-1">
							<button
								class="text-xs text-gray-500 underline"
								type="button"
								on:click={() => {
									info.meta.profile_image_url = '';
								}}
								>{$i18n.t('Reset Image')}</button
							>
						</div>

					</div>
				</div>

				<div class="w-full">
					<div class="flex flex-col">
						<div class="flex justify-between items-start my-2">
							<div class=" flex flex-col">
								<div class="flex-1">
									<div>
										<input
											class="text-4xl font-medium w-full bg-transparent outline-hidden"
											placeholder={$i18n.t('Model Name')}
											bind:value={name}
											required
										/>
									</div>
								</div>

								<div class="flex-1">
									<div>
										<input
											class="text-xs w-full bg-transparent outline-hidden"
											placeholder={$i18n.t('Model ID')}
											bind:value={id}
											disabled={edit}
											required
										/>
									</div>
								</div>
							</div>

							<div>
								<button
									class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
									type="button"
									on:click={() => {
										showAccessControlModal = true;
									}}
								>
									<LockClosed strokeWidth="2.5" className="size-3.5" />

									<div class="text-sm font-medium shrink-0">
										{$i18n.t('Access')}
									</div>
								</button>
							</div>
						</div>

						{#if preset}
							<div class="mb-1">
								<div class=" text-xs font-medium mb-1 text-gray-500">
									{$i18n.t('Base Model (From)')}
								</div>

								<div>
									<select
										class="text-sm w-full bg-transparent outline-hidden"
										placeholder={$i18n.t('Select a base model (e.g. llama3, gpt-4o)')}
										bind:value={info.base_model_id}
										on:change={(e) => {
											addUsage(e.target.value);
										}}
										required
									>
										<option value={null} class=" text-gray-900"
											>{$i18n.t('Select a base model')}</option
										>
										{#each $models.filter((m) => (model ? m.id !== model.id : true) && !m?.preset && m?.owned_by !== 'arena' && !(m?.direct ?? false)) as model}
											<option value={model.id} class=" text-gray-900">{model.name}</option>
										{/each}
									</select>
								</div>
							</div>
						{/if}

						<div class="mb-1">
							<div class="mb-1 flex w-full justify-between items-center">
								<div class=" self-center text-xs font-medium text-gray-500">
									{$i18n.t('Description')}
								</div>

								<button
									class="p-1 text-xs flex rounded-sm transition"
									type="button"
									aria-pressed={enableDescription ? 'true' : 'false'}
									aria-label={enableDescription
										? $i18n.t('Custom description enabled')
										: $i18n.t('Default description enabled')}
									on:click={() => {
										enableDescription = !enableDescription;
									}}
								>
									{#if !enableDescription}
										<span class="ml-2 self-center">{$i18n.t('Default')}</span>
									{:else}
										<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
									{/if}
								</button>
							</div>

							{#if enableDescription}
								<Textarea
									className=" text-sm w-full bg-transparent outline-hidden resize-none overflow-y-hidden "
									placeholder={$i18n.t('Add a short description about what this model does')}
									bind:value={info.meta.description}
								/>
							{/if}
						</div>

						<div class="my-1">
							<div class="mb-1 flex w-full justify-between items-center">
								<div class=" self-center text-sm font-medium">{$i18n.t('Accent Color')}</div>

								<button
									class="p-1 text-xs flex rounded-sm transition"
									type="button"
									on:click={() => {
										if (info.meta.accent_color) {
											info.meta.accent_color = null;
										} else {
											info.meta.accent_color = '#3b82f6';
										}
									}}
								>
									{#if !info.meta.accent_color}
										<span class="ml-2 self-center">{$i18n.t('Default')}</span>
									{:else}
										<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
									{/if}
								</button>
							</div>

							{#if info.meta.accent_color}
								<div class="flex items-center gap-2">
									<input
										type="color"
										class="w-8 h-8 rounded cursor-pointer border border-gray-200 dark:border-gray-700"
										value={info.meta.accent_color}
										on:input={(e) => {
											info.meta.accent_color = e.target.value;
											applyModelAccent(info.meta.accent_color);
											setModelAccentIntensity(info.meta.accent_intensity ?? 0.35);
										}}
									/>
									<input
										type="text"
										class="text-xs font-mono w-20 px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-transparent"
										value={info.meta.accent_color}
										placeholder="#000000"
										on:input={(e) => {
											let val = e.target.value;
											if (!val.startsWith('#')) val = '#' + val;
											if (/^#[0-9A-Fa-f]{6}$/.test(val)) {
												info.meta.accent_color = val;
												applyModelAccent(info.meta.accent_color);
												setModelAccentIntensity(info.meta.accent_intensity ?? 0.35);
											}
										}}
										on:blur={(e) => {
											let val = e.target.value;
											if (!val.startsWith('#')) val = '#' + val;
											if (!/^#[0-9A-Fa-f]{6}$/.test(val)) {
												e.target.value = info.meta.accent_color;
											}
										}}
									/>
								</div>

								<div class="mt-3">
									<div class="flex items-center justify-between mb-1">
										<span class="text-xs text-gray-500">{$i18n.t('Intensity')}</span>
										<button
											class="text-xs"
											type="button"
											on:click={() => {
												if (info.meta.accent_intensity != null) {
													info.meta.accent_intensity = null;
												} else {
													info.meta.accent_intensity = 0.35;
												}
												applyModelAccent(info.meta.accent_color);
												setModelAccentIntensity(info.meta.accent_intensity ?? 0.35);
											}}
										>
											{#if info.meta.accent_intensity == null}
												<span>{$i18n.t('Default')}</span>
											{:else}
												<span>{Math.round(info.meta.accent_intensity * 100)}%</span>
											{/if}
										</button>
									</div>
									{#if info.meta.accent_intensity != null}
										<input
											type="range"
											class="w-full accent-slider"
											min="0.1"
											max="1"
											step="0.05"
											value={info.meta.accent_intensity}
											style="--slider-color: {info.meta.accent_color}; --slider-opacity: {info.meta.accent_intensity};"
											on:input={(e) => {
												info.meta.accent_intensity = parseFloat(e.target.value);
												applyModelAccent(info.meta.accent_color);
												setModelAccentIntensity(info.meta.accent_intensity);
											}}
										/>
									{/if}
								</div>
							{/if}
						</div>

						<div class="w-full mb-1 max-w-full">
							<div class="">
								<Tags
									tags={info?.meta?.tags ?? []}
									on:delete={(e) => {
										const tagName = e.detail;
										info.meta.tags = info.meta.tags.filter((tag) => tag.name !== tagName);
									}}
									on:add={(e) => {
										const tagName = e.detail;
										if (!(info?.meta?.tags ?? null)) {
											info.meta.tags = [{ name: tagName }];
										} else {
											info.meta.tags = [...info.meta.tags, { name: tagName }];
										}
									}}
								/>
							</div>
						</div>

						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div class="my-2">
							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-medium text-gray-500">
									{$i18n.t('Model Params')}
								</div>
							</div>

							<div class="mt-2">
								<div class="my-1">
									<div class=" text-xs font-medium mb-2">{$i18n.t('System Prompt')}</div>
									<div>
										<Textarea
											className=" text-sm w-full bg-transparent outline-hidden resize-none overflow-y-hidden "
											placeholder={$i18n.t("You're a helpful assistant.")}
											bind:value={params.system}
										/>
									</div>
								</div>

								<div class=" text-xs font-medium">{$i18n.t('Advanced Params')}</div>

								<div class="mt-2">
									<button
										class="flex gap-1 items-center underline text-xs"
										type="button"
										on:click={() => {
											showAdvanced = !showAdvanced;
										}}
									>
										{#if showAdvanced}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="size-4"
											>
												<path
													fill-rule="evenodd"
													d="M9.47 6.47a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 1 1-1.06 1.06L10 8.06l-3.72 3.72a.75.75 0 0 1-1.06-1.06l4.25-4.25Z"
													clip-rule="evenodd"
												/>
											</svg>
											{$i18n.t('Hide')}
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="size-4"
											>
												<path
													fill-rule="evenodd"
													d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
													clip-rule="evenodd"
												/>
											</svg>
											{$i18n.t('Show')}
										{/if}
									</button>
								</div>

								{#if showAdvanced}
									<div class="my-2">
										<AdvancedParams admin={true} custom={true} bind:params />
									</div>
								{/if}
							</div>
						</div>

						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div class="my-2">
							<div class="flex w-full justify-between items-center">
								<div class="flex w-full justify-between items-center">
									<div class=" self-center text-xs font-medium text-gray-500">
										{$i18n.t('Prompts')}
									</div>

									<button
										class="p-1 text-xs flex rounded-sm transition"
										type="button"
										on:click={() => {
											if ((info?.meta?.suggestion_prompts ?? null) === null) {
												info.meta.suggestion_prompts = [{ content: '' }];
											} else {
												info.meta.suggestion_prompts = null;
											}
										}}
									>
										{#if (info?.meta?.suggestion_prompts ?? null) === null}
											<span class="ml-2 self-center">{$i18n.t('Default')}</span>
										{:else}
											<span class="ml-2 self-center"> {$i18n.t('Custom')}</span>
										{/if}
									</button>
								</div>
							</div>

							{#if info?.meta?.suggestion_prompts}
								<PromptSuggestions bind:promptSuggestions={info.meta.suggestion_prompts} />
							{/if}
						</div>

						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div class="my-2">
							<Knowledge bind:selectedItems={knowledge} />
						</div>

						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div class="my-2">
							<ToolsSelector bind:selectedToolIds={toolIds} tools={$tools} />
						</div>

						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div class="my-2">
							<FiltersSelector
								bind:selectedFilterIds={filterIds}
								filters={$functions.filter((func) => func.type === 'filter')}
							/>
						</div>

						{#if filterIds.length > 0}
							<div class="my-2">
								<DefaultFiltersSelector
									{filterIds}
									bind:selectedFilterIds={defaultFilterIds}
									filters={$functions.filter((func) => func.type === 'filter')}
								/>
							</div>
						{/if}

						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div class="my-2">
							<ActionsSelector
								bind:selectedActionIds={actionIds}
								actions={$functions.filter((func) => func.type === 'action')}
							/>
						</div>

						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div class="my-2">
							<Capabilities bind:capabilities />
						</div>

						{#if Object.keys(capabilities).filter((key) => capabilities[key]).length > 0}
							{@const availableFeatures = Object.entries(capabilities)
								.filter(
									([key, value]) =>
										value && ['web_search', 'image_generation', 'user_code_execution'].includes(key)
								)
								.map(([key]) => key)}

							{#if availableFeatures.length > 0}
								<div class="my-2">
									<DefaultFeatures {availableFeatures} bind:featureIds={defaultFeatureIds} />
								</div>
							{/if}
						{/if}

						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

						<div class="my-2 flex justify-end">
							<button
								class=" text-sm px-3 py-2 transition rounded-lg {loading
									? ' cursor-not-allowed bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'
									: 'bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'} flex w-full justify-center"
								type="submit"
								disabled={loading}
							>
								<div class=" self-center font-medium">
									{#if edit}
										{$i18n.t('Save & Update')}
									{:else}
										{$i18n.t('Save & Create')}
									{/if}
								</div>

								{#if loading}
									<div class="ml-1.5 self-center">
										<Spinner />
									</div>
								{/if}
							</button>
						</div>

						<div class="my-2 text-gray-300 dark:text-gray-700 pb-20">
							<div class="flex w-full justify-between mb-2">
								<div class=" self-center text-sm font-medium">{$i18n.t('JSON Preview')}</div>

								<button
									class="p-1 px-3 text-xs flex rounded-sm transition"
									type="button"
									on:click={() => {
										showPreview = !showPreview;
									}}
								>
									{#if showPreview}
										<span class="ml-2 self-center">{$i18n.t('Hide')}</span>
									{:else}
										<span class="ml-2 self-center">{$i18n.t('Show')}</span>
									{/if}
								</button>
							</div>

							{#if showPreview}
								<div>
									<textarea
										class="text-xs rounded-lg w-full bg-gray-100 dark:bg-gray-850 outline-hidden resize-none overflow-y-hidden"
										rows="10"
										value={JSON.stringify(info, null, 2)}
										disabled
										readonly
									/>
								</div>
							{/if}
						</div>
					</div>
				</div>
			</form>
		{/if}
	</div>
{/if}
