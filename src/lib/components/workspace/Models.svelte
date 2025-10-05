<script lang="ts">
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';
	import Sortable from 'sortablejs';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, mobile, models as _models, settings, user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import {
		createNewModel,
		deleteModelById,
		getModels as getWorkspaceModels,
		toggleModelById,
		updateModelById
	} from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import { getGroups } from '$lib/apis/groups';

	import { capitalizeFirstLetter, copyToClipboard } from '$lib/utils';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ModelMenu from './Models/ModelMenu.svelte';
	import ModelDeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Switch from '../common/Switch.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';
	import EyeSlash from '../icons/EyeSlash.svelte';
	import Eye from '../icons/Eye.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import TagSelector from './common/TagSelector.svelte';

	let shiftKey = false;

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;
	let tagsContainerElement: HTMLDivElement;

	let loaded = false;

	let models = [];
	let tags = [];

	let viewOption = '';
	let selectedTag = '';

	let filteredModels = [];
	let selectedModel = null;

	let showModelDeleteConfirm = false;

	let group_ids = [];

	$: if (models && query !== undefined && selectedTag !== undefined && viewOption !== undefined) {
		setFilteredModels();
	}

	const setFilteredModels = async () => {
		filteredModels = models.filter((m) => {
			if (query === '' && selectedTag === '' && viewOption === '') return true;
			const lowerQuery = query.toLowerCase();
			return (
				((m.name || '').toLowerCase().includes(lowerQuery) ||
					(m.user?.name || '').toLowerCase().includes(lowerQuery) || // Search by user name
					(m.user?.email || '').toLowerCase().includes(lowerQuery)) && // Search by user email
				(selectedTag === '' ||
					m?.meta?.tags?.some((tag) => tag.name.toLowerCase() === selectedTag.toLowerCase())) &&
				(viewOption === '' ||
					(viewOption === 'created' && m.user_id === $user?.id) ||
					(viewOption === 'shared' && m.user_id !== $user?.id))
			);
		});
	};

	let query = '';
	const deleteModelHandler = async (model) => {
		const res = await deleteModelById(localStorage.token, model.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: model.id }));
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
		models = await getWorkspaceModels(localStorage.token);
	};

	const cloneModelHandler = async (model) => {
		sessionStorage.model = JSON.stringify({
			...model,
			id: `${model.id}-clone`,
			name: `${model.name} (Clone)`
		});
		goto('/workspace/models/create');
	};

	const shareModelHandler = async (model) => {
		toast.success($i18n.t('Redirecting you to Open WebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/models/create`, '_blank');

		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(model), '*');
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
	};

	const hideModelHandler = async (model) => {
		model.meta = {
			...model.meta,
			hidden: !(model?.meta?.hidden ?? false)
		};

		console.log(model);

		const res = await updateModelById(localStorage.token, model.id, model);

		if (res) {
			toast.success(
				$i18n.t(`Model {{name}} is now {{status}}`, {
					name: model.id,
					status: model.meta.hidden ? 'hidden' : 'visible'
				})
			);
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
		models = await getWorkspaceModels(localStorage.token);
	};

	const copyLinkHandler = async (model) => {
		const baseUrl = window.location.origin;
		const res = await copyToClipboard(`${baseUrl}/?model=${encodeURIComponent(model.id)}`);

		if (res) {
			toast.success($i18n.t('Copied link to clipboard'));
		} else {
			toast.error($i18n.t('Failed to copy link'));
		}
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

	const setTags = () => {
		if (models) {
			tags = models
				.filter((model) => !(model?.meta?.hidden ?? false))
				.flatMap((model) => model?.meta?.tags ?? [])
				.map((tag) => tag.name);

			// Remove duplicates and sort
			tags = Array.from(new Set(tags)).sort((a, b) => a.localeCompare(b));
		}
	};

	onMount(async () => {
		viewOption = localStorage.workspaceViewOption ?? '';

		models = await getWorkspaceModels(localStorage.token);
		let groups = await getGroups(localStorage.token);
		group_ids = groups.map((group) => group.id);

		setTags();
		loaded = true;

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

<svelte:head>
	<title>
		{$i18n.t('Models')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<ModelDeleteConfirmDialog
		bind:show={showModelDeleteConfirm}
		on:confirm={() => {
			deleteModelHandler(selectedModel);
		}}
	/>

	<div class="flex flex-col gap-1 mt-1.5 my-1">
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
							if ($_models.find((m) => m.id === model.id)) {
								await updateModelById(localStorage.token, model.id, model.info).catch((error) => {
									return null;
								});
							} else {
								await createNewModel(localStorage.token, model.info).catch((error) => {
									return null;
								});
							}
						} else {
							if (model?.id && model?.name) {
								await createNewModel(localStorage.token, model).catch((error) => {
									return null;
								});
							}
						}
					}

					await _models.set(
						await getModels(
							localStorage.token,
							$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
						)
					);
					models = await getWorkspaceModels(localStorage.token);
				};

				reader.readAsText(importFiles[0]);
			}}
		/>
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>
					{$i18n.t('Models')}
				</div>

				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
					{filteredModels.length}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				{#if $user?.role === 'admin'}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						on:click={() => {
							modelsImportInputElement.click();
						}}
					>
						<div class=" self-center font-medium line-clamp-1">
							{$i18n.t('Import')}
						</div>
					</button>

					{#if models.length}
						<button
							class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
							on:click={async () => {
								downloadModels(models);
							}}
						>
							<div class=" self-center font-medium line-clamp-1">
								{$i18n.t('Export')}
							</div>
						</button>
					{/if}
				{/if}
				<a
					class=" px-2 py-1 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					href="/workspace/models/create"
				>
					<Plus className="size-3" strokeWidth="2.5" />

					<div class=" hidden md:block md:ml-1 text-xs">{$i18n.t('New Model')}</div>
				</a>
			</div>
		</div>

		<div class=" flex flex-1 items-center w-full space-x-2 py-0.5">
			<div class="flex flex-1 items-center">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Models')}
				/>

				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => {
								query = '';
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<div
		class=" flex w-full bg-transparent overflow-x-auto scrollbar-none -mx-1"
		on:wheel={(e) => {
			if (e.deltaY !== 0) {
				e.preventDefault();
				e.currentTarget.scrollLeft += e.deltaY;
			}
		}}
	>
		<div
			class="flex gap-1 w-fit text-center text-sm rounded-full bg-transparent px-1.5 whitespace-nowrap"
			bind:this={tagsContainerElement}
		>
			<ViewSelector
				bind:value={viewOption}
				onChange={async (value) => {
					localStorage.workspaceViewOption = value;

					await tick();
					setTags();
				}}
			/>

			{#if (tags ?? []).length > 0}
				<TagSelector
					bind:value={selectedTag}
					items={tags.map((tag) => {
						return { value: tag, label: tag };
					})}
				/>
			{/if}
		</div>
	</div>

	<div class=" my-2 mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3" id="model-list">
		{#each filteredModels as model (model.id)}
			<div
				class=" flex flex-col cursor-pointer w-full px-4 py-3 border border-gray-50 dark:border-gray-850 dark:hover:bg-white/5 hover:bg-black/5 rounded-2xl transition"
				id="model-item-{model.id}"
			>
				<div class="flex gap-4 mt-1 mb-0.5">
					<div class=" w-10">
						<div
							class=" rounded-full object-cover {model.is_active
								? ''
								: 'opacity-50 dark:opacity-50'} "
						>
							<img
								src={model?.meta?.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`}
								alt="modelfile profile"
								class=" rounded-full w-full h-auto object-cover"
							/>
						</div>
					</div>

					<a
						class=" flex flex-1 cursor-pointer w-full"
						href={`/?models=${encodeURIComponent(model.id)}`}
					>
						<div class=" flex-1 self-center {model.is_active ? '' : 'text-gray-500'}">
							<Tooltip
								content={marked.parse(model?.meta?.description ?? model.id)}
								className=" w-fit"
								placement="top-start"
							>
								<div class=" font-semibold line-clamp-1">{model.name}</div>
							</Tooltip>

							<div class="flex gap-1 text-xs overflow-hidden">
								<div class="line-clamp-1">
									{#if (model?.meta?.description ?? '').trim()}
										{model?.meta?.description}
									{:else}
										{model.id}
									{/if}
								</div>
							</div>
						</div>
					</a>
				</div>

				<div class="flex justify-between items-center -mb-0.5 px-0.5 mt-1.5">
					<div class=" text-xs mt-0.5">
						<Tooltip
							content={model?.user?.email ?? $i18n.t('Deleted User')}
							className="flex shrink-0"
							placement="top-start"
						>
							<div class="shrink-0 text-gray-500">
								{$i18n.t('By {{name}}', {
									name: capitalizeFirstLetter(
										model?.user?.name ?? model?.user?.email ?? $i18n.t('Deleted User')
									)
								})}
							</div>
						</Tooltip>
					</div>

					<div class="flex flex-row gap-0.5 items-center">
						{#if shiftKey}
							<Tooltip content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}>
								<button
									class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									type="button"
									on:click={() => {
										hideModelHandler(model);
									}}
								>
									{#if model?.meta?.hidden}
										<EyeSlash />
									{:else}
										<Eye />
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
							{#if $user?.role === 'admin' || model.user_id === $user?.id || model.access_control.write.group_ids.some( (wg) => group_ids.includes(wg) )}
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
							{/if}

							<ModelMenu
								user={$user}
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
								hideHandler={() => {
									hideModelHandler(model);
								}}
								copyLinkHandler={() => {
									copyLinkHandler(model);
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

							<div class="ml-1">
								<Tooltip content={model.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
									<Switch
										bind:state={model.is_active}
										on:change={async (e) => {
											toggleModelById(localStorage.token, model.id);
											_models.set(
												await getModels(
													localStorage.token,
													$config?.features?.enable_direct_connections &&
														($settings?.directConnections ?? null)
												)
											);
										}}
									/>
								</Tooltip>
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/each}
	</div>

	{#if $config?.features.enable_community_sharing}
		<div class=" my-16">
			<div class=" text-xl font-medium mb-1 line-clamp-1">
				{$i18n.t('Made by Open WebUI Community')}
			</div>

			<a
				class=" flex cursor-pointer items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-850 w-full mb-2 px-3.5 py-1.5 rounded-xl transition"
				href="https://openwebui.com/models"
				target="_blank"
			>
				<div class=" self-center">
					<div class=" font-semibold line-clamp-1">{$i18n.t('Discover a model')}</div>
					<div class=" text-sm line-clamp-1">
						{$i18n.t('Discover, download, and explore model presets')}
					</div>
				</div>

				<div>
					<div>
						<ChevronRight />
					</div>
				</div>
			</a>
		</div>
	{/if}
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
