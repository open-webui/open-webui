<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { toast } from 'svelte-sonner';
	import Sortable from 'sortablejs';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');
	dayjs.extend(relativeTime);

	import {
		WEBUI_NAME,
		config,
		mobile,
		models as _models,
		settings,
		user,
		workspaceActions
	} from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import {
		createNewModel,
		deleteModelById,
		getModelById,
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
	import ChevronUp from '../icons/ChevronUp.svelte';

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
	let sortKey = 'updated_at';
	let sortDirection = 'desc';

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

	$: if (
		loaded &&
		page !== undefined &&
		selectedTag !== undefined &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		getModelList();
	}

	const setSortKey = (key: string) => {
		if (sortKey === key) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDirection = key === 'updated_at' ? 'desc' : 'asc';
		}
	};

	const openModel = (model) => {
		if (model.write_access) {
			goto(`/workspace/models/edit?id=${encodeURIComponent(model.id)}`);
		}
	};

	const shouldIgnoreRowClick = (target: EventTarget | null) => {
		return target instanceof Element && !!target.closest('button, a, input, [role="menu"]');
	};

	const getModelList = async () => {
		if (!loaded) return;

		try {
			const res = await getWorkspaceModels(
				localStorage.token,
				query,
				viewOption,
				selectedTag,
				sortKey,
				sortDirection,
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

	const getFullModel = async (model: any) =>
		(await getModelById(localStorage.token, model.id).catch(() => null)) ?? model;

	const cloneModelHandler = async (model) => {
		model = await getFullModel(model);
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
		const fullModel = getFullModel(model);

		const tab = await window.open(`${url}/post?type=model`, '_blank');

		const messageHandler = async (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(await fullModel), '*');
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
	};

	const hideModelHandler = async (model) => {
		const updatedModel = {
			...model,
			meta: {
				...model.meta,
				hidden: !(model?.meta?.hidden ?? false)
			}
		};

		const res = await updateModelById(localStorage.token, updatedModel.id, updatedModel);

		if (res) {
			models = models.map((model) => (model.id === updatedModel.id ? updatedModel : model));
			toast.success(
				$i18n.t(`Model {{name}} is now {{status}}`, {
					name: updatedModel.id,
					status: updatedModel.meta.hidden ? 'hidden' : 'visible'
				})
			);

			page = 1;
			await getModelList();
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
		models = await Promise.all(models.map(getFullModel));
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const exportModelHandler = async (model) => {
		model = await getFullModel(model);
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
		{$i18n.t('Models')} / {$WEBUI_NAME}
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
				<div class="my-1" id="model-list">
					<div
						class="flex w-full items-center gap-2 px-1.5 pb-0.5 text-xs text-gray-400 dark:text-gray-600"
					>
						<button
							class="flex min-w-0 flex-1 items-center gap-1 py-0.5 text-left"
							type="button"
							on:click={() => setSortKey('name')}
						>
							{$i18n.t('Title')}
							{#if sortKey === 'name'}
								{#if sortDirection === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							{/if}
						</button>

						<div class="hidden w-44 shrink-0 md:block"></div>

						<button
							class="flex w-36 shrink-0 items-center justify-end gap-1 py-0.5 text-right"
							type="button"
							on:click={() => setSortKey('updated_at')}
						>
							{$i18n.t('Updated at')}
							{#if sortKey === 'updated_at'}
								{#if sortDirection === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							{/if}
						</button>
					</div>

					<div class="grid gap-y-0.5">
						{#each models as model (model.id)}
							<div
								class="group flex min-h-8 w-full items-center gap-2 overflow-hidden rounded-xl px-2 py-1 text-left {model.write_access
									? 'cursor-pointer'
									: ''} {model?.meta?.hidden ? 'opacity-50 dark:opacity-50' : ''}"
								id="model-item-{model.id}"
								role="button"
								tabindex={model.write_access ? 0 : -1}
								on:click={(e) => {
									if (shouldIgnoreRowClick(e.target)) return;
									openModel(model);
								}}
								on:keydown={(e) => {
									if (e.currentTarget !== e.target) return;
									if (e.key === 'Enter' || e.key === ' ') {
										e.preventDefault();
										openModel(model);
									}
								}}
							>
								<div class="mr-1 shrink-0 self-center">
									<div class="{model.is_active ? '' : 'opacity-50 dark:opacity-50'} bg-transparent">
										<img
											src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`}
											alt=""
											class="size-7 rounded-lg object-cover"
											loading="lazy"
											decoding="async"
											on:error={(e) => {
												e.target.src = '/favicon.png';
											}}
										/>
									</div>
								</div>

								<div class="flex min-w-0 flex-1 items-center gap-1 overflow-hidden">
									<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
										<div class="flex min-w-0 items-center gap-2 overflow-hidden">
											<div class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
												<Tooltip content={model.name} className="min-w-0" placement="top-start">
													<a
														href={`/?model=${encodeURIComponent(model.id)}`}
														class="truncate text-[13px] leading-5 text-gray-800 group-hover:underline dark:text-gray-200"
													>
														{model.name}
													</a>
												</Tooltip>

												<div
													class="min-w-0 max-w-[40%] shrink-0 truncate text-[11px] leading-5 text-gray-500"
												>
													{model.id}
												</div>

												<Tooltip content={dayjs(model.updated_at * 1000).format('LLLL')}>
													<div
														class="shrink-0 truncate text-[11px] leading-5 text-gray-400 dark:text-gray-600"
													>
														{dayjs(model.updated_at * 1000).fromNow()}
													</div>
												</Tooltip>

												{#if !model.write_access}
													<Badge type="muted" content={$i18n.t('Read Only')} />
												{/if}
											</div>
										</div>

										<Tooltip
											content={(model?.meta?.description ?? '').trim() ||
												model.base_model_id ||
												$i18n.t('No description')}
											className="min-w-0"
											placement="top-start"
										>
											<div
												class="truncate text-[0.6875rem] leading-4 text-gray-400 dark:text-gray-600"
											>
												{(model?.meta?.description ?? '').trim() ||
													model.base_model_id ||
													$i18n.t('No description')}
											</div>
										</Tooltip>
									</div>
								</div>

								<div
									class="hidden max-w-44 shrink-0 self-center truncate text-right text-[11px] leading-5 text-gray-500 dark:text-gray-500 md:block"
								>
									<Tooltip
										content={model?.user?.email ?? $i18n.t('Deleted User')}
										className="min-w-0"
										placement="top-start"
									>
										<div class="truncate">
											{capitalizeFirstLetter(
												model?.user?.name ?? model?.user?.email ?? $i18n.t('Deleted User')
											)}
										</div>
									</Tooltip>
								</div>

								<div class="ml-2 flex shrink-0 flex-row items-center self-center">
									{#if shiftKey && model.write_access}
										<Tooltip content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}>
											<button
												class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
												type="button"
												aria-label={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}
												on:click={(e) => {
													e.preventDefault();
													e.stopPropagation();
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

										<Tooltip content={$i18n.t('Delete')}>
											<button
												class="ml-0.5 flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
												type="button"
												aria-label={$i18n.t('Delete')}
												on:click={(e) => {
													e.preventDefault();
													e.stopPropagation();
													deleteModelHandler(model);
												}}
											>
												<GarbageBin className="size-4" />
											</button>
										</Tooltip>
									{:else}
										<div class="flex shrink-0 flex-row items-center gap-1.5 self-center">
											<ModelMenu
												user={$user}
												{model}
												writeAccess={model.write_access}
												editHandler={() => {
													goto(`/workspace/models/edit?id=${encodeURIComponent(model.id)}`);
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
													class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
												>
													<EllipsisHorizontal className="size-4" />
												</div>
											</ModelMenu>

											{#if model.write_access}
												<button
													class="flex h-6 items-center"
													type="button"
													on:click={(e) => {
														e.stopPropagation();
														e.preventDefault();
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
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</div>

				{#if total > 30}
					<Pagination bind:page count={total} perPage={30} />
				{/if}
			{:else}
				<div class="flex w-full flex-col items-center justify-center py-16 pb-24">
					<div class="max-w-sm text-center text-gray-900 dark:text-gray-100">
						<div class="mb-1.5 text-sm">{$i18n.t('No models found')}</div>
						<div class="text-center text-xs leading-5 text-gray-500">
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
