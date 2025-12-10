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
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import {
		createNewModel,
		deleteModelById,
		getModelItems as getWorkspaceModels,
		getModelTags,
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
	import Pagination from '../common/Pagination.svelte';

	let shiftKey = false;

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;
	let tagsContainerElement: HTMLDivElement;

	let loaded = false;

	let showModelDeleteConfirm = false;

	let selectedModel = null;

	let groupIds = [];

	let tags = [];
	let selectedTag = '';

	let query = '';
	let viewOption = '';

	let page = 1;
	let models = null;
	let total = null;

	$: if (
		page !== undefined &&
		query !== undefined &&
		selectedTag !== undefined &&
		viewOption !== undefined
	) {
		getModelList();
	}

	const getModelList = async () => {
		try {
			const res = await getWorkspaceModels(
				localStorage.token,
				query,
				viewOption,
				selectedTag,
				null,
				null,
				page
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				models = res.items;
				total = res.total;

				// get tags
				tags = await getModelTags(localStorage.token).catch((error) => {
					toast.error(`${error}`);
					return [];
				});
			}
		} catch (err) {
			console.error(err);
		}
	};

	const deleteModelHandler = async (model) => {
		const res = await deleteModelById(localStorage.token, model.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: model.id }));

			page = 1;
			getModelList();
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
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

			page = 1;
			getModelList();
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
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

	onMount(async () => {
		viewOption = localStorage.workspaceViewOption ?? '';
		page = 1;

		let groups = await getGroups(localStorage.token);
		groupIds = groups.map((group) => group.id);

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

	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
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
					let savedModels = [];
					try {
						savedModels = JSON.parse(event.target.result);
						console.log(savedModels);
					} catch (e) {
						toast.error($i18n.t('Invalid JSON file'));
						return;
					}

					for (const model of savedModels) {
						if (model?.info ?? false) {
							if ($_models.find((m) => m.id === model.id)) {
								await updateModelById(localStorage.token, model.id, model.info).catch((error) => {
									toast.error(`${error}`);
									return null;
								});
							} else {
								await createNewModel(localStorage.token, model.info).catch((error) => {
									toast.error(`${error}`);
									return null;
								});
							}
						} else {
							if (model?.id && model?.name) {
								await createNewModel(localStorage.token, model).catch((error) => {
									toast.error(`${error}`);
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

					page = 1;
					getModelList();
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
					{total}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models_import}
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
				{/if}

				{#if total && ($user?.role === 'admin' || $user?.permissions?.workspace?.models_export)}
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
				<a
					class=" px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					href="/workspace/models/create"
				>
					<Plus className="size-3" strokeWidth="2.5" />

					<div class=" hidden md:block md:ml-1 text-xs">{$i18n.t('New Model')}</div>
				</a>
			</div>
		</div>
	</div>

	<div
		class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
	>
		<div class="px-3.5 flex flex-1 items-center w-full space-x-2 py-0.5 pb-2">
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

		<div
			class="px-3 flex w-full bg-transparent overflow-x-auto scrollbar-none"
			on:wheel={(e) => {
				if (e.deltaY !== 0) {
					e.preventDefault();
					e.currentTarget.scrollLeft += e.deltaY;
				}
			}}
		>
			<div
				class="flex gap-0.5 w-fit text-center text-sm rounded-full bg-transparent px-0.5 whitespace-nowrap"
				bind:this={tagsContainerElement}
			>
				<ViewSelector
					bind:value={viewOption}
					onChange={async (value) => {
						localStorage.workspaceViewOption = value;
						await tick();
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

		{#if (models ?? []).length !== 0}
			<div class=" px-3 my-2 gap-1 lg:gap-2 grid lg:grid-cols-2" id="model-list">
				{#each models as model (model.id)}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<div
						class="  flex cursor-pointer dark:hover:bg-gray-850/50 hover:bg-gray-50 transition rounded-2xl w-full p-2.5"
						id="model-item-{model.id}"
						on:click={() => {
							if (
								$user?.role === 'admin' ||
								model.user_id === $user?.id ||
								model.access_control.write.group_ids.some((wg) => groupIds.includes(wg))
							) {
								goto(`/workspace/models/edit?id=${encodeURIComponent(model.id)}`);
							}
						}}
					>
						<div class="flex group/item gap-3.5 w-full">
							<div class="self-center pl-0.5">
								<div class="flex bg-white rounded-2xl">
									<div
										class="{model.is_active
											? ''
											: 'opacity-50 dark:opacity-50'} bg-transparent rounded-2xl"
									>
										<img
											src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`}
											alt="modelfile profile"
											class=" rounded-2xl size-12 object-cover"
										/>
									</div>
								</div>
							</div>

							<div class=" shrink-0 flex w-full min-w-0 flex-1 pr-1 self-center">
								<div class="flex h-full w-full flex-1 flex-col justify-start self-center group">
									<div class="flex-1 w-full">
										<div class="flex items-center justify-between w-full">
											<Tooltip content={model.name} className=" w-fit" placement="top-start">
												<a
													class=" font-medium line-clamp-1 hover:underline capitalize"
													href={`/?models=${encodeURIComponent(model.id)}`}
												>
													{model.name}
												</a>
											</Tooltip>

											<div class=" flex items-center gap-1">
												<div
													class="flex justify-end w-full {model.is_active ? '' : 'text-gray-500'}"
												>
													<div class="flex justify-between items-center w-full">
														<div class=""></div>
														<div class="flex flex-row gap-0.5 items-center">
															{#if shiftKey}
																<Tooltip
																	content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}
																>
																	<button
																		class="self-center w-fit text-sm p-1.5 dark:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																		type="button"
																		on:click={(e) => {
																			e.stopPropagation();
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
																		class="self-center w-fit text-sm p-1.5 dark:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																		type="button"
																		on:click={(e) => {
																			e.stopPropagation();
																			deleteModelHandler(model);
																		}}
																	>
																		<GarbageBin />
																	</button>
																</Tooltip>
															{:else}
																<ModelMenu
																	user={$user}
																	{model}
																	editHandler={() => {
																		goto(
																			`/workspace/models/edit?id=${encodeURIComponent(model.id)}`
																		);
																	}}
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
																	<div
																		class="self-center w-fit p-1 text-sm dark:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
																	>
																		<EllipsisHorizontal className="size-5" />
																	</div>
																</ModelMenu>
															{/if}
														</div>
													</div>
												</div>

												<button
													on:click={(e) => {
														e.stopPropagation();
													}}
												>
													<Tooltip
														content={model.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}
													>
														<Switch
															bind:state={model.is_active}
															on:change={async () => {
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
												</button>
											</div>
										</div>

										<div class=" flex gap-1 pr-2 -mt-1 items-center">
											<Tooltip
												content={model?.user?.email ?? $i18n.t('Deleted User')}
												className="flex shrink-0"
												placement="top-start"
											>
												<div class="shrink-0 text-gray-500 text-xs">
													{$i18n.t('By {{name}}', {
														name: capitalizeFirstLetter(
															model?.user?.name ?? model?.user?.email ?? $i18n.t('Deleted User')
														)
													})}
												</div>
											</Tooltip>

											<div>·</div>

											<Tooltip
												content={marked.parse(model?.meta?.description ?? model.id)}
												className=" w-fit text-left"
												placement="top-start"
											>
												<div class="flex gap-1 text-xs overflow-hidden">
													<div class="line-clamp-1">
														{#if (model?.meta?.description ?? '').trim()}
															{model?.meta?.description}
														{:else}
															{model.id}
														{/if}
													</div>
												</div>
											</Tooltip>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>

			{#if total > 30}
				<Pagination bind:page count={total} perPage={30} />
			{/if}
		{:else}
			<div class=" w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class=" text-3xl mb-3">😕</div>
					<div class=" text-lg font-medium mb-1">{$i18n.t('No models found')}</div>
					<div class=" text-gray-500 text-center text-xs">
						{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
					</div>
				</div>
			</div>
		{/if}
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
					<div class=" font-medium line-clamp-1">{$i18n.t('Discover a model')}</div>
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
