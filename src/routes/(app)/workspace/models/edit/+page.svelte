<script>
	import { v4 as uuidv4 } from 'uuid';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { settings, user, config, models, tools } from '$lib/stores';
	import { splitStream } from '$lib/utils';

	import { getModelInfos, updateModelById } from '$lib/apis/models';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import { getModels } from '$lib/apis';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';

	const i18n = getContext('i18n');

	let loading = false;
	let success = false;

	let filesInputElement;
	let inputFiles;

	let digest = '';
	let pullProgress = null;

	let showAdvanced = false;
	let showPreview = false;

	// ///////////
	// model
	// ///////////

	let model = null;

	let id = '';
	let name = '';

	let info = {
		id: '',
		base_model_id: null,
		name: '',
		meta: {
			profile_image_url: '/favicon.png',
			description: '',
			suggestion_prompts: null,
			tags: []
		},
		params: {
			system: ''
		}
	};

	let params = {};
	let capabilities = {
		vision: true
	};

	let knowledge = [];
	let toolIds = [];

	const updateHandler = async () => {
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

		info.params.stop = params.stop ? params.stop.split(',').filter((s) => s.trim()) : null;
		Object.keys(info.params).forEach((key) => {
			if (info.params[key] === '' || info.params[key] === null) {
				delete info.params[key];
			}
		});

		const res = await updateModelById(localStorage.token, info.id, info);

		if (res) {
			await models.set(await getModels(localStorage.token));
			toast.success('Model updated successfully');
			await goto('/workspace/models');
		}

		loading = false;
		success = false;
	};

	onMount(() => {
		const _id = $page.url.searchParams.get('id');

		if (_id) {
			model = $models.find((m) => m.id === _id);
			if (model) {
				id = model.id;
				name = model.name;

				info = {
					...info,
					...JSON.parse(
						JSON.stringify(
							model?.info
								? model?.info
								: {
										id: model.id,
										name: model.name
								  }
						)
					)
				};

				if (model.preset && model.owned_by === 'ollama' && !info.base_model_id.includes(':')) {
					info.base_model_id = `${info.base_model_id}:latest`;
				}

				params = { ...params, ...model?.info?.params };
				params.stop = params?.stop
					? (typeof params.stop === 'string' ? params.stop.split(',') : params?.stop ?? []).join(
							','
					  )
					: null;

				if (model?.info?.meta?.knowledge) {
					knowledge = [...model?.info?.meta?.knowledge];
				}

				if (model?.info?.meta?.toolIds) {
					toolIds = [...model?.info?.meta?.toolIds];
				}

				if (model?.owned_by === 'openai') {
					capabilities.usage = false;
				}

				if (model?.info?.meta?.capabilities) {
					capabilities = { ...capabilities, ...model?.info?.meta?.capabilities };
				}

				console.log(model);
			} else {
				goto('/workspace/models');
			}
		} else {
			goto('/workspace/models');
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
						newWidth = 100 * aspectRatio;
						newHeight = 100;
					} else {
						newWidth = 100;
						newHeight = 100 / aspectRatio;
					}

					// Set the canvas size
					canvas.width = 100;
					canvas.height = 100;

					// Calculate the position to center the image
					const offsetX = (100 - newWidth) / 2;
					const offsetY = (100 - newHeight) / 2;

					// Draw the image on the canvas
					ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

					// Get the base64 representation of the compressed image
					const compressedSrc = canvas.toDataURL('image/jpeg');

					// Display the compressed image
					info.meta.profile_image_url = compressedSrc;

					inputFiles = null;
				};
			};

			if (
				inputFiles &&
				inputFiles.length > 0 &&
				['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(inputFiles[0]['type'])
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

	{#if model}
		<form
			class="flex flex-col max-w-2xl mx-auto mt-4 mb-10"
			on:submit|preventDefault={() => {
				updateHandler();
			}}
		>
			<div class="flex justify-center my-4">
				<div class="self-center">
					<button
						class=" {info.meta.profile_image_url
							? ''
							: 'p-4'} rounded-full dark:bg-gray-700 border border-dashed border-gray-200 flex items-center"
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

			<div class="mt-2 my-1 flex space-x-2">
				<div class="flex-1">
					<div class=" text-sm font-semibold mb-1">{$i18n.t('Name')}*</div>

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
					<div class=" text-sm font-semibold mb-1">{$i18n.t('Model ID')}*</div>

					<div>
						<input
							class="px-3 py-1.5 text-sm w-full bg-transparent disabled:text-gray-500 border dark:border-gray-600 outline-none rounded-lg"
							placeholder={$i18n.t('Add a model id')}
							value={id}
							disabled
							required
						/>
					</div>
				</div>
			</div>

			{#if model.preset}
				<div class="my-1">
					<div class=" text-sm font-semibold mb-1">{$i18n.t('Base Model (From)')}</div>

					<div>
						<select
							class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg"
							placeholder="Select a base model (e.g. llama3, gpt-4o)"
							bind:value={info.base_model_id}
							required
						>
							<option value={null} class=" text-gray-900">{$i18n.t('Select a base model')}</option>
							{#each $models.filter((m) => m.id !== model.id && !m?.preset) as model}
								<option value={model.id} class=" text-gray-900">{model.name}</option>
							{/each}
						</select>
					</div>
				</div>
			{/if}

			<div class="my-1">
				<div class="flex w-full justify-between items-center">
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
					<input
						class="mt-1 px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg"
						placeholder={$i18n.t('Add a short description about what this model does')}
						bind:value={info.meta.description}
					/>
				{/if}
			</div>

			<hr class=" dark:border-gray-850 my-1" />

			<div class="my-2">
				<div class="flex w-full justify-between">
					<div class=" self-center text-sm font-semibold">{$i18n.t('Model Params')}</div>
				</div>

				<!-- <div class=" text-sm font-semibold mb-2"></div> -->

				<div class="mt-2">
					<div class="my-1">
						<div class=" text-xs font-semibold mb-2">{$i18n.t('System Prompt')}</div>
						<div>
							<textarea
								class="px-3 py-1.5 text-sm w-full bg-transparent border dark:border-gray-600 outline-none rounded-lg -mb-1"
								placeholder={`Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.`}
								rows="4"
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

			<div class="my-2">
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
				<Knowledge bind:knowledge />
			</div>

			<div class="my-2">
				<ToolsSelector bind:selectedToolIds={toolIds} tools={$tools} />
			</div>

			<div class="my-2">
				<div class="flex w-full justify-between mb-1">
					<div class=" self-center text-sm font-semibold">{$i18n.t('Capabilities')}</div>
				</div>
				<div class="flex flex-col">
					{#each Object.keys(capabilities) as capability}
						<div class=" flex items-center gap-2">
							<Checkbox
								state={capabilities[capability] ? 'checked' : 'unchecked'}
								on:change={(e) => {
									capabilities[capability] = e.detail === 'checked';
								}}
							/>

							<div class=" py-0.5 text-sm w-full capitalize">
								{$i18n.t(capability)}
							</div>
						</div>
					{/each}
				</div>
			</div>

			<div class="my-1">
				<div class="flex w-full justify-between items-center">
					<div class=" self-center text-sm font-semibold">{$i18n.t('Tags')}</div>
				</div>

				<div class="mt-2">
					<Tags
						tags={info?.meta?.tags ?? []}
						deleteTag={(tagName) => {
							info.meta.tags = info.meta.tags.filter((tag) => tag.name !== tagName);
						}}
						addTag={(tagName) => {
							console.log(tagName);
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
					<div class=" self-center font-medium">{$i18n.t('Save & Update')}</div>

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
	{/if}
</div>
