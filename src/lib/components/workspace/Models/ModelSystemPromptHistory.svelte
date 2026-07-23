<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	import {
		getModelSystemPromptHistory,
		restoreModelSystemPromptVersion,
		deleteModelSystemPromptHistoryEntry
	} from '$lib/apis/models';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import ModelSystemPromptDetailDiff from './ModelSystemPromptDetailDiff.svelte';
	import dayjs from 'dayjs';

	const i18n = getContext('i18n');

	export let modelId: string;
	export let versionId: string | null = null;
	export let onRestore: (system: string) => void;
	export let onRestoreComplete: (() => void) | undefined = undefined;

	let history: any[] = [];
	let searchQuery = '';
	let dateFrom = '';
	let dateTo = '';
	let loading = false;
	let loadingMore = false;
	let page = 0;
	let hasMore = true;
	let restoring = false;
	let showModal = false;

	$: filtered = history.filter((e) => {
		const q = searchQuery.toLowerCase();
		if (q && !(e.commit_message || '').toLowerCase().includes(q) && !(e.user?.name || '').toLowerCase().includes(q)) return false;
		if (dateFrom && e.created_at * 1000 < new Date(dateFrom).getTime()) return false;
		if (dateTo && e.created_at * 1000 > new Date(dateTo + 'T23:59:59').getTime()) return false;
		return true;
	});

	const loadHistory = async () => {
		if (!modelId) return;
		loading = true;
		page = 0;
		hasMore = true;
		try {
			history = (await getModelSystemPromptHistory(localStorage.token, modelId, 0)) || [];
		} catch {
			history = [];
		}
		loading = false;
	};

	const loadMore = async () => {
		if (!hasMore || loadingMore) return;
		loadingMore = true;
		try {
			const items = (await getModelSystemPromptHistory(localStorage.token, modelId, page + 1)) || [];
			if (items.length === 0) hasMore = false;
			else { history = [...history, ...items]; page++; }
		} catch { hasMore = false; }
		loadingMore = false;
	};

	const handleRestore = async (entry: any) => {
		if (!window.confirm($i18n.t('Restore this version? It will replace the current system prompt.'))) return;
		restoring = true;
		try {
			const updated = await restoreModelSystemPromptVersion(localStorage.token, modelId, entry.id);
			toast.success($i18n.t('System prompt version restored — already live, no need to save'));
			versionId = updated?.system_prompt_version_id ?? entry.id;
			onRestore(entry.system_prompt);
			onRestoreComplete?.();
		} catch (e) {
			toast.error(`${e}`);
		}
		restoring = false;
	};

	const handleDelete = async (entry: any) => {
		if (entry.id === versionId) {
			toast.error($i18n.t('Cannot delete the active version'));
			return;
		}
		try {
			await deleteModelSystemPromptHistoryEntry(localStorage.token, modelId, entry.id);
			toast.success($i18n.t('Version deleted'));
			await loadHistory();
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const renderDate = (timestamp: number) => {
		const d = timestamp * 1000;
		return dayjs(d).format('L LT');
	};

	onMount(loadHistory);
</script>

<ModelSystemPromptDetailDiff
	bind:show={showModal}
	{modelId}
	{versionId}
	{onRestore}
	{onRestoreComplete}
	history={filtered}
/>

<div class="mt-2">
	<div class="flex items-center justify-between mb-1">
		<div class="text-xs font-medium text-gray-500">{$i18n.t('Version History')}</div>
		<div class="flex items-center gap-2">
			{#if restoring}
				<Spinner className="size-3" />
			{/if}
			{#if history.length > 0}
				<button
					type="button"
					class="text-xs text-blue-600 hover:text-blue-700 transition"
					on:click={() => (showModal = true)}
				>
					{$i18n.t('View & Compare')}
				</button>
			{/if}
		</div>
	</div>

	<div class="flex gap-2 mb-2">
		<input
			class="flex-1 text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5"
			placeholder={$i18n.t('Search by commit message or user...')}
			bind:value={searchQuery}
		/>
		<input type="date" class="text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5" bind:value={dateFrom} title={$i18n.t('From date')} />
		<input type="date" class="text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5" bind:value={dateTo} title={$i18n.t('To date')} />
	</div>

	{#if loading}
		<div class="flex justify-center py-3">
			<Spinner className="size-4" />
		</div>
	{:else if filtered.length > 0}
		<div class="space-y-1 max-h-48 overflow-y-auto">
			{#each filtered as entry}
				<div
					class="flex items-center gap-2 px-3 py-1.5 rounded-lg {entry.id === versionId
						? 'bg-gray-100/50 dark:bg-gray-850/50'
						: 'hover:bg-gray-50 dark:hover:bg-gray-850'} transition"
				>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-1 mb-0.5">
							<span class="font-mono text-xs text-gray-500">{entry.id.slice(0, 7)}</span>
							{#if entry.id === versionId}
								<Badge type="success" content={$i18n.t('Live')} />
							{/if}
						</div>
						<div class="text-xs text-gray-400 truncate">{entry.commit_message || $i18n.t('Update')}</div>
						<div class="flex items-center gap-1 text-[11px] text-gray-400">
							{#if entry.user}
								<img
									src={`/api/v1/users/${entry.user.id}/profile/image`}
									alt={entry.user.name}
									class="size-3 rounded-full"
									on:error={(e) => (e.target.src = '/user.png')}
								/>
								<span class="truncate max-w-20">{entry.user.name}</span>
								<span>•</span>
							{/if}
							<span class="shrink-0">{renderDate(entry.created_at)}</span>
						</div>
					</div>
					<div class="flex items-center gap-1 shrink-0">
						{#if entry.id !== versionId}
							<button
								class="text-gray-400 hover:text-blue-500 transition text-xs"
								type="button"
								on:click={() => handleRestore(entry)}
								aria-label={$i18n.t('Restore this version')}
								title={$i18n.t('Restore')}
							>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
									<path fill-rule="evenodd" d="M8 3.5c-.771 0-1.537.22-2.185.634a3.5 3.5 0 0 0-.665 5.283.75.75 0 0 0 1.06-1.06 2 2 0 0 1 .38-3.019 2.015 2.015 0 0 1 2.188.426l.31.31H7.25a.75.75 0 0 0 0 1.5h3a.75.75 0 0 0 .75-.75v-3a.75.75 0 0 0-1.5 0v1.12l-.31-.31A3.5 3.5 0 0 0 8 3.5Z" clip-rule="evenodd" />
								</svg>
							</button>
						{/if}
						<button
							class="text-gray-400 hover:text-red-500 transition text-xs"
							type="button"
							on:click={() => handleDelete(entry)}
							aria-label={$i18n.t('Delete version')}
							title={$i18n.t('Delete')}
						>
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5">
								<path fill-rule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.286a1.5 1.5 0 0 0 1.492-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.074l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.074l.275-5.5a.75.75 0 0 1 .786-.713Z" clip-rule="evenodd" />
							</svg>
						</button>
					</div>
				</div>
			{/each}
		</div>
		{#if hasMore}
			<button
				type="button"
				class="w-full text-xs py-1 mt-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition disabled:opacity-50"
				on:click={loadMore}
				disabled={loadingMore}
			>
				{loadingMore ? $i18n.t('Loading...') : $i18n.t('Load More')}
			</button>
		{/if}
	{:else}
		<div class="text-xs text-gray-400 italic py-2">{$i18n.t('No version history yet')}</div>
	{/if}
</div>