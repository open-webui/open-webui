<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { models, tools, functions, knowledge as knowledgeCollections, user } from '$lib/stores';

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
	import AccessControl from '../common/AccessControl.svelte';
	import { stringify } from 'postcss';
	import { toast } from 'svelte-sonner';

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
			profile_image_url: '/static/favicon.png',
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
	let capabilities = {
		vision: true,
		usage: undefined,
		citations: true
	};

	let knowledge = [];
	let toolIds = [];
	let filterIds = [];
	let actionIds = [];

	let accessControl = {};

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

		if (id === '') {
			toast.error('Model ID is required.');
		}

		if (name === '') {
			toast.error('Model Name is required.');
		}

		info.access_control = accessControl;
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

		await onSubmit(info);

		loading = false;
		success = false;
	};

	onMount(async () => {
		await tools.set(await getTools(localStorage.token));
		await functions.set(await getFunctions(localStorage.token));
		await knowledgeCollections.set(await getKnowledgeBases(localStorage.token));

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
				on:submit|preventDefault={() => {
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
									disabled={edit}
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

					<div class=" mt-2 my-1">
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

					<div class="my-2">
						<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
							<AccessControl
								bind:accessControl
								accessRoles={['read', 'write']}
								allowPublic={$user?.permissions?.sharing?.public_models || $user?.role === 'admin'}
							/>
						</div>
					</div>

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
									<AdvancedParams
										admin={true}
										bind:params
										on:change={(e) => {
											info.params = { ...info.params, ...params };
										}}
									/>
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
										<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
									{/if}
								</button>
							</div>

							{#if (info?.meta?.suggestion_prompts ?? null) !== null}
								<button
									class="p-1 px-2 text-xs flex rounded-sm transition"
									type="button"
									on:click={() => {
										if (
											info.meta.suggestion_prompts.length === 0 ||
											info.meta.suggestion_prompts.at(-1).content !== ''
										) {
											info.meta.suggestion_prompts = [
												...info.meta.suggestion_prompts,
												{ content: '' }
											];
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

						{#if info?.meta?.suggestion_prompts}
							<div class="flex flex-col space-y-1 mt-1 mb-3">
								{#if info.meta.suggestion_prompts.length > 0}
									{#each info.meta.suggestion_prompts as prompt, promptIdx}
										<div class=" flex rounded-lg">
											<input
												class=" text-sm w-full bg-transparent outline-hidden border-r border-gray-100 dark:border-gray-850"
												placeholder={$i18n.t('Write a prompt suggestion (e.g. Who are you?)')}
												bind:value={prompt.content}
											/>

											<button
												class="px-2"
												type="button"
												on:click={() => {
													info.meta.suggestion_prompts.splice(promptIdx, 1);
													info.meta.suggestion_prompts = info.meta.suggestion_prompts;
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
						<Knowledge bind:selectedKnowledge={knowledge} collections={$knowledgeCollections} />
					</div>

					<div class="my-2">
						<ToolsSelector bind:selectedToolIds={toolIds} tools={$tools} />
					</div>

					<div class="my-2">
						<FiltersSelector
							bind:selectedFilterIds={filterIds}
							filters={$functions.filter((func) => func.type === 'filter')}
						/>
					</div>

					<div class="my-2">
						<ActionsSelector
							bind:selectedActionIds={actionIds}
							actions={$functions.filter((func) => func.type === 'action')}
						/>
					</div>

					<div class="my-2">
						<Capabilities bind:capabilities />
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
					</div>
				</div>
			</form>
		{/if}
	</div>
{/if}
