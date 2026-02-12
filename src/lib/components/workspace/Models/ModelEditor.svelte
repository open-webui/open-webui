<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { models, tools, functions, user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import { getTools } from '$lib/apis/tools';
	import { getFunctions } from '$lib/apis/functions';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';
	import SkillsSelector from '$lib/components/workspace/Models/SkillsSelector.svelte';
	import FiltersSelector from '$lib/components/workspace/Models/FiltersSelector.svelte';
	import ActionsSelector from '$lib/components/workspace/Models/ActionsSelector.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import DefaultFiltersSelector from './DefaultFiltersSelector.svelte';
	import DefaultFeatures from './DefaultFeatures.svelte';
	import BuiltinTools from './BuiltinTools.svelte';
	import PromptSuggestions from './PromptSuggestions.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import { updateModelAccessGrants } from '$lib/apis/models';

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

	let enableDescription = true;

	$: if (!edit) {
		if (name) {
			id = name
				.replace(/\s+/g, '-')
				.replace(/[^a-zA-Z0-9-]/g, '')
				.toLowerCase();
		}
	}

	let system = '';
	let info = {
		id: '',
		base_model_id: null,
		name: '',
		meta: {
			profile_image_url: `${WEBUI_BASE_URL}/static/favicon.png`,
			description: '',
			suggestion_prompts: null,
			tags: []
		},
		params: {
			system: ''
		}
	};

	let params = {
		system: ''
	};

	let knowledge = [];
	let toolIds = [];
	let skillIds = [];

	let filterIds = [];
	let defaultFilterIds = [];

	let capabilities = {
		file_context: true,
		vision: true,
		file_upload: true,
		web_search: true,
		image_generation: true,
		code_interpreter: true,
		citations: true,
		status_updates: true,
		usage: undefined,
		builtin_tools: true
	};
	let defaultFeatureIds = [];
	let builtinTools = {};

	let actionIds = [];
	let accessGrants = [];
	let tts = { voice: '' };

	const submitHandler = async () => {
		loading = true;

		info.id = id;
		info.name = name;

		if (id === '') {
			toast.error($i18n.t('Model ID is required.'));
			loading = false;

			return;
		}

		if (name === '') {
			toast.error($i18n.t('Model Name is required.'));
			loading = false;

			return;
		}

		if (knowledge.some((item) => item.status === 'uploading')) {
			toast.error($i18n.t('Please wait until all files are uploaded.'));
			loading = false;

			return;
		}

		info.params = { ...info.params, ...params };

		info.access_grants = accessGrants;
		info.meta.capabilities = capabilities;

		if (enableDescription) {
			info.meta.description = info.meta.description.trim() === '' ? null : info.meta.description;
		} else {
			info.meta.description = null;
		}

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

		if (skillIds.length > 0) {
			info.meta.skillIds = skillIds;
		} else {
			if (info.meta.skillIds) {
				delete info.meta.skillIds;
			}
		}

		if (filterIds.length > 0) {
			info.meta.filterIds = filterIds;
		} else {
			if (info.meta.filterIds) {
				delete info.meta.filterIds;
			}
		}

		if (defaultFilterIds.length > 0) {
			info.meta.defaultFilterIds = defaultFilterIds;
		} else {
			if (info.meta.defaultFilterIds) {
				delete info.meta.defaultFilterIds;
			}
		}

		if (actionIds.length > 0) {
			info.meta.actionIds = actionIds;
		} else {
			if (info.meta.actionIds) {
				delete info.meta.actionIds;
			}
		}

		if (defaultFeatureIds.length > 0) {
			info.meta.defaultFeatureIds = defaultFeatureIds;
		} else {
			if (info.meta.defaultFeatureIds) {
				delete info.meta.defaultFeatureIds;
			}
		}

		if (Object.keys(builtinTools).length > 0) {
			info.meta.builtinTools = builtinTools;
		} else {
			if (info.meta.builtinTools) {
				delete info.meta.builtinTools;
			}
		}

		if (tts.voice !== '') {
			if (!info.meta.tts) info.meta.tts = {};
			info.meta.tts.voice = tts.voice;
		} else {
			if (info.meta.tts?.voice) {
				delete info.meta.tts.voice;
				if (Object.keys(info.meta.tts).length === 0) {
					delete info.meta.tts;
				}
			}
		}

		info.params.system = system.trim() === '' ? null : system;
		info.params.stop = params.stop ? params.stop.split(',').filter((s) => s.trim()) : null;
		Object.keys(info.params).forEach((key) => {
			if (info.params[key] === '' || info.params[key] === null) {
				delete info.params[key];
			}
		});

		await onSubmit(info);

		loading = false;
		success = false;
	};

	onMount(async () => {
		await tools.set(await getTools(localStorage.token));
		await functions.set(await getFunctions(localStorage.token));

		// Scroll to top 'workspace-container' element
		const workspaceContainer = document.getElementById('workspace-container');
		if (workspaceContainer) {
			workspaceContainer.scrollTop = 0;
		}

		if (model) {
			name = model.name;
			await tick();

			id = model.id;

			enableDescription = model?.meta?.description !== null;

			if (model.base_model_id) {
				const base_model = $models
					.filter((m) => !m?.preset && !(m?.arena ?? false))
					.find((m) => [model.base_model_id, `${model.base_model_id}:latest`].includes(m.id));

				console.log('base_model', base_model);

				if (base_model) {
					model.base_model_id = base_model.id;
				} else {
					model.base_model_id = null;
				}
			}

			system = model?.params?.system ?? '';

			params = { ...params, ...model?.params };
			params.stop = params?.stop
				? (typeof params.stop === 'string' ? params.stop.split(',') : (params?.stop ?? [])).join(
						','
					)
				: null;

			knowledge = (model?.meta?.knowledge ?? []).map((item) => {
				if (item?.collection_name && item?.type !== 'file') {
					return {
						id: item.collection_name,
						name: item.name,
						legacy: true
					};
				} else if (item?.collection_names) {
					return {
						name: item.name,
						type: 'collection',
						collection_names: item.collection_names,
						legacy: true
					};
				} else {
					return item;
				}
			});

			toolIds = model?.meta?.toolIds ?? [];
			skillIds = model?.meta?.skillIds ?? [];
			filterIds = model?.meta?.filterIds ?? [];
			defaultFilterIds = model?.meta?.defaultFilterIds ?? [];
			actionIds = model?.meta?.actionIds ?? [];

			capabilities = { ...capabilities, ...(model?.meta?.capabilities ?? {}) };
			defaultFeatureIds = model?.meta?.defaultFeatureIds ?? [];
			builtinTools = model?.meta?.builtinTools ?? {};
			tts = { voice: model?.meta?.tts?.voice ?? '' };

			accessGrants = model?.access_grants ?? [];

			info = {
				...info,
				...JSON.parse(
					JSON.stringify(
						model
							? model
							: {
									id: model.id,
									name: model.name
								}
					)
				)
			};

			console.log(model);
		}

		loaded = true;
	});
</script>

{#if loaded}
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessGrants
		accessRoles={preset ? ['read', 'write'] : ['read']}
		share={$user?.permissions?.sharing?.models || $user?.role === 'admin'}
		sharePublic={$user?.permissions?.sharing?.public_models || $user?.role === 'admin' || edit}
		onChange={async () => {
			if (edit && model?.id) {
				try {
					await updateModelAccessGrants(localStorage.token, model.id, accessGrants);
					toast.success($i18n.t('Saved'));
				} catch (error) {
					toast.error(`${error}`);
				}
			}
		}}
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
					class="h-4 w-4"
				>
					<path
						fill-rule="evenodd"
						d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<div class=" self-center text-sm font-medium">{$i18n.t('Back')}</div>
		</button>
	{/if}

	<div class="w-full max-h-full flex justify-center">
		<input
			bind:this={filesInputElement}
			bind:files={inputFiles}
			type="file"
			hidden
			accept="image/*"
			on:change={() => {
				let reader = new FileReader();
				reader.onload = (event) => {
					let originalImageUrl = `${event.target?.result}`;

					// For animated formats (gif, webp), skip resizing to preserve animation
					const fileType = (inputFiles[0] as any)?.['type'];
					if (fileType === 'image/gif' || fileType === 'image/webp') {
						info.meta.profile_image_url = originalImageUrl;
						inputFiles = null;
						filesInputElement.value = '';
						return;
					}

					const img = new Image();
					img.src = originalImageUrl;

					img.onload = function () {
						const canvas = document.createElement('canvas');
						const ctx = canvas.getContext('2d');

						// Calculate the aspect ratio of the image
						const aspectRatio = img.width / img.height;

						// Calculate the new width and height to fit within 100x100
						let newWidth, newHeight;
						if (aspectRatio > 1) {
							newWidth = 250 * aspectRatio;
							newHeight = 250;
						} else {
							newWidth = 250;
							newHeight = 250 / aspectRatio;
						}

						// Set the canvas size
						canvas.width = 250;
						canvas.height = 250;

						// Calculate the position to center the image
						const offsetX = (250 - newWidth) / 2;
						const offsetY = (250 - newHeight) / 2;

						// Draw the image on the canvas
						ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

						// Get the base64 representation of the compressed image
						const compressedSrc = canvas.toDataURL('image/webp', 0.8);

						// Display the compressed image
						info.meta.profile_image_url = compressedSrc;

						inputFiles = null;
						filesInputElement.value = '';
					};
				};

				if (
					inputFiles &&
					inputFiles.length > 0 &&
					['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/svg+xml'].includes(
						(inputFiles[0] as any)?.['type']
					)
				) {
					reader.readAsDataURL(inputFiles[0]);
				} else {
					console.log(`Unsupported File Type '${(inputFiles[0] as any)?.['type']}'.`);
					inputFiles = null;
				}
			}}
		/>

		{#if !edit || (edit && model)}
			<form
				class="flex flex-col md:flex-row w-full gap-3 md:gap-6"
				on:submit|preventDefault={() => {
					submitHandler();
				}}
			>
				<div class="w-full px-1">
					<div class="flex flex-col md:flex-row gap-4 w-full">
						<div class="self-center md:self-start flex justify-center my-2 shrink-0">
							<div class="self-center">
								<button
									class="rounded-xl flex shrink-0 items-center {info.meta.profile_image_url !==
									`${WEBUI_BASE_URL}/static/favicon.png`
										? 'bg-transparent'
										: 'bg-white'} shadow-xl group relative"
									type="button"
									on:click={() => {
										filesInputElement.click();
									}}
								>
									{#if info.meta.profile_image_url}
										<img
											src={info.meta.profile_image_url}
											alt="model profile"
											class="rounded-xl size-60 object-cover shrink-0"
										/>
									{:else}
										<img
											src="{WEBUI_BASE_URL}/static/favicon.png"
											alt="model profile"
											class=" rounded-xl size-60 object-cover shrink-0"
										/>
									{/if}

									<div class="absolute bottom-0 right-0 z-10">
										<div class="m-1.5">
											<div
												class="shadow-xl p-1 rounded-full border-2 border-white bg-gray-800 text-white group-hover:bg-gray-600 transition dark:border-black dark:bg-white dark:group-hover:bg-gray-200 dark:text-black"
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="size-5"
												>
													<path
														fill-rule="evenodd"
														d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm10.5 5.707a.5.5 0 0 0-.146-.353l-1-1a.5.5 0 0 0-.708 0L9.354 9.646a.5.5 0 0 1-.708 0L6.354 7.354a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0-.146.353V12a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V9.707ZM12 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
														clip-rule="evenodd"
													/>
												</svg>
											</div>
										</div>
									</div>

									<div
										class="absolute top-0 bottom-0 left-0 right-0 bg-white dark:bg-black rounded-lg opacity-0 group-hover:opacity-20 transition"
									></div>
								</button>

								<div class="flex w-full mt-1 justify-end">
									<button
										class="px-2 py-1 text-gray-500 rounded-lg text-xs"
										on:click={() => {
											info.meta.profile_image_url = `${WEBUI_BASE_URL}/static/favicon.png`;
										}}
										type="button"
									>
										{$i18n.t('Reset Image')}</button
									>
								</div>
							</div>
						</div>

						<div class="flex flex-col w-full flex-1">
							<div class="flex justify-between items-start my-2">
								<div class=" flex flex-col w-full">
									<div class="flex-1 w-full">
										<input
											class="text-4xl font-medium w-full bg-transparent outline-hidden"
											placeholder={$i18n.t('Model Name')}
											bind:value={name}
											required
										/>
									</div>

									<div class="flex-1 w-full">
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

								<div class="shrink-0">
									<button
										class="bg-gray-50 shrink-0 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
										type="button"
										on:click={() => {
											showAccessControlModal = true;
										}}
									>
										<LockClosed strokeWidth="2.5" className="size-3.5 shrink-0" />

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
											class="dark:bg-gray-900 text-sm w-full bg-transparent outline-hidden"
											placeholder={$i18n.t('Select a base model (e.g. llama3, gpt-4o)')}
											bind:value={info.base_model_id}
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
						</div>
					</div>

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
										placeholder={$i18n.t(
											'Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.'
										)}
										rows={4}
										bind:value={system}
									/>
								</div>
							</div>

							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-medium">
									{$i18n.t('Advanced Params')}
								</div>

								<button
									class="p-1 px-3 text-xs flex rounded-sm transition"
									type="button"
									on:click={() => {
										showAdvanced = !showAdvanced;
									}}
								>
									{#if showAdvanced}
										<span class="ml-2 self-center">{$i18n.t('Hide')}</span>
									{:else}
										<span class="ml-2 self-center">{$i18n.t('Show')}</span>
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
											info.meta.suggestion_prompts = [{ content: '', title: ['', ''] }];
										} else {
											info.meta.suggestion_prompts = null;
										}
									}}
								>
									{#if (info?.meta?.suggestion_prompts ?? null) === null}
										<span class="ml-2 self-center">{$i18n.t('Default')}</span>
									{:else}
										<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
									{/if}
								</button>
							</div>
						</div>

						{#if info?.meta?.suggestion_prompts}
							<PromptSuggestions bind:promptSuggestions={info.meta.suggestion_prompts} />
						{/if}
					</div>

					<div class="my-4">
						<Knowledge bind:selectedItems={knowledge} />
					</div>

					<div class="my-4">
						<ToolsSelector bind:selectedToolIds={toolIds} tools={$tools ?? []} />
					</div>

					<div class="my-4">
						<SkillsSelector bind:selectedSkillIds={skillIds} />
					</div>

					{#if ($functions ?? []).filter((func) => func.type === 'filter').length > 0 || ($functions ?? []).filter((func) => func.type === 'action').length > 0}
						<hr class=" border-gray-100/30 dark:border-gray-850/30 my-4" />

						{#if ($functions ?? []).filter((func) => func.type === 'filter').length > 0}
							<div class="my-4">
								<FiltersSelector
									bind:selectedFilterIds={filterIds}
									filters={($functions ?? []).filter((func) => func.type === 'filter')}
								/>
							</div>

							{@const toggleableFilters = $functions.filter(
								(func) =>
									func.type === 'filter' &&
									(filterIds.includes(func.id) || func?.is_global) &&
									func?.meta?.toggle
							)}

							{#if toggleableFilters.length > 0}
								<div class="my-4">
									<DefaultFiltersSelector
										bind:selectedFilterIds={defaultFilterIds}
										filters={toggleableFilters}
									/>
								</div>
							{/if}
						{/if}

						{#if ($functions ?? []).filter((func) => func.type === 'action').length > 0}
							<div class="my-4">
								<ActionsSelector
									bind:selectedActionIds={actionIds}
									actions={($functions ?? []).filter((func) => func.type === 'action')}
								/>
							</div>
						{/if}
					{/if}

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-4" />

					<div class="my-4">
						<Capabilities bind:capabilities />
					</div>

					{#if Object.keys(capabilities).filter((key) => capabilities[key]).length > 0}
						{@const availableFeatures = Object.entries(capabilities)
							.filter(
								([key, value]) =>
									value && ['web_search', 'code_interpreter', 'image_generation'].includes(key)
							)
							.map(([key, value]) => key)}

						{#if availableFeatures.length > 0}
							<div class="my-4">
								<DefaultFeatures {availableFeatures} bind:featureIds={defaultFeatureIds} />
							</div>
						{/if}
					{/if}

					{#if capabilities.builtin_tools}
						<div class="my-4">
							<BuiltinTools bind:builtinTools />
						</div>
					{/if}

					<div class="my-4">
						<div class="flex w-full justify-between mb-1">
							<div class="self-center text-xs font-medium text-gray-500">
								{$i18n.t('TTS Voice')}
							</div>
						</div>
						<input
							class="w-full text-sm bg-transparent outline-hidden"
							type="text"
							bind:value={tts.voice}
							placeholder={$i18n.t('e.g. alloy, echo, shimmer')}
						/>
					</div>

					<hr class=" border-gray-100/30 dark:border-gray-850/30 my-4" />

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
									class="text-sm w-full bg-transparent outline-hidden resize-none"
									rows="10"
									value={JSON.stringify(info, null, 2)}
									disabled
									readonly
								/>
							</div>
						{/if}
					</div>
				</div>
			</form>
		{/if}
	</div>
{/if}
