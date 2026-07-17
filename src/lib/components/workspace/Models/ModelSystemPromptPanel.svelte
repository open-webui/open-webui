<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import { toast } from 'svelte-sonner';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import PromptHistoryMenu from '$lib/components/workspace/Prompts/PromptHistoryMenu.svelte';
	import { formatDate } from '$lib/utils';
	import {
		getModelSystemPromptBinding,
		getModelSystemPromptHistory,
		getModelSystemPromptHistoryEntry,
		createModelSystemPromptVersion,
		setActiveModelSystemPromptVersion,
		deleteModelSystemPromptHistoryEntry,
		type ModelSystemPromptBinding,
		type ModelSystemPromptVersion
	} from '$lib/apis/models/systemPrompt';

	dayjs.extend(localizedFormat);

	export let modelId: string;
	export let writeAccess = true;
	export let legacySystem = '';
	export let system = '';
	export let activeBaseline = '';

	const dispatch = createEventDispatcher<{
		bindingchange: ModelSystemPromptBinding | null;
	}>();

	const i18n = getContext<Writable<i18nType>>('i18n');

	let binding: ModelSystemPromptBinding | null = null;
	let history: ModelSystemPromptVersion[] = [];
	let historyLoading = false;
	let historyPage = 0;
	let historyHasMore = true;
	let selectedEntry: ModelSystemPromptVersion | null = null;
	let commitMessage = '';
	let savingVersion = false;
	let settingActive = false;
	let loaded = false;

	$: effectiveWriteAccess = writeAccess && binding?.source !== 'langfuse';

	const normalizeContent = (value: string) => (value.trim() === '' ? '' : value);

	const renderDate = (timestamp: number) => {
		const dateVal = timestamp * 1000;
		return $i18n.t(formatDate(dateVal), {
			LOCALIZED_TIME: dayjs(dateVal).format('LT'),
			LOCALIZED_DATE: dayjs(dateVal).format('L')
		});
	};

	const loadHistory = async (reset = false) => {
		if (!modelId) return;
		if (historyLoading) return;
		if (!reset && !historyHasMore) return;

		historyLoading = true;

		if (reset) {
			historyPage = 0;
			historyHasMore = true;
		}

		try {
			const newEntries = await getModelSystemPromptHistory(
				localStorage.token,
				modelId,
				historyPage
			);

			if (reset) {
				history = newEntries;
			} else {
				history = [...history, ...newEntries];
			}

			historyHasMore = newEntries.length > 0;
			historyPage = historyPage + 1;
		} catch (error) {
			console.error('Failed to load system prompt history:', error);
			if (reset) {
				history = [];
			}
		}

		historyLoading = false;
	};

	const resolveActiveEntry = async (): Promise<ModelSystemPromptVersion | null> => {
		if (binding?.active_version_id) {
			const inHistory = history.find((entry) => entry.id === binding?.active_version_id);
			if (inHistory) {
				return inHistory;
			}

			try {
				return await getModelSystemPromptHistoryEntry(
					localStorage.token,
					modelId,
					binding.active_version_id
				);
			} catch (error) {
				console.error('Failed to load active system prompt version:', error);
			}
		}

		if (history.length > 0) {
			return history[0];
		}

		return null;
	};

	const initializeSelection = async () => {
		const activeEntry = await resolveActiveEntry();

		if (activeEntry) {
			selectedEntry = activeEntry;
			system = activeEntry.content;
		} else {
			system = legacySystem ?? '';
			selectedEntry = null;
		}

		activeBaseline = normalizeContent(system);
	};

	const loadPanel = async () => {
		if (!modelId) return;

		try {
			binding = await getModelSystemPromptBinding(localStorage.token, modelId);
			dispatch('bindingchange', binding);
		} catch (error) {
			console.error('Failed to load system prompt binding:', error);
			binding = null;
			dispatch('bindingchange', null);
		}

		await loadHistory(true);
		await initializeSelection();
		loaded = true;
	};

	export const reload = async () => {
		loaded = false;
		await loadPanel();
	};

	const handleHistoryScroll = (e: Event) => {
		const target = e.target as HTMLElement;
		const nearBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 50;
		if (nearBottom && historyHasMore && !historyLoading) {
			loadHistory(false);
		}
	};

	const selectEntry = (entry: ModelSystemPromptVersion) => {
		selectedEntry = entry;
		system = entry.content;
	};

	const handleSaveVersion = async () => {
		if (!effectiveWriteAccess) {
			toast.error($i18n.t('You do not have permission to edit this model.'));
			return;
		}

		savingVersion = true;

		try {
			const created = await createModelSystemPromptVersion(localStorage.token, modelId, {
				content: system,
				commit_message: commitMessage.trim() || undefined,
				set_active: true
			});

			binding = await getModelSystemPromptBinding(localStorage.token, modelId);
			dispatch('bindingchange', binding);
			await loadHistory(true);
			selectedEntry = history.find((entry) => entry.id === created.id) ?? created;
			system = selectedEntry.content;
			activeBaseline = normalizeContent(system);
			commitMessage = '';
			toast.success($i18n.t('Version saved'));
		} catch (error) {
			toast.error(`${error}`);
		}

		savingVersion = false;
	};

	const handleSetActive = async () => {
		if (!effectiveWriteAccess || !selectedEntry) return;

		settingActive = true;

		try {
			binding = await setActiveModelSystemPromptVersion(
				localStorage.token,
				modelId,
				selectedEntry.id
			);
			dispatch('bindingchange', binding);
			system = selectedEntry.content;
			activeBaseline = normalizeContent(system);
			toast.success($i18n.t('Production version updated'));
		} catch (error) {
			toast.error(`${error}`);
		}

		settingActive = false;
	};

	const handleDeleteHistory = async (versionId: string) => {
		if (!effectiveWriteAccess) return;

		try {
			await deleteModelSystemPromptHistoryEntry(localStorage.token, modelId, versionId);
			toast.success($i18n.t('Version deleted'));
			await loadHistory(true);

			if (selectedEntry?.id === versionId) {
				await initializeSelection();
			}
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	onMount(async () => {
		await loadPanel();
	});
</script>

{#if loaded}
	<div class="flex flex-col gap-2 md:flex-row md:gap-3">
		{#if history.length > 0 || historyLoading}
			<div class="md:w-56 md:shrink-0">
				<div class="mb-1 text-xs text-gray-400 dark:text-gray-600">
					{$i18n.t('History')}
				</div>

				<div
					class="max-h-48 overflow-y-auto md:max-h-64"
					on:scroll={handleHistoryScroll}
				>
					{#each history as entry (entry.id)}
						<button
							type="button"
							class="group relative w-full px-1.5 py-1.5 pl-3 text-left transition {selectedEntry?.id ===
							entry.id
								? 'text-gray-900 dark:text-white'
								: 'text-gray-500 hover:text-gray-900 dark:text-gray-500 dark:hover:text-gray-200'}"
							on:click={() => selectEntry(entry)}
						>
							<span
								class="absolute left-0 top-1.5 h-[calc(100%-0.75rem)] w-px rounded-full transition {selectedEntry?.id ===
								entry.id
									? 'bg-gray-900 dark:bg-gray-200'
									: 'bg-transparent'}"
							></span>

							<div class="mb-1 flex items-center gap-2">
								<div class="truncate text-xs">
									{entry.commit_message || $i18n.t('Update')}
								</div>
								{#if entry.id === binding?.active_version_id}
									<span
										class="inline-flex shrink-0 items-center text-xs text-gray-400 dark:text-gray-500"
									>
										{$i18n.t('Live')}
									</span>
								{/if}
							</div>

							<div class="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
								{#if entry.user}
									<img
										src={`/api/v1/users/${entry.user.id}/profile/image`}
										alt={entry.user.name}
										class="mr-0.5 size-3 rounded-full"
										on:error={(e) => {
											const target = e.currentTarget as HTMLImageElement;
											target.src = '/user.png';
										}}
									/>
									<span class="truncate">{entry.user.name}</span>
									<span>•</span>
								{/if}
								<span class="shrink-0">{renderDate(entry.created_at)}</span>
							</div>
						</button>
					{/each}

					{#if historyLoading}
						<div class="flex justify-center py-2">
							<Spinner className="size-3" />
						</div>
					{/if}
				</div>
			</div>
		{:else if !historyLoading}
			<div class="text-xs italic text-gray-400 md:w-56">
				{$i18n.t('No history available')}
			</div>
		{/if}

		<div class="min-w-0 flex-1">
			<div class="mb-1 flex flex-wrap items-center justify-between gap-2">
				<div class="flex items-center gap-2">
					{#if selectedEntry}
						<span class="font-mono text-xs text-gray-500">
							{selectedEntry.id.slice(0, 7)}
						</span>
					{/if}
				</div>

				{#if effectiveWriteAccess && selectedEntry}
					<div class="flex items-center gap-2">
						{#if selectedEntry.id === binding?.active_version_id}
							<span class="inline-flex items-center text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('Live')}
							</span>
						{:else}
							<button
								type="button"
								class="text-xs text-gray-500 transition hover:text-gray-900 hover:underline dark:hover:text-gray-300"
								disabled={settingActive}
								on:click={handleSetActive}
							>
								{$i18n.t('Set as Production')}
							</button>
						{/if}

						<PromptHistoryMenu
							isProduction={selectedEntry.id === binding?.active_version_id}
							onDelete={() => {
								if (selectedEntry) {
									handleDeleteHistory(selectedEntry.id);
								}
							}}
							onClose={() => {}}
						/>
					</div>
				{/if}
			</div>

			{#if binding?.source === 'langfuse'}
				<div class="mb-2 text-xs text-amber-600 dark:text-amber-400">
					{$i18n.t('System prompt is managed by Langfuse. Detach to edit locally.')}
				</div>
			{/if}

			<Textarea
				className="min-h-12 w-full resize-none overflow-y-hidden bg-transparent py-1 text-[0.8125rem] text-gray-700 outline-hidden placeholder:text-gray-300 dark:text-gray-300 dark:placeholder:text-gray-700"
				placeholder={$i18n.t(
					'Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.'
				)}
				readonly={!effectiveWriteAccess}
				bind:value={system}
			/>

			{#if effectiveWriteAccess}
				<div class="mt-2 flex flex-col gap-2 sm:flex-row sm:items-end">
					<div class="min-w-0 flex-1">
						<div class="mb-1 text-xs text-gray-400 dark:text-gray-600">
							{$i18n.t('Commit message')} ({$i18n.t('optional')})
						</div>
						<input
							class="w-full rounded-lg bg-transparent py-1 text-xs text-gray-700 outline-hidden ring-1 ring-gray-200/70 placeholder:text-gray-300 focus:ring-gray-300 dark:text-gray-300 dark:ring-white/10 dark:placeholder:text-gray-700 dark:focus:ring-white/20 px-2"
							placeholder={$i18n.t('Describe this version')}
							bind:value={commitMessage}
						/>
					</div>

					<button
						type="button"
						class="shrink-0 rounded-lg bg-gray-50 px-3 py-1.5 text-xs text-gray-900 transition ring-1 ring-gray-200 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-850 dark:text-gray-100 dark:ring-gray-800 dark:hover:bg-gray-800"
						disabled={savingVersion}
						on:click={handleSaveVersion}
					>
						<div class="flex items-center gap-1.5">
							<span>{$i18n.t('Save version')}</span>
							{#if savingVersion}
								<Spinner className="size-3" />
							{/if}
						</div>
					</button>
				</div>
			{/if}
		</div>
	</div>
{:else}
	<div class="flex justify-center py-4">
		<Spinner className="size-4" />
	</div>
{/if}
