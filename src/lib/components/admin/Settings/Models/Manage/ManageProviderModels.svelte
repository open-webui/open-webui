<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';

	import {
		deleteProviderModel,
		downloadProviderModel,
		getErrorMessage,
		getProviderModelCatalog,
		loadProviderModel,
		unloadProviderModel
	} from '$lib/apis/openai';
	import { getModels } from '$lib/apis';
	import { config, models, settings } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Play from '$lib/components/icons/Play.svelte';
	import Refresh from '$lib/components/icons/Refresh.svelte';
	import Trash from '$lib/components/icons/Trash.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n: any = getContext('i18n');

	export let urlIdx: number;

	type ProviderModel = {
		id?: string;
		key?: string;
		name?: string;
		model?: string;
		display_name?: string;
		status?: string | { value?: string };
		path?: string;
		size?: number;
		loaded_instances?: { id?: string }[];
		[key: string]: unknown;
	};

	let loading = true;
	let actionModel = '';
	let modelRef = '';
	let modelToDelete = '';
	let showDeleteConfirm = false;
	export let provider = '';
	export let providerLabel = '';
	export let supportsDelete = false;

	let providerModels: ProviderModel[] = [];

	const inputClass =
		'h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2.5 text-left text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 disabled:opacity-50 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500';
	const iconButtonClass =
		'inline-flex h-7 items-center justify-center rounded-lg border border-gray-100/50 bg-gray-50/40 px-2.5 text-gray-700 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:hover:bg-white/[0.06]';

	const getModelId = (model: ProviderModel) =>
		model.key ?? model.id ?? model.name ?? model.model ?? '';

	const getDisplayName = (model: ProviderModel) => model.display_name ?? getModelId(model);

	const getUnloadId = (model: ProviderModel) =>
		model.loaded_instances?.[0]?.id ?? getModelId(model);

	const getStatus = (model: ProviderModel) => {
		if (model.loaded_instances?.length) {
			return 'loaded';
		}

		if (provider === 'lmstudio') {
			return 'unloaded';
		}

		const status = model.status;
		if (typeof status === 'string') return status;
		return status?.value ?? 'available';
	};

	const getStatusClass = (status: string) => {
		if (status === 'loaded' || status === 'sleeping') {
			return 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300';
		}
		if (status === 'loading' || status === 'downloading') {
			return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300';
		}
		return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300';
	};

	const normalizeModels = (response: any): ProviderModel[] => {
		const entries = Array.isArray(response)
			? response
			: (response?.models ?? response?.data ?? response?.items ?? []);

		return entries
			.map((model: ProviderModel | string) =>
				typeof model === 'string' ? { id: model, name: model } : model
			)
			.filter((model: ProviderModel) => getModelId(model) !== '')
			.sort((a: ProviderModel, b: ProviderModel) => getModelId(a).localeCompare(getModelId(b)));
	};

	const refreshModels = async () => {
		loading = true;
		const res = await getProviderModelCatalog(localStorage.token, urlIdx).catch((error) => {
			toast.error(getErrorMessage(error));
			return null;
		});
		providerModels = normalizeModels(res);
		loading = false;
	};

	const refreshGlobalModels = async () => {
		await models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null
			)
		);
	};

	const runModelAction = async (
		modelId: string,
		action: (token: string, urlIdx: number, model: string) => Promise<unknown>,
		successMessage: string
	) => {
		actionModel = modelId;
		const res = await action(localStorage.token, urlIdx, modelId).catch((error) => {
			toast.error(getErrorMessage(error));
			return null;
		});

		if (res) {
			toast.success(successMessage);
			await refreshModels();
			await refreshGlobalModels();
		}
		actionModel = '';
	};

	const downloadModelHandler = async () => {
		const model = modelRef.trim();
		if (!model) return;

		await runModelAction(model, downloadProviderModel, $i18n.t('Model download started'));
		modelRef = '';
	};

	const loadModelHandler = async (model: string) => {
		await runModelAction(model, loadProviderModel, $i18n.t('Model loaded successfully'));
	};

	const unloadModelHandler = async (model: ProviderModel) => {
		const modelId = getModelId(model);
		const instanceId = getUnloadId(model);

		actionModel = modelId;
		const res = await unloadProviderModel(localStorage.token, urlIdx, modelId, instanceId).catch(
			(error) => {
				toast.error(getErrorMessage(error));
				return null;
			}
		);

		if (res) {
			toast.success($i18n.t('Model unloaded successfully'));
			await refreshModels();
			await refreshGlobalModels();
		}
		actionModel = '';
	};

	const deleteModelHandler = async () => {
		await runModelAction(modelToDelete, deleteProviderModel, $i18n.t('Model deleted successfully'));
		modelToDelete = '';
	};

	$: if (urlIdx !== undefined) {
		refreshModels();
	}

	onMount(refreshModels);
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Model')}
	message={$i18n.t('This will delete the cached model and cannot be undone.')}
	onConfirm={deleteModelHandler}
/>

<div class="flex flex-col gap-3">
	<div class="flex items-center justify-between">
		<div class="text-sm font-normal">{providerLabel || provider}</div>
		<Tooltip content={$i18n.t('Refresh')}>
			<button class={iconButtonClass} type="button" on:click={refreshModels} disabled={loading}>
				<Refresh className="size-4" />
			</button>
		</Tooltip>
	</div>

	<form class="flex gap-1.5" on:submit|preventDefault={downloadModelHandler}>
		<input
			class={inputClass}
			type="text"
			bind:value={modelRef}
			placeholder={$i18n.t('Type a model ref')}
			autocomplete="off"
		/>
		<Tooltip content={$i18n.t('Download Model')}>
			<button
				class={iconButtonClass}
				type="submit"
				disabled={actionModel !== '' || modelRef.trim() === ''}
			>
				<Download className="size-4" />
			</button>
		</Tooltip>
	</form>

	{#if loading}
		<div class="py-5">
			<Spinner />
		</div>
	{:else if providerModels.length === 0}
		<div class="py-5 text-center text-xs text-gray-400">
			{$i18n.t('No models found')}
		</div>
	{:else}
		<div
			class="max-h-96 overflow-y-auto rounded-lg border border-gray-100/50 dark:border-white/[0.04]"
		>
			{#each providerModels as model}
				{@const modelId = getModelId(model)}
				{@const displayName = getDisplayName(model)}
				{@const status = getStatus(model)}
				<div
					class="flex items-center justify-between gap-2 border-b border-gray-100/50 px-2 py-2 last:border-b-0 dark:border-white/[0.04]"
				>
					<div class="min-w-0 flex-1">
						<div class="truncate text-xs font-medium text-gray-700 dark:text-gray-200">
							{displayName}
						</div>
						{#if displayName !== modelId}
							<div class="truncate text-[0.65rem] text-gray-400">{modelId}</div>
						{/if}
						<div class="mt-1 flex items-center gap-1.5">
							<span class="rounded-full px-1.5 py-0.5 text-[0.65rem] {getStatusClass(status)}">
								{status}
							</span>
						</div>
					</div>

					<div class="flex shrink-0 gap-1">
						<Tooltip content={$i18n.t('Load Model')}>
							<button
								class={iconButtonClass}
								type="button"
								aria-label={$i18n.t('Load Model')}
								disabled={actionModel !== '' || status === 'loaded' || status === 'loading'}
								on:click={() => loadModelHandler(modelId)}
							>
								<Play className="size-4" />
							</button>
						</Tooltip>

						<Tooltip content={$i18n.t('Unload Model')}>
							<button
								class={iconButtonClass}
								type="button"
								aria-label={$i18n.t('Unload Model')}
								disabled={actionModel !== '' || status === 'unloaded'}
								on:click={() => unloadModelHandler(model)}
							>
								<XMark className="size-4" />
							</button>
						</Tooltip>

						{#if supportsDelete}
							<Tooltip content={$i18n.t('Delete Model')}>
								<button
									class={iconButtonClass}
									type="button"
									aria-label={$i18n.t('Delete Model')}
									disabled={actionModel !== ''}
									on:click={() => {
										modelToDelete = modelId;
										showDeleteConfirm = true;
									}}
								>
									<Trash className="size-4" />
								</button>
							</Tooltip>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
