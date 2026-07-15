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
		getBaseModelTags,
		getBaseModels,
		toggleModelById,
		updateModelById,
		updateModelAccessGrants,
		importModels
	} from '$lib/apis/models';
	import { copyToClipboard } from '$lib/utils';
	import { page } from '$app/stores';
	import { updateUserSettings } from '$lib/apis/users';

	import { getModels } from '$lib/apis';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import ModelEditor from '$lib/components/workspace/Models/ModelEditor.svelte';
	import { toast } from 'svelte-sonner';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ModelSettingsModal from './Models/ModelSettingsModal.svelte';
	import ManageModelsModal from './Models/ManageModelsModal.svelte';
	import ModelMenu from '$lib/components/admin/Settings/Models/ModelMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { goto } from '$app/navigation';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import AdminViewSelector from './Models/AdminViewSelector.svelte';
	import TagSelector from '$lib/components/workspace/common/TagSelector.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';

	type ModelListItem = { id: string; name?: string };

	let shiftKey = false;

	let modelsImportInProgress = false;
	let importFiles;
	let modelsImportInputElement: HTMLInputElement;
	let tagsContainerElement: HTMLDivElement;

	let models = null;

	let workspaceModels: ModelListItem[] = [];
	let baseModels: ModelListItem[] = [];

	let filteredModels = [];
	let selectedModelId = null;

	let showConfigModal = false;
	let showManageModal = false;

	let viewOption = ''; // '' = All, 'enabled', 'disabled', 'visible', 'hidden'
	let tags: string[] = [];
	let selectedTag = '';

	const perPage = 30;
	let currentPage = 1;

	const isPublicModel = (model) => {
		return (model?.access_grants ?? []).some(
			(g) => g.principal_type === 'user' && g.principal_id === '*' && g.permission === 'read'
		);
	};

	const isSharedModel = (model) => (model?.access_grants ?? []).length > 0 && !isPublicModel(model);

	const modelAccessLabel = (model) => {
		if (isPublicModel(model)) {
			return $i18n.t('Public');
		}
		if (isSharedModel(model)) {
			return $i18n.t('Shared');
		}
		return $i18n.t('Private');
	};

	const modelAccessClass = (model) => {
		if (isPublicModel(model)) {
			return 'text-[#4f7a5a] dark:text-[#8db395]';
		}
		if (isSharedModel(model)) {
			return 'text-[#4f6f93] dark:text-[#8ba6c6]';
		}
		return 'text-gray-500 dark:text-gray-400';
	};

	$: if (models) {
		filteredModels = models
			.filter((m) => searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase()))
			.filter((m) => {
				if (viewOption === 'enabled') return m?.is_active ?? true;
				if (viewOption === 'disabled') return !(m?.is_active ?? true);
				if (viewOption === 'visible') return !(m?.meta?.hidden ?? false);
				if (viewOption === 'hidden') return m?.meta?.hidden === true;
				if (viewOption === 'public') return isPublicModel(m);
				if (viewOption === 'private') return !isPublicModel(m);
				return true; // All
			})
			.sort((a, b) => {
				return (a?.name ?? a?.id ?? '').localeCompare(b?.name ?? b?.id ?? '');
			});
	}

	let searchValue = '';

	$: if (searchValue || viewOption !== undefined) {
		currentPage = 1;
	}

	const enableAllHandler = async () => {
		const modelsToEnable = filteredModels.filter((m) => !(m.is_active ?? true));
		// Optimistic UI update
		modelsToEnable.forEach((m) => (m.is_active = true));
		models = models;
		// Sync with server
		await Promise.all(
			modelsToEnable.map((model) => upsertModelHandler(model, { is_active: true }, false))
		);

		await tick();
		await init();
	};

	const disableAllHandler = async () => {
		const modelsToDisable = filteredModels.filter((m) => m.is_active ?? true);
		// Optimistic UI update
		modelsToDisable.forEach((m) => (m.is_active = false));
		models = models;
		// Sync with server
		await Promise.all(
			modelsToDisable.map((model) => upsertModelHandler(model, { is_active: false }, false))
		);

		await tick();
		await init();
	};

	const showAllHandler = async () => {
		const modelsToShow = filteredModels.filter((m) => m?.meta?.hidden === true);
		// Optimistic UI update
		modelsToShow.forEach((m) => {
			m.meta = { ...m.meta, hidden: false };
		});
		models = models;
		// Sync with server
		await Promise.all(
			modelsToShow.map((model) =>
				upsertModelHandler(model, { meta: { ...model.meta, hidden: false } }, false)
			)
		);

		toast.success($i18n.t('All models are now visible'));
		await tick();
		await init();
	};

	const hideAllHandler = async () => {
		const modelsToHide = filteredModels.filter((m) => !(m?.meta?.hidden ?? false));
		// Optimistic UI update
		modelsToHide.forEach((m) => {
			m.meta = { ...m.meta, hidden: true };
		});
		models = models;
		// Sync with server
		await Promise.all(
			modelsToHide.map((model) =>
				upsertModelHandler(model, { meta: { ...model.meta, hidden: true } }, false)
			)
		);

		toast.success($i18n.t('All models are now hidden'));
		await tick();
		await init();
	};

	const downloadModels = async (models) => {
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const init = async () => {
		models = null;

		tags = await getBaseModelTags(localStorage.token);
		if (selectedTag && !tags.includes(selectedTag)) {
			selectedTag = '';
		}

		workspaceModels = await getBaseModels(localStorage.token, selectedTag);
		baseModels = await getModels(localStorage.token, null, true);
		const workspaceModelIds = new Set<string>(workspaceModels.map((wm: ModelListItem) => wm.id));

		models = baseModels
			.filter((m: ModelListItem) => !selectedTag || workspaceModelIds.has(m.id))
			.map((m: ModelListItem) => {
				const workspaceModel = workspaceModels.find((wm: ModelListItem) => wm.id === m.id);

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

		_models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const upsertModelHandler = async (model, overrides = {}, showToast = true) => {
		model = { ...model, base_model_id: null, ...overrides };

		if (workspaceModels.find((m) => m.id === model.id)) {
			const res = await updateModelById(localStorage.token, model.id, model).catch((error) => {
				return null;
			});

			if (res && showToast) {
				toast.success($i18n.t('Model updated successfully'));
			}
		} else {
			const res = await createNewModel(localStorage.token, {
				meta: {},
				id: model.id,
				name: model.name,
				base_model_id: null,
				params: {},
				access_grants: [],
				...model
			}).catch((error) => {
				return null;
			});

			if (res && showToast) {
				toast.success($i18n.t('Model updated successfully'));
				await init();
			}
		}
	};

	const toggleModelHandler = async (model) => {
		if (!Object.keys(model).includes('base_model_id')) {
			await createNewModel(localStorage.token, {
				id: model.id,
				name: model.name,
				base_model_id: null,
				meta: {},
				params: {},
				access_grants: [],
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

		console.debug(model);

		upsertModelHandler(model, { meta: model.meta }, false);

		toast.success(
			model.meta.hidden
				? $i18n.t(`Model {{name}} is now hidden`, {
						name: model.id
					})
				: $i18n.t(`Model {{name}} is now visible`, {
						name: model.id
					})
		);
	};

	const toggleModelPrivacyHandler = async (model) => {
		const nextAccessGrants = isPublicModel(model)
			? []
			: [
					...(model?.access_grants ?? []),
					{
						principal_type: 'user',
						principal_id: '*',
						permission: 'read'
					}
				];

		const res = await updateModelAccessGrants(
			localStorage.token,
			model.id,
			model.name,
			nextAccessGrants
		).catch(() => null);

		if (res) {
			models = models.map((m) =>
				m.id === model.id ? { ...m, access_grants: res.access_grants ?? nextAccessGrants } : m
			);
			_models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
			toast.success(
				isPublicModel({ access_grants: nextAccessGrants })
					? $i18n.t('Model is now public')
					: $i18n.t('Model is now private')
			);
		}
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

	const cloneHandler = async (model) => {
		sessionStorage.model = JSON.stringify({
			...model,
			base_model_id: model.id,
			id: `${model.id}-clone`,
			name: `${model.name} (Clone)`
		});
		goto('/workspace/models/create');
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

	onMount(async () => {
		await init();
		const id = $page.url.searchParams.get('id');

		if (id) {
			selectedModelId = id;
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

<ModelSettingsModal bind:show={showConfigModal} initHandler={init} />
<ManageModelsModal bind:show={showManageModal} />

{#if models !== null}
	{#if selectedModelId === null}
		<div class="flex h-full min-h-0 flex-col text-sm">
			<div class="flex items-center justify-between mb-2">
				<h2 class="text-sm font-medium text-gray-900 dark:text-white">
					{$i18n.t('Models')}
					<span class="ml-2 font-normal text-gray-500 dark:text-gray-500">
						{filteredModels.length}
					</span>
				</h2>

				<div class="flex items-center gap-2">
					{#if $user?.role === 'admin'}
						<button
							type="button"
							class="text-[0.625rem] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100 disabled:opacity-30 disabled:pointer-events-none"
							disabled={modelsImportInProgress}
							on:click={() => {
								modelsImportInputElement?.click();
							}}
						>
							{$i18n.t('Import')}
						</button>
						<button
							type="button"
							class="text-[0.625rem] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100"
							on:click={() => {
								downloadModels(models ?? []);
							}}
						>
							{$i18n.t('Export')}
						</button>
					{/if}
					<button
						type="button"
						class="text-[0.625rem] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100"
						on:click={() => {
							showManageModal = true;
						}}
					>
						{$i18n.t('Manage')}
					</button>
					<button
						type="button"
						class="text-[0.625rem] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-100"
						on:click={() => {
							showConfigModal = true;
						}}
					>
						{$i18n.t('Settings')}
					</button>
				</div>
			</div>

			{#if $user?.role === 'admin'}
				<input
					id="models-import-input"
					bind:this={modelsImportInputElement}
					bind:files={importFiles}
					type="file"
					accept=".json"
					hidden
					on:change={() => {
						if (importFiles.length > 0) {
							const reader = new FileReader();
							reader.onload = async (event) => {
								modelsImportInProgress = true;

								try {
									const models = JSON.parse(String(event.target.result));
									const res = await importModels(localStorage.token, models);

									if (res) {
										toast.success($i18n.t('Models imported successfully'));
										await init();
									} else {
										toast.error($i18n.t('Failed to import models'));
									}
								} catch (e) {
									toast.error(e?.detail ?? $i18n.t('Invalid JSON file'));
									console.error(e);
								}

								modelsImportInProgress = false;
							};
							reader.readAsText(importFiles[0]);
						}
					}}
				/>
			{/if}

			<div class="flex min-h-0 flex-1 flex-col space-y-1">
				<div class="flex h-8 shrink-0 items-center w-full gap-2">
					<div class="flex min-w-0 flex-1 items-center">
						<div class=" self-center ml-1 mr-3">
							<Search className="size-3.5" />
						</div>
						<input
							class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
							bind:value={searchValue}
							placeholder={$i18n.t('Search Models')}
						/>
						{#if searchValue}
							<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
								<button
									class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
									aria-label={$i18n.t('Clear search')}
									on:click={() => {
										searchValue = '';
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
							<AdminViewSelector bind:value={viewOption} align="end" />

							{#if (tags ?? []).length > 0}
								<TagSelector
									bind:value={selectedTag}
									align="end"
									items={tags.map((tag) => {
										return { value: tag, label: tag };
									})}
									onChange={async () => {
										currentPage = 1;
										await init();
									}}
								/>
							{/if}
						</div>

						<Dropdown align="end">
							<Tooltip content={$i18n.t('Actions')}>
								<button
									class="flex h-8 items-center gap-1.5 rounded-xl bg-transparent px-1.5 text-[13px] font-normal text-gray-700 transition hover:text-gray-900 dark:text-gray-200 dark:hover:text-gray-100"
									type="button"
								>
									<span>{$i18n.t('Actions')}</span>
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

				<div
					class="my-0.5 min-h-0 flex-1 space-y-px {filteredModels.length > 0
						? 'overflow-y-auto scrollbar-hover pr-1.5'
						: 'overflow-hidden'}"
					id="model-list"
				>
					{#if filteredModels.length > 0}
						{#each filteredModels.slice((currentPage - 1) * perPage, currentPage * perPage) as model, modelIdx (`${model.id}-${modelIdx}`)}
							<div
								class="flex cursor-pointer transition w-full px-2 py-1 rounded-xl hover:bg-gray-50/70 dark:hover:bg-gray-850/50 {model
									?.meta?.hidden
									? 'opacity-50 dark:opacity-50'
									: ''}"
								id="model-item-{model.id}"
							>
								<button
									class="flex group/item gap-2.5 w-full min-w-0 flex-1 text-left cursor-pointer"
									type="button"
									on:click={() => {
										selectedModelId = model.id;
									}}
								>
									<div class="self-center">
										<div class="flex bg-white rounded-xl">
											<div
												class="{(model?.is_active ?? true)
													? ''
													: 'opacity-50 dark:opacity-50'} bg-transparent rounded-xl"
											>
												<img
													src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`}
													alt="modelfile profile"
													class=" rounded-xl size-7 object-cover"
													loading="lazy"
													decoding="async"
													on:error={(e) => {
														e.target.src = '/favicon.png';
													}}
												/>
											</div>
										</div>
									</div>

									<div
										class="shrink-0 flex w-full min-w-0 flex-1 pr-1 self-center {(model?.is_active ??
										true)
											? ''
											: 'text-gray-500'}"
									>
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
											<div
												class="text-[13px] leading-4 font-normal line-clamp-1 flex items-center gap-1.5"
											>
												{model.name}

												<span class=" line-clamp-1 text-gray-500">
													{!!model?.meta?.description
														? model?.meta?.description
														: model?.ollama?.digest
															? `${model.id} (${model?.ollama?.digest})`
															: model.id}
												</span>

												<span
													class="shrink-0 text-[11px] font-normal leading-4 {modelAccessClass(
														model
													)}"
												>
													{modelAccessLabel(model)}
												</span>
											</div>
										</Tooltip>
									</div>
								</button>
								<div class="flex flex-row gap-0.5 items-center self-center">
									{#if shiftKey}
										<Tooltip content={model?.meta?.hidden ? $i18n.t('Show') : $i18n.t('Hide')}>
											<button
												class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
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
									{/if}

									<button
										class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
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
											class="size-3.5"
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
										privacyHandler={() => {
											toggleModelPrivacyHandler(model);
										}}
										pinModelHandler={() => {
											pinModelHandler(model.id);
										}}
										copyLinkHandler={() => {
											copyLinkHandler(model);
										}}
										cloneHandler={() => {
											cloneHandler(model);
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
										<Tooltip
											content={(model?.is_active ?? true)
												? $i18n.t('Enabled')
												: $i18n.t('Disabled')}
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
						<div class="flex h-full w-full items-center justify-center py-10">
							<div class="max-w-md text-center">
								<div class="mb-2 text-xl">😕</div>
								<div class="mb-1 text-sm text-gray-700 dark:text-gray-300">
									{$i18n.t('No models found')}
								</div>
								<div class=" text-gray-500 text-center text-xs">
									{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
								</div>
							</div>
						</div>
					{/if}
				</div>

				{#if filteredModels.length > perPage}
					<Pagination bind:page={currentPage} count={filteredModels.length} {perPage} />
				{/if}
			</div>
		</div>
	{:else}
		<ModelEditor
			edit
			model={models.find((m) => m.id === selectedModelId)}
			preset={false}
			onSubmit={async (model) => {
				console.log(model);
				await upsertModelHandler(model);
				selectedModelId = null;
				await init();
			}}
			onBack={async () => {
				selectedModelId = null;
				await init();
			}}
		/>
	{/if}
{:else}
	<div class=" h-full w-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
