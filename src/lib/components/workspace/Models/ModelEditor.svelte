<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { models, tools, functions, knowledge as knowledgeCollections, user } from '$lib/stores';
	import { get } from 'svelte/store';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';
	import FiltersSelector from '$lib/components/workspace/Models/FiltersSelector.svelte';
	import ActionsSelector from '$lib/components/workspace/Models/ActionsSelector.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import { getTools } from '$lib/apis/tools';
	import { getFunctions } from '$lib/apis/functions';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { getToolValvesSpecById } from '$lib/apis/tools';
	import { getFunctionValvesSpecById } from '$lib/apis/functions';
	import { getUserGroups } from '$lib/apis/users';
	import AccessControl from '../common/AccessControl.svelte';
	import { stringify } from 'postcss';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let onSubmit: Function;
	export let onBack: null | Function = null;

	let userGroups = [];
	let userGroupsLoaded = false;

	$: hasInspectAccess =
		edit &&
		loaded &&
		userGroupsLoaded &&
		(() => {
			if (!loaded || !userGroupsLoaded || !accessControl || !$user) {
				return false;
			}

			if (!accessControl?.inspect?.group_ids?.length) {
				return false;
			}

			const isModelCreator = accessControl?.write?.user_ids?.includes($user.id);
			if (isModelCreator) {
				return false;
			}

			const userGroupIds = userGroups.map((group) => group.id);

			const hasInspectAccess = userGroupIds.some((groupId) => {
				return accessControl.inspect.group_ids.includes(groupId);
			});

			return hasInspectAccess;
		})();

	export let model = null;
	export let edit = false;

	export let preset = true;

	let loading = false;
	let success = false;

	let filesInputElement;
	let inputFiles;

	let showAdvanced = false;
	let showPreview = false;

	let loaded = false;

	// ///////////
	// model
	// ///////////

	let id = '';
	let name = '';

	let enableDescription = true;
	let enableCustomSuggestions = false;

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
			profile_image_url: '/static/favicon.png',
			description: '',
			suggestion_prompts: null,
			tags: [],
			valves: {
				functions: {},
				tools: {}
			}
		},
		params: {
			system: ''
		}
	};

	let params = {
		system: ''
	};
	let capabilities = {
		vision: true,
		file_upload: true,
		web_search: true,
		image_generation: true,
		code_interpreter: true,
		citations: true,
		usage: undefined
	};

	let knowledge = [];
	let toolIds = [];
	let filterIds = [];
	let actionIds = [];
	let customSuggestionPrompts = [];
	let toolValvesSpecs = {};
	let functionValvesSpecs = {};
	let functionValves = {};
	let toolValves = {};

	let accessControl = {};
	let accessControlComponent;

	const addUsage = (base_model_id) => {
		const baseModel = $models.find((m) => m.id === base_model_id);

		if (baseModel) {
			if (baseModel.owned_by === 'openai') {
				capabilities.usage = baseModel?.meta?.capabilities?.usage ?? false;
			} else {
				delete capabilities.usage;
			}
			capabilities = capabilities;
		}
	};

	const submitHandler = async () => {
		loading = true;

		info.id = id;
		info.name = name;
		info.meta.valves = {};

		console.log(`submitting with new toolValves: ${JSON.stringify(toolValves)}`);
		console.log(`submitting with new functionValves: ${JSON.stringify(functionValves)}`);

		if (id === '') {
			toast.error('Model ID is required.');
		}

		if (name === '') {
			toast.error('Model Name is required.');
		}

		info.params = { ...info.params, ...params };

		if (hasInspectAccess && model?.access_control) {
			info.access_control = model.access_control;
		} else {
			info.access_control = accessControl;
		}

		if (info.access_control && info.access_control !== null) {
			if (!info.access_control.write) {
				info.access_control.write = { group_ids: [], user_ids: [] };
			}
			if (!info.access_control.write.user_ids) {
				info.access_control.write.user_ids = [];
			}

			let modelCreatorId;
			if (edit && model?.user_id) {
				modelCreatorId = model.user_id;
			} else {
				const hadExistingUserIds = info.access_control.write.user_ids.length > 0;
				info.access_control.write.user_ids = [];
				modelCreatorId = $user?.id;
			}

			if (modelCreatorId && !info.access_control.write.user_ids.includes(modelCreatorId)) {
				info.access_control.write.user_ids.push(modelCreatorId);
			}
		}

		info.meta.capabilities = capabilities;

		if (enableDescription) {
			info.meta.description = info.meta.description.trim() === '' ? null : info.meta.description;
		} else {
			info.meta.description = null;
		}

		if (enableCustomSuggestions) {
			const validSuggestions = customSuggestionPrompts.filter(
				(prompt) => prompt.content.trim() !== ''
			);
			info.meta.suggestion_prompts = validSuggestions.length > 0 ? validSuggestions : null;
		} else {
			info.meta.suggestion_prompts = null;
		}

		if (knowledge.length > 0) {
			info.meta.knowledge = knowledge;
		} else {
			if (info.meta.knowledge) {
				delete info.meta.knowledge;
			}
		}

		info.meta.valves.tools = toolValves;
		if (toolIds.length > 0) {
			info.meta.toolIds = toolIds;
		} else {
			if (info.meta.toolIds) {
				delete info.meta.toolIds;
			}
		}

		info.meta.valves.functions = functionValves;
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

		info.params.system = system.trim() === '' ? null : system;
		info.params.stop = params.stop ? params.stop.split(',').filter((s) => s.trim()) : null;
		Object.keys(info.params).forEach((key) => {
			if (info.params[key] === '' || info.params[key] === null) {
				delete info.params[key];
			}
		});
		// iterate through all valve settings for both functions and tools, and remove empty settings (aka things that got set back to default)
		Object.keys(info.meta.valves).forEach((valveType) => {
			Object.keys(info.meta.valves[valveType]).forEach((functionId) => {
				Object.keys(info.meta.valves[valveType][functionId]).forEach((key) => {
					if (info.meta.valves[valveType][functionId][key] === null) {
						delete info.meta.valves[valveType][functionId][key];
					}
				});
			});
		});

		await onSubmit(info);

		loading = false;
		success = false;
	};

	onMount(async () => {
		// Fetch user groups first
		try {
			userGroups = await getUserGroups(localStorage.token);
			console.log('User groups loaded:', userGroups);
			userGroupsLoaded = true;
		} catch (error) {
			console.error('Error loading user groups:', error);
			userGroups = [];
			userGroupsLoaded = true;
		}

		await tools.set(await getTools(localStorage.token));
		await functions.set(await getFunctions(localStorage.token));
		await knowledgeCollections.set(await getKnowledgeBases(localStorage.token));

		// Populate the tool valve specs
		try {
			const currentTools = get(tools) ?? [];
			const toolValvePromises = currentTools.map((tool) =>
				getToolValvesSpecById(localStorage.token, tool.id)
			);
			const resolvedToolValves = await Promise.all(toolValvePromises);
			console.log(`resolvedToolValves: ${resolvedToolValves}`);

			// Convert array of results to an object with tool IDs as keys
			toolValvesSpecs = resolvedToolValves.reduce((acc, spec, index) => {
				if (spec) {
					console.log(
						`setting index ${index} to ${spec} from ${JSON.stringify(currentTools[index])}`
					);
					acc[currentTools[index].id] = spec;
				}
				return acc;
			}, {});
			console.log(`toolValvesSpecs: ${JSON.stringify(toolValvesSpecs)}`);

			// Initialize tool valves with default values from specs for the selected tools
			toolValves = model?.meta?.valves?.tools ?? {};
		} catch (error) {
			console.error('Error loading tool valve specs:', error);
		}

		// Populate the function valve specs
		try {
			// Use get() to access the store's current value in non-reactive context
			const currentFunctions = get(functions) ?? [];
			console.log(JSON.stringify(currentFunctions));
			const functionValvePromises = currentFunctions.map((func) =>
				getFunctionValvesSpecById(localStorage.token, func.id)
			);
			const resolvedFunctionValves = await Promise.all(functionValvePromises);
			console.log(resolvedFunctionValves);

			// Convert array of results to an object with function IDs as keys
			functionValvesSpecs = resolvedFunctionValves.reduce((acc, spec, index) => {
				if (spec) {
					acc[currentFunctions[index].id] = spec;
				}
				return acc;
			}, {});
			console.log(`functionValvesSpecs: ${JSON.stringify(functionValvesSpecs)}`);
			functionValves = model?.meta?.valves?.functions ?? {};
		} catch (error) {
			console.error('Error loading function valve specs:', error);
		}

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
			enableCustomSuggestions = model?.meta?.suggestion_prompts !== null;
			customSuggestionPrompts = model?.meta?.suggestion_prompts || [{ content: '' }];

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

			toolIds = model?.meta?.toolIds ?? [];
			filterIds = model?.meta?.filterIds ?? [];
			actionIds = model?.meta?.actionIds ?? [];
			knowledge = (model?.meta?.knowledge ?? []).map((item) => {
				if (item?.collection_name) {
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
			capabilities = { ...capabilities, ...(model?.meta?.capabilities ?? {}) };

			if ('access_control' in model) {
				accessControl = model.access_control;
			} else {
				accessControl = {};
			}

			console.log(model?.access_control);
			console.log(accessControl);

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
	{#if hasInspectAccess}
		<div
			class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg"
		>
			<div class="flex items-center">
				<svg
					class="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-2"
					fill="currentColor"
					viewBox="0 0 20 20"
				>
					<path
						fill-rule="evenodd"
						d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
						clip-rule="evenodd"
					/>
				</svg>
				<span class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
					{$i18n.t(
						'Template Mode: All settings are read-only. Please clone this model to modify its configuration.'
					)}
				</span>
			</div>
		</div>
	{/if}

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
			<div class=" self-center text-sm font-medium">{'Back'}</div>
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
					let originalImageUrl = `${event.target.result}`;

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
						const compressedSrc = canvas.toDataURL();

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

		{#if !edit || (edit && model)}
			<form
				class="flex flex-col md:flex-row w-full gap-3 md:gap-6"
				on:submit|preventDefault={(e) => {
					if (hasInspectAccess) {
						e.preventDefault();
						toast.error(
							$i18n.t(
								'Template Mode: All settings are read-only. Please clone this model to modify its configuration.'
							)
						);
						return;
					}
					// Commit AccessControl changes before saving
					if (accessControlComponent) {
						accessControlComponent.commitChanges();
					}
					submitHandler();
				}}
			>
				<div class="self-center md:self-start flex justify-center my-2 shrink-0">
					<div class="self-center">
						<button
							class="rounded-xl flex shrink-0 items-center {info.meta.profile_image_url !==
							'/static/favicon.png'
								? 'bg-transparent'
								: 'bg-white'} shadow-xl group relative"
							type="button"
							disabled={hasInspectAccess}
							on:click={() => {
								filesInputElement.click();
							}}
						>
							{#if info.meta.profile_image_url}
								<img
									src={info.meta.profile_image_url}
									alt="model profile"
									class="rounded-xl size-72 md:size-60 object-cover shrink-0"
								/>
							{:else}
								<img
									src="/static/favicon.png"
									alt="model profile"
									class=" rounded-xl size-72 md:size-60 object-cover shrink-0"
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
									info.meta.profile_image_url = '/static/favicon.png';
								}}
								type="button"
							>
								Reset Image</button
							>
						</div>
					</div>
				</div>

				<div class="w-full">
					<div class="mt-2 my-2 flex flex-col">
						<div class="flex-1">
							<div>
								<input
									class="text-3xl font-semibold w-full bg-transparent outline-hidden"
									placeholder={$i18n.t('Model Name')}
									bind:value={name}
									disabled={hasInspectAccess}
									required
								/>
							</div>
						</div>

						<div class="flex-1">
							<div>
								<input
									class="text-xs w-full bg-transparent text-gray-500 outline-hidden"
									placeholder={$i18n.t('Model ID')}
									bind:value={id}
									disabled={edit || hasInspectAccess}
									required
								/>
							</div>
						</div>
					</div>

					{#if preset}
						<div class="my-1">
							<div class=" text-sm font-semibold mb-1">{$i18n.t('Base Model (From)')}</div>

							<div>
								<select
									class="text-sm w-full bg-transparent outline-hidden"
									placeholder="Select a base model (e.g. llama3, gpt-4o)"
									bind:value={info.base_model_id}
									disabled={hasInspectAccess}
									style={hasInspectAccess ? 'background-image: none;' : ''}
									on:change={(e) => {
										addUsage(e.target.value);
									}}
									required
								>
									<option value={null} class=" text-gray-900"
										>{$i18n.t('Select a base model')}</option
									>
									{#each $models.filter((m) => (model ? m.id !== model.id : true) && !m?.preset && m?.owned_by !== 'arena') as model}
										<option value={model.id} class=" text-gray-900">{model.name}</option>
									{/each}
								</select>
							</div>
						</div>
					{/if}

					<div class="my-1">
						<div class="mb-1 flex w-full justify-between items-center">
							<div class=" self-center text-sm font-semibold">{$i18n.t('Description')}</div>

							<button
								class="p-1 text-xs flex rounded-sm transition"
								type="button"
								on:click={() => {
									enableDescription = !enableDescription;
								}}
							>
								{#if hasInspectAccess}
									{#if !enableDescription}
										<span class="ml-2 self-center">{$i18n.t('Show')}</span>
									{:else}
										<span class="ml-2 self-center">{$i18n.t('Hide')}</span>
									{/if}
								{:else if !enableDescription}
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
								disabled={hasInspectAccess}
							/>
						{/if}
					</div>

					<div class=" mt-2 my-1">
						<div class="">
							{#if !hasInspectAccess}
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
							{:else}
								<div class="flex flex-wrap gap-1">
									{#each info?.meta?.tags ?? [] as tag}
										<span class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
											{tag.name}
										</span>
									{/each}
									{#if (info?.meta?.tags ?? []).length === 0}
										<span class="text-gray-500 text-xs">No tags</span>
									{/if}
								</div>
							{/if}
						</div>
					</div>

					{#if !hasInspectAccess}
						<div class="my-2">
							<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
								<AccessControl
									bind:this={accessControlComponent}
									bind:accessControl
									accessRoles={['read', 'write', 'inspect']}
									allowPublic={$user?.permissions?.sharing?.public_models ||
										$user?.role === 'admin'}
									onChange={(newAccessControl) => {
										accessControl = newAccessControl;
									}}
								/>
							</div>
						</div>
					{:else}
						<div class="my-2">
							<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
								<div class="text-sm text-gray-500 text-center py-2">
									Access control settings are read-only for inspect users.
								</div>
							</div>
						</div>
					{/if}

					<hr class=" border-gray-100 dark:border-gray-850 my-1.5" />

					<div class="my-2">
						<div class="flex w-full justify-between">
							<div class=" self-center text-sm font-semibold">{$i18n.t('Model Params')}</div>
						</div>

						<div class="mt-2">
							<div class="my-1">
								<div class=" text-xs font-semibold mb-2">{$i18n.t('System Prompt')}</div>
								<div>
									<Textarea
										className=" text-sm w-full bg-transparent outline-hidden resize-none overflow-y-hidden "
										placeholder={`Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.`}
										rows={4}
										bind:value={system}
										disabled={hasInspectAccess}
									/>
								</div>
							</div>

							<div class="flex w-full justify-between">
								<div class=" self-center text-xs font-semibold">
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
									<div
										class="pointer-events-{hasInspectAccess ? 'none' : 'auto'} {hasInspectAccess
											? 'opacity-60'
											: ''}"
									>
										<AdvancedParams admin={true} custom={true} bind:params />
									</div>
								</div>
							{/if}
						</div>
					</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-1" />

					<div class="my-2">
						<div class="flex w-full justify-between items-center">
							<div class="flex w-full justify-between items-center">
								<div class=" self-center text-sm font-semibold">
									{$i18n.t('Prompt suggestions')}
								</div>

								<button
									class="p-1 text-xs flex rounded-sm transition"
									type="button"
									on:click={() => {
										enableCustomSuggestions = !enableCustomSuggestions;
									}}
								>
									{#if hasInspectAccess}
										{#if !enableCustomSuggestions}
											<span class="ml-2 self-center">{$i18n.t('Show')}</span>
										{:else}
											<span class="ml-2 self-center">{$i18n.t('Hide')}</span>
										{/if}
									{:else if !enableCustomSuggestions}
										<span class="ml-2 self-center">{$i18n.t('Default')}</span>
									{:else}
										<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
									{/if}
								</button>
							</div>

							{#if enableCustomSuggestions && !hasInspectAccess}
								<button
									class="p-1 px-2 text-xs flex rounded-sm transition"
									type="button"
									on:click={() => {
										if (
											customSuggestionPrompts.length === 0 ||
											customSuggestionPrompts.at(-1).content !== ''
										) {
											customSuggestionPrompts = [...customSuggestionPrompts, { content: '' }];
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
											d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z"
										/>
									</svg>
								</button>
							{/if}
						</div>

						{#if enableCustomSuggestions}
							<div class="flex flex-col space-y-1 mt-1 mb-3">
								{#if customSuggestionPrompts.length > 0}
									{#each customSuggestionPrompts as prompt, promptIdx}
										<div class=" flex rounded-lg">
											<input
												class=" text-sm w-full bg-transparent outline-hidden {hasInspectAccess
													? ''
													: 'border-r border-gray-100 dark:border-gray-850'}"
												placeholder={$i18n.t('Write a prompt suggestion (e.g. Who are you?)')}
												bind:value={prompt.content}
												disabled={hasInspectAccess}
											/>

											{#if !hasInspectAccess}
												<button
													class="px-2"
													type="button"
													on:click={() => {
														customSuggestionPrompts.splice(promptIdx, 1);
														customSuggestionPrompts = customSuggestionPrompts;
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="w-4 h-4"
													>
														<path
															d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
														/>
													</svg>
												</button>
											{/if}
										</div>
									{/each}
								{:else}
									<div class="text-xs text-center">No suggestion prompts</div>
								{/if}
							</div>
						{/if}
					</div>

					<hr class=" border-gray-100 dark:border-gray-850 my-1.5" />

					<div class="my-2">
						{#if !hasInspectAccess}
							<Knowledge bind:selectedKnowledge={knowledge} collections={$knowledgeCollections} />
						{:else}
							<div>
								<div class="flex w-full justify-between mb-1">
									<div class=" self-center text-sm font-semibold">Knowledge</div>
								</div>
								<div class="flex flex-wrap gap-1">
									{#each knowledge as item}
										<span class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
											{item.name}
										</span>
									{/each}
									{#if knowledge.length === 0}
										<span class="text-gray-500 text-xs">No knowledge bases selected</span>
									{/if}
								</div>
							</div>
						{/if}
					</div>

					<div class="my-2">
						{#if !hasInspectAccess}
							<ToolsSelector
								valvesSpecs={toolValvesSpecs}
								bind:valves={toolValves}
								bind:selectedToolIds={toolIds}
								tools={$tools}
							/>
						{:else}
							<div>
								<div class="flex w-full justify-between mb-1">
									<div class=" self-center text-sm font-semibold">Tools</div>
								</div>
								<div class="flex flex-wrap gap-1">
									{#each $tools.filter((tool) => toolIds.includes(tool.id)) as tool}
										<span class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
											{tool.name}
										</span>
									{/each}
									{#if toolIds.length === 0}
										<span class="text-gray-500 text-xs">No tools selected</span>
									{/if}
								</div>
							</div>
						{/if}
					</div>

					<div class="my-2">
						{#if !hasInspectAccess}
							<FiltersSelector
								valvesSpecs={functionValvesSpecs}
								bind:valves={functionValves}
								bind:selectedFilterIds={filterIds}
								filters={$functions.filter((func) => func.type === 'filter')}
							/>
						{:else}
							<div>
								<div class="flex w-full justify-between mb-1">
									<div class=" self-center text-sm font-semibold">Filters</div>
								</div>
								<div class="flex flex-wrap gap-1">
									{#each $functions.filter((func) => func.type === 'filter' && filterIds.includes(func.id)) as filter}
										<span class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
											{filter.name}
										</span>
									{/each}
									{#if filterIds.length === 0}
										<span class="text-gray-500 text-xs">No filters selected</span>
									{/if}
								</div>
							</div>
						{/if}
					</div>

					<div class="my-2">
						{#if !hasInspectAccess}
							<ActionsSelector
								valvesSpecs={functionValvesSpecs}
								bind:valves={functionValves}
								bind:selectedActionIds={actionIds}
								actions={$functions.filter((func) => func.type === 'action')}
							/>
						{:else}
							<div>
								<div class="flex w-full justify-between mb-1">
									<div class=" self-center text-sm font-semibold">Actions</div>
								</div>
								<div class="flex flex-wrap gap-1">
									{#each $functions.filter((func) => func.type === 'action' && actionIds.includes(func.id)) as action}
										<span class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
											{action.name}
										</span>
									{/each}
									{#if actionIds.length === 0}
										<span class="text-gray-500 text-xs">No actions selected</span>
									{/if}
								</div>
							</div>
						{/if}
					</div>

					<div class="my-2">
						{#if !hasInspectAccess}
							<Capabilities bind:capabilities />
						{:else}
							<div>
								<div class="flex w-full justify-between mb-1">
									<div class=" self-center text-sm font-semibold">Capabilities</div>
								</div>
								<div class="flex flex-wrap gap-1">
									{#each Object.keys(capabilities).filter((key) => capabilities[key]) as capability}
										<span class="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs">
											{capability}
										</span>
									{/each}
									{#if Object.keys(capabilities).filter((key) => capabilities[key]).length === 0}
										<span class="text-gray-500 text-xs">No capabilities enabled</span>
									{/if}
								</div>
							</div>
						{/if}
					</div>

					<div class="my-2 text-gray-300 dark:text-gray-700">
						<div class="flex w-full justify-between mb-2">
							<div class=" self-center text-sm font-semibold">{$i18n.t('JSON Preview')}</div>

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

					<div class="my-2 flex justify-end pb-20">
						{#if !hasInspectAccess}
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
						{:else}
							<div class="text-sm text-gray-500 text-center w-full py-2">
								{$i18n.t(
									'Template Mode: All settings are read-only. Please clone this model to modify its configuration.'
								)}
							</div>
						{/if}
					</div>
				</div>
			</form>
		{/if}
	</div>
{/if}
