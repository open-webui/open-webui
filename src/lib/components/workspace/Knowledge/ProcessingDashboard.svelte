<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	const i18n = getContext<Writable<i18nType>>('i18n');
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Spinner from '$lib/components/common/Spinner.svelte';

	// ── Types ──
	interface ProcessingTask {
		id: string;
		knowledge_id: string;
		file_id: string;
		task_type: string;
		status: 'pending' | 'chunking' | 'embedding' | 'completed' | 'failed';
		progress_pct: number;
		chunks_total: number | null;
		chunks_processed: number | null;
		error_message: string | null;
		created_at: number;
		updated_at: number;
	}

	// ── State ──
	let knowledgeId = '';
	let tasks: ProcessingTask[] = [];
	let eventSource: EventSource | null = null;
	let connected = false;
	let loaded = false;

	$: if ($page.params.id) {
		knowledgeId = $page.params.id;
	}

	// ── Status helpers ──
	const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
		pending:   { label: 'Pending',    color: 'text-gray-500', bg: 'bg-gray-100 dark:bg-gray-700' },
		chunking:  { label: 'Chunking',   color: 'text-blue-500', bg: 'bg-blue-100 dark:bg-blue-900' },
		embedding: { label: 'Embedding',  color: 'text-amber-500', bg: 'bg-amber-100 dark:bg-amber-900' },
		completed: { label: 'Completed',  color: 'text-green-500', bg: 'bg-green-100 dark:bg-green-900' },
		failed:    { label: 'Failed',     color: 'text-red-500', bg: 'bg-red-100 dark:bg-red-900' },
	};

	function getStatusConfig(status: string) {
		return statusConfig[status] ?? statusConfig.pending;
	}

	function progressBarColor(status: string): string {
		switch (status) {
			case 'completed': return 'bg-green-500';
			case 'failed': return 'bg-red-500';
			case 'embedding': return 'bg-amber-500';
			case 'chunking': return 'bg-blue-500';
			default: return 'bg-gray-300 dark:bg-gray-600';
		}
	}

	// ── Polling fallback ──
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	async function pollProgress() {
		try {
			const res = await fetch(
				`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/progress`,
				{
					headers: { authorization: `Bearer ${$user?.token}` }
				}
			);
			if (res.ok) {
				tasks = await res.json();
				loaded = true;
			}
		} catch (e) {
			// ignore poll errors
		}
	}

	// ── SSE connection ──
	function connectSSE() {
		if (!knowledgeId || !$user?.token) return;

		const url = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/progress/stream`;
		eventSource = new EventSource(url + '?token=' + encodeURIComponent($user.token));

		// Note: EventSource doesn't support custom headers, so we pass token as query param
		// The backend ignores it as query param; SSE auth is handled via cookie/session.
		// We'll use polling as primary and SSE as supplementary.

		eventSource.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				if (Array.isArray(data)) {
					tasks = data;
					loaded = true;
				}
			} catch (e) {
				// ignore parse errors
			}
		};

		eventSource.onopen = () => {
			connected = true;
		};

		eventSource.onerror = () => {
			connected = false;
			eventSource?.close();
			// Retry after 5s
			setTimeout(connectSSE, 5000);
		};
	}

	onMount(() => {
		pollTimer = setInterval(pollProgress, 3000);
		pollProgress(); // immediate first poll
		// SSE as supplement - will update faster if it connects
		connectSSE();
	});

	onDestroy(() => {
		if (pollTimer) clearInterval(pollTimer);
		eventSource?.close();
	});

	// ── Computed ──
	$: activeTasks = tasks.filter(t => !['completed', 'failed'].includes(t.status));
	$: completedTasks = tasks.filter(t => t.status === 'completed');
	$: failedTasks = tasks.filter(t => t.status === 'failed');
	$: overallProgress = tasks.length > 0
		? Math.round((completedTasks.length / tasks.length) * 100)
		: 0;
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
		<div>
			<h1 class="text-xl font-semibold">Processing Status</h1>
			<p class="text-sm text-gray-500 mt-1">Real-time document processing progress</p>
		</div>
		<div class="flex items-center gap-3">
			{#if !loaded}
				<Spinner />
				<span class="text-sm text-gray-400">Connecting...</span>
			{:else}
				<span class="text-xs px-2 py-1 rounded-full {connected ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-500'}">
					{connected ? 'Live' : 'Polling'}
				</span>
			{/if}
		</div>
	</div>

	<!-- Overall Progress -->
	{#if tasks.length > 0}
		<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
			<div class="flex items-center justify-between mb-2">
				<span class="text-sm font-medium">Overall</span>
				<span class="text-xs text-gray-500">
					{completedTasks.length}/{tasks.length} completed
					{#if failedTasks.length > 0}
						· {failedTasks.length} failed
					{/if}
				</span>
			</div>
			<div class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
				<div
					class="h-full transition-all duration-500 rounded-full {failedTasks.length > 0 ? 'bg-red-500' : 'bg-blue-500'}"
					style="width: {overallProgress}%"
				></div>
			</div>
		</div>
	{/if}

	<!-- Task List -->
	<div class="flex-1 overflow-auto">
		{#if !loaded}
			<div class="flex items-center justify-center py-20">
				<Spinner />
				<span class="ml-3 text-sm text-gray-400">Loading tasks...</span>
			</div>
		{:else if tasks.length === 0}
			<div class="text-center py-20 text-gray-400">
				<p>No processing tasks yet.</p>
				<p class="text-xs mt-1">Tasks will appear here when files are added to this knowledge base.</p>
			</div>
		{:else}
			<div class="divide-y divide-gray-100 dark:divide-gray-800">
				{#each tasks as task (task.id)}
					<div class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-900/50 transition">
						<div class="flex items-center justify-between mb-2">
							<div class="flex items-center gap-2">
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300 truncate max-w-xs">
									{task.file_id?.substring(0, 8) ?? 'N/A'}...
								</span>
								<span class="text-xs px-2 py-0.5 rounded-full {getStatusConfig(task.status).bg} {getStatusConfig(task.status).color} font-medium">
									{getStatusConfig(task.status).label}
								</span>
							</div>
							<span class="text-xs text-gray-400">{task.progress_pct}%</span>
						</div>

						<!-- Per-file Progress Bar -->
						<div class="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-1">
							<div
								class="h-full transition-all duration-700 rounded-full {progressBarColor(task.status)}"
								style="width: {task.progress_pct}%"
							></div>
						</div>

						<!-- Details -->
						<div class="flex items-center gap-4 text-xs text-gray-400">
							{#if task.chunks_total != null}
								<span>{task.chunks_processed ?? 0} / {task.chunks_total} chunks</span>
							{/if}
							{#if task.error_message}
								<span class="text-red-400 truncate max-w-xs" title={task.error_message}>
									⚠ {task.error_message}
								</span>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Footer Actions -->
	<div class="p-4 border-t border-gray-200 dark:border-gray-700 flex gap-2">
		<button
			on:click={pollProgress}
			class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 transition"
		>
			Refresh
		</button>
		<button
			on:click={() => goto(`/workspace/knowledge/${knowledgeId}`)}
			class="px-3 py-1.5 text-sm rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition"
		>
			← Back to Files
		</button>
	</div>
</div>
