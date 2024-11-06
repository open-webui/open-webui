<script lang="ts">
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';
	import Sortable from 'sortablejs';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';

	import { WEBUI_NAME, config, mobile, models, settings, user } from '$lib/stores';
	import { addNewModel, deleteModelById, getModelInfos, updateModelById } from '$lib/apis/models';

	import { deleteModel } from '$lib/apis/ollama';
	import { goto } from '$app/navigation';

	import { getModels } from '$lib/apis';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ModelMenu from './Models/ModelMenu.svelte';
	import ModelDeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';

	const i18n = getContext('i18n');

	let shiftKey = false;

	let showModelDeleteConfirm = false;

	let localModelfiles = [];

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;

	let _models = [];

	let filteredModels = [];
	let selectedModel = null;

	$: if (_models) {
		filteredModels = _models
			.filter((m) => m?.owned_by !== 'arena')
			.filter(
				(m) => searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase())
			);
	}

	let sortable = null;
	let searchValue = '';

	const deleteModelHandler = async (model) => {
		console.log(model.info);
		if (!model?.info) {
			toast.error(
				$i18n.t('{{ owner }}: You cannot delete a base model', {
					owner: model.owned_by.toUpperCase()
				})
			);
			return null;
		}

		const res = await deleteModelById(localStorage.token, model.id);

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: model.id }));
		}

		await models.set(await getModels(localStorage.token));
		_models = $models;
	};

	const cloneModelHandler = async (model) => {
		if ((model?.info?.base_model_id ?? null) === null) {
			toast.error($i18n.t('You cannot clone a base model'));
			return;
		} else {
			sessionStorage.model = JSON.stringify({
				...model,
				id: `${model.id}-clone`,
				name: `${model.name} (Clone)`
			});
			goto('/workspace/models/create');
		}
	};

	const shareModelHandler = async (model) => {
		toast.success($i18n.t('Redirecting you to OpenWebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/models/create`, '_blank');

		// Define the event handler function
		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(model), '*');

				// Remove the event listener after handling the message
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
	};

	const moveToTopHandler = async (model) => {
		// find models with position 0 and set them to 1
		const topModels = _models.filter((m) => m.info?.meta?.position === 0);
		for (const m of topModels) {
			let info = m.info;
			if (!info) {
				info = {
					id: m.id,
					name: m.name,
					meta: {
						position: 1
					},
					params: {}
				};
			}

			info.meta = {
				...info.meta,
				position: 1
			};

			await updateModelById(localStorage.token, info.id, info);
		}

		let info = model.info;

		if (!info) {
			info = {
				id: model.id,
				name: model.name,
				meta: {
					position: 0
				},
				params: {}
			};
		}

		info.meta = {
			...info.meta,
			position: 0
		};

		const res = await updateModelById(localStorage.token, info.id, info);

		if (res) {
			toast.success($i18n.t(`Model {{name}} is now at the top`, { name: info.id }));
		}

		await models.set(await getModels(localStorage.token));
		_models = $models;
	};

	const hideModelHandler = async (model) => {
		let info = model.info;

		if (!info) {
			info = {
				id: model.id,
				name: model.name,
				meta: {
					suggestion_prompts: null
				},
				params: {}
			};
		}

		info.meta = {
			...info.meta,
			hidden: !(info?.meta?.hidden ?? false)
		};

		console.log(info);

		const res = await updateModelById(localStorage.token, info.id, info);

		if (res) {
			toast.success(
				$i18n.t(`Model {{name}} is now {{status}}`, {
					name: info.id,
					status: info.meta.hidden ? 'hidden' : 'visible'
				})
			);
		}

		await models.set(await getModels(localStorage.token));
		_models = $models;
	};

	const downloadModels = async (models) => {
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const exportModelHandler = async (model) => {
		let blob = new Blob([JSON.stringify([model])], {
			type: 'application/json'
		});
		saveAs(blob, `${model.id}-${Date.now()}.json`);
	};

	const positionChangeHandler = async () => {
		// Get the new order of the models
		const modelIds = Array.from(document.getElementById('model-list').children).map((child) =>
			child.id.replace('model-item-', '')
		);

		// Update the position of the models
		for (const [index, id] of modelIds.entries()) {
			const model = $models.find((m) => m.id === id);
			if (model) {
				let info = model.info;

				if (!info) {
					info = {
						id: model.id,
						name: model.name,
						meta: {
							position: index
						},
						params: {}
					};
				}

				info.meta = {
					...info.meta,
					position: index
				};
				await updateModelById(localStorage.token, info.id, info);
			}
		}

		await tick();
		await models.set(await getModels(localStorage.token));
	};

	onMount(async () => {
		// Legacy code to sync localModelfiles with models
		_models = $models;
		localModelfiles = JSON.parse(localStorage.getItem('modelfiles') ?? '[]');

		if (localModelfiles) {
			console.log(localModelfiles);
		}

		if (!$mobile) {
			// SortableJS
			sortable = new Sortable(document.getElementById('model-list'), {
				animation: 150,
				onUpdate: async (event) => {
					console.log(event);
					positionChangeHandler();
				}
			});
		}

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
		window.addEventListener('blur', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Models')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<ModelDeleteConfirmDialog
	bind:show={showModelDeleteConfirm}
	on:confirm={() => {
		deleteModelHandler(selectedModel);
	}}
/>

<div class=" flex w-full space-x-2 mb-2.5">
	<div class="flex flex-1">
		<div class=" self-center ml-1 mr-3">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
		<input
			class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
			bind:value={searchValue}
			placeholder={$i18n.t('Search Models')}
		/>
	</div>

	<div>
		<a
			class=" px-2 py-2 rounded-xl border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition font-medium text-sm flex items-center space-x-1"
			href="/workspace/models/create"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
				/>
			</svg>
		</a>
	</div>
</div>

<div class="mb-3.5">
	<div class="flex justify-between items-center">
		<div class="flex md:self-center text-base font-medium px-0.5">
			{$i18n.t('Models')}
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
			<span class="text-base font-medium text-gray-500 dark:text-gray-300"
				>{filteredModels.length}</span
			>
		</div>
	</div>
</div>

<a class=" flex space-x-4 cursor-pointer w-full mb-2 px-3 py-1" href="/workspace/models/create">
	<div class=" self-center w-8 flex-shrink-0">
		<div
			class="w-full h-8 flex justify-center rounded-full bg-transparent dark:bg-gray-700 border border-dashed border-gray-200"
		>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6">
				<path
					fill-rule="evenodd"
					d="M12 3.75a.75.75 0 01.75.75v6.75h6.75a.75.75 0 010 1.5h-6.75v6.75a.75.75 0 01-1.5 0v-6.75H4.5a.75.75 0 010-1.5h6.75V4.5a.75.75 0 01.75-.75z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
	</div>

	<div class=" self-center">
		<div class=" font-semibold line-clamp-1">{$i18n.t('Create a model')}</div>
		<div class=" text-sm line-clamp-1 text-gray-500">
			{$i18n.t('Customize models for a specific purpose')}
		</div>
	</div>
</a>

<div class=" my-2 mb-5" id="model-list">
	{#each filteredModels as model}
		<div
			class=" flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl"
			id="model-item-{model.id}"
		>
			<a
				class=" flex flex-1 space-x-3.5 cursor-pointer w-full"
				href={`/?models=${encodeURIComponent(model.id)}`}
			>
				<div class=" self-start w-8 pt-0.5">
					<div
						class=" rounded-full object-cover {(model?.info?.meta?.hidden ?? false)
							? 'brightness-90 dark:brightness-50'
							: ''} "
					>
						<img
							src={model?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
							alt="modelfile profile"
							class=" rounded-full w-full h-auto object-cover"
						/>
					</div>
				</div>

				<div
					class=" flex-1 self-center {(model?.info?.meta?.hidden ?? false) ? 'text-gray-500' : ''}"
				>
					<Tooltip
						content={marked.parse(
							model?.ollama?.digest
								? `${model?.ollama?.digest} *(${model?.ollama?.modified_at})*`
								: ''
						)}
						className=" w-fit"
						placement="top-start"
					>
						<div class="  font-semibold line-clamp-1">{model.name}</div>
					</Tooltip>
					<div class=" text-xs overflow-hidden text-ellipsis line-clamp-1 text-gray-500">
						{!!model?.info?.meta?.description
							? model?.info?.meta?.description
							: model?.ollama?.digest
								? `${model.id} (${model?.ollama?.digest})`
								: model.id}
					</div>
				</div>
			</a>
			<div class="flex flex-row gap-0.5 self-center">
				{#if shiftKey}
					<Tooltip
						content={(model?.info?.meta?.hidden ?? false)
							? $i18n.t('Show Model')
							: $i18n.t('Hide Model')}
					>
						<button
							class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
							type="button"
							on:click={() => {
								hideModelHandler(model);
							}}
						>
							{#if model?.info?.meta?.hidden ?? false}
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
										d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88"
									/>
								</svg>
							{:else}
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
										d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
									/>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
									/>
								</svg>
							{/if}
						</button>
					</Tooltip>

					<Tooltip content={$i18n.t('Delete')}>
						<button
							class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
							type="button"
							on:click={() => {
								deleteModelHandler(model);
							}}
						>
							<GarbageBin />
						</button>
					</Tooltip>
				{:else}
					<a
						class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
						type="button"
						href={`/workspace/models/edit?id=${encodeURIComponent(model.id)}`}
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
					</a>

					<ModelMenu
						{model}
						shareHandler={() => {
							shareModelHandler(model);
						}}
						cloneHandler={() => {
							cloneModelHandler(model);
						}}
						exportHandler={() => {
							exportModelHandler(model);
						}}
						moveToTopHandler={() => {
							moveToTopHandler(model);
						}}
						hideHandler={() => {
							hideModelHandler(model);
						}}
						deleteHandler={() => {
							selectedModel = model;
							showModelDeleteConfirm = true;
						}}
						onClose={() => {}}
					>
						<button
							class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
							type="button"
						>
							<EllipsisHorizontal className="size-5" />
						</button>
					</ModelMenu>
				{/if}
			</div>
		</div>
	{/each}
</div>

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
						if (model?.info ?? false) {
							if ($models.find((m) => m.id === model.id)) {
								await updateModelById(localStorage.token, model.id, model.info).catch((error) => {
									return null;
								});
							} else {
								await addNewModel(localStorage.token, model.info).catch((error) => {
									return null;
								});
							}
						}
					}

					await models.set(await getModels(localStorage.token));
					_models = $models;
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
			<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Import Models')}</div>

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
				downloadModels($models);
			}}
		>
			<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Export Models')}</div>

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

	{#if localModelfiles.length > 0}
		<div class="flex">
			<div class=" self-center text-sm font-medium mr-4">
				{localModelfiles.length} Local Modelfiles Detected
			</div>

			<div class="flex space-x-1">
				<button
					class="self-center w-fit text-sm p-1.5 border dark:border-gray-600 rounded-xl flex"
					on:click={async () => {
						downloadModels(localModelfiles);

						localStorage.removeItem('modelfiles');
						localModelfiles = JSON.parse(localStorage.getItem('modelfiles') ?? '[]');
					}}
				>
					<div class=" self-center">
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
								d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
							/>
						</svg>
					</div>
				</button>
			</div>
		</div>
	{/if}
</div>

{#if $config?.features.enable_community_sharing}
	<div class=" my-16">
		<div class=" text-lg font-semibold mb-3 line-clamp-1">
			{$i18n.t('Made by OpenWebUI Community')}
		</div>

		<a
			class=" flex space-x-4 cursor-pointer w-full mb-2 px-3 py-2"
			href="https://openwebui.com/#open-webui-community"
			target="_blank"
		>
			<div class=" self-center w-10 flex-shrink-0">
				<div
					class="w-full h-10 flex justify-center rounded-full bg-transparent dark:bg-gray-700 border border-dashed border-gray-200"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						class="w-6"
					>
						<path
							fill-rule="evenodd"
							d="M12 3.75a.75.75 0 01.75.75v6.75h6.75a.75.75 0 010 1.5h-6.75v6.75a.75.75 0 01-1.5 0v-6.75H4.5a.75.75 0 010-1.5h6.75V4.5a.75.75 0 01.75-.75z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
			</div>

			<div class=" self-center">
				<div class=" font-semibold line-clamp-1">{$i18n.t('Discover a model')}</div>
				<div class=" text-sm line-clamp-1">
					{$i18n.t('Discover, download, and explore model presets')}
				</div>
			</div>
		</a>
	</div>
{/if}
