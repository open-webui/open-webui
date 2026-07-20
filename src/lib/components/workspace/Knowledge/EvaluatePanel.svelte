<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext<Writable<any>>('i18n');
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Spinner from '$lib/components/common/Spinner.svelte';

	// ── Types ──
	interface SearchResult {
		chunk_id: string;
		text: string;
		score: number;
		metadata: any;
		rank: number;
	}

	interface Metrics {
		recall_at_k: number;
		precision_at_k: number;
		mrr: number;
		total_relevant: number;
	}

	interface Annotation {
		chunk_id: string;
		document_text: string;
		rank_position: number;
		relevance: number; // 0 or 1
	}

	// ── State ──
	let knowledgeId = '';
	$: if ($page.params.id) knowledgeId = $page.params.id;

	let query = '';
	let k = 10;
	let searching = false;
	let annotating = false;

	let results: SearchResult[] = [];
	let metrics: Metrics | null = null;
	let annotations: Record<string, number> = {}; // chunk_id → 0|1

	// ── Prompt template ──
	let promptTemplate = '';
	let promptIsDefault = true;
	let showPromptEditor = false;
	let savingPrompt = false;

	async function loadPrompt() {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/prompt`, {
				headers: { authorization: `Bearer ${$user?.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				promptTemplate = data.prompt_template;
				promptIsDefault = data.is_default;
			}
		} catch (e) { /* ignore */ }
	}

	async function savePrompt() {
		savingPrompt = true;
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/prompt`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${$user?.token}`
				},
				body: JSON.stringify({ prompt_template: promptTemplate })
			});
			if (!res.ok) throw await res.json();
			promptIsDefault = false;
			toast.success('Prompt template saved');
		} catch (e: any) {
			toast.error(e?.detail ?? 'Failed to save prompt');
		} finally {
			savingPrompt = false;
		}
	}

	function resetPrompt() {
		promptTemplate = 'You are a helpful AI assistant. Use the following reference materials to answer the user\'s question.\n\nReference Materials:\n{context}\n\nUser Question: {query}\n\nIf the reference materials do not contain relevant information, please say so honestly.';
	}

	// ── Run evaluation query ──
	async function runQuery() {
		if (!query.trim()) return;
		searching = true;
		results = [];
		metrics = null;
		annotations = {};

		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/evaluate/query`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${$user?.token}`
				},
				body: JSON.stringify({ query: query.trim(), k })
			});
			if (!res.ok) throw await res.json();
			const data = await res.json();
			results = data.results ?? [];
			metrics = data.metrics ?? null;
			// Load existing annotations for this query
			await loadAnnotations();
		} catch (e: any) {
			toast.error(e?.detail ?? 'Query failed');
		} finally {
			searching = false;
		}
	}

	// ── Load existing annotations ──
	async function loadAnnotations() {
		try {
			const res = await fetch(
				`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/evaluate/judgments`,
				{ headers: { authorization: `Bearer ${$user?.token}` } }
			);
			if (!res.ok) return;
			const data = await res.json();
			const grouped = data.judgments ?? {};
			// Load annotations for current query
			const currentJudgments = grouped[query.trim()] ?? [];
			annotations = {};
			for (const j of currentJudgments) {
				if (j.chunk_id) annotations[j.chunk_id] = j.relevance;
			}
		} catch (e) {
			// ignore
		}
	}

	// ── Toggle relevance annotation ──
	async function toggleRelevance(chunkId: string, relevance: number) {
		annotations[chunkId] = relevance;
		annotations = { ...annotations }; // trigger reactivity

		annotating = true;
		try {
			const chunk = results.find(r => r.chunk_id === chunkId);
			await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/evaluate/annotate`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${$user?.token}`
				},
				body: JSON.stringify({
					query_text: query.trim(),
					judgments: [{
						chunk_id: chunkId,
						rank_position: chunk?.rank ?? 0,
						document_text: chunk?.text?.substring(0, 200) ?? '',
						relevance
					}]
				})
			});
			// Reload metrics after annotating
			const res = await fetch(
				`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/evaluate/query`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						authorization: `Bearer ${$user?.token}`
					},
					body: JSON.stringify({ query: query.trim(), k })
				}
			);
			if (res.ok) {
				const data = await res.json();
				metrics = data.metrics ?? null;
			}
		} catch (e: any) {
			toast.error(e?.detail ?? 'Annotation failed');
		} finally {
			annotating = false;
		}
	}

	// ── Score color ──
	function scoreColor(val: number): string {
		if (val > 0.8) return 'text-green-600';
		if (val > 0.5) return 'text-amber-600';
		return 'text-red-500';
	}

	function precisionColor(val: number): string {
		if (val > 0.7) return 'text-green-600';
		if (val > 0.4) return 'text-amber-600';
		return 'text-red-500';
	}

	onMount(() => loadPrompt());
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
		<div>
			<h1 class="text-xl font-semibold">Retrieval Evaluation</h1>
			<p class="text-sm text-gray-500 mt-1">Test retrieval quality and annotate results</p>
		</div>
		<button
			on:click={() => goto(`/workspace/knowledge/${knowledgeId}`)}
			class="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
		>
			← Back to Files
		</button>
	</div>

	<!-- Prompt Template Editor -->
	<div class="border-b border-gray-200 dark:border-gray-700">
		<button
			on:click={() => showPromptEditor = !showPromptEditor}
			class="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-900 transition"
		>
			<span>RAG Prompt Template {promptIsDefault ? '(default)' : '(customized)'}</span>
			<span class="text-xs">{showPromptEditor ? '▲' : '▼'}</span>
		</button>
		{#if showPromptEditor}
			<div class="px-4 pb-3 space-y-2">
				<div class="text-xs text-gray-400">
					Variables: <code class="px-1 bg-gray-100 dark:bg-gray-700 rounded">{'{query}'}</code>
					<code class="px-1 bg-gray-100 dark:bg-gray-700 rounded">{'{context}'}</code>
					<code class="px-1 bg-gray-100 dark:bg-gray-700 rounded">{'{kb_name}'}</code>
				</div>
				<textarea
					bind:value={promptTemplate}
					rows="6"
					class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm font-mono"
				></textarea>
				<div class="flex gap-2">
					<button
						on:click={savePrompt}
						disabled={savingPrompt}
						class="px-3 py-1 text-xs rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
					>
						{savingPrompt ? 'Saving...' : 'Save'}
					</button>
					<button
						on:click={resetPrompt}
						class="px-3 py-1 text-xs rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
					>
						Reset to Default
					</button>
				</div>
			</div>
		{/if}
	</div>

	<!-- Query Input -->
	<div class="p-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
		<div class="flex gap-2">
			<input
				type="text"
				bind:value={query}
				placeholder="Enter a test query..."
				class="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm"
				on:keydown={(e) => { if (e.key === 'Enter') runQuery(); }}
			/>
			<select bind:value={k} class="w-20 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-2 text-sm">
				<option value="5">K=5</option>
				<option value="10">K=10</option>
				<option value="20">K=20</option>
			</select>
			<button
				on:click={runQuery}
				disabled={searching || !query.trim()}
				class="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition"
			>
				{#if searching}<Spinner />{:else}Search{/if}
			</button>
		</div>
	</div>

	<div class="flex-1 overflow-auto">
		{#if searching}
			<div class="flex items-center justify-center py-20">
				<Spinner /><span class="ml-3 text-sm text-gray-400">Searching...</span>
			</div>
		{:else if results.length > 0}
			<div class="p-4 space-y-4">
				<!-- Metrics Panel -->
				{#if metrics}
					<div class="grid grid-cols-4 gap-3">
						<div class="rounded-lg bg-green-50 dark:bg-green-900/20 p-3 text-center">
							<div class="text-2xl font-bold {precisionColor(metrics.recall_at_k)}">{metrics.recall_at_k}</div>
							<div class="text-xs text-gray-500 mt-1">Recall@{k}</div>
						</div>
						<div class="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-3 text-center">
							<div class="text-2xl font-bold {precisionColor(metrics.precision_at_k)}">{metrics.precision_at_k}</div>
							<div class="text-xs text-gray-500 mt-1">Precision@{k}</div>
						</div>
						<div class="rounded-lg bg-amber-50 dark:bg-amber-900/20 p-3 text-center">
							<div class="text-2xl font-bold text-amber-600">{metrics.mrr}</div>
							<div class="text-xs text-gray-500 mt-1">MRR</div>
						</div>
						<div class="rounded-lg bg-gray-50 dark:bg-gray-800 p-3 text-center">
							<div class="text-2xl font-bold text-gray-600">{metrics.total_relevant}</div>
							<div class="text-xs text-gray-500 mt-1">Relevant docs</div>
						</div>
					</div>
				{:else}
					<div class="text-center text-xs text-gray-400 py-2">
						Annotate results below to see metrics. Mark chunks as relevant ✓ or not relevant ✗.
					</div>
				{/if}

				<!-- Results List -->
				<div class="space-y-2">
					<h3 class="text-sm font-medium text-gray-600 dark:text-gray-400">
						Top-{results.length} Results
					</h3>
					{#each results as result (result.chunk_id)}
						<div
							class="rounded-lg border border-gray-200 dark:border-gray-700 p-3 hover:bg-gray-50 dark:hover:bg-gray-900/50 transition"
							class:border-green-300={annotations[result.chunk_id] === 1}
							class:border-red-300={annotations[result.chunk_id] === 0}
						>
							<div class="flex items-start justify-between gap-3">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="text-xs font-mono px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500">
											#{result.rank}
										</span>
										<span class="text-xs font-mono {scoreColor(result.score)}">
											score: {result.score?.toFixed(4) ?? 'N/A'}
										</span>
									</div>
									<div class="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
										{result.text?.substring(0, 300)}
									</div>
								</div>
								<div class="flex items-center gap-1 shrink-0">
									<button
										on:click={() => toggleRelevance(result.chunk_id, annotations[result.chunk_id] === 1 ? 0 : 1)}
										disabled={annotating}
										class="px-2 py-1 text-xs rounded transition {annotations[result.chunk_id] === 1
											? 'bg-green-500 text-white'
											: 'bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-green-100'}"
										title="Mark as relevant"
									>
										✓
									</button>
									<button
										on:click={() => toggleRelevance(result.chunk_id, annotations[result.chunk_id] === 0 ? -1 : 0)}
										disabled={annotating}
										class="px-2 py-1 text-xs rounded transition {annotations[result.chunk_id] === 0
											? 'bg-red-500 text-white'
											: 'bg-gray-100 dark:bg-gray-700 text-gray-500 hover:bg-red-100'}"
										title="Mark as not relevant"
									>
										✗
									</button>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{:else}
			<div class="text-center py-20 text-gray-400">
				<p class="mb-2">Enter a query to evaluate retrieval quality.</p>
				<p class="text-xs">The system will search the knowledge base and show the top-K results with relevance scores.</p>
			</div>
		{/if}
	</div>
</div>
