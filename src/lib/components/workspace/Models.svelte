<script lang="ts">
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';
	import Sortable from 'sortablejs';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');

	import {
		WEBUI_NAME,
		config,
		mobile,
		models as _models,
		settings,
		user,
		workspaceActions
	} from '$lib/stores';
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
	import { updateUserSettings } from '$lib/apis/users';

	import { capitalizeFirstLetter, copyToClipboard } from '$lib/utils';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import CheckCircle from '../icons/CheckCircle.svelte';
	import Minus from '../icons/Minus.svelte';
	import ModelMenu from './Models/ModelMenu.svelte';
	import ModelDeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Switch from '../common/Switch.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';
	import EyeSlash from '../icons/EyeSlash.svelte';
	import Eye from '../icons/Eye.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import TagSelector from './common/TagSelector.svelte';
	import CommunityDiscover from './common/CommunityDiscover.svelte';
	import Pagination from '../common/Pagination.svelte';
	import Badge from '$lib/components/common/Badge.svelte';

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

	let searchDebounceTimer;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'models-new',
				label: $i18n.t('Create'),
				href: '/workspace/models/create'
			},
			{
				id: 'models-import',
				label: $i18n.t('Import JSON'),
				onClick: () => modelsImportInputElement?.click(),
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.models_import
			},
			{
				id: 'models-export',
				label: $i18n.t('Export JSON'),
				onClick: async () => {
					await downloadModels(models);
				},
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.models_export
			}
		]);
	}

	$: if (loaded && page !== undefined && selectedTag !== undefined && viewOption !== undefined) {
		getModelList();
	}

	const getModelList = async () => {
		if (!loaded) return;

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

		const tab = await window.open(`${url}/post?type=model`, '_blank');

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

	const pinModelHandler = async (modelId) => {
		let pinnedModels = $settings?.pinnedModels ?? [];

		if (pinnedModels.includes(modelId)) {
			pinnedModels = pinnedModels.filter((id) => id !== modelId);
		} else {
			pinnedModels = [...new Set([...pinnedModels, modelId])];
		}

		settings.set({ ...$settings, pinnedModels: pinnedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	const fetchAllWorkspaceModels = async () => {
		// Fetch all workspace models across every page
		const allModels = [];
		let currentPage = 1;
		let fetchedTotal = 0;

		while (true) {
			const res = await getWorkspaceModels(
				localStorage.token,
				query,
				viewOption,
				selectedTag,
				null,
				null,
				currentPage
			);
			if (!res || !res.items || res.items.length === 0) break;
			allModels.push(...res.items);
			fetchedTotal = res.total;
			if (allModels.length >= fetchedTotal) break;
			currentPage++;
		}

		return allModels;
	};

	const enableAllHandler = async () => {
		const allModels = await fetchAllWorkspaceModels();
		const modelsToEnable = allModels.filter((m) => !(m.is_active ?? true));
		if (modelsToEnable.length === 0) return;
		// Optimistic UI update for current page
		(models ?? []).forEach((m) => (m.is_active = true));
		models = models;
		// Sync with server
		await Promise.all(modelsToEnable.map((model) => toggleModelById(localStorage.token, model.id)));
		await getModelList();
	};

	const disableAllHandler = async () => {
		const allModels = await fetchAllWorkspaceModels();
		const modelsToDisable = allModels.filter((m) => m.is_active ?? true);
		if (modelsToDisable.length === 0) return;
		// Optimistic UI update for current page
		(models ?? []).forEach((m) => (m.is_active = false));
		models = models;
		// Sync with server
		await Promise.all(
			modelsToDisable.map((model) => toggleModelById(localStorage.token, model.id))
		);
		await getModelList();
	};

	const showAllHandler = async () => {
		const allModels = await fetchAllWorkspaceModels();
		const modelsToShow = allModels.filter((m) => m?.meta?.hidden === true);
		if (modelsToShow.length === 0) return;
		// Optimistic UI update for current page
		(models ?? []).forEach((m) => {
			m.meta = { ...m.meta, hidden: false };
		});
		models = models;
		// Sync with server
		await Promise.all(
			modelsToShow.map((model) => {
				model.meta = { ...model.meta, hidden: false };
				return updateModelById(localStorage.token, model.id, model);
			})
		);
		await getModelList();
		toast.success($i18n.t('All models are now visible'));
	};

	const hideAllHandler = async () => {
		const allModels = await fetchAllWorkspaceModels();
		const modelsToHide = allModels.filter((m) => !(m?.meta?.hidden ?? false));
		if (modelsToHide.length === 0) return;
		// Optimistic UI update for current page
		(models ?? []).forEach((m) => {
			m.meta = { ...m.meta, hidden: true };
		});
		models = models;
		// Sync with server
		await Promise.all(
			modelsToHide.map((model) => {
				model.meta = { ...model.meta, hidden: true };
				return updateModelById(localStorage.token, model.id, model);
			})
		);
		await getModelList();
		toast.success($i18n.t('All models are now hidden'));
	};

	onMount(async () => {
		viewOption = localStorage.workspaceViewOption ?? '';
		page = 1;

		let groups = await getGroups(localStorage.token);
		groupIds = groups.map((group) => group.id);

		await tick();
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

	<div class="space-y-1">
		<div class="flex h-8 flex-1 items-center w-full gap-2">
			<div class="flex min-w-0 flex-1 items-center">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					aria-label={$i18n.t('Search Models')}
					placeholder={$i18n.t('Search Models')}
					maxlength="500"
					on:input={() => {
						clearTimeout(searchDebounceTimer);
						searchDebounceTimer = setTimeout(() => {
							page = 1;
							getModelList();
						}, 300);
					}}
				/>

				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
								page = 1;
								getModelList();
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<div
				class="flex max-w-[60%] shrink-0 items-center gap-1 overflow-x-auto scrollbar-none"
				bind:this={tagsContainerElement}
				on:wheel={(e) => {
					if (e.deltaY !== 0) {
						e.preventDefault();
						e.currentTarget.scrollLeft += e.deltaY;
					}
				}}
			>
				<div
					class="flex w-fit gap-0.5 text-center text-sm rounded-full bg-transparent whitespace-nowrap"
				>
					<ViewSelector
						bind:value={viewOption}
						align="end"
						onChange={async (value) => {
							localStorage.workspaceViewOption = value;
							await tick();
						}}
					/>

					{#if (tags ?? []).length > 0}
						<TagSelector
							bind:value={selectedTag}
							align="end"
							items={tags.map((tag) => {
								return { value: tag, label: tag };
							})}
						/>
					{/if}
				</div>

				<Dropdown align="end">
					<Tooltip content={$i18n.t('Actions')}>
						<button
							class="flex h-8 min-w-0 max-w-28 items-center gap-1.5 rounded-xl bg-transparent px-1.5 text-[13px] font-normal text-gray-700 transition hover:text-gray-900 dark:text-gray-200 dark:hover:text-gray-100"
							type="button"
						>
							<span class="min-w-0 truncate">{$i18n.t('Actions')}</span>
							<ChevronDown className="size-3" strokeWidth="2.5" />
						</button>
					</Tooltip>

					<div slot="content">
						<DropdownMenu className="w-[170px] shadow-sm">
							<button
								class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
								type="button"
								on:click={() => {
									enableAllHandler();
								}}
							>
								<CheckCircle className="size-3.5" />
								<div class="flex items-center">{$i18n.t('Enable All')}</div>
							</button>

							<button
								class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
								type="button"
								on:click={() => {
									disableAllHandler();
								}}
							>
								<Minus className="size-3.5" />
								<div class="flex items-center">{$i18n.t('Disable All')}</div>
							</button>

							<hr class="mx-1 my-0.5 border-gray-100 dark:border-gray-800" />

							<button
								class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
								type="button"
								on:click={() => {
									showAllHandler();
								}}
							>
								<Eye className="size-3.5" />
								<div class="flex items-center">{$i18n.t('Show All')}</div>
							</button>

							<button
								class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
								type="button"
								on:click={() => {
									hideAllHandler();
								}}
							>
								<EyeSlash className="size-3.5" />
								<div class="flex items-center">{$i18n.t('Hide All')}</div>
							</button>
						</DropdownMenu>
					</div>
				</Dropdown>
			</div>
		</div>

		{#if models !== null}
			{#if (models ?? []).length !== 0}
				<div class="my-1 grid gap-x-2 gap-y-0.5 lg:grid-cols-2" id="model-list">
					{#each models as model (model.id)}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<div
							class="flex w-full rounded-xl px-2 py-1 transition {model.write_access
								? 'cursor-pointer hover:bg-gray-50/60 dark:hover:bg-gray-850/40'
								: ''}"
							id="model-item-{model.id}"
							on:click={() => {
								if (model.write_access) {
									goto(`/workspace/models/edit?id=${encodeURIComponent(model.id)}`);
								}
							}}
						>
							<div class="flex group/item min-w-0 gap-2.5 w-full">
								<div class="self-center">
									<div class="flex">
										<div
											class="{model.is_active
												? ''
												: 'opacity-50 dark:opacity-50'} bg-transparent rounded-xl"
										>
											<img
												src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`}
												alt="modelfile profile"
												class="size-8 rounded-xl object-cover"
												loading="lazy"
												decoding="async"
												on:error={(e) => {
													e.target.src = '/favicon.png';
												}}
											/>
										</div>
									</div>
								</div>

								<div class="flex min-w-0 w-full flex-1 self-center pr-1">
									<div class="flex h-full w-full flex-1 flex-col justify-start self-center group">
										<div class="min-w-0 flex-1 w-full">
											<div class="flex min-w-0 items-center justify-between w-full gap-2">
												<Tooltip
													content={model.name}
													className="min-w-0 flex-1"
													placement="top-start"
												>
													<a
														class="line-clamp-1 text-sm font-normal capitalize hover:underline"
														href={`/?models=${encodeURIComponent(model.id)}`}
													>
														{model.name}
													</a>
												</Tooltip>

												<div class="flex shrink-0 items-center gap-1">
													{#if !model.write_access}
														<div>
															<Badge type="muted" content={$i18n.t('Read Only')} />
														</div>
													{/if}

													<div class="flex {model.is_active ? '' : 'text-gray-500'}">
														<div class="flex items-center gap-0.5">
															{#if shiftKey && model.write_access}
																<Tooltip
																	content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}
																>
																	<button
																		class="self-center w-fit rounded-lg p-1 text-sm hover:bg-black/5 dark:text-white dark:hover:bg-white/5"
																		type="button"
																		aria-label={model?.meta?.hidden
																			? $i18n.t('Show')
																			: $i18n.t('Hide')}
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
																		class="self-center w-fit rounded-lg p-1 text-sm hover:bg-black/5 dark:text-white dark:hover:bg-white/5"
																		type="button"
																		aria-label={$i18n.t('Delete')}
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
																	writeAccess={model.write_access}
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
																	pinModelHandler={() => {
																		pinModelHandler(model.id);
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
																		class="self-center w-fit rounded-lg p-1 text-sm hover:bg-black/5 dark:text-white dark:hover:bg-white/5"
																	>
																		<EllipsisHorizontal className="size-4" />
																	</div>
																</ModelMenu>
															{/if}
														</div>
													</div>

													{#if model.write_access}
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
													{/if}
												</div>
											</div>

											<div class="flex min-w-0 items-center gap-1 pr-2 text-xs text-gray-500">
												<Tooltip
													content={model?.user?.email ?? $i18n.t('Deleted User')}
													className="flex shrink-0"
													placement="top-start"
												>
													<div class="shrink-0">
														{$i18n.t('By {{name}}', {
															name: capitalizeFirstLetter(
																model?.user?.name ?? model?.user?.email ?? $i18n.t('Deleted User')
															)
														})}
													</div>
												</Tooltip>

												<div class="shrink-0">·</div>

												<Tooltip
													content={marked.parse(model?.meta?.description ?? model.id)}
													className="min-w-0 text-left"
													placement="top-start"
												>
													<div class="flex min-w-0 gap-1 overflow-hidden">
														<div class="line-clamp-1 min-w-0">
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
						<div class=" text-lg font-normal mb-1">{$i18n.t('No models found')}</div>
						<div class=" text-gray-500 text-center text-xs">
							{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
						</div>
					</div>
				</div>
			{/if}
		{:else}
			<div class="w-full h-full flex justify-center items-center py-10">
				<Spinner className="size-4" />
			</div>
		{/if}
	</div>

	{#if $config?.features.enable_community_sharing}
		<CommunityDiscover
			href="https://openwebui.com/models"
			title={$i18n.t('Discover a model')}
			description={$i18n.t('Discover, download, and explore model presets')}
		/>
	{/if}
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
