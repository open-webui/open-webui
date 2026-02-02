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
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import ManageModelsModal from './Models/ManageModelsModal.svelte';
	import ModelMenu from '$lib/components/admin/Settings/Models/ModelMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';

	let shiftKey = false;

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;

	let models = null;

	let workspaceModels = null;
	let baseModels = null;

	let filteredModels = [];
	let selectedModelId = null;

	let showConfigModal = false;
	let showManageModal = false;

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
		baseModels = await getModels(localStorage.token, null, true);

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
			const res = await createNewModel(localStorage.token, {
				meta: {},
				id: model.id,
				name: model.name,
				base_model_id: null,
				params: {},
				access_control: {},
				...model
			}).catch((error) => {
				return null;
			});

			if (res) {
				toast.success($i18n.t('Model updated successfully'));
			}
		}

		_models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
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

		// await init();
		_models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const hideModelHandler = async (model) => {
		model.meta = {
			...model.meta,
			hidden: !(model?.meta?.hidden ?? false)
		};

		console.log(model);

		toast.success(
			model.meta.hidden
				? $i18n.t(`Model {{name}} is now hidden`, {
						name: model.id
					})
				: $i18n.t(`Model {{name}} is now visible`, {
						name: model.id
					})
		);

		upsertModelHandler(model);
	};

	const exportModelHandler = async (model) => {
		let blob = new Blob([JSON.stringify([model])], {
			type: 'application/json'
		});
		saveAs(blob, `${model.id}-${Date.now()}.json`);
	};

	onMount(async () => {
		await init();

		const onKeyDown = (event) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur-sm', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur-sm', onBlur);
		};
	});
</script>

<ConfigureModelsModal bind:show={showConfigModal} initHandler={init} />
<ManageModelsModal bind:show={showManageModal} />

{#if models !== null}
	{#if selectedModelId === null}
		<!-- Header Section -->
		<div class="flex flex-col gap-3 mt-1.5 mb-4">
			<div class="flex justify-between items-center">
				<div class="flex items-center gap-3">
					<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
						{$i18n.t('Models')}
					</h2>
					<div class="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded-full border border-blue-200 dark:border-blue-800">
						<span class="text-sm font-semibold text-blue-700 dark:text-blue-400">
							{filteredModels.length}
						</span>
						<span class="text-xs text-blue-600 dark:text-blue-500">
							{filteredModels.length === 1 ? 'model' : 'models'}
						</span>
					</div>
				</div>

				<div class="flex items-center gap-2">
					<Tooltip content={$i18n.t('Manage Models')}>
						<button
							class="p-2.5 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 transition-all duration-200 hover:shadow-sm"
							type="button"
							on:click={() => {
								showManageModal = true;
							}}
						>
							<ArrowDownTray className="size-4" />
						</button>
					</Tooltip>

					<Tooltip content={$i18n.t('Settings')}>
						<button
							class="p-2.5 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 transition-all duration-200 hover:shadow-sm"
							type="button"
							on:click={() => {
								showConfigModal = true;
							}}
						>
							<Cog6 className="size-4" />
						</button>
					</Tooltip>
				</div>
			</div>

			<!-- Search Bar -->
			<div class="relative">
				<div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
					<Search className="size-4 text-gray-400" />
				</div>
				<input
					class="w-full pl-11 pr-4 py-3 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-xl placeholder:text-gray-400 dark:placeholder:text-gray-500 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all duration-200"
					bind:value={searchValue}
					placeholder={$i18n.t('Search Models')}
				/>
			</div>
		</div>

		<!-- Models List -->
		<div class="space-y-2 mb-5" id="model-list">
			{#if models.length > 0}
				{#each filteredModels as model, modelIdx (model.id)}
					<div
						class="group flex items-center gap-4 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:shadow-md transition-all duration-200 {model
							?.meta?.hidden
							? 'opacity-60 dark:opacity-60'
							: ''}"
						id="model-item-{model.id}"
					>
						<button
							class="flex flex-1 items-center gap-4 text-left cursor-pointer min-w-0"
							type="button"
							on:click={() => {
								selectedModelId = model.id;
							}}
						>
							<!-- Model Image -->
							<div class="flex-shrink-0">
								<div
									class="w-12 h-12 rounded-xl overflow-hidden ring-2 ring-gray-200 dark:ring-gray-700 {(model?.is_active ?? true)
										? ''
										: 'opacity-50 grayscale'}"
								>
									<img
										src={model?.meta?.profile_image_url ?? '/static/favicon.png'}
										alt="model profile"
										class="w-full h-full object-cover"
									/>
								</div>
							</div>

							<!-- Model Info -->
							<div class="flex-1 min-w-0 {(model?.is_active ?? true) ? '' : 'opacity-60'}">
								<Tooltip
									content={marked.parse(
										!!model?.meta?.description
											? model?.meta?.description
											: model?.ollama?.digest
												? `${model?.ollama?.digest} **(${model?.ollama?.modified_at})**`
												: model.id
									)}
									className="w-fit"
									placement="top-start"
								>
									<h3 class="font-semibold text-gray-900 dark:text-gray-100 line-clamp-1 mb-1">
										{model.name}
									</h3>
								</Tooltip>
								<p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
									{!!model?.meta?.description
										? model?.meta?.description
										: model?.ollama?.digest
											? `${model.id} (${model?.ollama?.digest})`
											: model.id}
								</p>
							</div>
						</button>

						<!-- Action Buttons -->
						<div class="flex items-center gap-1 flex-shrink-0">
							{#if shiftKey}
								<Tooltip content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}>
									<button
										class="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200"
										type="button"
										on:click={() => {
											hideModelHandler(model);
										}}
									>
										{#if model?.meta?.hidden}
											<EyeSlash className="size-4" />
										{:else}
											<Eye className="size-4" />
										{/if}
									</button>
								</Tooltip>
							{:else}
								<button
									class="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200"
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
										class="size-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
										/>
									</svg>
								</button>

								<ModelMenu
									user={$user}
									{model}
									exportHandler={() => {
										exportModelHandler(model);
									}}
									hideHandler={() => {
										hideModelHandler(model);
									}}
									onClose={() => {}}
								>
									<button
										class="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all duration-200"
										type="button"
									>
										<EllipsisHorizontal className="size-4" />
									</button>
								</ModelMenu>

								<div class="ml-2">
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
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div class="flex flex-col items-center justify-center py-16 px-4 bg-white dark:bg-gray-800 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl">
					<svg class="w-16 h-16 text-gray-400 dark:text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
					</svg>
					<p class="text-gray-500 dark:text-gray-400 text-sm font-medium">
						{$i18n.t('No models found')}
					</p>
				</div>
			{/if}
		</div>

		<!-- Import/Export Section -->
		{#if $user?.role === 'admin'}
			<div class="flex justify-end gap-2 mb-3">
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

							await _models.set(
								await getModels(
									localStorage.token,
									$config?.features?.enable_direct_connections &&
										($settings?.directConnections ?? null)
								)
							);
							init();
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

				<button
					class="flex items-center gap-2 px-4 py-2.5 text-sm font-medium bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-700 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md"
					on:click={() => {
						modelsImportInputElement.click();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
							clip-rule="evenodd"
						/>
					</svg>
					<span>{$i18n.t('Import Presets')}</span>
				</button>

				<button
					class="flex items-center gap-2 px-4 py-2.5 text-sm font-medium bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-700 rounded-lg transition-all duration-200 shadow-sm hover:shadow-md"
					on:click={async () => {
						downloadModels(models);
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
							clip-rule="evenodd"
						/>
					</svg>
					<span>{$i18n.t('Export Presets')}</span>
				</button>
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
	<div class="h-full w-full flex flex-col justify-center items-center gap-3">
		<Spinner className="size-8" />
		<p class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading models...')}</p>
	</div>
{/if}