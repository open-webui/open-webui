<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { user } from '$lib/stores';
	import { slugify, formatDate } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import {
		getPromptHistory,
		updatePromptByCommand,
		setProductionPromptVersion,
		deletePromptHistoryVersion
	} from '$lib/apis/prompts';
	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import PromptHistoryMenu from './PromptHistoryMenu.svelte';
	import Badge from '$lib/components/common/Badge.svelte';

	dayjs.extend(localizedFormat);

	export let onSubmit: Function;
	export let edit = false;
	export let prompt = null;
	export let clone = false;
	export let disabled = false;

	const i18n = getContext('i18n');

	let loading = false;
	let showEditModal = false;

	let name = '';
	let command = '';
	let content = '';
	let commitMessage = '';

	let accessControl = {};
	let showAccessControlModal = false;
	let hasManualEdit = false;

	let history: any[] = [];
	let historyLoading = false;
	let selectedHistoryEntry: any = null;

	$: if (!edit && !hasManualEdit) {
		command = name !== '' ? slugify(name) : '';
	}

	function handleCommandInput(e: Event) {
		hasManualEdit = true;
	}

	const submitHandler = async () => {
		if (disabled) {
			toast.error($i18n.t('You do not have permission to edit this prompt.'));
			return;
		}
		loading = true;

		if (validateCommandString(command)) {
			await onSubmit({
				name,
				command,
				content,
				access_control: accessControl,
				commit_message: commitMessage || undefined
			});
			showEditModal = false;
			commitMessage = '';
			await loadHistory();
		} else {
			toast.error(
				$i18n.t('Only alphanumeric characters and hyphens are allowed in the command string.')
			);
		}

		loading = false;
	};

	const validateCommandString = (inputString) => {
		const regex = /^[a-zA-Z0-9-_]+$/;
		return regex.test(inputString);
	};

	const loadHistory = async () => {
		if (!prompt?.command || !edit) return;
		historyLoading = true;
		try {
			history = await getPromptHistory(localStorage.token, prompt.command);
		} catch (error) {
			console.error('Failed to load history:', error);
			history = [];
		}
		historyLoading = false;
	};

	const setAsProduction = async (historyEntry: any) => {
		if (disabled) {
			toast.error($i18n.t('You do not have permission to edit this prompt.'));
			return;
		}

		try {
			await setProductionPromptVersion(localStorage.token, prompt.command, historyEntry.id);
			// Update local prompt object to trigger reactivity
			prompt = { ...prompt, version_id: historyEntry.id };
			toast.success($i18n.t('Production version updated'));
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	const handleDeleteHistory = async (historyId: string) => {
		if (disabled) return;

		try {
			await deletePromptHistoryVersion(localStorage.token, prompt.command, historyId);
			toast.success($i18n.t('Version deleted'));
			// Reload history
			await loadHistory();
			// Reset selection if deleted entry was selected
			if (selectedHistoryEntry?.id === historyId) {
				selectedHistoryEntry = history.length > 0 ? history[0] : null;
			}
		} catch (error) {
			toast.error(`${error}`);
		}
	};

	const renderDate = (timestamp: number) => {
		const dateVal = timestamp * 1000;
		return $i18n.t(formatDate(dateVal), {
			LOCALIZED_TIME: dayjs(dateVal).format('LT'),
			LOCALIZED_DATE: dayjs(dateVal).format('L')
		});
	};
	onMount(async () => {
		if (prompt) {
			name = prompt.name || '';
			await tick();
			command = prompt.command.at(0) === '/' ? prompt.command.slice(1) : prompt.command;
			content = prompt.content;
			accessControl = prompt?.access_control === undefined ? {} : prompt?.access_control;

			if (edit) {
				await loadHistory();
				// Auto-select production version
				if (prompt.version_id && history.length > 0) {
					selectedHistoryEntry = history.find((h) => h.id === prompt.version_id) || history[0];
				} else if (history.length > 0) {
					selectedHistoryEntry = history[0];
				}
			}
		}
	});
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessControl
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.prompts || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_prompts || $user?.role === 'admin'}
/>

<!-- Edit Modal -->
<Modal size="lg" bind:show={showEditModal}>
	<div class="px-5 pt-4 pb-5">
		<div class="flex justify-between items-center mb-2">
			<div class="text-lg font-medium">{$i18n.t('Edit Prompt')}</div>
			<button
				class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
				on:click={() => (showEditModal = false)}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<form on:submit|preventDefault={submitHandler}>
			<div class="my-2">
				<Tooltip
					content={`${$i18n.t('Only alphanumeric characters and hyphens are allowed')} - ${$i18n.t('Activate this command by typing "/{{COMMAND}}" to chat input.', { COMMAND: command })}`}
					placement="bottom-start"
				>
					<div class="flex flex-col w-full">
						<div class="flex items-center">
							<input
								class="text-2xl font-medium w-full bg-transparent outline-hidden"
								placeholder={$i18n.t('Name')}
								bind:value={name}
								required
							/>
						</div>
						<div class="flex gap-0.5 items-center text-xs text-gray-500">
							<div>/</div>
							<input
								class="w-full bg-transparent outline-hidden"
								placeholder={$i18n.t('Command')}
								bind:value={command}
								on:input={handleCommandInput}
								required
								disabled
							/>
						</div>
					</div>
				</Tooltip>
			</div>

			<div class="my-2">
				<div class="flex w-full justify-between">
					<div class="text-gray-500 text-xs">{$i18n.t('Prompt Content')}</div>
				</div>

				<div class="mt-1">
					<Textarea
						className="text-sm w-full bg-transparent outline-hidden overflow-y-hidden resize-none"
						placeholder={$i18n.t('Write a summary in 50 words that summarizes {{topic}}.')}
						bind:value={content}
						rows={6}
						required
					/>

					<div class="text-xs text-gray-400 dark:text-gray-500">
						ⓘ {$i18n.t('Format your variables using brackets like this:')}&nbsp;<span
							class="text-gray-600 dark:text-gray-300 font-medium"
							>{'{{'}{$i18n.t('variable')}{'}}'}</span
						>.
						{$i18n.t('Make sure to enclose them with')}
						<span class="text-gray-600 dark:text-gray-300 font-medium">{'{{'}</span>
						{$i18n.t('and')}
						<span class="text-gray-600 dark:text-gray-300 font-medium">{'}}'}</span>.
					</div>

					<div class="text-xs text-gray-400 dark:text-gray-500 underline">
						<a href="https://docs.openwebui.com/features/workspace/prompts" target="_blank">
							{$i18n.t('To learn more about powerful prompt variables, click here')}
						</a>
					</div>
				</div>
			</div>

			<div class="mt-4 flex justify-end">
				<button
					class="text-sm px-4 py-2 transition rounded-full {loading
						? 'cursor-not-allowed bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
						: 'bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black'} flex justify-center"
					type="submit"
					disabled={loading}
				>
					<div class="font-medium">{$i18n.t('Save')}</div>
					{#if loading}
						<div class="ml-1.5">
							<Spinner />
						</div>
					{/if}
				</button>
			</div>
		</form>
	</div>
</Modal>

{#if edit}
	<!-- Edit mode: Read-only view with history -->
	<div class="w-full max-h-full">
		<!-- Main Content -->
		<div class="flex-1 min-w-0">
			<!-- Header -->
			<div class="flex items-start justify-between gap-4 mb-2">
				<div class="min-w-0">
					<h1 class="text-2xl font-medium truncate">{name}</h1>
					<div class="text-sm text-gray-500 mt-0.5">/{command}</div>
				</div>
				<div class="flex items-center gap-2 shrink-0">
					{#if !disabled}
						<button
							class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2.5 py-1.5 rounded-full flex gap-1.5 items-center text-sm border border-gray-100 dark:border-gray-800"
							on:click={() => (showAccessControlModal = true)}
						>
							<LockClosed strokeWidth="2.5" className="size-3.5" />
							{$i18n.t('Access')}
						</button>
						<button
							class="px-4 py-1.5 text-sm font-medium bg-black text-white dark:bg-white dark:text-black rounded-full hover:opacity-90 transition shadow-xs"
							on:click={() => (showEditModal = true)}
						>
							{$i18n.t('Edit')}
						</button>
					{:else}
						<span class="text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full"
							>{$i18n.t('Read Only')}</span
						>
					{/if}
				</div>
			</div>

			<div class="flex flex-col lg:flex-row gap-6">
				<!-- Desktop History Sidebar -->
				<div class="hidden lg:block w-72 shrink-0 mt-1 mb-2">
					<div class="sticky">
						{@render historySection()}
					</div>
				</div>

				<!-- Prompt Content -->
				<div class="mb-6 flex-1">
					<div class="flex items-center justify-between mb-1">
						<div class="flex items-center gap-2">
							<div class="text-gray-500 text-xs">
								{$i18n.t('Prompt Content')}
							</div>
							{#if selectedHistoryEntry}
								<span
									class="text-xs text-gray-500 font-mono bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded"
								>
									{selectedHistoryEntry.id.slice(0, 7)}
								</span>
							{/if}
						</div>

						{#if selectedHistoryEntry && !disabled}
							<div class="flex items-center gap-2">
								{#if selectedHistoryEntry.id === prompt?.version_id}
									<Badge type="success" content={$i18n.t('Live')} />
								{:else}
									<button
										class="text-xs text-gray-500 hover:text-gray-900 dark:hover:text-gray-300 hover:underline transition"
										on:click={() => setAsProduction(selectedHistoryEntry)}
									>
										{$i18n.t('Set as Production')}
									</button>
								{/if}
								<PromptHistoryMenu
									isProduction={selectedHistoryEntry.id === prompt?.version_id}
									onDelete={() => handleDeleteHistory(selectedHistoryEntry.id)}
									onClose={() => {}}
								/>
							</div>
						{/if}
					</div>
					<div
						class="bg-gray-50 dark:bg-gray-900 rounded-xl px-4 py-3 border border-gray-100 dark:border-gray-800"
					>
						<pre class="text-sm whitespace-pre-wrap font-mono">{selectedHistoryEntry?.snapshot
								?.content || content}</pre>
					</div>
				</div>

				<!-- Mobile History -->
				<div class="lg:hidden pb-20">
					{@render historySection()}
				</div>
			</div>
		</div>
	</div>
{:else}
	<!-- Create mode: Form -->
	<div class="w-full max-h-full flex justify-center">
		<form class="flex flex-col w-full mb-10" on:submit|preventDefault={submitHandler}>
			<div class="mb-2">
				<Tooltip
					content={`${$i18n.t('Only alphanumeric characters and hyphens are allowed')} - ${$i18n.t('Activate this command by typing "/{{COMMAND}}" to chat input.', { COMMAND: command })}`}
					placement="bottom-start"
				>
					<div class="flex flex-col w-full">
						<div class="flex items-center">
							<input
								class="text-2xl font-medium w-full bg-transparent outline-hidden"
								placeholder={$i18n.t('Name')}
								bind:value={name}
								required
							/>
							<div class="self-center shrink-0">
								<button
									class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
									type="button"
									on:click={() => (showAccessControlModal = true)}
								>
									<LockClosed strokeWidth="2.5" className="size-3.5" />
									<div class="text-sm font-medium shrink-0">{$i18n.t('Access')}</div>
								</button>
							</div>
						</div>
						<div class="flex gap-0.5 items-center text-xs text-gray-500">
							<div>/</div>
							<input
								class="w-full bg-transparent outline-hidden"
								placeholder={$i18n.t('Command')}
								bind:value={command}
								on:input={handleCommandInput}
								required
							/>
						</div>
					</div>
				</Tooltip>
			</div>

			<div class="my-2">
				<div class="text-gray-500 text-xs">{$i18n.t('Prompt Content')}</div>
				<div class="mt-1">
					<Textarea
						className="text-sm w-full bg-transparent outline-hidden overflow-y-hidden resize-none"
						placeholder={$i18n.t('Write a summary in 50 words that summarizes {{topic}}.')}
						bind:value={content}
						rows={6}
						required
					/>
					<div class="text-xs text-gray-400 dark:text-gray-500">
						ⓘ {$i18n.t('Use')}
						<span class="font-medium text-gray-600 dark:text-gray-300"
							>{'{{'}{$i18n.t('variable')}{'}}'}</span
						>
						{$i18n.t('for placeholders')}
					</div>
				</div>
			</div>

			<div class="my-4 flex justify-end pb-20">
				<button
					class="text-sm w-full lg:w-fit px-4 py-2 transition rounded-xl bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black flex w-full justify-center"
					type="submit"
					disabled={loading}
				>
					<div class="font-medium">{$i18n.t('Save & Create')}</div>
					{#if loading}
						<div class="ml-1.5">
							<Spinner />
						</div>
					{/if}
				</button>
			</div>
		</form>
	</div>
{/if}

{#snippet historySection()}
	<div>
		<div class="flex items-center justify-between mb-2">
			<div class="text-gray-500 text-xs">{$i18n.t('History')}</div>
			{#if historyLoading}
				<Spinner className="size-3" />
			{/if}
		</div>

		{#if history.length > 0}
			<div class="space-y-0">
				{#each history as entry, index}
					<div class="flex">
						<!-- Content -->
						<button
							class="flex-1 text-left px-3.5 py-2 mb-1 rounded-2xl transition group
								{selectedHistoryEntry?.id === entry.id
								? 'bg-gray-50 dark:bg-gray-850'
								: 'hover:bg-gray-50 dark:hover:bg-gray-850'}"
							on:click={() => (selectedHistoryEntry = entry)}
						>
							<!-- Commit Message -->
							<div class="flex items-center gap-2 mb-1">
								<div class="text-xs text-gray-900 dark:text-white truncate">
									{entry.commit_message || $i18n.t('Update')}
								</div>
								{#if entry.id === prompt?.version_id}
									<Badge type="success" content={$i18n.t('Live')} />
								{/if}
							</div>

							<!-- User + Time -->
							<div class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
								{#if entry.user}
									<img
										src={`/api/v1/users/${entry.user.id}/profile/image`}
										alt={entry.user.name}
										class="size-3 rounded-full"
										on:error={(e) => (e.target.src = '/user.png')}
									/>
									<span class="truncate">{entry.user.name}</span>
									<span>•</span>
								{/if}
								<span class="shrink-0">{renderDate(entry.created_at)}</span>
							</div>
						</button>
					</div>
				{/each}
			</div>
		{:else if !historyLoading}
			<div class="text-xs text-gray-400 text-center py-6 italic">
				{$i18n.t('No history available')}
			</div>
		{/if}
	</div>
{/snippet}
