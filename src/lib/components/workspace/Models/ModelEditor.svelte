<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import {
		models,
		tools,
		functions,
		knowledge as knowledgeCollections,
		user,
		companyConfig
	} from '$lib/stores';

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
	import BackIcon from '$lib/components/icons/BackIcon.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import TagSelect from '$lib/components/common/TagSelect.svelte';
	import AccessSelect from '$lib/components/common/AccessSelect.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
	import { onClickOutside, getModelIcon, emojiToBase64 } from '$lib/utils';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import CapabilitiesNew from './CapabilitiesNew.svelte';
	import { transcribeAudio } from '$lib/apis/audio';
	import { blobToFile } from '$lib/utils';
	import { uploadFile } from '$lib/apis/files';
	import Dropzone from './Dropzone.svelte';
	import { v4 as uuidv4 } from 'uuid';
	import DocumentIcon from '$lib/components/icons/DocumentIcon.svelte';
	import AddKnowledgeModal from '../Knowledge/AddKnowledgeModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { modelsInfo, mapModelsToOrganizations } from '../../../../data/modelsInfo';
	import EmojiMenu from './EmojiMenu.svelte';


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
	let showEmojiMenu = false;

	// ///////////
	// model
	// ///////////

	let id = '';
	let name = '';

	$: if (!edit) {
		if (name) {
			id = name
				.replace(/\s+/g, '-')
				.replace(/[^a-zA-Z0-9-]/g, '')
				.toLowerCase();
		}
	}

	const gptDefault = $models?.find((item) => item.name === 'GPT 4o-mini');
	let info = {
		id: '',
		base_model_id: $companyConfig?.config?.models?.DEFAULT_MODELS
			? $companyConfig?.config?.models?.DEFAULT_MODELS
			: gptDefault?.id,
		name: '',
		meta: {
			profile_image_url: '🤖',
			description: '',
			suggestion_prompts: [{ content: '' }],
			tags: []
		},
		params: {
			system: '',
			temperature: 0.5
		}
	};

	let params = {
		system: ''
	};
	let capabilities = {
		websearch: false,
		image_generation: false,
		code_interpreter: false,
		vision: true,
		// usage: undefined,
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
			loading = false;
			return;
		}

		if (!info.base_model_id) {
			toast.error('Base Model is required.');
			loading = false;
			return;
		}

		info.access_control = accessControl;
		info.meta.capabilities = capabilities;
		info.meta.files = files;

		info.meta.description = info?.meta?.description?.trim() === '' ? null : info?.meta?.description;

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
		const baseModel = $models?.find((item) => item.id === info.base_model_id);
		Object.keys(info.params).forEach((key) => {
			if (
				info.params[key] === '' ||
				info.params[key] === null ||
				((baseModel?.name === 'GPT o3-mini' ||
					baseModel?.name === 'GPT o1' ||
					baseModel?.name === 'GPT o1-mini') &&
					key === 'temperature')
			) {
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
			const baseModel = $models?.find((item) => item.id === model.base_model_id);
			if (
				baseModel?.name === 'GPT o3-mini' ||
				baseModel?.name === 'GPT o1' ||
				baseModel?.name === 'GPT o1-mini'
			) {
				disableCreativity = true;
			}
			console.log(model);
			name = model.name;
			await tick();

			id = model.id;

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
			// capabilities = { ...capabilities, ...(model?.meta?.capabilities ?? {}) };
			const { usage, ...rest } = model?.meta?.capabilities ?? {};
			capabilities = { ...capabilities, ...rest };

			if ('access_control' in model) {
				accessControl = model.access_control;
			} else {
				accessControl = {};
			}

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

			files = model?.meta?.files ? model?.meta?.files : [];
		}

		loaded = true;
	});

	let showDropdown = false;
	let dropdownRef;
	$: selectedModel = $models.find((m) => m.id === info.base_model_id);
	let disableCreativity = false;

	let showTemperatureDropdown = false;
	let temperatureDropdownRef;

	const temperatureOptions = [
		{ label: 'Determined', value: 0.2 },
		{ label: 'Balanced', value: 0.5 },
		{ label: 'Creative', value: 0.8 }
	];

	$: selectedTemperatureLabel = temperatureOptions.find(
		(opt) => opt.value === info?.params?.temperature
	)?.label;

	let files: { id: string; name: string }[] = [];

	const uploadFileHandler = async (file) => {
		console.log(file);

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			size: file.size,
			status: 'uploading',
			error: '',
			itemId: tempItemId
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		// Check if the file is an audio file and transcribe/convert it to text file
		if (['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/x-m4a'].includes(file['type'])) {
			const res = await transcribeAudio(localStorage.token, file).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				console.log(res);
				const blob = new Blob([res.text], { type: 'text/plain' });
				file = blobToFile(blob, `${file.name}.txt`);
			}
		}

		try {
			const uploadedFile = await uploadFile(localStorage.token, file).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (uploadedFile) {
				console.log(uploadedFile);
				if (uploadedFile?.id) {
					files = [...files, { id: uploadedFile.id, name: uploadedFile.meta?.name || file.name }];
				}
			} else {
				toast.error($i18n.t('Failed to upload file.'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	let showAddKnowledge = false;


	let organizations = mapModelsToOrganizations(modelsInfo);
	const desiredOrder = Object.values(organizations).flat();
	const orderMap = new Map(desiredOrder.map((name, index) => [name, index]));

	$: console.log($models)

</script>

{#if loaded}
	<!-- {#if onBack}
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
	{/if} -->
	<AddKnowledgeModal
		bind:show={showAddKnowledge}
		bind:selectedKnowledge={knowledge}
		collections={$knowledgeCollections}
	/>
	<div class="flex flex-col h-screen">
		<div class="py-[22px] px-[15px] border-b border-lightGray-400 dark:border-customGray-700">
			<button class="flex items-center gap-1" on:click={() => history.back()}>
				<BackIcon />
				<div
					class="flex items-center text-lightGray-100 dark:text-customGray-100 md:self-center text-sm-plus font-medium leading-none px-0.5"
				>
					{$i18n.t('Create assistant')}
				</div>
			</button>
		</div>

		<div class="flex flex-1 overflow-hidden">
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
				<div class="overflow-y-auto overflow-x-hidden w-[34rem] py-3 px-4">
					<form
						class="flex flex-col gap-3 bg-lightGray-550 dark:bg-customGray-800 rounded-2xl py-5 px-2.5"
						on:submit|preventDefault={() => {
							submitHandler();
						}}
					>
						<div class="self-center flex justify-center flex-shrink-0">
							<div class="self-center">
								<button
									class="rounded-xl flex flex-shrink-0 items-center {info.meta.profile_image_url !==
									'/static/favicon.png'
										? 'bg-transparent'
										: 'bg-white'} shadow-xl group relative"
									type="button"
									on:click={() => {
										showEmojiMenu = true;
										// filesInputElement.click();
									}}
								>
									<EmojiMenu
										bind:open={showEmojiMenu}
										uploadImage={() => {
											filesInputElement.click();
										}}
										selectEmoji={(emoji) => {
											info.meta.profile_image_url = emojiToBase64(emoji);
										}}
										removeImage={() => (info.meta.profile_image_url = '')}
									>
										<div class="">
											{#if !info.meta.profile_image_url || info.meta.profile_image_url.length > 5}
												{#if info.meta.profile_image_url}
													<img
														src={info.meta.profile_image_url}
														alt=""
														class="rounded-lg size-16 object-cover shrink-0"
													/>
												{:else}
													<div
														class="rounded-lg size-16 shrink-0 bg-customViolet-200 dark:bg-customViolet-300"
													/>
												{/if}
											{:else}
												<div
													class="flex justify-center items-center rounded-lg size-16 shrink-0 bg-customViolet-200 dark:bg-customViolet-300"
														>
													<div class="text-[2.7rem]">
														{info.meta.profile_image_url}
													</div>
												</div>
											{/if}
										</div>
									</EmojiMenu>
									<!-- {#if info.meta.profile_image_url}
										<img
											src={info.meta.profile_image_url}
											alt="model profile"
											class="rounded-lg size-16 object-cover shrink-0"
										/>
									{:else}
										<div
											class="rounded-lg size-16 shrink-0 bg-customViolet-200 dark:bg-customViolet-300"
										/>
									{/if} -->

									<div class="absolute bottom-0 right-0 z-10">
										<div class="-m-2">
											<div
												class="p-1 rounded-lg border border-lightGray-1200 dark:bg-customGray-900 bg-lightGray-300 dark:bg-gray-800 text-lightGray-1200 transition dark:border-customGray-700 dark:text-white"
											>
												<Plus className="size-3" />
											</div>
										</div>
									</div>
								</button>
							</div>
						</div>

						<div class="w-full">
							<div class="mt-2 my-2 flex flex-col">
								<div class="flex-1 mb-1.5">
									<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
										{#if name}
											<div
												class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50"
											>
												{$i18n.t('Name')}
											</div>
										{/if}
										<input
											class={`px-2.5 text-sm ${name ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 dark:text-customGray-100 placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 outline-none`}
											placeholder={$i18n.t('Name')}
											bind:value={name}
											required
										/>
										{#if !name}
											<span
												class="absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-lightGray-100/50 dark:text-customGray-100/50 pointer-events-none select-none"
											>
												{$i18n.t('AI-Assistant')}
											</span>
										{/if}
									</div>
								</div>
								<div class="flex-1 mb-1.5">
									<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
										{#if info.meta.description}
											<div
												class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50"
											>
												{$i18n.t('Description')}
											</div>
										{/if}
										<input
											class={`px-2.5 text-sm ${info.meta.description ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 dark:text-customGray-100 placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 outline-none`}
											placeholder={$i18n.t('Description')}
											bind:value={info.meta.description}
										/>
										{#if !info.meta.description}
											<span
												class="absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-lightGray-100/50 dark:text-customGray-100/50 pointer-events-none select-none"
											>
												{$i18n.t('Brief description of the assistant')}
											</span>
										{/if}
									</div>
								</div>
								<div class="mb-1.5">
									<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
										{#if info.params.system}
											<div
												class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50"
											>
												{$i18n.t('System Prompt')}
											</div>
										{/if}
										<Textarea
											className={`px-2.5 py-2 text-sm ${info.params.system ? 'pt-4' : 'pt-2'} w-full h-20 bg-transparent text-lightGray-100 dark:text-customGray-100 placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 outline-none`}
											placeholder={$i18n.t('System Prompt')}
											rows={4}
											bind:value={info.params.system}
										/>
										{#if !info.params.system}
											<span
												class="absolute top-[26px] w-[180px] text-right right-2.5 -translate-y-1/2 text-xs text-lightGray-100/50 dark:text-customGray-100/50 pointer-events-none select-none"
											>
												{$i18n.t('You are a helpful assistant that helps users with tasks.')}
											</span>
										{/if}
									</div>
								</div>

								<div class="mb-5">
									<div
										class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2"
									>
										<div class="flex w-full justify-between items-center">
											<div class="text-xs text-lightGray-100 dark:text-customGray-300">
												{$i18n.t('Knowledge')}
											</div>
											{#if $knowledgeCollections.length > 0}
												<button
													class="shrink-0 text-xs text-lightGray-100 dark:text-customGray-200 flex rounded transition"
													type="button"
													on:click={() => {
														showAddKnowledge = true;
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
													{$i18n.t('Add')}
												</button>
											{:else}
												<Tooltip
													content={$i18n.t(
														'You don’t have a knowledge base yet — create one in the “Knowledge” tab or upload a document here.'
													)}
												>
													<button
														class="shrink-0 text-xs dark:text-customGray-200 flex rounded transition"
														type="button"
														disabled
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
														{$i18n.t('Add')}
													</button>
												</Tooltip>
											{/if}
										</div>
									</div>
									<Dropzone {uploadFileHandler} />
									{#if knowledge.length > 0}
										{#each knowledge as item}
											<div class="min-h-10 flex rounded-lg my-2">
												<div
													class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md px-2.5 py-4 text-sm text-lightGray-100 dark:text-white leading-[1.2]"
												>
													<span>{item.name}</span>
												</div>
												<button
													class="px-2 text-lightGray-100 dark:text-customGray-300 dark:hover:text-white"
													type="button"
													on:click={() => {
														knowledge = knowledge.filter((k) => k.id !== item.id);
													}}
												>
													<DeleteIcon />
												</button>
											</div>
										{/each}
									{/if}
									{#if files.length}
										<ul class="mt-2.5 space-y-1 text-sm">
											{#each files as file (file.id)}
												<li
													class="group flex justify-start items-center text-lightGray-100 dark:text-customGray-100 cursor-pointer dark:hover:text-white"
												>
													<DocumentIcon />
													<span class="truncate ml-2 mr-3.5">{file.name}</span>
													<button
														class="opacity-0 group-hover:opacity-100"
														on:click={() => {
															files = files.filter((f) => f.id !== file.id);
														}}
													>
														<DeleteIcon />
													</button>
												</li>
											{/each}
										</ul>
									{/if}
								</div>

								<div class="mb-1.5">
									<div
										class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700"
									>
										<div class="flex w-full justify-between items-center">
											<div class="text-xs text-lightGray-100 dark:text-customGray-300">
												{$i18n.t('Prompt suggestions')}
											</div>
										</div>
										<button
											class="shrink-0 text-xs dark:text-customGray-200 flex rounded transition"
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
											{$i18n.t('Add')}
										</button>
										<!-- {/if} -->
									</div>

									{#if info?.meta?.suggestion_prompts}
										<div class="flex flex-col space-y-1 mt-2.5 mb-3">
											{#if info.meta.suggestion_prompts.length > 0}
												{#each info.meta.suggestion_prompts as prompt, promptIdx}
													<div class=" flex rounded-lg">
														<div
															class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md"
														>
															<input
																class="px-2.5 text-sm h-12 w-full bg-lightGray-300 dark:bg-customGray-900 text-lightGray-100 dark:text-customGray-100 placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 rounded-md outline-none"
																placeholder={$i18n.t('Prompt suggestion')}
																bind:value={prompt.content}
															/>
															{#if !prompt.content}
																<span
																	class="absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-lightGray-100/50 dark:text-customGray-100/50 pointer-events-none select-none"
																>
																	{$i18n.t('Who are you')}
																</span>
															{/if}
														</div>
														<button
															class="px-2 dark:text-customGray-300"
															type="button"
															on:click={() => {
																info.meta.suggestion_prompts.splice(promptIdx, 1);
																info.meta.suggestion_prompts = info.meta.suggestion_prompts;
															}}
														>
															<DeleteIcon />
														</button>
													</div>
												{/each}
											{:else}
												<div class="text-xs text-center">{$i18n.t('No suggestion prompts')}</div>
											{/if}
										</div>
									{/if}
								</div>

								<div>
									<div class="py-2.5 border-b border-lightGray-400 dark:border-customGray-700">
										<div class="text-xs text-lightGray-100 dark:text-customGray-300">
											{$i18n.t('Organization')}
										</div>
									</div>
									<div class="py-3">
										<div class="mb-2">
											<TagSelect bind:selected={info.meta.tags} placeholder="Add category..." />
										</div>
										<AccessSelect bind:accessControl accessRoles={['read', 'write']} />
									</div>
								</div>

								<div>
									<div class="py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2">
										<div class="text-xs text-lightGray-100 dark:text-customGray-300">
											{$i18n.t('Output settings')}
										</div>
									</div>
								</div>

								{#if preset}
									<div class="my-1" use:onClickOutside={() => (showDropdown = false)}>
										<div class="relative" bind:this={dropdownRef}>
											<button
												type="button"
												class={`flex items-center justify-between w-full text-sm h-12 px-3 py-2  ${showDropdown ? 'border' : ''} border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 dark:bg-customGray-900 cursor-pointer`}
												on:click={() => (showDropdown = !showDropdown)}
											>
												<span class="text-lightGray-100 dark:text-customGray-100"
													>{$i18n.t('Model Selection')}</span
												>
												<div class="flex items-center gap-2">
													{#if info.base_model_id}
														<div
															class="flex items-center gap-2 text-xs text-lightGray-100/50 dark:text-customGray-100/50"
														>
															<img
																src={getModelIcon(selectedModel.name)}
																alt="icon"
																class="w-4 h-4"
															/>
															{selectedModel.name}
														</div>
													{/if}
													<ChevronDown className="size-3" />
												</div>
											</button>

											{#if showDropdown}
												<div
													class="max-h-60 overflow-y-auto custom-scrollbar absolute z-50 w-full -mt-1 bg-lightGray-300 dark:bg-customGray-900 border-l border-r border-b border-lightGray-400 dark:border-customGray-700 rounded-b-md"
												>
													<hr
														class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5"
													/>
													<div class="px-1">

														{#each $models?.filter(item => !item.base_model_id)?.filter((m) => (model ? m.id !== model.id : true) && !m?.preset && m?.owned_by !== 'arena')?.sort((a, b) => (orderMap.get(a?.name) ?? Infinity) - (orderMap.get(b?.name) ?? Infinity)) as model}

															<button
																class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-lightGray-700 dark:hover:bg-customGray-950 text-lightGray-100 dark:text-customGray-100 cursor-pointer"
																on:click={() => {
																	info.base_model_id = model.id;
																	if (
																		model.name === 'GPT o3-mini' ||
																		model?.name === 'GPT o1' ||
																		model?.name === 'GPT o1-mini'
																	) {
																		disableCreativity = true;
																	} else {
																		if (disableCreativity) {
																			disableCreativity = false;
																			info.params = { ...info.params, temperature: 0.5 };
																		}
																	}
																	// addUsage(model.id);
																	showDropdown = false;
																}}
															>
																<img src={getModelIcon(model.name)} alt="icon" class="w-4 h-4" />
																{model.name}
															</button>
														{/each}
													</div>
												</div>
											{/if}
										</div>
									</div>
								{/if}

								<div class="my-1" use:onClickOutside={() => (showTemperatureDropdown = false)}>
									<div class="relative" bind:this={temperatureDropdownRef}>
										<button
											type="button"
											class={`flex items-center justify-between w-full text-sm h-12 px-3 py-2 ${
												showTemperatureDropdown ? 'border' : ''
											} border-lightGray-400 dark:border-customGray-700 rounded-md bg-lightGray-300 ${disableCreativity ? 'bg-lightGray-300 dark:bg-customGray-800' : 'dark:bg-customGray-900 bg-lightGray-300'}  cursor-pointer`}
											on:click={() => {
												if (disableCreativity) return;
												showTemperatureDropdown = !showTemperatureDropdown;
											}}
										>
											<span class="text-lightGray-100 dark:text-customGray-100"
												>{$i18n.t('Creativity Scale')}</span
											>
											{#if !disableCreativity}
												<div
													class="flex items-center gap-2 text-xs text-lightGray-100/50 dark:text-customGray-100/50"
												>
													{selectedTemperatureLabel}
													<ChevronDown className="size-3" />
												</div>
											{/if}
										</button>

										{#if showTemperatureDropdown}
											<div
												class="max-h-40 overflow-y-auto absolute z-50 w-full -mt-1 bg-lightGray-300 pb-1 dark:bg-customGray-900 border-l border-r border-b border-lightGray-400 dark:border-customGray-700 rounded-b-md"
											>
												<hr
													class="border-t border-lightGray-400 dark:border-customGray-700 mb-2 mt-1 mx-0.5"
												/>
												<div class="px-1">
													{#each temperatureOptions as option}
														<button
															class="px-3 py-2 flex items-center gap-2 w-full rounded-xl text-sm hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:text-customGray-100 cursor-pointer text-lightGray-100"
															on:click={() => {
																info.params.temperature = option.value;
																showTemperatureDropdown = false;
															}}
														>
															{option.label}
														</button>
													{/each}
												</div>
											</div>
										{/if}
									</div>
								</div>

								<CapabilitiesNew bind:capabilities />
							</div>

							<div class="my-2 flex justify-end">
								<button
									class=" text-xs w-[168px] h-10 px-3 py-2 font-medium transition rounded-lg {loading
										? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-500 text-lightGray-100 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border dark:border-customGray-700'
										: 'bg-lightGray-300 hover:bg-lightGray-500 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700'} flex justify-center"
									type="submit"
									disabled={loading}
								>
									<div class=" self-center">
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
				</div>
			{/if}
			<div class="w-1/2 hidden md:visible"></div>
		</div>
	</div>
{/if}
