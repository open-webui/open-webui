<script lang="ts">
	import { onMount, onDestroy, tick, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { goto, beforeNavigate } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { user } from '$lib/stores';
	import { slugify, formatDate, copyToClipboard } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import {
		getPromptHistory,
		getPromptDiff,
		getPromptHistoryEntry,
		setProductionPromptVersion,
		deletePromptHistoryVersion,
		updatePromptMetadata,
		updatePromptAccessGrants,
		getPromptTags
	} from '$lib/apis/prompts';
	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import PromptHistoryMenu from './PromptHistoryMenu.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import VersionMenuItem from '../common/VersionMenuItem.svelte';
	import VersionDiff from '../common/VersionDiff.svelte';

	dayjs.extend(localizedFormat);
	export let onSubmit: Function;
	export let edit = false;
	export let prompt: any = null;
	export let clone = false;
	export let disabled = false;
	export let modal = false;
	export let onCancel: Function = () => {};
	const i18n = getContext<Writable<i18nType>>('i18n');

	let loading = false;
	let ready = false;
	let name = '';
	let command = '';
	let content = '';
	let savedContent = '';
	let tags: { name: string }[] = [];
	let commitMessage = '';
	let isProduction = true;
	let accessGrants = [];
	let showAccessControlModal = false;
	let hasManualEdit = false;
	let history: any[] = [];
	let productionEntry: any = null;
	let historyLoading = false;
	let historyError = false;
	let selectedHistoryEntry: any = null;
	let historyPage = 0;
	let historyHasMore = false;
	let showHistory = false;
	let editingHistory = false;
	let historyDiff: any = null;
	let comparing = false;
	let contentCopied = false;
	let contentInput: HTMLTextAreaElement;
	let originalName = '';
	let originalCommand = '';
	let originalTags: { name: string }[] = [];
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let copyTimer: ReturnType<typeof setTimeout> | null = null;
	let metadataSave: Promise<void> = Promise.resolve();
	let suggestionTags: { name: string }[] = [];
	let showDiscard = false;
	let discardAction: () => void = () => {};

	$: selectedVersionId = selectedHistoryEntry?.id ?? prompt?.version_id;
	$: historical = edit && !!selectedHistoryEntry && selectedVersionId !== prompt?.version_id;
	$: readOnly = disabled || (historical && !editingHistory);
	$: metadataDirty =
		name !== originalName ||
		command !== originalCommand ||
		JSON.stringify(tags) !== JSON.stringify(originalTags);
	$: dirty = ready && !disabled && (content !== savedContent || !!commitMessage || metadataDirty);
	$: if (!edit && !hasManualEdit) command = name !== '' ? slugify(name) : '';

	const confirmDiscard = (action: () => void) => {
		if (dirty) {
			discardAction = action;
			showDiscard = true;
		} else action();
	};
	beforeNavigate(({ cancel }) => {
		if (dirty && !loading && !window.confirm($i18n.t('Discard unsaved changes?'))) cancel();
	});

	const validateCommandString = (value: string) => /^[a-zA-Z0-9_-]+$/.test(value);
	const rememberMetadata = () => {
		originalName = name;
		originalCommand = command;
		originalTags = tags;
	};
	const loadHistory = async (reset = false) => {
		if (!prompt?.id || !edit || historyLoading) return;
		historyLoading = true;
		historyError = false;
		const page = reset ? 0 : historyPage;
		try {
			const entries = await getPromptHistory(localStorage.token, prompt.id, page);
			history = reset ? entries : [...history, ...entries];
			historyHasMore = entries.length === 20;
			historyPage = page + 1;
			if (prompt.version_id) {
				productionEntry =
					history.find((entry) => entry.id === prompt.version_id) ||
					(productionEntry?.id === prompt.version_id
						? productionEntry
						: await getPromptHistoryEntry(localStorage.token, prompt.id, prompt.version_id));
			}
		} catch (error) {
			historyError = true;
			toast.error(`${error}`);
		} finally {
			historyLoading = false;
		}
	};
	const selectVersion = (entry: any = null) => {
		historyDiff = null;
		selectedHistoryEntry = entry?.id === prompt?.version_id ? null : entry;
		content = selectedHistoryEntry
			? (selectedHistoryEntry.snapshot.content ?? '')
			: (prompt?.content ?? '');
		savedContent = content;
		commitMessage = '';
		editingHistory = false;
		isProduction = !selectedHistoryEntry;
	};
	const chooseVersion = (entry: any = null) => {
		showHistory = false;
		if ((entry?.id ?? prompt?.version_id) !== selectedVersionId)
			confirmDiscard(() => selectVersion(entry));
	};
	const editVersion = async () => {
		historyDiff = null;
		editingHistory = true;
		isProduction = false;
		await tick();
		contentInput?.focus();
	};
	const compareToCurrent = async () => {
		if (comparing || historyDiff || !historical || editingHistory) return;
		const fromId = selectedVersionId;
		const toId = prompt.version_id;
		comparing = true;
		try {
			const result = await getPromptDiff(localStorage.token, prompt.id, fromId, toId);
			if (selectedVersionId !== fromId || prompt.version_id !== toId || editingHistory) return;
			const before = result.from_snapshot as Record<string, unknown>;
			const after = result.to_snapshot as Record<string, unknown>;
			historyDiff = {
				fromId,
				toId,
				metadata: Object.fromEntries(
					['name', 'tags'].map((key) => [key, { before: before[key], after: after[key] }])
				),
				files:
					result.content_diff.length || result.line_endings_only
						? [{ path: $i18n.t('Prompt Content'), status: 'modified', binary: false }]
						: [],
				line_endings_only: result.line_endings_only,
				content: result.content_diff.join('\n')
			};
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			comparing = false;
		}
	};
	const submitHandler = async () => {
		if (loading || readOnly || historyLoading) return;
		if (!name.trim() || !content.trim() || !validateCommandString(command)) {
			toast.error($i18n.t('Enter a name, content, and a valid command.'));
			return;
		}
		if (debounceTimer) clearTimeout(debounceTimer);
		loading = true;
		try {
			await metadataSave;
			const previousIds = new Set(history.map((entry) => entry.id));
			const production = isProduction;
			const result = await onSubmit({
				id: prompt?.id,
				name,
				command,
				content,
				tags: tags.map((tag) => tag.name),
				access_grants: accessGrants,
				commit_message: commitMessage || undefined,
				is_production: production
			});
			if (!result) throw new Error($i18n.t('Failed to save prompt'));
			prompt = result;
			savedContent = content;
			commitMessage = '';
			rememberMetadata();
			if (edit) {
				await loadHistory(true);
				if (production) selectVersion();
				else {
					const saved = history.find(
						(entry) => !previousIds.has(entry.id) && entry.snapshot.content === content
					);
					if (saved) selectVersion(saved);
				}
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};
	const copyContent = async () => {
		if (await copyToClipboard(content)) {
			contentCopied = true;
			if (copyTimer) clearTimeout(copyTimer);
			copyTimer = setTimeout(() => (contentCopied = false), 2000);
		}
	};
	const setAsProduction = async () => {
		if (disabled || !selectedHistoryEntry || loading) return;
		if (debounceTimer) clearTimeout(debounceTimer);
		loading = true;
		try {
			await metadataSave;
			const result = await setProductionPromptVersion(
				localStorage.token,
				prompt.id,
				selectedHistoryEntry.id
			);
			if (!result) throw new Error($i18n.t('Failed to save prompt'));
			prompt = result;
			name = result.name;
			tags = (result.tags || []).map((tag: string) => ({ name: tag }));
			rememberMetadata();
			selectVersion();
			toast.success($i18n.t('Production version updated'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};
	const handleDeleteHistory = async (historyId: string) => {
		if (disabled || loading) return;
		loading = true;
		try {
			await deletePromptHistoryVersion(localStorage.token, prompt.id, historyId);
			if (selectedHistoryEntry?.id === historyId) selectVersion();
			await loadHistory(true);
			toast.success($i18n.t('Version deleted'));
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};
	const renderDate = (timestamp: number) =>
		$i18n.t(formatDate(timestamp * 1000), {
			LOCALIZED_TIME: dayjs(timestamp * 1000)
				.locale($i18n.language)
				.format('LT'),
			LOCALIZED_DATE: dayjs(timestamp * 1000)
				.locale($i18n.language)
				.format('L')
		});
	const debouncedSaveMetadata = () => {
		if (disabled || !edit) return;
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			metadataSave = metadataSave.then(async () => {
				if (!validateCommandString(command)) {
					toast.error(
						$i18n.t('Only alphanumeric characters and hyphens are allowed in the command string.')
					);
					command = originalCommand;
					return;
				}
				const savedName = name,
					savedCommand = command,
					savedTags = tags;
				try {
					const result = await updatePromptMetadata(
						localStorage.token,
						prompt.id,
						savedName,
						savedCommand,
						savedTags.map((tag) => tag.name)
					);
					prompt = { ...prompt, ...result };
					originalName = savedName;
					originalCommand = savedCommand;
					originalTags = savedTags;
				} catch (error) {
					toast.error(`${error}`);
				}
			});
		}, 500);
	};

	onMount(async () => {
		if (prompt) {
			name = prompt.name || '';
			await tick();
			command = prompt.command.replace(/^\//, '');
			hasManualEdit = true;
			content = prompt.content ?? '';
			tags = (prompt.tags || []).map((tag: string) => ({ name: tag }));
			accessGrants = prompt.access_grants ?? [];
		}
		savedContent = content;
		rememberMetadata();
		ready = true;
		if (edit) await loadHistory(true);
		try {
			const result = await getPromptTags(localStorage.token);
			suggestionTags = (result || []).map((tag: string) => ({ name: tag }));
		} catch (error) {
			console.error('Failed to load prompt tags:', error);
		}
	});
	onDestroy(() => {
		if (debounceTimer) clearTimeout(debounceTimer);
		if (copyTimer) clearTimeout(copyTimer);
	});
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.prompts || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_prompts || $user?.role === 'admin'}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	allowGroups={($user?.permissions?.access_grants?.allow_groups ?? true) || $user?.role === 'admin'}
	onChange={async () => {
		if (edit && prompt?.id) {
			try {
				await updatePromptAccessGrants(localStorage.token, prompt.id, accessGrants);
				toast.success($i18n.t('Saved'));
			} catch (error) {
				toast.error(`${error}`);
			}
		}
	}}
/>

<ConfirmDialog
	bind:show={showDiscard}
	title={$i18n.t('Discard unsaved changes?')}
	confirmLabel={$i18n.t('Discard')}
	onConfirm={discardAction}
/>

<div
	class="flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden {modal
		? 'px-5 pt-3 pb-1'
		: ''}"
>
	<form
		class="flex h-full min-h-0 min-w-0 flex-col"
		inert={loading}
		on:submit|preventDefault={submitHandler}
	>
		<div class="flex min-h-7 shrink-0 items-center justify-between gap-2">
			{#if modal}
				<span class="text-xs text-gray-500"
					>{$i18n.t(clone ? 'Clone Prompt' : 'Create Prompt')}</span
				>
			{:else}
				<button
					type="button"
					class="flex h-6 w-fit shrink-0 items-center gap-1 whitespace-nowrap rounded-md text-xs text-gray-400 transition-colors hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
					on:click={() => goto('/workspace/prompts')}
				>
					<ChevronLeft className="size-3" strokeWidth="2" />{$i18n.t('Back')}
				</button>
			{/if}
			<div class="flex shrink-0 items-center gap-1 pr-0.5">
				{#if !disabled}<AccessButton on:click={() => (showAccessControlModal = true)} />
				{:else}<span class="px-2 py-1 text-xs text-gray-500">{$i18n.t('Read Only')}</span>{/if}
				{#if modal}<button
						type="button"
						aria-label={$i18n.t('Close')}
						class="p-1 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
						on:click={() => confirmDiscard(() => onCancel())}><XMark className="size-4" /></button
					>{/if}
			</div>
		</div>

		<div class="shrink-0 px-1 pb-2">
			<input
				class="w-full bg-transparent text-sm outline-hidden"
				placeholder={$i18n.t('Prompt Name')}
				aria-label={$i18n.t('Prompt Name')}
				bind:value={name}
				on:input={debouncedSaveMetadata}
				required
				{disabled}
			/>
			<div class="mt-0.5 flex min-w-0 items-center gap-2 text-xs text-gray-500">
				<Tooltip
					className="min-w-0 flex-1"
					content={$i18n.t('Activate this command by typing "/{{COMMAND}}" to chat input.', {
						COMMAND: command
					})}
					placement="bottom-start"
				>
					<div class="flex min-w-0 items-center gap-0.5">
						<span>/</span>
						<input
							class="min-w-0 flex-1 bg-transparent outline-hidden"
							placeholder={$i18n.t('Command')}
							aria-label={$i18n.t('Command')}
							bind:value={command}
							on:input={() => {
								hasManualEdit = true;
								debouncedSaveMetadata();
							}}
							required
							{disabled}
						/>
					</div>
				</Tooltip>
				{#if edit}
					<Tooltip className="min-w-0 max-w-[45%]" content={$i18n.t('Click to copy ID')}>
						<button
							type="button"
							class="w-full truncate font-mono text-xs text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
							on:click={async () => {
								if (await copyToClipboard(prompt.id))
									toast.success($i18n.t('ID copied to clipboard'));
							}}>{prompt.id}</button
						>
					</Tooltip>
				{/if}
			</div>
			<div class="mt-1">
				<Tags
					{tags}
					{disabled}
					{suggestionTags}
					on:add={(e) => {
						tags = [...tags, { name: e.detail }];
						debouncedSaveMetadata();
					}}
					on:delete={(e) => {
						tags = tags.filter((tag) => tag.name !== e.detail);
						debouncedSaveMetadata();
					}}
				/>
			</div>
		</div>

		<div
			class="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-gray-100 bg-white dark:border-white/5 dark:bg-gray-900"
		>
			{#if historyDiff}
				<VersionDiff
					diff={historyDiff}
					currentLabel="Production"
					showFileHeaders={false}
					loadFileDiff={async () => ({
						diff: historyDiff.content,
						line_endings_only: historyDiff.line_endings_only
					})}
					onClose={() => (historyDiff = null)}
				/>
			{:else}
				<div
					class="flex shrink-0 items-center gap-1 bg-gray-50/60 px-2.5 py-1.5 text-xs dark:bg-black"
				>
					<div class="min-w-0 flex-1">
						{#if edit}
							<Dropdown bind:show={showHistory}>
								<button
									type="button"
									aria-label={$i18n.t('Select version')}
									class="flex max-w-full items-center gap-2 py-0.5 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
									disabled={loading}
								>
									<span class="truncate"
										>{historical
											? selectedHistoryEntry.commit_message || selectedVersionId.slice(0, 7)
											: $i18n.t('Production')}{editingHistory
											? ` · ${$i18n.t('Editing')}`
											: ''}</span
									><ChevronDown className="size-3 shrink-0" />
								</button>
								<div slot="content">
									<DropdownMenu className="w-56 max-w-[calc(100vw-2rem)] max-h-80 overflow-y-auto">
										<VersionMenuItem
											entry={history.find((entry) => entry.id === prompt?.version_id) ||
												(productionEntry?.id === prompt?.version_id ? productionEntry : null)}
											status={$i18n.t('Production')}
											selected={!historical}
											onSelect={() => chooseVersion()}
										/>
										{#if history.some((entry) => entry.id !== prompt?.version_id)}<hr
												class="border-gray-100 dark:border-gray-800"
											/>{/if}
										{#each history.filter((entry) => entry.id !== prompt?.version_id) as entry (entry.id)}
											<VersionMenuItem
												{entry}
												selected={selectedVersionId === entry.id}
												onSelect={() => chooseVersion(entry)}
											/>
										{/each}
										{#if historyLoading}<div
												class="flex items-center gap-2 px-2 py-1 text-xs text-gray-500"
											>
												<Spinner className="size-3" />{$i18n.t('Loading...')}
											</div>
										{:else if historyError}<button
												type="button"
												on:click={() => loadHistory(historyPage === 0)}>{$i18n.t('Retry')}</button
											>
										{:else if historyHasMore}<hr class="border-gray-100 dark:border-gray-800" />
											<button type="button" on:click={() => loadHistory()}
												>{$i18n.t('Load more')}</button
											>{/if}
									</DropdownMenu>
								</div>
							</Dropdown>
						{:else}<span class="text-gray-500">{$i18n.t('Prompt Content')}</span>{/if}
					</div>
					<Tooltip content={$i18n.t('Use {{variable}} for placeholders')}
						><span class="px-1 text-gray-400">{'{{variable}}'}</span></Tooltip
					>
					<button
						type="button"
						aria-label={$i18n.t('Copy content')}
						class="shrink-0 p-0.5 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
						on:click={copyContent}
						>{#if contentCopied}<Check className="size-3.5 text-green-500" />{:else}<Clipboard
								className="size-3.5"
							/>{/if}</button
					>
					{#if edit && !disabled && selectedVersionId && !editingHistory}
						<PromptHistoryMenu
							isProduction={!historical}
							onDelete={() => handleDeleteHistory(selectedVersionId)}
							onClose={() => {}}
						>
							<button
								type="button"
								aria-label={$i18n.t('More Options')}
								class="shrink-0 p-0.5 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
								><EllipsisHorizontal className="size-3.5" /></button
							>
						</PromptHistoryMenu>
					{/if}
				</div>
				<textarea
					bind:this={contentInput}
					bind:value={content}
					aria-label={$i18n.t('Prompt Content')}
					placeholder={$i18n.t('Write a summary in 50 words that summarizes {{topic}}.')}
					readonly={readOnly}
					required
					spellcheck="false"
					class="min-h-0 w-full flex-1 resize-none bg-transparent px-3 py-2 font-mono text-xs leading-relaxed outline-hidden"
					on:keydown={(event) => {
						if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
							event.preventDefault();
							submitHandler();
						}
					}}
				></textarea>
			{/if}
		</div>

		{#if historical}
			<div
				class="flex shrink-0 flex-wrap items-center justify-between gap-2 px-1 py-2 text-xs text-gray-500"
			>
				<span
					>{selectedHistoryEntry.id.slice(0, 7)} · {renderDate(
						selectedHistoryEntry.created_at
					)}</span
				>
				{#if !editingHistory}<div class="ml-auto flex flex-wrap justify-end gap-2">
						<button
							type="button"
							class="flex h-7 items-center rounded-lg bg-gray-100 px-2.5 text-xs text-gray-700 disabled:opacity-60 dark:bg-gray-850 dark:text-gray-200"
							disabled={comparing || !!historyDiff}
							on:click={compareToCurrent}
							>{#if comparing}<Spinner className="mr-1.5 size-3" />{/if}{$i18n.t(
								'Compare to current'
							)}</button
						>
						{#if !disabled}
							<button
								type="button"
								class="flex h-7 items-center rounded-lg bg-gray-100 px-2.5 text-xs text-gray-700 dark:bg-gray-850 dark:text-gray-200"
								on:click={editVersion}>{$i18n.t('Edit as new version')}</button
							><button
								type="button"
								class="flex h-7 items-center rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
								on:click={() => confirmDiscard(setAsProduction)}
								>{$i18n.t('Set as Production')}</button
							>
						{/if}
					</div>{/if}
			</div>
		{/if}

		{#if !readOnly}
			<div class="flex shrink-0 flex-wrap items-center gap-2 py-2">
				{#if edit}<input
						class="min-w-0 flex-1 bg-transparent px-2 text-xs outline-hidden"
						placeholder={$i18n.t('Describe this change')}
						aria-label={$i18n.t('Commit Message')}
						bind:value={commitMessage}
					/>{:else}<div class="flex-1"></div>{/if}
				<div class="ml-auto flex shrink-0 items-center gap-3">
					{#if historical}<label
							class="flex cursor-pointer items-center gap-1.5 whitespace-nowrap text-xs text-gray-500"
							><input
								type="checkbox"
								bind:checked={isProduction}
								class="size-3 rounded border-gray-300 dark:border-gray-600"
							/><span>{$i18n.t('Set as Production')}</span></label
						>{/if}
					<button
						type="submit"
						class="flex h-7 shrink-0 items-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
						disabled={loading || !ready || historyLoading}
					>
						{$i18n.t(edit ? 'Save' : 'Save & Create')}{#if loading}<Spinner
								className="size-3"
							/>{/if}
					</button>
				</div>
			</div>
		{/if}
	</form>
</div>
