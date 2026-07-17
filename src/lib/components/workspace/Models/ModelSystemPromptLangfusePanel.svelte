<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import { toast } from 'svelte-sonner';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { formatDate } from '$lib/utils';
	import {
		getModelSystemPromptBinding,
		getModelLangfuseConnections,
		getModelLangfusePrompts,
		patchModelSystemPromptBinding,
		syncModelSystemPromptFromLangfuse,
		previewModelSystemPromptFromLangfuse,
		detachModelSystemPromptToLocal,
		type ModelSystemPromptBinding
	} from '$lib/apis/models/systemPrompt';
	import type { LangfuseConnection, LangfusePromptSummary } from '$lib/apis/langfuse';

	dayjs.extend(localizedFormat);

	export let modelId: string;
	export let writeAccess = true;
	export let system = '';
	export let activeBaseline = '';

	const dispatch = createEventDispatcher<{
		bindingchange: ModelSystemPromptBinding | null;
		detach: { binding: ModelSystemPromptBinding; content: string };
	}>();

	const i18n = getContext<Writable<i18nType>>('i18n');

	let connections: LangfuseConnection[] = [];
	let binding: ModelSystemPromptBinding | null = null;
	let promptSuggestions: LangfusePromptSummary[] = [];

	let connectionId = '';
	let externalName = '';
	let externalLabel = '';
	let externalVersion = '';

	let loaded = false;
	let promptsLoading = false;
	let previewing = false;
	let syncing = false;
	let detaching = false;
	let isPreview = false;

	const normalizeContent = (value: string) => (value.trim() === '' ? '' : value);

	const renderDate = (timestamp: number) => {
		const dateVal = timestamp * 1000;
		return $i18n.t(formatDate(dateVal), {
			LOCALIZED_TIME: dayjs(dateVal).format('LT'),
			LOCALIZED_DATE: dayjs(dateVal).format('L')
		});
	};

	const getPreviewForm = () => ({
		connection_id: connectionId || null,
		external_name: externalName.trim() || null,
		external_label: externalLabel.trim() || null,
		external_version: externalVersion.trim() || null
	});

	const validateRefs = () => {
		if (!connectionId) {
			toast.error($i18n.t('Select a Langfuse connection'));
			return false;
		}
		if (!externalName.trim()) {
			toast.error($i18n.t('Prompt name is required'));
			return false;
		}
		return true;
	};

	const applyBindingToForm = (value: ModelSystemPromptBinding | null) => {
		connectionId = value?.connection_id ?? connections[0]?.id ?? '';
		externalName = value?.external_name ?? '';
		externalLabel = value?.external_label ?? '';
		externalVersion = value?.external_version ?? '';
	};

	const applyContentFromBinding = (value: ModelSystemPromptBinding | null) => {
		if (value?.cached_content != null) {
			system = value.cached_content;
			activeBaseline = normalizeContent(system);
			isPreview = false;
		}
	};

	const emitBinding = (value: ModelSystemPromptBinding | null) => {
		binding = value;
		dispatch('bindingchange', value);
	};

	const refreshBinding = async () => {
		const next = await getModelSystemPromptBinding(localStorage.token, modelId);
		emitBinding(next);
		applyContentFromBinding(next);
		return next;
	};

	const loadPromptSuggestions = async () => {
		if (!connectionId) {
			promptSuggestions = [];
			return;
		}

		promptsLoading = true;
		try {
			const res = await getModelLangfusePrompts(localStorage.token, modelId, connectionId, {
				limit: 100
			});
			promptSuggestions = res.data ?? [];
		} catch (error) {
			console.error('Failed to load Langfuse prompts:', error);
			promptSuggestions = [];
		}
		promptsLoading = false;
	};

	const loadPanel = async () => {
		if (!modelId) return;

		try {
			const res = await getModelLangfuseConnections(localStorage.token, modelId);
			connections = res.connections ?? [];
		} catch (error) {
			console.error('Failed to load Langfuse connections:', error);
			connections = [];
		}

		try {
			const nextBinding = await getModelSystemPromptBinding(localStorage.token, modelId);
			emitBinding(nextBinding);
			applyBindingToForm(nextBinding);
			applyContentFromBinding(nextBinding);
		} catch (error) {
			console.error('Failed to load system prompt binding:', error);
			emitBinding(null);
			applyBindingToForm(null);
		}

		await loadPromptSuggestions();
		loaded = true;
	};

	export const reload = async () => {
		loaded = false;
		await loadPanel();
	};

	const patchBinding = async () => {
		return patchModelSystemPromptBinding(localStorage.token, modelId, {
			source: 'langfuse',
			connection_id: connectionId,
			external_name: externalName.trim(),
			external_label: externalLabel.trim() || null,
			external_version: externalVersion.trim() || null
		});
	};

	const handlePreview = async () => {
		if (!validateRefs()) return;

		previewing = true;
		try {
			const result = await previewModelSystemPromptFromLangfuse(
				localStorage.token,
				modelId,
				getPreviewForm()
			);
			system = result.content;
			isPreview = true;
			toast.success($i18n.t('Preview loaded'));
		} catch (error) {
			toast.error(`${error}`);
		}
		previewing = false;
	};

	const handleSync = async () => {
		if (!writeAccess) {
			toast.error($i18n.t('You do not have permission to edit this model.'));
			return;
		}
		if (!validateRefs()) return;

		syncing = true;
		try {
			emitBinding(await patchBinding());
			const result = await syncModelSystemPromptFromLangfuse(localStorage.token, modelId);
			await refreshBinding();
			system = result.content;
			activeBaseline = normalizeContent(system);
			isPreview = false;
			toast.success($i18n.t('Synced from Langfuse'));
		} catch (error) {
			toast.error(`${error}`);
		}
		syncing = false;
	};

	const handleDetach = async () => {
		if (!writeAccess) {
			toast.error($i18n.t('You do not have permission to edit this model.'));
			return;
		}

		detaching = true;
		try {
			const result = await detachModelSystemPromptToLocal(localStorage.token, modelId);
			system = result.version.content;
			activeBaseline = normalizeContent(system);
			emitBinding(result.binding);
			toast.success($i18n.t('Detached to local version'));
			dispatch('detach', { binding: result.binding, content: result.version.content });
		} catch (error) {
			toast.error(`${error}`);
		}
		detaching = false;
	};

	const handleConnectionChange = async () => {
		externalName = '';
		await loadPromptSuggestions();
	};

	onMount(async () => {
		await loadPanel();
	});
</script>

{#if loaded}
	<div class="flex flex-col gap-3">
		<div class="grid gap-2 sm:grid-cols-2">
			<div>
				<div class="mb-1 text-xs text-gray-400 dark:text-gray-600">
					{$i18n.t('Connection')}
				</div>
				<select
					class="w-full rounded-lg bg-transparent py-1 text-xs text-gray-700 outline-hidden ring-1 ring-gray-200/70 focus:ring-gray-300 dark:text-gray-300 dark:ring-white/10 dark:focus:ring-white/20 px-2"
					bind:value={connectionId}
					disabled={!writeAccess}
					on:change={handleConnectionChange}
				>
					<option value="">{$i18n.t('Select a connection')}</option>
					{#each connections as connection (connection.id)}
						<option value={connection.id}>{connection.name || connection.id}</option>
					{/each}
				</select>
			</div>

			<div>
				<div class="mb-1 text-xs text-gray-400 dark:text-gray-600">
					{$i18n.t('Prompt name')}
				</div>
				<input
					class="w-full rounded-lg bg-transparent py-1 text-xs text-gray-700 outline-hidden ring-1 ring-gray-200/70 placeholder:text-gray-300 focus:ring-gray-300 dark:text-gray-300 dark:ring-white/10 dark:placeholder:text-gray-700 dark:focus:ring-white/20 px-2"
					list="langfuse-prompt-names"
					placeholder={$i18n.t('e.g. movie-critic')}
					bind:value={externalName}
					disabled={!writeAccess}
				/>
				<datalist id="langfuse-prompt-names">
					{#each promptSuggestions as prompt (prompt.name)}
						<option value={prompt.name}></option>
					{/each}
				</datalist>
				{#if promptsLoading}
					<div class="mt-1 text-xs text-gray-400">{$i18n.t('Loading prompts...')}</div>
				{/if}
			</div>

			<div>
				<div class="mb-1 text-xs text-gray-400 dark:text-gray-600">
					{$i18n.t('Label')} ({$i18n.t('optional')})
				</div>
				<input
					class="w-full rounded-lg bg-transparent py-1 text-xs text-gray-700 outline-hidden ring-1 ring-gray-200/70 placeholder:text-gray-300 focus:ring-gray-300 dark:text-gray-300 dark:ring-white/10 dark:placeholder:text-gray-700 dark:focus:ring-white/20 px-2"
					placeholder={$i18n.t('e.g. production')}
					bind:value={externalLabel}
					disabled={!writeAccess || externalVersion.trim() !== ''}
				/>
			</div>

			<div>
				<div class="mb-1 text-xs text-gray-400 dark:text-gray-600">
					{$i18n.t('Version')} ({$i18n.t('optional')})
				</div>
				<input
					class="w-full rounded-lg bg-transparent py-1 text-xs text-gray-700 outline-hidden ring-1 ring-gray-200/70 placeholder:text-gray-300 focus:ring-gray-300 dark:text-gray-300 dark:ring-white/10 dark:placeholder:text-gray-700 dark:focus:ring-white/20 px-2"
					placeholder={$i18n.t('e.g. 3')}
					bind:value={externalVersion}
					disabled={!writeAccess}
				/>
			</div>
		</div>

		<div class="flex flex-wrap items-center justify-between gap-2">
			<div class="flex flex-wrap items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
				{#if binding?.cached_version}
					<span>{$i18n.t('Cached version')}: {binding.cached_version}</span>
				{/if}
				{#if binding?.cached_at}
					<span>{$i18n.t('Cached at')}: {renderDate(binding.cached_at)}</span>
				{/if}
				{#if isPreview}
					<span class="text-amber-600 dark:text-amber-400">{$i18n.t('Preview')}</span>
				{/if}
			</div>

			<div class="flex flex-wrap items-center gap-2">
				<button
					type="button"
					class="rounded-lg bg-gray-50 px-3 py-1.5 text-xs text-gray-900 transition ring-1 ring-gray-200 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-850 dark:text-gray-100 dark:ring-gray-800 dark:hover:bg-gray-800"
					disabled={previewing}
					on:click={handlePreview}
				>
					<div class="flex items-center gap-1.5">
						<span>{$i18n.t('Preview')}</span>
						{#if previewing}
							<Spinner className="size-3" />
						{/if}
					</div>
				</button>

				{#if writeAccess}
					<button
						type="button"
						class="rounded-lg bg-gray-50 px-3 py-1.5 text-xs text-gray-900 transition ring-1 ring-gray-200 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-850 dark:text-gray-100 dark:ring-gray-800 dark:hover:bg-gray-800"
						disabled={syncing}
						on:click={handleSync}
					>
						<div class="flex items-center gap-1.5">
							<span>{$i18n.t('Sync')}</span>
							{#if syncing}
								<Spinner className="size-3" />
							{/if}
						</div>
					</button>

					{#if binding?.source === 'langfuse' && binding?.cached_content}
						<button
							type="button"
							class="text-xs text-gray-500 transition hover:text-gray-900 hover:underline dark:hover:text-gray-300"
							disabled={detaching}
							on:click={handleDetach}
						>
							<div class="flex items-center gap-1.5">
								<span>{$i18n.t('Detach to local')}</span>
								{#if detaching}
									<Spinner className="size-3" />
								{/if}
							</div>
						</button>
					{/if}
				{/if}
			</div>
		</div>

		<Textarea
			className="min-h-12 w-full resize-none overflow-y-hidden bg-transparent py-1 text-[0.8125rem] text-gray-700 outline-hidden placeholder:text-gray-300 dark:text-gray-300 dark:placeholder:text-gray-700"
			placeholder={$i18n.t('Langfuse prompt content will appear here after preview or sync.')}
			readonly={true}
			bind:value={system}
		/>
	</div>
{:else}
	<div class="flex justify-center py-4">
		<Spinner className="size-4" />
	</div>
{/if}
