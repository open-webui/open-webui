<script context="module">
	let savedPyodidePath = '/mnt/uploads';
</script>

<script lang="ts">
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import { pyodideWorker } from '$lib/stores';
	import PyodideWorkerConstructor from '$lib/workers/pyodide.worker?worker';
	import type { FileEntry } from '$lib/apis/terminal';

	import FileNavToolbar from './FileNav/FileNavToolbar.svelte';
	import FileEntryRow from './FileNav/FileEntryRow.svelte';
	import FilePreview from './FileNav/FilePreview.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Folder from '../icons/Folder.svelte';
	import Document from '../icons/Document.svelte';

	const i18n = getContext('i18n');

	export let overlay = false;

	// ── State ─────────────────────────────────────────────────────────────
	let currentPath = savedPyodidePath;
	let entries: FileEntry[] = [];
	let loading = false;
	let error: string | null = null;

	let selectedFile: string | null = null;
	let fileLoading = false;
	let fileContent: string | null = null;
	let fileImageUrl: string | null = null;

	let isDragOver = false;
	let showDeleteConfirm = false;
	let deletePath = '';
	let deleteName = '';

	let creatingFolder = false;
	let newFolderName = '';
	let newFolderInput: HTMLInputElement;

	let creatingFile = false;
	let newFileName = '';
	let newFileInput: HTMLInputElement;

	// ── Navigation history ──────────────────────────────────────────────────
	type NavEntry = { path: string; file: string | null };
	let navHistory: NavEntry[] = [];
	let navIndex = -1;
	let navigatingHistory = false;

	$: canGoBack = navIndex > 0;
	$: canGoForward = navIndex < navHistory.length - 1;

	const pushNavHistory = (path: string, file: string | null = null) => {
		if (navigatingHistory) return;
		const current = navHistory[navIndex];
		if (current && current.path === path && current.file === file) return;
		if (navIndex < navHistory.length - 1) {
			navHistory = navHistory.slice(0, navIndex + 1);
		}
		navHistory = [...navHistory, { path, file }];
		navIndex = navHistory.length - 1;
	};

	const goBack = async () => {
		if (!canGoBack) return;
		navigatingHistory = true;
		navIndex -= 1;
		const entry = navHistory[navIndex];
		await loadDir(entry.path);
		if (entry.file) {
			const fileName = entry.file.split('/').pop() ?? '';
			await openEntry({ name: fileName, type: 'file', size: 0 });
		}
		navigatingHistory = false;
	};

	const goForward = async () => {
		if (!canGoForward) return;
		navigatingHistory = true;
		navIndex += 1;
		const entry = navHistory[navIndex];
		await loadDir(entry.path);
		if (entry.file) {
			const fileName = entry.file.split('/').pop() ?? '';
			await openEntry({ name: fileName, type: 'file', size: 0 });
		}
		navigatingHistory = false;
	};

	let _reqId = 0;

	const IMAGE_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico', 'avif']);
	const isImage = (path: string) => IMAGE_EXTS.has(path.split('.').pop()?.toLowerCase() ?? '');

	// ── Worker management ─────────────────────────────────────────────────

	function ensureWorker(): Worker {
		let worker = $pyodideWorker;
		if (!worker) {
			worker = new PyodideWorkerConstructor();
			pyodideWorker.set(worker);
		}
		return worker;
	}

	function sendWorkerMessage(msg: any): Promise<any> {
		const worker = ensureWorker();
		const id = `fs-${++_reqId}`;
		return new Promise((resolve, reject) => {
			const timeout = setTimeout(() => {
				worker.removeEventListener('message', handler);
				reject('Timeout');
			}, 30000);

			function handler(event: MessageEvent) {
				if (event.data?.id !== id) return;
				clearTimeout(timeout);
				worker.removeEventListener('message', handler);
				resolve(event.data);
			}

			worker.addEventListener('message', handler);
			worker.postMessage({ ...msg, id });
		});
	}

	// ── Breadcrumbs ───────────────────────────────────────────────────────

	const buildBreadcrumbs = (path: string) => {
		const parts = path.split('/').filter(Boolean);
		return parts.reduce(
			(acc, part) => {
				const prev = acc[acc.length - 1];
				acc.push({ label: part, path: `${prev.path}${part}/` });
				return acc;
			},
			[{ label: '/', path: '/' }]
		);
	};

	$: breadcrumbs = buildBreadcrumbs(currentPath);

	// ── Operations ────────────────────────────────────────────────────────

	const loadDir = async (path: string) => {
		loading = true;
		error = null;
		selectedFile = null;
		clearPreview();
		currentPath = path.endsWith('/') ? path : path + '/';
		savedPyodidePath = currentPath;
		pushNavHistory(currentPath);

		try {
			const res = await sendWorkerMessage({
				type: 'fs:list',
				path: currentPath.replace(/\/$/, '') || '/'
			});
			entries = (res.entries || []).sort((a: FileEntry, b: FileEntry) => {
				if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
				return a.name.localeCompare(b.name);
			});
		} catch {
			error = 'Failed to list directory';
			entries = [];
		}
		loading = false;
	};

	const openEntry = async (entry: FileEntry) => {
		if (entry.type === 'directory') {
			await loadDir(`${currentPath}${entry.name}/`);
			return;
		}

		const filePath = `${currentPath}${entry.name}`;
		pushNavHistory(currentPath, filePath);
		selectedFile = filePath;
		fileLoading = true;
		clearPreview();

		try {
			const res = await sendWorkerMessage({ type: 'fs:read', path: filePath });
			if (res.error) {
				fileContent = `Error: ${res.error}`;
			} else if (isImage(filePath)) {
				const blob = new Blob([res.data]);
				fileImageUrl = URL.createObjectURL(blob);
			} else {
				const decoder = new TextDecoder('utf-8', { fatal: true });
				try {
					fileContent = decoder.decode(res.data);
				} catch {
					fileContent = `[Binary file: ${entry.size ?? 0} bytes]`;
				}
			}
		} catch {
			fileContent = 'Failed to read file';
		}
		fileLoading = false;
	};

	const clearPreview = () => {
		fileContent = null;
		if (fileImageUrl) {
			URL.revokeObjectURL(fileImageUrl);
			fileImageUrl = null;
		}
	};

	const downloadFile = async (path: string) => {
		try {
			const res = await sendWorkerMessage({ type: 'fs:read', path });
			if (res.data) {
				const blob = new Blob([res.data]);
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = path.split('/').pop() ?? 'file';
				a.click();
				URL.revokeObjectURL(url);
			}
		} catch (e) {
			console.error('Download failed:', e);
		}
	};

	const confirmDelete = (path: string, name: string) => {
		deletePath = path;
		deleteName = name;
		showDeleteConfirm = true;
	};

	const doDelete = async () => {
		try {
			await sendWorkerMessage({ type: 'fs:delete', path: deletePath });
			if (selectedFile === deletePath) {
				selectedFile = null;
				clearPreview();
			}
			await loadDir(currentPath);
		} catch (e) {
			console.error('Delete failed:', e);
		}
	};

	const startNewFolder = async () => {
		creatingFolder = true;
		newFolderName = '';
		await tick();
		newFolderInput?.focus();
	};

	const submitNewFolder = async () => {
		const name = newFolderName.trim();
		creatingFolder = false;
		newFolderName = '';
		if (!name) return;
		const folderPath = `${currentPath}${name}`.replace(/\/$/, '');
		try {
			await sendWorkerMessage({ type: 'fs:mkdir', path: folderPath });
			await loadDir(currentPath);
		} catch (e) {
			console.error('Failed to create folder:', e);
		}
	};

	const startNewFile = async () => {
		creatingFile = true;
		newFileName = '';
		await tick();
		newFileInput?.focus();
	};

	const submitNewFile = async () => {
		const name = newFileName.trim();
		creatingFile = false;
		newFileName = '';
		if (!name) return;
		try {
			await sendWorkerMessage({
				type: 'fs:upload',
				files: [{ name, data: new ArrayBuffer(0) }],
				dir: currentPath.replace(/\/$/, '') || '/'
			});
			await loadDir(currentPath);
		} catch (e) {
			console.error('Failed to create file:', e);
		}
	};

	const uploadFiles = async (fileList: File[]) => {
		const payloads: { name: string; data: ArrayBuffer }[] = [];
		for (const file of fileList) {
			payloads.push({ name: file.name, data: await file.arrayBuffer() });
		}
		try {
			await sendWorkerMessage({
				type: 'fs:upload',
				files: payloads,
				dir: currentPath.replace(/\/$/, '') || '/'
			});
		} catch (e) {
			console.error('Upload failed:', e);
		}
		await loadDir(currentPath);
	};

	// ── Drag and drop ─────────────────────────────────────────────────────

	const handleDragOver = (e: DragEvent) => {
		if (selectedFile) return;
		if (!e.dataTransfer?.types.includes('Files')) return;
		e.preventDefault();
		e.stopPropagation();
		isDragOver = true;
	};

	const handleDrop = async (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		isDragOver = false;
		if (selectedFile) return;
		const droppedFiles = Array.from(e.dataTransfer?.files ?? []);
		if (droppedFiles.length) await uploadFiles(droppedFiles);
	};

	// ── Lifecycle ─────────────────────────────────────────────────────────

	const onFilesChanged = async () => {
		try {
			await sendWorkerMessage({ type: 'fs:sync' });
		} catch {}
		loadDir(currentPath);
	};

	onMount(() => {
		ensureWorker();
		loadDir(currentPath);
		window.addEventListener('pyodide:files', onFilesChanged);
	});

	onDestroy(() => {
		window.removeEventListener('pyodide:files', onFilesChanged);
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete {{name}}', { name: deleteName })}
	message={$i18n.t('Are you sure you want to delete this?')}
	on:confirm={doDelete}
/>

<div
	class="flex flex-col h-full min-h-0 min-w-0 relative"
	on:dragover={handleDragOver}
	on:dragleave={() => (isDragOver = false)}
	on:drop={handleDrop}
	role="region"
	aria-label={$i18n.t('Pyodide file browser')}
>
	{#if isDragOver}
		<div
			class="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/80 dark:bg-gray-850/80 backdrop-blur-sm pointer-events-none gap-1.5"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				class="size-5 text-gray-400 dark:text-gray-500"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
				/>
			</svg>
			<span class="text-xs text-gray-400 dark:text-gray-500">{$i18n.t('Drop files here')}</span>
		</div>
	{/if}

	{#if overlay}
		<div class="absolute inset-0 z-10 pointer-events-none" />
	{/if}

	<!-- Toolbar (shared with FileNav) -->
	<FileNavToolbar
		{breadcrumbs}
		{selectedFile}
		{loading}
		{canGoBack}
		{canGoForward}
		onGoBack={goBack}
		onGoForward={goForward}
		onNavigate={(path) => loadDir(path)}
		onRefresh={async () => {
			try {
				await sendWorkerMessage({ type: 'fs:sync' });
			} catch {}
			if (selectedFile) {
				const name = selectedFile.split('/').pop() ?? '';
				openEntry({ name, type: 'file', size: 0 });
			} else {
				loadDir(currentPath);
			}
		}}
		onNewFolder={startNewFolder}
		onNewFile={startNewFile}
		onUploadFiles={uploadFiles}
		onMove={() => {}}
	>
		<!-- File action buttons when a file is selected (slot content) -->
		<button
			class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
			on:click={() => selectedFile && downloadFile(selectedFile)}
			aria-label={$i18n.t('Download')}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="size-3.5"
			>
				<path
					d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z"
				/>
				<path
					d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z"
				/>
			</svg>
		</button>
	</FileNavToolbar>

	<!-- Content area -->
	<div class="flex-1 min-h-0 flex flex-col">
		{#if selectedFile}
			<FilePreview {selectedFile} {fileLoading} {fileImageUrl} {fileContent} {overlay} />
		{:else if loading}
			<div class="flex items-center justify-center flex-1 p-6">
				<Spinner className="size-4" />
			</div>
		{:else if error}
			<div class="flex items-center justify-center flex-1 p-6">
				<div class="text-xs text-red-500">{error}</div>
			</div>
		{:else if entries.length === 0 && !creatingFolder && !creatingFile}
			<div class="flex flex-col items-center justify-center flex-1 p-6 text-center gap-2">
				<Folder className="size-5 text-gray-300 dark:text-gray-600" />
				<div class="text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t('No files yet. Upload files or run Python code to create them.')}
				</div>
			</div>
		{/if}

		{#if !loading && !error && !selectedFile}
			{#if creatingFolder}
				<div class="flex items-center gap-2 px-3 py-1.5">
					<Folder className="size-4 shrink-0 text-blue-400 dark:text-blue-300" />
					<input
						bind:this={newFolderInput}
						bind:value={newFolderName}
						class="flex-1 text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded px-1.5 py-0.5 outline-none focus:border-blue-400 dark:focus:border-blue-500"
						placeholder={$i18n.t('Folder name')}
						on:keydown={(e) => {
							if (e.key === 'Enter') submitNewFolder();
							if (e.key === 'Escape') {
								creatingFolder = false;
								newFolderName = '';
							}
						}}
						on:blur={submitNewFolder}
					/>
				</div>
			{/if}
			{#if creatingFile}
				<div class="flex items-center gap-2 px-3 py-1.5">
					<Document className="size-4 shrink-0 text-gray-400 dark:text-gray-500" />
					<input
						bind:this={newFileInput}
						bind:value={newFileName}
						class="flex-1 text-xs bg-transparent border border-gray-200 dark:border-gray-700 rounded px-1.5 py-0.5 outline-none focus:border-blue-400 dark:focus:border-blue-500"
						placeholder={$i18n.t('File name')}
						on:keydown={(e) => {
							if (e.key === 'Enter') submitNewFile();
							if (e.key === 'Escape') {
								creatingFile = false;
								newFileName = '';
							}
						}}
						on:blur={submitNewFile}
					/>
				</div>
			{/if}

			{#if entries.length > 0 || creatingFolder || creatingFile}
				<ul class="overflow-y-auto flex-1 min-h-0">
					{#each entries as entry (entry.name)}
						<FileEntryRow
							{entry}
							{currentPath}
							onOpen={openEntry}
							onDownload={downloadFile}
							onDelete={confirmDelete}
						/>
					{/each}
				</ul>
			{/if}
		{/if}
	</div>
</div>
