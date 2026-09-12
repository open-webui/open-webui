<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let show = false;
	export let knowledgeId = '';
	export let directoryId: string | null = null;
	export let token = '';
	export let onImportComplete: () => void = () => {};

	type BrowseEntry = {
		name: string;
		type: 'dir' | 'file';
		size: number;
		modified: string;
	};

	type ImportResult = {
		path: string;
		status: 'completed' | 'failed';
		file_id?: string;
		error?: string;
	};

	// State
	let entries: BrowseEntry[] = [];
	let currentPath = '/';
	let pathSegments: { name: string; path: string }[] = [];
	let loading = false;

	// Selection
	let selectedFiles: Set<string> = new Set();
	let selectedFolder: string | null = null;

	// Import
	let importing = false;
	let importResults: Map<string, ImportResult> = new Map();
	let importProgress = 0;
	let importTotal = 0;

	// Computed
	$: selectionCount = selectedFolder
		? entries.filter((e) => e.type === 'file').length
		: selectedFiles.size;

	$: if (show) {
		reset();
		browse('/');
	}

	function reset() {
		currentPath = '/';
		pathSegments = [];
		selectedFiles = new Set();
		selectedFolder = null;
		importing = false;
		importResults = new Map();
		importProgress = 0;
		importTotal = 0;
	}

	function buildSegments(path: string) {
		const parts = path.split('/').filter(Boolean);
		const segments = [{ name: 'local-import', path: '/' }];
		let accumulated = '';
		for (const part of parts) {
			accumulated += '/' + part;
			segments.push({ name: part, path: accumulated });
		}
		return segments;
	}

	async function browse(path: string) {
		loading = true;
		selectedFiles = new Set();
		selectedFolder = null;

		try {
			const res = await fetch(
				`${WEBUI_API_BASE_URL}/files/local/browse?path=${encodeURIComponent(path)}`,
				{
					headers: { Authorization: `Bearer ${token}` }
				}
			);
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.detail || 'Browse failed');
			}
			entries = await res.json();
			currentPath = path;
			pathSegments = buildSegments(path);
		} catch (e) {
			toast.error(`${e}`);
			entries = [];
		} finally {
			loading = false;
		}
	}

	function toggleFile(name: string) {
		if (importing) return;
		// Deselect folder when selecting files
		selectedFolder = null;
		const newSet = new Set(selectedFiles);
		if (newSet.has(name)) {
			newSet.delete(name);
		} else {
			newSet.add(name);
		}
		selectedFiles = newSet;
	}

	function toggleFolder(name: string) {
		if (importing) return;
		// Deselect files when selecting a folder
		selectedFiles = new Set();
		selectedFolder = selectedFolder === name ? null : name;
	}

	function formatSize(bytes: number): string {
		if (bytes === 0) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(1024));
		return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
	}

	async function startImport() {
		if (importing) return;

		let paths: string[] = [];

		if (selectedFolder) {
			// Import all files in the selected folder
			const folderPath = currentPath === '/' ? '/' + selectedFolder : currentPath + '/' + selectedFolder;

			// Browse the folder to get file list
			try {
				const res = await fetch(
					`${WEBUI_API_BASE_URL}/files/local/browse?path=${encodeURIComponent(folderPath)}`,
					{
						headers: { Authorization: `Bearer ${token}` }
					}
				);
				if (!res.ok) throw new Error('Failed to list folder');
				const folderEntries: BrowseEntry[] = await res.json();
				paths = folderEntries
					.filter((e) => e.type === 'file')
					.map((e) => folderPath + '/' + e.name);
			} catch (e) {
				toast.error(`${e}`);
				return;
			}
		} else {
			paths = Array.from(selectedFiles).map((name) =>
				currentPath === '/' ? '/' + name : currentPath + '/' + name
			);
		}

		if (paths.length === 0) {
			toast.error($i18n.t('No files selected'));
			return;
		}

		importing = true;
		importTotal = paths.length;
		importProgress = 0;
		importResults = new Map();

		for (const path of paths) {
			const fileName = path.split('/').pop() || path;
			importResults.set(fileName, { path, status: 'completed' }); // placeholder
			importResults = importResults; // trigger reactivity

			try {
				const res = await fetch(`${WEBUI_API_BASE_URL}/files/local/import`, {
					method: 'POST',
					headers: {
						Authorization: `Bearer ${token}`,
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						paths: [path],
						knowledge_id: knowledgeId,
						directory_id: directoryId
					})
				});

				if (!res.ok) {
					const err = await res.json();
					importResults.set(fileName, {
						path,
						status: 'failed',
						error: err.detail || 'Request failed'
					});
				} else {
					const results: ImportResult[] = await res.json();
					if (results.length > 0) {
						importResults.set(fileName, results[0]);
					}
				}
			} catch (e) {
				importResults.set(fileName, { path, status: 'failed', error: `${e}` });
			}

			importProgress++;
			importResults = importResults; // trigger reactivity
		}

		const succeeded = Array.from(importResults.values()).filter((r) => r.status === 'completed').length;
		const failed = Array.from(importResults.values()).filter((r) => r.status === 'failed').length;

		if (succeeded > 0) {
			toast.success($i18n.t('{{count}} file(s) imported successfully', { count: succeeded }));
		}
		if (failed > 0) {
			toast.error($i18n.t('{{count}} file(s) failed', { count: failed }));
		}

		onImportComplete();
	}
</script>

<Modal size="md" bind:show>
	<div class="flex flex-col max-h-[80vh]">
		<!-- Header -->
		<div class="flex justify-between items-center dark:text-gray-100 px-4 pt-3 pb-1">
			<h3 class="text-base font-normal">{$i18n.t('Local import')}</h3>
			<button
				class="self-center shrink-0 ml-2"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					if (!importing) show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<!-- Breadcrumb -->
		<div class="flex items-center gap-1 px-4 py-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
			{#each pathSegments as segment, idx}
				{#if idx > 0}
					<ChevronRight className="size-3 shrink-0" />
				{/if}
				{#if idx < pathSegments.length - 1}
					<button
						class="hover:text-gray-900 dark:hover:text-gray-100 transition"
						on:click={() => browse(segment.path)}
						disabled={importing}
					>
						{segment.name}
					</button>
				{:else}
					<span class="text-gray-900 dark:text-gray-100">{segment.name}</span>
				{/if}
			{/each}
		</div>

		<!-- File list -->
		<div class="flex-1 overflow-y-auto px-4 pb-2 min-h-[20rem] max-h-[50vh]">
			{#if loading}
				<div class="flex items-center justify-center h-32 text-gray-400">
					<svg class="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
					</svg>
				</div>
			{:else if entries.length === 0}
				<div class="flex items-center justify-center h-32 text-gray-400 text-sm">
					{$i18n.t('Empty directory')}
				</div>
			{:else}
				<div class="flex flex-col gap-0.5">
					{#each entries as entry}
						{#if entry.type === 'dir'}
							<!-- Directory row -->
							<div class="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800 group">
								<!-- Radio toggle -->
								<button
									class="shrink-0"
									on:click|stopPropagation={() => toggleFolder(entry.name)}
									disabled={importing}
									aria-label={$i18n.t('Select folder')}
								>
									<div
										class="w-4 h-4 rounded-full border-2 flex items-center justify-center transition
										{selectedFolder === entry.name
											? 'border-blue-500 bg-blue-500'
											: 'border-gray-300 dark:border-gray-600'}"
									>
										{#if selectedFolder === entry.name}
											<div class="w-1.5 h-1.5 rounded-full bg-white"></div>
										{/if}
									</div>
								</button>

								<!-- Folder icon + name (clickable to navigate) -->
								<button
									class="flex items-center gap-2 flex-1 min-w-0 text-left text-sm"
									on:click={() => browse(currentPath === '/' ? '/' + entry.name : currentPath + '/' + entry.name)}
									disabled={importing}
								>
									<Folder className="size-4 shrink-0 text-gray-400" />
									<span class="truncate dark:text-gray-200">{entry.name}</span>
								</button>

								<ChevronRight className="size-3.5 text-gray-300 dark:text-gray-600 shrink-0" />
							</div>
						{:else}
							<!-- File row -->
							<div class="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800">
								{#if importing}
									<!-- Import status icon -->
									<div class="shrink-0 w-4 h-4 flex items-center justify-center">
										{#if importResults.has(entry.name)}
											{@const result = importResults.get(entry.name)}
											{#if result && result.status === 'completed'}
												<CheckCircle className="size-4 text-green-500" />
											{:else if result && result.status === 'failed'}
												<svg class="size-4 text-amber-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
													<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
												</svg>
											{:else}
												<svg class="w-4 h-4 animate-spin text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
													<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
													<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
												</svg>
											{/if}
										{:else}
											<svg class="w-4 h-4 text-gray-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
												<circle cx="12" cy="12" r="10"></circle>
											</svg>
										{/if}
									</div>
								{:else}
									<!-- Checkbox -->
									<button
										class="shrink-0"
										on:click={() => toggleFile(entry.name)}
										aria-label={$i18n.t('Select file')}
									>
										<div
											class="w-4 h-4 rounded border flex items-center justify-center transition
											{selectedFiles.has(entry.name)
												? 'border-blue-500 bg-blue-500'
												: 'border-gray-300 dark:border-gray-600'}"
										>
											{#if selectedFiles.has(entry.name)}
												<svg class="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
													<path d="M10 3L4.5 8.5L2 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
												</svg>
											{/if}
										</div>
									</button>
								{/if}

								<!-- File icon + name + size -->
								<div class="flex items-center gap-2 flex-1 min-w-0 text-sm">
									<Document className="size-4 shrink-0 text-gray-400" />
									<span class="truncate dark:text-gray-200">{entry.name}</span>
								</div>

								<div class="shrink-0 text-xs text-gray-400">
									{#if importing && importResults.has(entry.name)}
										{@const result = importResults.get(entry.name)}
										{#if result && result.status === 'failed'}
											<span class="text-amber-500 truncate max-w-[10rem] inline-block" title={result.error}>
												{result.error}
											</span>
										{/if}
									{:else}
										{formatSize(entry.size)}
									{/if}
								</div>
							</div>
						{/if}
					{/each}
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="flex items-center justify-between px-4 pb-3.5 pt-2 border-t border-gray-100 dark:border-gray-800">
			<div class="text-xs text-gray-400">
				{#if importing}
					{importProgress} / {importTotal}
				{:else if selectionCount > 0}
					{selectionCount} {$i18n.t('selected')}
				{/if}
			</div>
			<div class="flex gap-2">
				{#if importing && importProgress >= importTotal}
					<button
						class="px-3.5 py-1.5 text-sm bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						on:click={() => {
							show = false;
						}}
					>
						{$i18n.t('Done')}
					</button>
				{:else}
					<button
						class="px-3 py-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 transition"
						on:click={() => {
							if (!importing) show = false;
						}}
						disabled={importing}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="px-3.5 py-1.5 text-sm bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={selectionCount === 0 || importing}
						on:click={startImport}
					>
						{#if importing}
							{$i18n.t('Importing...')}
						{:else}
							{$i18n.t('Import')} ({selectionCount})
						{/if}
					</button>
				{/if}
			</div>
		</div>
	</div>
</Modal>
