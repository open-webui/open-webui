<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { user } from '$lib/stores';
	import dayjs from 'dayjs';
	import { toast } from 'svelte-sonner';
	import {
		getModelSystemPromptDetail,
		getModelSystemPromptDiff,
		getModelSystemPromptComments,
		createModelSystemPromptComment,
		deleteModelSystemPromptComment
	} from '$lib/apis/models';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Badge from '$lib/components/common/Badge.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let modelId: string;
	export let versionId: string | null = null;
	export let onRestore: (system: string) => void;
	export let onRestoreComplete: (() => void) | undefined = undefined;

	let tab: 'detail' | 'diff' = 'diff';

	// detail
	let detailId = '';
	let detailLoading = false;
	let detail: any = null;

	// diff
	let fromId = '';
	let toId = '';
	let diffLoading = false;
	let diffResult: string[] | null = null;
	let snapshotDiff: { field: string; from: any; to: any }[] | null = null;

	// comments
	let comments: any[] = [];
	let commentsLoading = false;
	let newComment = '';

	// pick two versions
	export let history: any[] = [];
	let searchQuery = '';
	let dateFrom = '';
	let dateTo = '';

	$: filtered = history.filter((e) => {
		const q = searchQuery.toLowerCase();
		if (q && !(e.commit_message || '').toLowerCase().includes(q) && !(e.user?.name || '').toLowerCase().includes(q)) return false;
		if (dateFrom && e.created_at * 1000 < new Date(dateFrom).getTime()) return false;
		if (dateTo && e.created_at * 1000 > new Date(dateTo + 'T23:59:59').getTime()) return false;
		return true;
	});

	$: ordered = [...filtered].reverse();

	const loadDetail = async (historyId: string) => {
		detailLoading = true;
		try {
			detail = await getModelSystemPromptDetail(localStorage.token, modelId, historyId);
		} catch {
			detail = null;
		}
		detailLoading = false;
	};

	const loadComments = async (historyId: string) => {
		commentsLoading = true;
		try {
			comments = (await getModelSystemPromptComments(localStorage.token, modelId, historyId)) || [];
		} catch {
			comments = [];
		}
		commentsLoading = false;
	};

	const handleVersionClick = (entry: any) => {
		if (!fromId) {
			fromId = entry.id;
		} else if (!toId && entry.id !== fromId) {
			toId = entry.id;
		} else {
			fromId = entry.id;
			toId = '';
			diffResult = null;
		}
		tab = 'diff';
	};

	const runDiff = async () => {
		if (!fromId || !toId) return;
		diffLoading = true;
		try {
			const res = await getModelSystemPromptDiff(localStorage.token, modelId, fromId, toId);
			diffResult = res?.content_diff ?? null;
			const fromEntry = findEntry(fromId);
			const toEntry = findEntry(toId);
			snapshotDiff = computeSnapshotDiff(fromEntry?.snapshot, toEntry?.snapshot);
		} catch {
			diffResult = null;
		}
		diffLoading = false;
	};

	const selectForDetail = async (entry: any) => {
		tab = 'detail';
		await loadDetail(entry.id);
		await loadComments(entry.id);
	};

	const handleAddComment = async () => {
		if (!newComment.trim() || !detail) return;
		try {
			await createModelSystemPromptComment(localStorage.token, modelId, detail.id, newComment.trim());
			newComment = '';
			await loadComments(detail.id);
			toast.success($i18n.t('Comment added'));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleDeleteComment = async (comment: any) => {
		try {
			await deleteModelSystemPromptComment(localStorage.token, modelId, detail.id, comment.id);
			await loadComments(detail.id);
			toast.success($i18n.t('Comment deleted'));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const swap = () => {
		const tmp = fromId;
		fromId = toId;
		toId = tmp;
		diffResult = null;
	};

	const findEntry = (id: string) => history.find((h) => h.id === id);

	const renderDate = (ts: number) => dayjs(ts * 1000).format('L LT');

	const formatVal = (v: any): string => {
		if (v === null || v === undefined || v === '') return '(empty)';
		if (Array.isArray(v)) return v.length ? v.join(', ') : '(empty)';
		if (typeof v === 'object') return JSON.stringify(v);
		return String(v);
	};

	const computeSnapshotDiff = (from: any, to: any): { field: string; from: any; to: any }[] => {
		if (!from || !to) return [];
		const diffs: { field: string; from: any; to: any }[] = [];
		const keys = new Set([...Object.keys(from), ...Object.keys(to)]);
		for (const key of keys) {
			const a = JSON.stringify(from[key]);
			const b = JSON.stringify(to[key]);
			if (a !== b) diffs.push({ field: key, from: from[key], to: to[key] });
		}
		const prune = (v: any) => (typeof v === 'object' && v !== null ? Object.fromEntries(Object.entries(v).filter(([, x]) => x !== null && x !== undefined && x !== '')) : v);
		return diffs
			.map((d) => ({ ...d, from: prune(d.from), to: prune(d.to) }))
			.filter((d) => JSON.stringify(d.from) !== JSON.stringify(d.to));
	};

	const handleRestore = () => {
		if (!window.confirm($i18n.t('Load this prompt into the editor? It will overwrite the current system prompt.'))) return;
		const entry = findEntry(toId || fromId);
		if (entry) {
			onRestore(entry.system_prompt);
			onRestoreComplete?.();
			show = false;
			toast.success($i18n.t('Prompt loaded into editor — save to apply'));
		}
	};
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<svelte:window on:keydown={(e) => { if (e.key === 'Escape' && show) show = false; }} />

{#if show}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
		on:click={() => (show = false)}
		role="dialog"
		aria-modal="true"
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col mx-4"
			on:click|stopPropagation
		>
			<!-- header -->
			<div class="flex items-center justify-between px-5 py-3 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center gap-3">
					<h2 class="text-base font-semibold">{$i18n.t('System Prompt Versions')}</h2>
					<div class="flex gap-1">
						<button
							type="button"
							class="px-2.5 py-1 text-xs rounded-lg transition {tab === 'detail' ? 'bg-gray-200 dark:bg-gray-700' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}"
							on:click={() => (tab = 'detail')}
						>
							{$i18n.t('Detail')}
						</button>
						<button
							type="button"
							class="px-2.5 py-1 text-xs rounded-lg transition {tab === 'diff' ? 'bg-gray-200 dark:bg-gray-700' : 'hover:bg-gray-100 dark:hover:bg-gray-800'}"
							on:click={() => (tab = 'diff')}
						>
							{$i18n.t('Difference')}
						</button>
					</div>
				</div>
				<button
					type="button"
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
					on:click={() => (show = false)}
					aria-label={$i18n.t('Close')}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
						<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
					</svg>
				</button>
			</div>

			<!-- search + date filters -->
			<div class="flex gap-2 px-5 pt-3 pb-1">
				<input
					class="flex-1 text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5"
					placeholder={$i18n.t('Search by commit message or user...')}
					bind:value={searchQuery}
				/>
				<input type="date" class="text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5" bind:value={dateFrom} title={$i18n.t('From date')} />
				<input type="date" class="text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5" bind:value={dateTo} title={$i18n.t('To date')} />
			</div>

			<!-- body -->
			<div class="flex-1 overflow-y-auto p-5 space-y-4">
				{#if tab === 'detail'}
					<div class="space-y-3">
						<div class="text-xs font-medium text-gray-500 mb-1">{$i18n.t('Select a version')}</div>
						<select
							class="w-full text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5"
							bind:value={detailId}
							on:change={() => { if (detailId) { loadDetail(detailId); loadComments(detailId); } }}
						>
							<option value="">—</option>
							{#each ordered as entry}
								<option value={entry.id}>{entry.commit_message || entry.id.slice(0, 7)}</option>
							{/each}
						</select>
					</div>
					{#if detailLoading}
						<div class="flex justify-center py-6"><Spinner className="size-5" /></div>
					{:else if detail}
						<div class="space-y-3">
							<div class="flex items-center gap-2">
								<span class="font-mono text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">{detail.id.slice(0, 7)}</span>
								{#if detail.id === versionId}
									<Badge type="success" content={$i18n.t('Live')} />
								{/if}
							</div>

							<div class="flex items-center gap-2 text-xs text-gray-500">
								{#if detail.user}
									<img
										src={`/api/v1/users/${detail.user.id}/profile/image`}
										alt={detail.user.name}
										class="size-4 rounded-full"
										on:error={(e) => (e.target.src = '/user.png')}
									/>
									<span>{detail.user.name}</span>
									<span>•</span>
								{/if}
								<span>{renderDate(detail.created_at)}</span>
							</div>

							{#if detail.commit_message}
								<div class="text-xs text-gray-500 italic">"{detail.commit_message}"</div>
							{/if}

							{#if detail.snapshot}
								<div class="text-xs font-medium text-gray-500 mb-1">{$i18n.t('Snapshot')}</div>
								<div class="text-xs bg-gray-50 dark:bg-gray-850 rounded-lg p-3 max-h-48 overflow-y-auto whitespace-pre-wrap break-words">{JSON.stringify(detail.snapshot, null, 2)}</div>
							{/if}

							<div>
								<div class="text-xs font-medium text-gray-500 mb-1">{$i18n.t('System Prompt')}</div>
								<pre class="text-xs bg-gray-50 dark:bg-gray-850 rounded-lg p-3 max-h-48 overflow-y-auto whitespace-pre-wrap break-words">{detail.system_prompt || $i18n.t('(empty)')}</pre>
							</div>

							<!-- comments -->
							<div>
								<div class="text-xs font-medium text-gray-500 mb-2">{$i18n.t('Comments')}</div>

								{#if commentsLoading}
									<div class="flex justify-center py-2"><Spinner className="size-3" /></div>
								{:else if comments.length > 0}
									<div class="space-y-2 max-h-40 overflow-y-auto">
										{#each comments as comment}
											<div class="flex items-start gap-2 bg-gray-50 dark:bg-gray-850 rounded-lg px-3 py-2">
												{#if comment.user}
													<img
														src={`/api/v1/users/${comment.user.id}/profile/image`}
														alt={comment.user.name}
														class="size-5 rounded-full mt-0.5"
														on:error={(e) => (e.target.src = '/user.png')}
													/>
												{/if}
												<div class="flex-1 min-w-0">
													<div class="flex items-center gap-2">
														<span class="text-xs font-medium">{comment.user?.name || '—'}</span>
														<span class="text-[10px] text-gray-400">{renderDate(comment.created_at)}</span>
														{#if comment.user_id === $user?.id}
															<button
																type="button"
																class="ml-auto text-gray-400 hover:text-red-500 transition shrink-0"
																on:click={() => handleDeleteComment(comment)}
																aria-label={$i18n.t('Delete comment')}
															>
																<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3">
																	<path d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.286a1.5 1.5 0 0 0 1.492-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.074l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.074l.275-5.5a.75.75 0 0 1 .786-.713Z" />
																</svg>
															</button>
														{/if}
													</div>
													<div class="text-xs mt-0.5">{comment.content}</div>
												</div>
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-xs text-gray-400 italic py-1">{$i18n.t('No comments yet')}</div>
								{/if}

								<div class="flex gap-2 mt-2">
									<input
										class="flex-1 text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 outline-hidden"
										placeholder={$i18n.t('Add a comment...')}
										bind:value={newComment}
										on:keydown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAddComment(); } }}
									/>
									<button
										type="button"
										class="text-xs px-3 py-1.5 bg-black text-white dark:bg-white dark:text-black rounded-lg transition disabled:opacity-50"
										disabled={!newComment.trim()}
										on:click={handleAddComment}
									>
										{$i18n.t('Send')}
									</button>
								</div>
							</div>

							<button
								type="button"
								class="w-full text-xs py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
								on:click={handleRestore}
							>
								{$i18n.t('Load This Prompt Into Editor')}
							</button>
						</div>
					{/if}
				{:else}
					<!-- Diff tab -->
					<div>
						<div class="text-xs font-medium text-gray-500 mb-2">{$i18n.t('Select two versions to compare')}</div>

						<div class="flex items-center gap-2 mb-3">
							<div class="flex-1">
								<div class="text-[10px] text-gray-400 mb-0.5">{$i18n.t('From (older)')}</div>
								<select
									class="w-full text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5"
									bind:value={fromId}
									on:change={() => { diffResult = null; snapshotDiff = null; }}
								>
									<option value="">—</option>
									{#each ordered as entry}
										<option value={entry.id}>{entry.commit_message || entry.id.slice(0, 7)}</option>
									{/each}
								</select>
							</div>
							<div class="self-end pb-1">
								<button
									class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
									on:click={swap}
									aria-label={$i18n.t('Swap')}
								>
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5">
										<path fill-rule="evenodd" d="M10 2a.75.75 0 0 1 .75.75v12.59l1.95-2.1a.75.75 0 1 1 1.1 1.02l-3.25 3.5a.75.75 0 0 1-1.1 0L6.2 14.26a.75.75 0 1 1 1.1-1.02l1.95 2.1V2.75A.75.75 0 0 1 10 2Z" clip-rule="evenodd" />
									</svg>
								</button>
							</div>
							<div class="flex-1">
								<div class="text-[10px] text-gray-400 mb-0.5">{$i18n.t('To (newer)')}</div>
								<select
									class="w-full text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1.5"
									bind:value={toId}
									on:change={() => { diffResult = null; snapshotDiff = null; }}
								>
									<option value="">—</option>
									{#each ordered as entry}
										<option value={entry.id}>{entry.commit_message || entry.id.slice(0, 7)}</option>
									{/each}
								</select>
							</div>
						</div>

						<button
							type="button"
							class="w-full text-xs py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition mb-3 disabled:opacity-50"
							disabled={!fromId || !toId || fromId === toId}
							on:click={runDiff}
						>
							{$i18n.t('Compare')}
						</button>

						{#if diffLoading}
							<div class="flex justify-center py-4"><Spinner className="size-4" /></div>
						{:else if diffResult}
							<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-3 max-h-64 overflow-y-auto">
								{#each diffResult as line}
									{@const cls = line.startsWith('---') || line.startsWith('+++') || line.startsWith('@@')
										? 'text-gray-500 font-mono text-[11px]'
										: line.startsWith('+')
											? 'text-green-700 dark:text-green-400 font-mono text-[11px]'
											: line.startsWith('-')
												? 'text-red-700 dark:text-red-400 font-mono text-[11px]'
												: 'text-gray-700 dark:text-gray-300 font-mono text-[11px]'}
									<div class={cls}>{line}</div>
								{/each}
							</div>
							{#if snapshotDiff && snapshotDiff.length > 0}
								<div class="text-xs font-medium text-gray-500 mt-3 mb-1">{$i18n.t('Parameter Changes')}</div>
								<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-3 max-h-48 overflow-y-auto space-y-1">
									{#each snapshotDiff as d}
										<div class="text-[11px]">
											<span class="font-medium">{d.field}</span>
<span class="text-red-600 dark:text-red-400"> -{formatVal(d.from)}</span>
						<span class="text-green-600 dark:text-green-400"> +{formatVal(d.to)}</span>
										</div>
									{/each}
								</div>
							{/if}
						{:else if fromId && toId && fromId !== toId}
							<div class="text-xs text-gray-400 italic text-center py-4">{$i18n.t('Click Compare to see the diff')}</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}