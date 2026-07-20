<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	const i18n = getContext<Writable<any>>('i18n');
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Spinner from '$lib/components/common/Spinner.svelte';

	interface Snapshot {
		id: string;
		knowledge_id: string;
		label: string | null;
		description: string | null;
		file_count: number;
		chunk_count: number | null;
		snapshot_data: any;
		created_by: string;
		created_at: number;
	}

	interface CompareResult {
		added_files: Array<{ file_id: string; filename: string }>;
		removed_files: Array<{ file_id: string; filename: string }>;
		modified_files: Array<{ file_id: string; filename: string }>;
		total_chunks_before: number;
		total_chunks_after: number;
	}

	let knowledgeId = '';
	$: if ($page.params.id) knowledgeId = $page.params.id;

	let snapshots: Snapshot[] = [];
	let loaded = false;
	let loading = false;

	// Create modal
	let showCreate = false;
	let snapLabel = '';
	let snapDesc = '';

	// Rollback confirm
	let showRollback = '';
	let rollingBack = false;

	// Compare
	let showCompare = false;
	let compareA = '';
	let compareB = '';
	let compareResult: CompareResult | null = null;

	// ── Load ──
	async function loadSnapshots() {
		loading = true;
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/snapshots`, {
				headers: { authorization: `Bearer ${$user?.token}` }
			});
			if (res.ok) snapshots = await res.json();
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
			loaded = true;
		}
	}

	// ── Create ──
	async function createSnapshot() {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/snapshots`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${$user?.token}`
				},
				body: JSON.stringify({ label: snapLabel || null, description: snapDesc || null })
			});
			if (!res.ok) throw await res.json();
			showCreate = false;
			snapLabel = '';
			snapDesc = '';
			toast.success('Snapshot created');
			await loadSnapshots();
		} catch (e: any) {
			toast.error(e?.detail ?? 'Failed to create snapshot');
		}
	}

	// ── Rollback ──
	async function doRollback(snapId: string) {
		rollingBack = true;
		try {
			const res = await fetch(
				`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/snapshots/${snapId}/rollback`,
				{ method: 'POST', headers: { authorization: `Bearer ${$user?.token}` } }
			);
			if (!res.ok) throw await res.json();
			const data = await res.json();
			showRollback = '';
			toast.success(`Rolled back to "${data.snapshot_label || 'snapshot'}" - ${data.restored_files} files restored`);
			await loadSnapshots();
		} catch (e: any) {
			toast.error(e?.detail ?? 'Rollback failed');
		} finally {
			rollingBack = false;
		}
	}

	// ── Delete ──
	async function deleteSnapshot(snapId: string) {
		if (!confirm('Delete this snapshot?')) return;
		try {
			await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/snapshots/${snapId}`, {
				method: 'DELETE',
				headers: { authorization: `Bearer ${$user?.token}` }
			});
			toast.success('Snapshot deleted');
			await loadSnapshots();
		} catch (e: any) {
			toast.error('Delete failed');
		}
	}

	// ── Compare ──
	async function doCompare() {
		if (!compareA || !compareB) return;
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/snapshots/compare`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${$user?.token}`
				},
				body: JSON.stringify({ snapshot_a_id: compareA, snapshot_b_id: compareB })
			});
			if (!res.ok) throw await res.json();
			compareResult = await res.json();
		} catch (e: any) {
			toast.error(e?.detail ?? 'Compare failed');
		}
	}

	function formatDate(ts: number): string {
		return new Date(ts * 1000).toLocaleString();
	}

	onMount(() => loadSnapshots());
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
		<div>
			<h1 class="text-xl font-semibold">Snapshots</h1>
			<p class="text-sm text-gray-500 mt-1">Version management for knowledge base state</p>
		</div>
		<div class="flex gap-2">
			<button
				on:click={() => { showCompare = !showCompare; compareResult = null; }}
				class="px-3 py-1.5 text-sm rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 transition"
			>
				Compare
			</button>
			<button
				on:click={() => showCreate = true}
				class="px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition"
			>
				+ Create Snapshot
			</button>
			<button
				on:click={() => goto(`/workspace/knowledge/${knowledgeId}`)}
				class="text-sm text-gray-500 hover:text-gray-700"
			>
				← Back
			</button>
		</div>
	</div>

	<div class="flex-1 overflow-auto p-4">
		<!-- Compare Panel -->
		{#if showCompare}
			<div class="mb-4 p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
				<h3 class="text-sm font-medium mb-3">Compare Snapshots</h3>
				<div class="flex items-center gap-3 mb-3">
					<select bind:value={compareA} class="flex-1 rounded border px-2 py-1 text-sm">
						<option value="">-- Snapshot A (older) --</option>
						{#each snapshots as s}
							<option value={s.id}>{s.label || s.id.substring(0, 8)} — {formatDate(s.created_at)}</option>
						{/each}
					</select>
					<span class="text-gray-400">vs</span>
					<select bind:value={compareB} class="flex-1 rounded border px-2 py-1 text-sm">
						<option value="">-- Snapshot B (newer) --</option>
						{#each snapshots as s}
							<option value={s.id}>{s.label || s.id.substring(0, 8)} — {formatDate(s.created_at)}</option>
						{/each}
					</select>
					<button on:click={doCompare} class="px-3 py-1 text-sm rounded bg-blue-600 text-white hover:bg-blue-700">Go</button>
				</div>
				{#if compareResult}
					<div class="grid grid-cols-3 gap-3 text-sm">
						<div class="rounded bg-green-50 dark:bg-green-900/20 p-3">
							<div class="font-medium text-green-600 mb-1">+ Added ({compareResult.added_files.length})</div>
							{#each compareResult.added_files as f}
								<div class="text-xs truncate">{f.filename}</div>
							{/each}
							{#if compareResult.added_files.length === 0}<div class="text-xs text-gray-400">None</div>{/if}
						</div>
						<div class="rounded bg-red-50 dark:bg-red-900/20 p-3">
							<div class="font-medium text-red-600 mb-1">- Removed ({compareResult.removed_files.length})</div>
							{#each compareResult.removed_files as f}
								<div class="text-xs truncate">{f.filename}</div>
							{/each}
							{#if compareResult.removed_files.length === 0}<div class="text-xs text-gray-400">None</div>{/if}
						</div>
						<div class="rounded bg-amber-50 dark:bg-amber-900/20 p-3">
							<div class="font-medium text-amber-600 mb-1">~ Modified ({compareResult.modified_files.length})</div>
							{#each compareResult.modified_files as f}
								<div class="text-xs truncate">{f.filename}</div>
							{/each}
							{#if compareResult.modified_files.length === 0}<div class="text-xs text-gray-400">None</div>{/if}
						</div>
					</div>
					<div class="text-xs text-gray-400 mt-2">
						Chunks: {compareResult.total_chunks_before} → {compareResult.total_chunks_after}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Snapshot List -->
		{#if loading}
			<div class="flex items-center justify-center py-20"><Spinner /></div>
		{:else if snapshots.length === 0}
			<div class="text-center py-20 text-gray-400">
				<p class="mb-2">No snapshots yet.</p>
				<p class="text-xs">Create a snapshot to save the current state of your knowledge base.</p>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each snapshots as snap (snap.id)}
					<div class="rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition">
						<div class="flex items-start justify-between mb-2">
							<div class="font-medium text-sm">{snap.label || 'Snapshot'}</div>
							<span class="text-xs text-gray-400">{formatDate(snap.created_at)}</span>
						</div>
						{#if snap.description}
							<p class="text-xs text-gray-500 mb-2">{snap.description}</p>
						{/if}
						<div class="flex items-center gap-3 text-xs text-gray-400 mb-3">
							<span>📄 {snap.file_count} files</span>
							<span>🧩 {snap.chunk_count ?? '?'} chunks</span>
						</div>
						<div class="flex gap-1">
							<button
								on:click={() => showRollback === snap.id ? showRollback = '' : showRollback = snap.id}
								class="flex-1 px-2 py-1 text-xs rounded bg-amber-100 hover:bg-amber-200 dark:bg-amber-900 dark:hover:bg-amber-800 text-amber-700 dark:text-amber-300 transition"
							>
								Rollback
							</button>
							<button
								on:click={() => deleteSnapshot(snap.id)}
								class="px-2 py-1 text-xs rounded bg-red-50 hover:bg-red-100 dark:bg-red-900/30 dark:hover:bg-red-900/50 text-red-500 transition"
							>
								Delete
							</button>
						</div>
						{#if showRollback === snap.id}
							<div class="mt-3 p-2 bg-amber-50 dark:bg-amber-900/30 rounded text-xs">
								<p class="text-amber-700 dark:text-amber-300 mb-2">This will restore the KB to this snapshot state. Vectors will be re-indexed. Continue?</p>
								<div class="flex gap-1">
									<button on:click={() => doRollback(snap.id)} disabled={rollingBack}
										class="px-2 py-1 bg-amber-500 text-white rounded hover:bg-amber-600">
										{rollingBack ? 'Rolling back...' : 'Confirm Rollback'}
									</button>
									<button on:click={() => showRollback = ''} class="px-2 py-1 bg-gray-200 dark:bg-gray-600 rounded">Cancel</button>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Create Modal -->
	{#if showCreate}
		<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" on:click={() => showCreate = false} role="dialog" tabindex="-1">
			<div class="bg-white dark:bg-gray-900 rounded-xl shadow-xl max-w-md w-full mx-4" on:click|stopPropagation>
				<div class="p-4 border-b"><h3 class="font-semibold">Create Snapshot</h3></div>
				<div class="p-4 space-y-3">
					<div>
						<label class="block text-sm mb-1">Label (optional)</label>
						<input type="text" bind:value={snapLabel} placeholder="v1.0" class="w-full rounded-lg border px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600" />
					</div>
					<div>
						<label class="block text-sm mb-1">Description (optional)</label>
						<textarea bind:value={snapDesc} rows="2" placeholder="Snapshot description..." class="w-full rounded-lg border px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-600"></textarea>
					</div>
				</div>
				<div class="flex justify-end gap-2 p-4 border-t">
					<button on:click={() => showCreate = false} class="px-4 py-1.5 text-sm rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700">Cancel</button>
					<button on:click={createSnapshot} class="px-4 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700">Create</button>
				</div>
			</div>
		</div>
	{/if}
</div>
