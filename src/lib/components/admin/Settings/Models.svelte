<script lang="ts">
	import { marked } from 'marked';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, mobile, models as _models, settings, user } from '$lib/stores';
	import {
		createNewModel,
		deleteAllModels,
		getBaseModels,
		toggleModelById,
		updateModelById
	} from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import ModelEditor from '$lib/components/workspace/Models/ModelEditor.svelte';
	import { toast } from 'svelte-sonner';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ConfigureModelsModal from './Models/ConfigureModelsModal.svelte';

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;

	let models = null;

	let workspaceModels = null;
	let baseModels = null;

	let filteredModels = [];
	let selectedModelId = null;

	let showConfigModal = false;

	$: if (models) {
		filteredModels = models
			.filter((m) => searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase()))
			.sort((a, b) => {
				// // Check if either model is inactive and push them to the bottom
				// if ((a.is_active ?? true) !== (b.is_active ?? true)) {
				// 	return (b.is_active ?? true) - (a.is_active ?? true);
				// }
				// If both models' active states are the same, sort alphabetically
				return a.name.localeCompare(b.name);
			});
	}

	let searchValue = '';

	const downloadModels = async (models) => {
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const init = async () => {
		workspaceModels = await getBaseModels(localStorage.token);
		baseModels = await getModels(localStorage.token, true);

		models = baseModels.map((m) => {
			const workspaceModel = workspaceModels.find((wm) => wm.id === m.id);

			if (workspaceModel) {
				return {
					...m,
					...workspaceModel
				};
			} else {
				return {
					...m,
					id: m.id,
					name: m.name,

					is_active: true
				};
			}
		});
	};

	const upsertModelHandler = async (model) => {
		model.base_model_id = null;

		if (workspaceModels.find((m) => m.id === model.id)) {
			const res = await updateModelById(localStorage.token, model.id, model).catch((error) => {
				return null;
			});

			if (res) {
				toast.success($i18n.t('Model updated successfully'));
			}
		} else {
			const res = await createNewModel(localStorage.token, model).catch((error) => {
				return null;
			});

			if (res) {
				toast.success($i18n.t('Model updated successfully'));
			}
		}

		_models.set(await getModels(localStorage.token));
		await init();
	};

	const toggleModelHandler = async (model) => {
		if (!Object.keys(model).includes('base_model_id')) {
			await createNewModel(localStorage.token, {
				id: model.id,
				name: model.name,
				base_model_id: null,
				meta: {},
				params: {},
				access_control: {},
				is_active: model.is_active
			}).catch((error) => {
				return null;
			});
		} else {
			await toggleModelById(localStorage.token, model.id);
		}

		await init();
		_models.set(await getModels(localStorage.token));
	};

	onMount(async () => {
		init();
	});
</script>

<ConfigureModelsModal bind:show={showConfigModal} {init} />

{#if models !== null}
	{#if selectedModelId === null}
		<div class="flex flex-col gap-1 mt-1.5 mb-2">
			<div class="flex justify-between items-center">
				<div class="flex items-center md:self-center text-xl font-medium px-0.5">
					{$i18n.t('Models')}
					<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
					<span class="text-lg font-medium text-gray-500 dark:text-gray-300"
						>{filteredModels.length}</span
					>
				</div>

				<div>
					<Tooltip content={$i18n.t('Configure')}>
						<button
							class=" px-2.5 py-1 rounded-full flex gap-1 items-center"
							type="button"
							on:click={() => {
								showConfigModal = true;
							}}
						>
							<Cog6 />
						</button>
					</Tooltip>
				</div>
			</div>

			<div class=" flex flex-1 items-center w-full space-x-2">
				<div class="flex flex-1 items-center">
					<div class=" self-center ml-1 mr-3">
						<Search className="size-3.5" />
					</div>
					<input
						class=" w-full text-sm py-1 rounded-r-xl outline-none bg-transparent"
						bind:value={searchValue}
						placeholder={$i18n.t('Search Models')}
					/>
				</div>
			</div>
		</div>

		<div class=" my-2 mb-5" id="model-list">
			{#if models.length > 0}
				{#each filteredModels as model, modelIdx (model.id)}
					<div
						class=" flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-lg transition"
						id="model-item-{model.id}"
					>
						<button
							class=" flex flex-1 text-left space-x-3.5 cursor-pointer w-full"
							type="button"
							on:click={() => {
								selectedModelId = model.id;
							}}
						>
							<div class=" self-center w-8">
								<div
									class=" rounded-full object-cover {(model?.is_active ?? true)
										? ''
										: 'opacity-50 dark:opacity-50'} "
								>
									<img
										src={model?.meta?.profile_image_url ?? '/static/favicon.png'}
										alt="modelfile profile"
										class=" rounded-full w-full h-auto object-cover"
									/>
								</div>
							</div>

							<div class=" flex-1 self-center {(model?.is_active ?? true) ? '' : 'text-gray-500'}">
								<Tooltip
									content={marked.parse(
										!!model?.meta?.description
											? model?.meta?.description
											: model?.ollama?.digest
												? `${model?.ollama?.digest} **(${model?.ollama?.modified_at})**`
												: model.id
									)}
									className=" w-fit"
									placement="top-start"
								>
									<div class="  font-semibold line-clamp-1">{model.name}</div>
								</Tooltip>
								<div class=" text-xs overflow-hidden text-ellipsis line-clamp-1 text-gray-500">
									<span class=" line-clamp-1">
										{!!model?.meta?.description
											? model?.meta?.description
											: model?.ollama?.digest
												? `${model.id} (${model?.ollama?.digest})`
												: model.id}
									</span>
								</div>
							</div>
						</button>
						<div class="flex flex-row gap-0.5 items-center self-center">
							<button
								class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
								type="button"
								on:click={() => {
									selectedModelId = model.id;
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
									class="w-4 h-4"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
									/>
								</svg>
							</button>

							<div class="ml-1">
								<Tooltip
									content={(model?.is_active ?? true) ? $i18n.t('Enabled') : $i18n.t('Disabled')}
								>
									<Switch
										bind:state={model.is_active}
										on:change={async () => {
											toggleModelHandler(model);
										}}
									/>
								</Tooltip>
							</div>
						</div>
					</div>
				{/each}
			{:else}
				<div class="flex flex-col items-center justify-center w-full h-20">
					<div class="text-gray-500 dark:text-gray-400 text-xs">
						{$i18n.t('No models found')}
					</div>
				</div>
			{/if}
		</div>

		{#if $user?.role === 'admin'}
			<div class=" flex justify-end w-full mb-3">
				<div class="flex space-x-1">
					<input
						id="models-import-input"
						bind:this={modelsImportInputElement}
						bind:files={importFiles}
						type="file"
						accept=".json"
						hidden
						on:change={() => {
							console.log(importFiles);

							let reader = new FileReader();
							reader.onload = async (event) => {
								let savedModels = JSON.parse(event.target.result);
								console.log(savedModels);

								for (const model of savedModels) {
									if (Object.keys(model).includes('base_model_id')) {
										if (model.base_model_id === null) {
											upsertModelHandler(model);
										}
									} else {
										if (model?.info ?? false) {
											if (model.info.base_model_id === null) {
												upsertModelHandler(model.info);
											}
										}
									}
								}

								await _models.set(await getModels(localStorage.token));
								init();
							};

							reader.readAsText(importFiles[0]);
						}}
					/>

					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
						on:click={() => {
							modelsImportInputElement.click();
						}}
					>
						<div class=" self-center mr-2 font-medium line-clamp-1">
							{$i18n.t('Import Presets')}
						</div>

						<div class=" self-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-3.5 h-3.5"
							>
								<path
									fill-rule="evenodd"
									d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</button>

					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
						on:click={async () => {
							downloadModels(models);
						}}
					>
						<div class=" self-center mr-2 font-medium line-clamp-1">
							{$i18n.t('Export Presets')}
						</div>

						<div class=" self-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-3.5 h-3.5"
							>
								<path
									fill-rule="evenodd"
									d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</button>
				</div>
			</div>
		{/if}
	{:else}
		<ModelEditor
			edit
			model={models.find((m) => m.id === selectedModelId)}
			preset={false}
			onSubmit={(model) => {
				console.log(model);
				upsertModelHandler(model);
				selectedModelId = null;
			}}
			onBack={() => {
				selectedModelId = null;
			}}
		/>
	{/if}
{:else}
	<div class=" h-full w-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
