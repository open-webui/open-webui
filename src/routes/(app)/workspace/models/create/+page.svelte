<script>
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import {
		settings,
		user,
		config,
		models,
		tools,
		functions,
		knowledge as _knowledge
	} from '$lib/stores';

	import TurndownService from 'turndown';

	import { onMount, tick, getContext } from 'svelte';
	import { addNewModel, getModelById, getModelInfos } from '$lib/apis/models';
	import { getModels } from '$lib/apis';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';
	import { stringify } from 'postcss';
	import { parseFile } from '$lib/utils/characters';
	import FiltersSelector from '$lib/components/workspace/Models/FiltersSelector.svelte';
	import ActionsSelector from '$lib/components/workspace/Models/ActionsSelector.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	let filesInputElement;
	let inputFiles;

	let showAdvanced = false;
	let showPreview = false;

	let loading = false;
	let success = false;

	// ///////////
	// Model
	// ///////////

	let id = '';
	let name = '';

	let info = {
		id: '',
		base_model_id: null,
		name: '',
		meta: {
			profile_image_url: null,
			description: '',
			suggestion_prompts: [
				{
					content: ''
				}
			]
		},
		params: {
			system: ''
		}
	};

	let params = {};
	let capabilities = {
		vision: true,
		usage: undefined
	};

	let toolIds = [];
	let knowledge = [];
	let filterIds = [];
	let actionIds = [];

	$: if (name) {
		id = name
			.replace(/\s+/g, '-')
			.replace(/[^a-zA-Z0-9-]/g, '')
			.toLowerCase();
	}

	const addUsage = (base_model_id) => {
		const baseModel = $models.find((m) => m.id === base_model_id);

		if (baseModel) {
			if (baseModel.owned_by === 'openai') {
				capabilities.usage = baseModel.info?.meta?.capabilities?.usage ?? false;
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
		info.meta.capabilities = capabilities;

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

		info.params.stop = params.stop ? params.stop.split(',').filter((s) => s.trim()) : null;
		Object.keys(info.params).forEach((key) => {
			if (info.params[key] === '' || info.params[key] === null) {
				delete info.params[key];
			}
		});

		if ($models.find((m) => m.id === info.id)) {
			toast.error(
				`Error: A model with the ID '${info.id}' already exists. Please select a different ID to proceed.`
			);
			loading = false;
			success = false;
			return success;
		}

		if (info) {
			const res = await addNewModel(localStorage.token, {
				...info,
				meta: {
					...info.meta,
					profile_image_url: info.meta.profile_image_url ?? '/static/favicon.png',
					suggestion_prompts: info.meta.suggestion_prompts
						? info.meta.suggestion_prompts.filter((prompt) => prompt.content !== '')
						: null
				},
				params: { ...info.params, ...params }
			});

			if (res) {
				await models.set(await getModels(localStorage.token));
				toast.success($i18n.t('Model created successfully!'));
				await goto('/workspace/models');
			}
		}

		loading = false;
		success = false;
	};

	const initModel = async (model) => {
		name = model.name;
		await tick();

		id = model.id;

		if (model.info.base_model_id) {
			const base_model = $models
				.filter((m) => !m?.preset && m?.owned_by !== 'arena')
				.find((m) =>
					[model.info.base_model_id, `${model.info.base_model_id}:latest`].includes(m.id)
				);

			console.log('base_model', base_model);

			if (!base_model) {
				model.info.base_model_id = null;
			} else if ($models.find((m) => m.id === `${model.info.base_model_id}:latest`)) {
				model.info.base_model_id = `${model.info.base_model_id}:latest`;
			}
		}

		params = { ...params, ...model?.info?.params };
		params.stop = params?.stop ? (params?.stop ?? []).join(',') : null;

		capabilities = { ...capabilities, ...(model?.info?.meta?.capabilities ?? {}) };
		toolIds = model?.info?.meta?.toolIds ?? [];

		if (model?.info?.meta?.filterIds) {
			filterIds = [...model?.info?.meta?.filterIds];
		}

		if (model?.info?.meta?.actionIds) {
			actionIds = [...model?.info?.meta?.actionIds];
		}

		info = {
			...info,
			...model.info
		};

		console.log(info);
	};

	onMount(async () => {
		window.addEventListener('message', async (event) => {
			if (
				!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:5173'].includes(
					event.origin
				)
			)
				return;

			const model = JSON.parse(event.data);
			console.log(model);

			initModel(model);
		});

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}

		if (sessionStorage.model) {
			const model = JSON.parse(sessionStorage.model);
			sessionStorage.removeItem('model');

			console.log(model);
			initModel(model);
		}
	});
</script>

<div class="w-full max-h-full">
	<input
		bind:this={filesInputElement}
		bind:files={inputFiles}
		type="file"
		hidden
		accept="image/*"
		on:change={() => {
			let reader = new FileReader();
			reader.onload = async (event) => {
				let originalImageUrl = `${event.target.result}`;

				let character = await parseFile(inputFiles[0]).catch((error) => {
					return null;
				});

				console.log(character);

				if (character && character.character) {
					character = character.character;
					console.log(character);

					name = character.name;

					const pattern = /<\/?[a-z][\s\S]*>/i;
					if (character.summary.match(pattern)) {
						const turndownService = new TurndownService();
						info.meta.description = turndownService.turndown(character.summary);
					} else {
						info.meta.description = character.summary;
					}

					info.params.system = `Personality: ${character.personality}${
						character?.scenario ? `\nScenario: ${character.scenario}` : ''
					}${character?.greeting ? `\First Message: ${character.greeting}` : ''}${
						character?.examples ? `\nExamples: ${character.examples}` : ''
					}`;
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
					const compressedSrc = canvas.toDataURL();

					// Display the compressed image
					info.meta.profile_image_url = compressedSrc;

					inputFiles = null;
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

	<button
		class="flex space-x-1"
		on:click={() => {
			goto('/workspace/models');
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
	<!-- <hr class="my-3 dark:border-gray-850" /> -->

	<form
		class="flex flex-col max-w-2xl mx-auto mt-4 mb-10"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div class="flex justify-center my-4">
			<div class="self-center">
				<button
					class=" {info.meta.profile_image_url
						? ''
						: 'p-4'} rounded-full border border-dashed border-gray-200 flex items-center"
					type="button"
					on:click={() => {
						filesInputElement.click();
					}}
				>
					{#if info.meta.profile_image_url}
						<img
							src={info.meta.profile_image_url}
							alt="modelfile profile"
							class=" rounded-full size-16 object-cover"
						/>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="currentColor"
							class="size-8"
						>
							<path
								fill-rule="evenodd"
								d="M12 3.75a.75.75 0 01.75.75v6.75h6.75a.75.75 0 010 1.5h-6.75v6.75a.75.75 0 01-1.5 0v-6.75H4.5a.75.75 0 010-1.5h6.75V4.5a.75.75 0 01.75-.75z"
								clip-rule="evenodd"
							/>
						</svg>
					{/if}
				</button>
			</div>
		</div>

		<div class="my-2 flex space-x-2">
			<div class="flex-1">
				<div class=" text-sm font-semibold mb-2">{$i18n.t('Name')}*</div>

				<div>
					<input
						class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg"
						placeholder={$i18n.t('Name your model')}
						bind:value={name}
						required
					/>
				</div>
			</div>

			<div class="flex-1">
				<div class=" text-sm font-semibold mb-2">{$i18n.t('Model ID')}*</div>

				<div>
					<input
						class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg"
						placeholder={$i18n.t('Add a model id')}
						bind:value={id}
						required
					/>
				</div>
			</div>
		</div>

		<div class="my-2">
			<div class=" text-sm font-semibold mb-2">{$i18n.t('Base Model (From)')}</div>

			<div>
				<select
					class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg"
					placeholder="Select a base model (e.g. llama3, gpt-4o)"
					bind:value={info.base_model_id}
					on:change={(e) => {
						addUsage(e.target.value);
					}}
					required
				>
					<option value={null} class=" text-gray-900">{$i18n.t('Select a base model')}</option>
					{#each $models.filter((m) => !m?.preset && m?.owned_by !== 'arena') as model}
						<option value={model.id} class=" text-gray-900">{model.name}</option>
					{/each}
				</select>
			</div>
		</div>

		<div class="my-1">
			<div class="flex w-full justify-between items-center mb-1">
				<div class=" self-center text-sm font-semibold">{$i18n.t('Description')}</div>

				<button
					class="p-1 text-xs flex rounded transition"
					type="button"
					on:click={() => {
						if (info.meta.description === null) {
							info.meta.description = '';
						} else {
							info.meta.description = null;
						}
					}}
				>
					{#if info.meta.description === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>

			{#if info.meta.description !== null}
				<textarea
					class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg"
					placeholder={$i18n.t('Add a short description about what this model does')}
					bind:value={info.meta.description}
					row="3"
				/>
			{/if}
		</div>

		<hr class=" dark:border-gray-850 my-1" />

		<div class="my-2">
			<div class="flex w-full justify-between">
				<div class=" self-center text-sm font-semibold">{$i18n.t('Model Params')}</div>
			</div>

			<div class="mt-2">
				<div class="my-1">
					<div class=" text-xs font-semibold mb-2">{$i18n.t('System Prompt')}</div>
					<div>
						<Textarea
							className="px-3 py-2 text-sm w-full bg-transparent border dark:border-gray-600 outline-none resize-none overflow-y-hidden rounded-lg "
							placeholder={`Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.`}
							rows={4}
							bind:value={info.params.system}
						/>
					</div>
				</div>

				<div class="flex w-full justify-between">
					<div class=" self-center text-xs font-semibold">
						{$i18n.t('Advanced Params')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
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

		<hr class=" dark:border-gray-850 my-1" />

		<div class="my-1">
			<div class="flex w-full justify-between items-center">
				<div class="flex w-full justify-between items-center">
					<div class=" self-center text-sm font-semibold">{$i18n.t('Prompt suggestions')}</div>

					<button
						class="p-1 text-xs flex rounded transition"
						type="button"
						on:click={() => {
							if (info.meta.suggestion_prompts === null) {
								info.meta.suggestion_prompts = [{ content: '' }];
							} else {
								info.meta.suggestion_prompts = null;
							}
						}}
					>
						{#if info.meta.suggestion_prompts === null}
							<span class="ml-2 self-center">{$i18n.t('Default')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
						{/if}
					</button>
				</div>

				{#if info.meta.suggestion_prompts !== null}
					<button
						class="p-1 px-2 text-xs flex rounded transition"
						type="button"
						on:click={() => {
							if (
								info.meta.suggestion_prompts.length === 0 ||
								info.meta.suggestion_prompts.at(-1).content !== ''
							) {
								info.meta.suggestion_prompts = [...info.meta.suggestion_prompts, { content: '' }];
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

			{#if info.meta.suggestion_prompts}
				<div class="flex flex-col space-y-1 mt-2">
					{#if info.meta.suggestion_prompts.length > 0}
						{#each info.meta.suggestion_prompts as prompt, promptIdx}
							<div class=" flex border dark:border-gray-600 rounded-lg">
								<input
									class="px-3 py-1.5 text-sm w-full bg-transparent outline-none border-r dark:border-gray-600"
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

		<div class="my-2">
			<Knowledge bind:selectedKnowledge={knowledge} collections={$_knowledge} />
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

		<div class="my-1">
			<Capabilities bind:capabilities />
		</div>

		<div class="my-1">
			<div class="flex w-full justify-between items-center">
				<div class=" self-center text-sm font-semibold">{$i18n.t('Tags')}</div>
			</div>

			<div class="mt-2">
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

		<div class="my-2 text-gray-300 dark:text-gray-700">
			<div class="flex w-full justify-between mb-2">
				<div class=" self-center text-sm font-semibold">{$i18n.t('JSON Preview')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
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
						class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg"
						rows="10"
						value={JSON.stringify(info, null, 2)}
						disabled
						readonly
					/>
				</div>
			{/if}
		</div>

		<div class="my-2 flex justify-end mb-20">
			<button
				class=" text-sm px-3 py-2 transition rounded-xl {loading
					? ' cursor-not-allowed bg-gray-100 dark:bg-gray-800'
					: ' bg-gray-50 hover:bg-gray-100 dark:bg-gray-700 dark:hover:bg-gray-800'} flex"
				type="submit"
				disabled={loading}
			>
				<div class=" self-center font-medium">{$i18n.t('Save & Create')}</div>

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
	</form>
</div>
