<script lang="ts">
	import { marked } from 'marked';
	import Fuse from 'fuse.js';

	import dayjs from '$lib/dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { flyAndScale } from '$lib/utils/transitions';

	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	import { deleteModel, getOllamaVersion, pullModel } from '$lib/apis/ollama';
	import { deleteModelById } from '$lib/apis/models';
	import { unloadModel } from '$lib/apis';
	import {
		downloadProviderModel,
		getErrorMessage,
		getOpenAIConfig,
		getProviderModelDownloadStatus
	} from '$lib/apis/openai';

	import {
		user,
		MODEL_DOWNLOAD_POOL,
		mobile,
		models,
		temporaryChatEnabled,
		settings,
		config,
		showSettings
	} from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { capitalizeFirstLetter, sanitizeResponseContent, splitStream } from '$lib/utils';
	import { getModels } from '$lib/apis';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import Keyframes from '$lib/components/icons/Keyframes.svelte';
	import TagSelector from '$lib/components/workspace/common/TagSelector.svelte';

	import ModelItem from './ModelItem.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let id = '';
	export let value: string | null = '';
	export let values: string[] | null = null;
	export let compareEnabled = false;
	export let multipleEnabled = false;
	export let disabled = false;
	export let placeholder = $i18n.t('Select a model');
	export let searchEnabled = true;
	export let searchPlaceholder = $i18n.t('Search a model');
	export let selectionOnly = false;
	export let includeHidden = false;

	export let items: {
		label: string;
		value: string;
		model: Model;
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		[key: string]: any;
	}[] = [];

	export let className = 'w-[20rem]';
	export let triggerClassName = 'text-lg';
	export let placement: 'top' | 'bottom' | 'auto' = 'bottom';
	export let align: 'start' | 'end' = 'start';
	export let showSetDefault = false;
	export let onSetDefault: () => Promise<void> | void = () => {};

	export let pinModelHandler: (modelId: string) => void = () => {};

	let show = false;
	let triggerElement: HTMLElement | null = null;
	let contentElement: HTMLElement | null = null;
	let panelElement: HTMLElement | null = null;
	let dropdownPosition = { top: 0, left: 0, maxHeight: undefined as number | undefined };
	let positionFrame: number | undefined;
	let settleTimers: number[] = [];

	const portal = (node: HTMLElement) => {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	};

	const measureContent = () => {
		if (!contentElement) return { width: 0, height: 0 };

		const previousMaxHeight = panelElement?.style.maxHeight;
		if (panelElement) panelElement.style.maxHeight = '';
		const rect = contentElement.getBoundingClientRect();
		if (panelElement && previousMaxHeight !== undefined) {
			panelElement.style.maxHeight = previousMaxHeight;
		}

		return { width: rect.width, height: rect.height };
	};

	const visualViewportRect = () => {
		const viewport = window.visualViewport;
		return {
			left: viewport?.offsetLeft ?? 0,
			top: viewport?.offsetTop ?? 0,
			width: viewport?.width ?? window.innerWidth,
			height: viewport?.height ?? window.innerHeight
		};
	};

	const updatePosition = () => {
		if (!show || !triggerElement) return;
		const rect = triggerElement.getBoundingClientRect();
		const { width: contentWidth, height: contentHeight } = measureContent();
		const viewport = visualViewportRect();
		const viewportRight = viewport.left + viewport.width;
		const viewportBottom = viewport.top + viewport.height;
		const pad = 8;
		const gap = 2;
		const spaceBelow = viewportBottom - rect.bottom - gap - pad;
		const spaceAbove = rect.top - viewport.top - gap - pad;
		const preferredLeft = align === 'end' && contentWidth ? rect.right - contentWidth : rect.left;
		const maxLeft = contentWidth ? viewportRight - contentWidth - pad : preferredLeft;
		const resolvedPlacement =
			placement === 'auto'
				? contentHeight && spaceBelow < contentHeight && spaceAbove > spaceBelow
					? 'top'
					: 'bottom'
				: placement;
		const availableHeight = resolvedPlacement === 'top' ? spaceAbove : spaceBelow;
		const constrainedHeight =
			contentHeight && availableHeight >= 0
				? Math.min(contentHeight, availableHeight)
				: contentHeight;
		const top =
			resolvedPlacement === 'top' && contentHeight
				? rect.top - constrainedHeight - gap
				: rect.bottom + gap;

		dropdownPosition = {
			top: Math.max(viewport.top + pad, Math.min(top, viewportBottom - pad - constrainedHeight)),
			left: Math.max(viewport.left + pad, Math.min(preferredLeft, maxLeft)),
			maxHeight:
				contentHeight && availableHeight >= 0 && contentHeight > availableHeight
					? Math.max(0, availableHeight)
					: undefined
		};
	};

	const schedulePositionUpdate = () => {
		if (positionFrame != null) cancelAnimationFrame(positionFrame);
		positionFrame = requestAnimationFrame(() => {
			positionFrame = undefined;
			updatePosition();
		});
	};

	const scheduleSettledPositionUpdates = () => {
		for (const timer of settleTimers) window.clearTimeout(timer);
		settleTimers = [];
		schedulePositionUpdate();
		for (const delay of [50, 150, 300]) {
			settleTimers.push(window.setTimeout(schedulePositionUpdate, delay));
		}
	};

	const handleScroll = (event: Event) => {
		if (event.target instanceof Node && contentElement?.contains(event.target)) return;
		schedulePositionUpdate();
	};

	const focusSearchInput = () => {
		if (!$mobile) {
			document.getElementById('model-search-input')?.focus();
		}
	};
	const focusChatInput = () => {
		if (!$mobile) {
			document.getElementById('chat-input')?.focus();
		}
	};

	const toggleOpen = async () => {
		show = !show;
		if (show) {
			searchValue = '';
			listScrollTop = 0;
			if (!selectionOnly) {
				setOllamaVersion();
				setProviderDownloadConnections();
			}
			resetView();
			updatePosition();
			await tick();
			updatePosition();
			for (const delay of [0, 50, 150]) {
				window.setTimeout(focusSearchInput, delay);
			}
		} else {
			document.getElementById(`model-selector-${id}-button`)?.blur();
		}
	};

	export const open = async () => {
		if (!show) {
			await toggleOpen();
		}
	};

	const handlePointerDown = (e: PointerEvent) => {
		if (!show) return;
		const target = e.target as Node;
		if (
			(triggerElement && triggerElement.contains(target)) ||
			(contentElement && contentElement.contains(target)) ||
			((target as HTMLElement).closest?.('.model-selector-child-menu') ?? false)
		) {
			return;
		}
		show = false;
		document.getElementById(`model-selector-${id}-button`)?.blur();
	};

	const handleKeydown = (e: KeyboardEvent) => {
		if (show && e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			show = false;
			document.getElementById(`model-selector-${id}-button`)?.blur();
		}
	};

	let tags = [];

	let selectedModel = '';
	$: selectedValues = values ?? (value ? [value] : []);
	$: primaryValue = selectedValues[0] ?? value ?? '';
	$: selectedModel = items.find((item) => item.value === primaryValue) ?? '';
	$: selectedCount = selectedValues.filter(Boolean).length;
	$: triggerLabel = selectedModel
		? compareEnabled && selectedCount > 1
			? `${selectedModel.label} +${selectedCount - 1}`
			: selectedModel.label
		: placeholder;

	let searchValue = '';

	let selectedTag = '';
	let selectedConnectionType = '';
	let selectedFilter = '';
	let modelFilterItems = [];

	let ollamaVersion = null;
	let providerDownloadConnections = [];
	let selectedModelIdx = 0;

	const MANAGEMENT_PROVIDERS = new Set(['llama.cpp', 'lmstudio']);

	const normalizeProvider = (provider = '') => {
		const value = provider.trim().toLowerCase();
		if (value === 'lm studio' || value === 'lm-studio') return 'lmstudio';
		return value;
	};

	const getProviderLabel = (provider = '') => {
		const normalizedProvider = normalizeProvider(provider);
		if (normalizedProvider === 'lmstudio') return $i18n.t('LM Studio');
		if (normalizedProvider === 'llama.cpp') return $i18n.t('llama.cpp');
		return provider;
	};

	const getProviderPoolKey = (connection, model: string) =>
		`${connection.provider}:${connection.idx}:${model}`;

	const fuse = new Fuse(
		items.map((item) => {
			const _item = {
				...item,
				modelName: item.model?.name,
				tags: (item.model?.tags ?? []).map((tag) => tag.name).join(' '),
				desc: item.model?.info?.meta?.description
			};
			return _item;
		}),
		{
			keys: ['value', 'tags', 'modelName'],
			threshold: 0.4
		}
	);

	const updateFuse = () => {
		if (fuse) {
			fuse.setCollection(
				items.map((item) => {
					const _item = {
						...item,
						modelName: item.model?.name,
						tags: (item.model?.tags ?? []).map((tag) => tag.name).join(' '),
						desc: item.model?.info?.meta?.description
					};
					return _item;
				})
			);
		}
	};

	$: if (items) {
		updateFuse();
	}

	$: filteredItems = (
		searchValue
			? fuse
					.search(searchValue)
					.map((e) => {
						return e.item;
					})
					.filter((item) => {
						if (selectedTag === '') {
							return true;
						}

						return (item.model?.tags ?? [])
							.map((tag) => tag.name.toLowerCase())
							.includes(selectedTag.toLowerCase());
					})
					.filter((item) => {
						if (selectedConnectionType === '') {
							return true;
						} else if (selectedConnectionType === 'local') {
							return item.model?.connection_type === 'local';
						} else if (selectedConnectionType === 'external') {
							return item.model?.connection_type === 'external';
						} else if (selectedConnectionType === 'direct') {
							return item.model?.direct;
						}
					})
			: items
					.filter((item) => {
						if (selectedTag === '') {
							return true;
						}
						return (item.model?.tags ?? [])
							.map((tag) => tag.name.toLowerCase())
							.includes(selectedTag.toLowerCase());
					})
					.filter((item) => {
						if (selectedConnectionType === '') {
							return true;
						} else if (selectedConnectionType === 'local') {
							return item.model?.connection_type === 'local';
						} else if (selectedConnectionType === 'external') {
							return item.model?.connection_type === 'external';
						} else if (selectedConnectionType === 'direct') {
							return item.model?.direct;
						}
					})
	).filter((item) => includeHidden || !(item.model?.info?.meta?.hidden ?? false));

	$: sanitizedSearchValue = searchValue.trim();
	$: downloadTargets =
		!selectionOnly && sanitizedSearchValue && $user?.role === 'admin'
			? [
					...(ollamaVersion
						? [
								{
									id: 'ollama',
									label: $i18n.t('Ollama'),
									poolKey: sanitizedSearchValue,
									download: $MODEL_DOWNLOAD_POOL[sanitizedSearchValue],
									actionLabel: $i18n.t(`Pull "{{searchValue}}" from Ollama.com`, {
										searchValue: searchValue
									}),
									type: 'ollama'
								}
							]
						: []),
					...providerDownloadConnections.map((connection) => {
						const poolKey = getProviderPoolKey(connection, sanitizedSearchValue);
						return {
							...connection,
							id: `${connection.provider}:${connection.idx}`,
							label: getProviderLabel(connection.provider),
							poolKey,
							download: $MODEL_DOWNLOAD_POOL[poolKey],
							actionLabel: $i18n.t(`Download "{{searchValue}}" from {{provider}}`, {
								searchValue: searchValue,
								provider: getProviderLabel(connection.provider)
							}),
							type: 'provider'
						};
					})
				]
			: [];
	$: activeDownloadKeys = new Set(
		downloadTargets.filter((target) => target.download).map((target) => target.poolKey)
	);

	$: if (
		selectedTag !== undefined ||
		selectedConnectionType !== undefined ||
		searchValue !== undefined
	) {
		resetView();
	}

	$: modelFilterItems = [
		...(items.find((item) => item.model?.connection_type === 'local')
			? [{ value: 'connection:local', label: $i18n.t('Local') }]
			: []),
		...(items.find((item) => item.model?.connection_type === 'external')
			? [{ value: 'connection:external', label: $i18n.t('External') }]
			: []),
		...(items.find((item) => item.model?.direct)
			? [{ value: 'connection:direct', label: $i18n.t('Direct') }]
			: []),
		...tags.map((tag) => ({ value: `tag:${tag}`, label: tag }))
	];

	$: selectedFilter = selectedConnectionType
		? `connection:${selectedConnectionType}`
		: selectedTag
			? `tag:${selectedTag}`
			: '';

	const setModelFilter = (filterValue: string) => {
		if (!filterValue) {
			selectedConnectionType = '';
			selectedTag = '';
		} else if (filterValue.startsWith('connection:')) {
			selectedConnectionType = filterValue.replace('connection:', '');
			selectedTag = '';
		} else if (filterValue.startsWith('tag:')) {
			selectedConnectionType = '';
			selectedTag = filterValue.replace('tag:', '');
		}
	};

	const resetView = async () => {
		await tick();

		const selectedInFiltered = filteredItems.findIndex((item) => item.value === primaryValue);

		if (selectedInFiltered >= 0) {
			// The selected model is visible in the current filter
			selectedModelIdx = selectedInFiltered;
		} else {
			// The selected model is not visible, default to first item in filtered list
			selectedModelIdx = 0;
		}

		// Set the virtual scroll position so the selected item is rendered and centered
		const targetScrollTop = Math.max(0, selectedModelIdx * ITEM_HEIGHT - 128 + ITEM_HEIGHT / 2);
		listScrollTop = targetScrollTop;

		await tick();

		if (listContainer) {
			listContainer.scrollTop = targetScrollTop;
		}

		await tick();
		const item = document.querySelector(`[data-arrow-selected="true"]`);
		item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
		schedulePositionUpdate();
	};

	const setCompareEnabled = (enabled: boolean) => {
		compareEnabled = enabled;

		if (!enabled && values) {
			values = [primaryValue || selectedValues[0] || ''];
			value = values[0];
		}
	};

	const selectItem = (item, index: number) => {
		selectedModelIdx = index;

		if (values) {
			if (compareEnabled) {
				const nextValues = selectedValues.includes(item.value)
					? selectedValues.length > 1
						? selectedValues.filter((selectedValue) => selectedValue !== item.value)
						: selectedValues
					: [...selectedValues.filter(Boolean), item.value];

				values = nextValues.length ? nextValues : [item.value];
				value = values[0];
				return;
			}

			values = [item.value];
			value = item.value;
			show = false;
			window.setTimeout(focusChatInput, 0);
			return;
		}

		value = item.value;
		show = false;
		window.setTimeout(focusChatInput, 0);
	};

	const setDefaultHandler = async () => {
		await onSetDefault();
	};

	const pullModelHandler = async () => {
		const sanitizedModelTag = searchValue.trim().replace(/^ollama\s+(run|pull)\s+/, '');

		console.log($MODEL_DOWNLOAD_POOL);
		if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag]) {
			toast.error(
				$i18n.t(`Model '{{modelTag}}' is already in queue for downloading.`, {
					modelTag: sanitizedModelTag
				})
			);
			return;
		}
		if (Object.keys($MODEL_DOWNLOAD_POOL).length === 3) {
			toast.error(
				$i18n.t('Maximum of 3 models can be downloaded simultaneously. Please try again later.')
			);
			return;
		}

		const [res, controller] = await pullModel(localStorage.token, sanitizedModelTag, '0').catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL,
				[sanitizedModelTag]: {
					...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
					abortController: controller,
					reader,
					model: sanitizedModelTag,
					done: false
				}
			});

			while (true) {
				try {
					const { value, done } = await reader.read();
					if (done) break;

					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line);
							console.log(data);
							if (data.error) {
								throw data.error;
							}
							if (data.detail) {
								throw data.detail;
							}

							if (data.status) {
								if (data.digest) {
									let downloadProgress = 0;
									if (data.completed) {
										downloadProgress = Math.round((data.completed / data.total) * 1000) / 10;
									} else {
										downloadProgress = 100;
									}

									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											pullProgress: downloadProgress,
											digest: data.digest
										}
									});
								} else {
									toast.success(data.status);

									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											done: data.status === 'success'
										}
									});
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
					if (typeof error !== 'string') {
						error = error.message;
					}

					toast.error(getErrorMessage(error));
					// opts.callback({ success: false, error, modelName: opts.modelName });
					break;
				}
			}

			if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag].done) {
				toast.success(
					$i18n.t(`Model '{{modelName}}' has been successfully downloaded.`, {
						modelName: sanitizedModelTag
					})
				);

				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			} else {
				toast.error($i18n.t('Download canceled'));
			}

			delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
		}
	};

	const setOllamaVersion = async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => false);
	};

	const downloadProviderModelHandler = async (connection) => {
		const model = sanitizedSearchValue;
		const poolKey = getProviderPoolKey(connection, model);

		if ($MODEL_DOWNLOAD_POOL[poolKey]) {
			toast.error(
				$i18n.t(`Model '{{modelTag}}' is already in queue for downloading.`, {
					modelTag: model
				})
			);
			return;
		}
		if (Object.keys($MODEL_DOWNLOAD_POOL).length === 3) {
			toast.error(
				$i18n.t('Maximum of 3 models can be downloaded simultaneously. Please try again later.')
			);
			return;
		}

		const controller = new AbortController();
		MODEL_DOWNLOAD_POOL.set({
			...$MODEL_DOWNLOAD_POOL,
			[poolKey]: {
				abortController: controller,
				model,
				providerLabel: getProviderLabel(connection.provider),
				done: false
			}
		});

		try {
			const res = await downloadProviderModel(
				localStorage.token,
				connection.idx,
				model,
				controller.signal
			);
			const jobId = res?.job_id;

			if (res?.status) {
				MODEL_DOWNLOAD_POOL.set({
					...$MODEL_DOWNLOAD_POOL,
					[poolKey]: {
						...$MODEL_DOWNLOAD_POOL[poolKey],
						digest: res.status,
						done: ['completed', 'already_downloaded'].includes(res.status)
					}
				});
			}

			if (jobId) {
				while (!controller.signal.aborted) {
					await new Promise((resolve) => setTimeout(resolve, 1500));
					if (controller.signal.aborted) break;

					const status = await getProviderModelDownloadStatus(
						localStorage.token,
						connection.idx,
						jobId,
						controller.signal
					);
					const total = status?.total_size_bytes ?? 0;
					const downloaded = status?.downloaded_bytes ?? 0;
					const pullProgress = total ? Math.round((downloaded / total) * 1000) / 10 : undefined;

					MODEL_DOWNLOAD_POOL.set({
						...$MODEL_DOWNLOAD_POOL,
						[poolKey]: {
							...$MODEL_DOWNLOAD_POOL[poolKey],
							...(pullProgress !== undefined ? { pullProgress } : {}),
							digest: status?.status ?? ''
						}
					});

					if (status?.status === 'completed') {
						MODEL_DOWNLOAD_POOL.set({
							...$MODEL_DOWNLOAD_POOL,
							[poolKey]: {
								...$MODEL_DOWNLOAD_POOL[poolKey],
								pullProgress: 100,
								done: true
							}
						});
						break;
					}
					if (status?.status === 'failed') {
						throw status?.error ?? 'Download failed';
					}
				}
			} else if (!$MODEL_DOWNLOAD_POOL[poolKey]?.done) {
				MODEL_DOWNLOAD_POOL.set({
					...$MODEL_DOWNLOAD_POOL,
					[poolKey]: {
						...$MODEL_DOWNLOAD_POOL[poolKey],
						pullProgress: 100,
						done: true
					}
				});
			}

			if ($MODEL_DOWNLOAD_POOL[poolKey]?.done) {
				toast.success(
					$i18n.t(`Model '{{modelName}}' has been successfully downloaded.`, {
						modelName: model
					})
				);
				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			}
		} catch (error) {
			if (!controller.signal.aborted) {
				toast.error(getErrorMessage(error));
			}
		}

		delete $MODEL_DOWNLOAD_POOL[poolKey];
		MODEL_DOWNLOAD_POOL.set({
			...$MODEL_DOWNLOAD_POOL
		});
	};

	const downloadModelHandler = (target) => {
		if (target.type === 'ollama') {
			pullModelHandler();
			return;
		}

		downloadProviderModelHandler(target);
	};

	const setProviderDownloadConnections = async () => {
		if ($user?.role !== 'admin') {
			providerDownloadConnections = [];
			return;
		}

		const openaiConfig = await getOpenAIConfig(localStorage.token).catch(() => null);
		providerDownloadConnections = openaiConfig?.ENABLE_OPENAI_API
			? (openaiConfig.OPENAI_API_BASE_URLS ?? [])
					.map((url: string, idx: number) => {
						const config =
							openaiConfig.OPENAI_API_CONFIGS?.[idx] ??
							openaiConfig.OPENAI_API_CONFIGS?.[String(idx)] ??
							openaiConfig.OPENAI_API_CONFIGS?.[url] ??
							{};

						return {
							idx,
							url,
							provider: normalizeProvider(config?.provider ?? '')
						};
					})
					.filter((connection) => MANAGEMENT_PROVIDERS.has(connection.provider))
			: [];
	};

	onMount(() => {
		if (items) {
			tags = items
				.filter((item) => includeHidden || !(item.model?.info?.meta?.hidden ?? false))
				.flatMap((item) => item.model?.tags ?? [])
				.map((tag) => tag.name.toLowerCase());
			// Remove duplicates and sort
			tags = Array.from(new Set(tags)).sort((a, b) => a.localeCompare(b));
		}

		window.addEventListener('scroll', handleScroll, true);
		window.visualViewport?.addEventListener('resize', scheduleSettledPositionUpdates);
		window.visualViewport?.addEventListener('scroll', schedulePositionUpdate);

		return () => {
			if (positionFrame != null) cancelAnimationFrame(positionFrame);
			for (const timer of settleTimers) window.clearTimeout(timer);
			window.removeEventListener('scroll', handleScroll, true);
			window.visualViewport?.removeEventListener('resize', scheduleSettledPositionUpdates);
			window.visualViewport?.removeEventListener('scroll', schedulePositionUpdate);
		};
	});

	const cancelModelPullHandler = async (model: string) => {
		const { reader, abortController, providerLabel } = $MODEL_DOWNLOAD_POOL[model];
		if (abortController) {
			abortController.abort();
		}
		if (reader) {
			await reader.cancel();
			delete $MODEL_DOWNLOAD_POOL[model];
			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
			await deleteModel(localStorage.token, model);
			toast.success($i18n.t('{{model}} download has been canceled', { model: model }));
		} else {
			const displayModel = $MODEL_DOWNLOAD_POOL[model]?.model ?? model;
			delete $MODEL_DOWNLOAD_POOL[model];
			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
			toast.success(
				$i18n.t('{{model}} download has been canceled', {
					model: providerLabel ? `${displayModel} (${providerLabel})` : displayModel
				})
			);
		}
	};

	const unloadModelHandler = async (model: string) => {
		const res = await unloadModel(localStorage.token, model).catch((error) => {
			toast.error($i18n.t('Error unloading model: {{error}}', { error }));
		});

		if (res) {
			toast.success($i18n.t('Model unloaded successfully'));
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}
	};

	let showDeleteConfirm = false;
	let deleteModelTarget: any = null;

	const deleteModelHandler = async (model: any) => {
		deleteModelTarget = model;
		showDeleteConfirm = true;
	};

	const confirmDeleteModel = async () => {
		const model = deleteModelTarget;
		if (!model) return;

		let success = false;

		if (model?.info?.base_model_id) {
			// Workspace model: only delete the workspace model record, not the underlying base model
			const res = await deleteModelById(localStorage.token, model.id).catch((error) => {
				toast.error($i18n.t('Error deleting model: {{error}}', { error }));
				return null;
			});
			success = !!res;
		} else {
			// Base Ollama model: delete from Ollama directly
			const res = await deleteModel(localStorage.token, model.id).catch((error) => {
				toast.error($i18n.t('Error deleting model: {{error}}', { error }));
				return null;
			});
			success = !!res;
		}

		if (success) {
			toast.success(
				$i18n.t('Model {{modelName}} deleted successfully', { modelName: model.name ?? model.id })
			);

			// If the deleted model was selected, clear the selection
			if (value === model.id) {
				value = '';
			}

			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
		}

		deleteModelTarget = null;
	};

	const ITEM_HEIGHT = 32;
	const OVERSCAN = 10;

	let listScrollTop = 0;
	let listContainer;
	let listViewportHeight = 288;

	const trackListViewport = (node: HTMLElement) => {
		const updateHeight = () => {
			listViewportHeight = node.clientHeight || 288;
		};

		updateHeight();

		if (!('ResizeObserver' in window)) {
			return { destroy() {} };
		}

		const observer = new ResizeObserver(updateHeight);
		observer.observe(node);

		return {
			destroy() {
				observer.disconnect();
			}
		};
	};

	$: visibleStart = Math.max(0, Math.floor(listScrollTop / ITEM_HEIGHT) - OVERSCAN);
	$: visibleEnd = Math.min(
		filteredItems.length,
		Math.ceil((listScrollTop + listViewportHeight) / ITEM_HEIGHT) + OVERSCAN
	);
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Model')}
	message={$i18n.t('Are you sure you want to delete **{{modelName}}**?', {
		modelName: deleteModelTarget?.name ?? deleteModelTarget?.id ?? ''
	})}
	on:confirm={() => {
		confirmDeleteModel();
	}}
/>

<svelte:window
	on:pointerdown={handlePointerDown}
	on:keydown={handleKeydown}
	on:resize={scheduleSettledPositionUpdates}
/>

<div class="relative w-full">
	<button
		bind:this={triggerElement}
		class="focus-ring relative w-full {($settings?.highContrastMode ?? false)
			? ''
			: 'outline-hidden focus:outline-hidden'}"
		aria-label={selectedModel
			? $i18n.t('Selected model: {{modelName}}', { modelName: triggerLabel })
			: placeholder}
		aria-haspopup="listbox"
		aria-expanded={show}
		id="model-selector-{id}-button"
		type="button"
		{disabled}
		on:click={toggleOpen}
	>
		<div
			class="flex w-full min-w-0 text-left px-0.5 bg-transparent {triggerClassName} justify-between {($settings?.highContrastMode ??
			false)
				? 'dark:placeholder-gray-100 placeholder-gray-800'
				: 'placeholder-gray-400'}"
			on:mouseenter={async () => {
				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			}}
		>
			<span class="min-w-0 flex-1 truncate">{triggerLabel}</span>
			<ChevronDown className="ml-1 size-2.5 shrink-0 self-center" strokeWidth="2.5" />
		</div>
	</button>

	{#if show}
		<div
			use:portal
			bind:this={contentElement}
			style="position: fixed; z-index: 9999; top: {dropdownPosition.top}px; left: {dropdownPosition.left}px;"
		>
			<div
				bind:this={panelElement}
				class="z-40 {className ??
					'w-[20rem]'} max-w-[calc(100vw-1rem)] justify-start rounded-xl border border-gray-100 bg-white p-0.5 shadow-lg outline-hidden dark:border-gray-800 dark:bg-gray-850 dark:text-white flex flex-col overflow-hidden"
				style={dropdownPosition.maxHeight ? `max-height: ${dropdownPosition.maxHeight}px;` : ''}
				transition:flyAndScale
			>
				<slot>
					{#if searchEnabled}
						<div class="my-0.5 flex ml-2 mr-0.5 h-[1.6875rem] shrink-0 items-center gap-2">
							<Search className=" size-3.5 shrink-0" strokeWidth="2" />

							<input
								id="model-search-input"
								bind:value={searchValue}
								class="w-full bg-transparent text-[0.8125rem] font-normal outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-500"
								placeholder={searchPlaceholder}
								autocomplete="off"
								aria-label={$i18n.t('Search In Models')}
								on:keydown={(e) => {
									if (e.code === 'Enter') {
										if (selectedModelIdx >= filteredItems.length) {
											const target = downloadTargets[selectedModelIdx - filteredItems.length];
											if (target && !target.download) {
												downloadModelHandler(target);
											}
										} else if (filteredItems[selectedModelIdx]) {
											selectItem(filteredItems[selectedModelIdx], selectedModelIdx);
										}
										return; // dont need to scroll on selection
									} else if (e.code === 'ArrowDown') {
										e.stopPropagation();
										selectedModelIdx = Math.min(
											selectedModelIdx + 1,
											Math.max(filteredItems.length - 1 + downloadTargets.length, 0)
										);
									} else if (e.code === 'ArrowUp') {
										e.stopPropagation();
										selectedModelIdx = Math.max(selectedModelIdx - 1, 0);
									} else {
										// if the user types something, reset to the top selection.
										selectedModelIdx = 0;
									}

									const item = document.querySelector(`[data-arrow-selected="true"]`);
									item?.scrollIntoView({
										block: 'center',
										inline: 'nearest',
										behavior: 'instant'
									});
								}}
							/>

							{#if modelFilterItems.length > 0 || (multipleEnabled && items.length > 0)}
								<div class="flex min-w-0 shrink-0 items-center gap-0.5">
									{#if multipleEnabled && items.length > 0}
										<Tooltip content={$i18n.t('Compare')}>
											<button
												type="button"
												class="focus-ring flex size-[1.375rem] shrink-0 items-center justify-center rounded-lg transition-colors duration-100 {compareEnabled
													? ($settings?.highContrastMode ?? false)
														? 'bg-gray-200 text-gray-900 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-800'
														: 'bg-gray-50 text-gray-700 hover:bg-gray-50 dark:bg-gray-800/60 dark:text-gray-200 dark:hover:bg-gray-800/60'
													: ($settings?.highContrastMode ?? false)
														? 'text-gray-700 hover:bg-gray-200 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-gray-100'
														: 'text-gray-500 hover:bg-gray-50/40 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800/40 dark:hover:text-gray-100'}"
												aria-label={$i18n.t('Compare')}
												aria-pressed={compareEnabled}
												on:click={() => {
													setCompareEnabled(!compareEnabled);
												}}
											>
												<Keyframes className="size-3" strokeWidth="2" />
											</button>
										</Tooltip>
									{/if}

									{#if modelFilterItems.length > 0}
										<TagSelector
											bind:value={selectedFilter}
											placeholder={$i18n.t('All')}
											align="end"
											items={modelFilterItems}
											triggerClass="relative flex h-[1.375rem] max-w-32 items-center gap-0.5 rounded-xl bg-transparent px-1.5 text-[0.6875rem] font-normal transition-colors duration-100 {($settings?.highContrastMode ??
											false)
												? 'text-gray-700 hover:bg-gray-200 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-gray-100'
												: 'text-gray-500 hover:bg-gray-50/40 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800/40 dark:hover:text-gray-100'}"
											itemClass="flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] capitalize {($settings?.highContrastMode ??
											false)
												? 'hover:bg-gray-200 hover:text-gray-900 dark:hover:bg-gray-800 dark:hover:text-gray-100'
												: 'hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100'}"
											contentClass="min-w-36 model-selector-child-menu"
											onChange={setModelFilter}
										/>
									{/if}
								</div>
							{/if}
						</div>
					{/if}

					<div class="group relative flex min-h-0 flex-1 flex-col">
						{#if filteredItems.length === 0}
							{#if items.length === 0 && $user?.role === 'admin'}
								<div
									class="my-2 flex w-full flex-col items-start justify-center px-4 py-3 text-start"
								>
									<div
										class="mb-0.5 text-xs font-normal leading-4 text-gray-800 dark:text-gray-100"
									>
										{$i18n.t('No models available')}
									</div>
									<div class="w-full text-[0.6875rem] leading-3.5 text-gray-500 dark:text-gray-400">
										{$i18n.t('Connect to an AI provider to start chatting')}
									</div>
									<button
										type="button"
										class="focus-ring mt-3 rounded-lg px-0 py-1 text-[0.6875rem] font-normal leading-none text-gray-600 underline-offset-2 transition-colors duration-100 hover:text-gray-800 hover:underline focus:outline-hidden focus:underline dark:text-gray-300 dark:hover:text-gray-100"
										on:click={() => {
											show = false;
											showSettings.set('admin:connections');
										}}
									>
										{$i18n.t('Manage Connections')}
									</button>
								</div>
							{:else}
								<div class="">
									<div
										class="flex min-h-8 items-center rounded-xl px-2 text-[0.8125rem] text-gray-700 dark:text-gray-100"
									>
										{$i18n.t('No results found')}
									</div>
								</div>
							{/if}
						{:else}
							<!-- svelte-ignore a11y-no-static-element-interactions -->
							<div
								class="min-h-0 flex-1 overflow-y-auto"
								style="max-height: 18rem;"
								role="listbox"
								aria-label={$i18n.t('Available models')}
								bind:this={listContainer}
								use:trackListViewport
								on:scroll={() => {
									listScrollTop = listContainer.scrollTop;
								}}
							>
								<div style="height: {visibleStart * ITEM_HEIGHT}px;" />
								{#each filteredItems.slice(visibleStart, visibleEnd) as item, i (item.value)}
									{@const index = visibleStart + i}
									<ModelItem
										{selectedModelIdx}
										{item}
										{index}
										value={primaryValue}
										{pinModelHandler}
										{unloadModelHandler}
										{deleteModelHandler}
										{selectionOnly}
										{compareEnabled}
										{selectedValues}
										onClick={() => {
											selectItem(item, index);
										}}
									/>
								{/each}
								<div style="height: {(filteredItems.length - visibleEnd) * ITEM_HEIGHT}px;" />
							</div>
						{/if}

						{#each downloadTargets as target, targetIndex (target.id)}
							{#if target.download}
								<Tooltip
									content={target.download?.digest && target.download.digest !== 'downloading'
										? target.download.digest
										: searchValue}
									placement="top-start"
								>
									<div
										role="option"
										aria-selected={selectedModelIdx === filteredItems.length + targetIndex}
										data-arrow-selected={selectedModelIdx === filteredItems.length + targetIndex}
										class="flex h-8 w-full select-none items-center gap-2 rounded-xl px-2 text-left text-[0.8125rem] font-normal text-gray-700 outline-hidden transition-colors duration-75 dark:text-gray-100 {selectedModelIdx ===
										filteredItems.length + targetIndex
											? ($settings?.highContrastMode ?? false)
												? 'bg-gray-200 dark:bg-gray-800'
												: 'bg-gray-50/70 dark:bg-gray-800/60'
											: ''}"
									>
										<Spinner className="size-3 shrink-0 text-gray-400 dark:text-gray-500" />
										<div class="min-w-0 flex-1 truncate">
											{$i18n.t('Downloading "{{searchValue}}"', { searchValue: searchValue })}
										</div>
										{#if 'pullProgress' in target.download}
											<div
												class="shrink-0 text-[0.6875rem] tabular-nums text-gray-500 dark:text-gray-400"
											>
												{target.download.pullProgress}%
											</div>
										{/if}
										<button
											class="focus-ring flex size-4 shrink-0 items-center justify-center rounded text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
											aria-label={$i18n.t('Cancel download of {{model}}', { model: searchValue })}
											on:click|stopPropagation={() => {
												cancelModelPullHandler(target.poolKey);
											}}
										>
											<svg
												class="size-2.5"
												aria-hidden="true"
												xmlns="http://www.w3.org/2000/svg"
												width="24"
												height="24"
												fill="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke="currentColor"
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2.5"
													d="M6 18 17.94 6M18 18 6.06 6"
												/>
											</svg>
										</button>
									</div>
								</Tooltip>
							{:else}
								<Tooltip content={target.actionLabel} placement="top-start">
									<button
										type="button"
										role="option"
										aria-selected={selectedModelIdx === filteredItems.length + targetIndex}
										data-arrow-selected={selectedModelIdx === filteredItems.length + targetIndex}
										class="focus-ring flex h-8 w-full cursor-pointer select-none items-center gap-2 rounded-xl px-2 text-left text-[0.8125rem] font-normal text-gray-700 outline-hidden transition-colors duration-75 dark:text-gray-100 {($settings?.highContrastMode ??
										false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'hover:bg-gray-50/40 dark:hover:bg-gray-800/40'} {selectedModelIdx ===
										filteredItems.length + targetIndex
											? ($settings?.highContrastMode ?? false)
												? 'bg-gray-200 dark:bg-gray-800'
												: 'bg-gray-50/70 dark:bg-gray-800/60'
											: ''}"
										on:click={() => {
											downloadModelHandler(target);
										}}
									>
										<Download className="size-3.5 shrink-0 text-gray-400 dark:text-gray-500" />
										<div class="min-w-0 flex-1 truncate">
											{$i18n.t('Download "{{searchValue}}"', { searchValue: searchValue })}
										</div>
										<div
											class="shrink-0 truncate text-[0.6875rem] text-gray-500 dark:text-gray-400"
										>
											{target.label}
										</div>
									</button>
								</Tooltip>
							{/if}
						{/each}

						{#each selectionOnly ? [] : Object.keys($MODEL_DOWNLOAD_POOL).filter((model) => !activeDownloadKeys.has(model)) as model}
							{@const download = $MODEL_DOWNLOAD_POOL[model]}
							{@const downloadName = download?.model ?? model}
							<Tooltip
								content={download?.digest && download.digest !== 'downloading'
									? download.digest
									: downloadName}
								placement="top-start"
							>
								<div
									class="flex h-8 w-full select-none items-center gap-2 rounded-xl px-2 text-left text-[0.8125rem] font-normal text-gray-700 outline-hidden transition-colors duration-75 dark:text-gray-100"
								>
									<Spinner className="size-3 shrink-0 text-gray-400 dark:text-gray-500" />
									<div class="min-w-0 flex-1 truncate">
										Downloading "{downloadName}"{download?.providerLabel
											? ` from ${download.providerLabel}`
											: ''}
									</div>
									{#if 'pullProgress' in download}
										<div
											class="shrink-0 text-[0.6875rem] tabular-nums text-gray-500 dark:text-gray-400"
										>
											{download.pullProgress}%
										</div>
									{/if}
									<button
										class="focus-ring flex size-4 shrink-0 items-center justify-center rounded text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
										aria-label={$i18n.t('Cancel download of {{model}}', { model: downloadName })}
										on:click|stopPropagation={() => {
											cancelModelPullHandler(model);
										}}
									>
										<svg
											class="size-2.5"
											aria-hidden="true"
											xmlns="http://www.w3.org/2000/svg"
											width="24"
											height="24"
											fill="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke="currentColor"
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2.5"
												d="M6 18 17.94 6M18 18 6.06 6"
											/>
										</svg>
									</button>
								</div>
							</Tooltip>
						{/each}
					</div>

					{#if showSetDefault}
						<div class="flex shrink-0 items-center justify-end px-2 py-1 leading-none">
							<button
								type="button"
								class="focus-ring text-[0.65rem] font-normal leading-none text-gray-500 underline-offset-2 transition-colors duration-100 hover:text-gray-700 hover:underline dark:text-gray-500 dark:hover:text-gray-300"
								on:click|stopPropagation={setDefaultHandler}
							>
								{$i18n.t('Set as default')}
							</button>
						</div>
					{:else}
						<div class="shrink-0 pb-1"></div>
					{/if}

					<div class="hidden w-[42rem]" />
					<div class="hidden w-[28rem]" />
					<div class="hidden w-[24rem]" />
					<div class="hidden w-[22rem]" />
					<div class="hidden w-[20rem]" />
				</slot>
			</div>
		</div>
	{/if}
</div>
