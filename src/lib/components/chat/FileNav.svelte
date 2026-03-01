<script context="module">
	// Persists across mount/unmount cycles (module-level, not per-instance)
	let savedPath = '/';
</script>

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import { terminalServers, settings, showFileNavPath, selectedTerminalId } from '$lib/stores';
	import {
		getCwd,
		listFiles,
		readFile,
		downloadFileBlob,
		uploadToTerminal,
		createDirectory,
		deleteEntry,
		setCwd,
		type FileEntry
	} from '$lib/apis/terminal';
	import Folder from '../icons/Folder.svelte';
	import Document from '../icons/Document.svelte';
	import PenAlt from '../icons/PenAlt.svelte';
	import Reset from '../icons/Reset.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';

	import FileNavToolbar from './FileNav/FileNavToolbar.svelte';
	import FilePreview from './FileNav/FilePreview.svelte';
	import FileEntryRow from './FileNav/FileEntryRow.svelte';

	const i18n = getContext('i18n');

	export let onAttach: ((blob: Blob, name: string, contentType: string) => void) | null = null;

	// ── Directory state ──────────────────────────────────────────────────
	let currentPath = savedPath;
	let entries: FileEntry[] = [];
	let loading = false;
	let error: string | null = null;

	// ── File preview state ───────────────────────────────────────────────
	let selectedFile: string | null = null;
	let fileContent: string | null = null;
	let fileImageUrl: string | null = null;
	let filePdfData: ArrayBuffer | null = null;
	let fileLoading = false;
	let filePreviewRef: FilePreview;

	// ── File preview toolbar state (bound from FilePreview) ─────────────
	let editing = false;
	let showRaw = false;
	let saving = false;

	const MD_EXTS = new Set(['md', 'markdown', 'mdx']);
	const CSV_EXTS = new Set(['csv', 'tsv']);
	const getFileExt = (path: string | null) => path?.split('.').pop()?.toLowerCase() ?? '';

	$: isMarkdown = MD_EXTS.has(getFileExt(selectedFile));
	$: isCsv = CSV_EXTS.has(getFileExt(selectedFile));
	$: isTextFile = fileContent !== null && fileImageUrl === null && filePdfData === null;

	// ── Upload / folder creation ─────────────────────────────────────────
	let isDragOver = false;
	let uploading = false;
	let creatingFolder = false;
	let newFolderName = '';
	let newFolderInput: HTMLInputElement;
	let creatingFile = false;
	let newFileName = '';
	let newFileInput: HTMLInputElement;

	// ── Delete confirmation ──────────────────────────────────────────────
	let deleteTarget: { path: string; name: string } | null = null;
	let showDeleteConfirm = false;
	let shiftKey = false;

	// ── Terminal resolution ──────────────────────────────────────────────
	let selectedTerminal: { url: string; key: string } | null = null;

	const getTerminal = (): { url: string; key: string } | null => {
		const systemTerminal = $selectedTerminalId
			? (($terminalServers ?? []).find((t) => t.id === $selectedTerminalId) ?? null)
			: ($terminalServers?.[0] ?? null);

		const userTerminal = ($settings?.terminalServers ?? []).find(
			(s) => s.url === $selectedTerminalId
		);

		const isSystem = !!systemTerminal;
		const url = systemTerminal?.url ?? userTerminal?.url ?? '';
		const key = isSystem ? localStorage.token : (userTerminal?.key ?? '');

		return url ? { url, key } : null;
	};

	// Detect terminal changes — the explicit store references ensure
	// Svelte re-runs this block when any of them update.
	let prevTerminalUrl = '';
	$: {
		$selectedTerminalId, $terminalServers, $settings;
		const terminal = getTerminal();
		selectedTerminal = terminal;

		if (terminal && terminal.url !== prevTerminalUrl) {
			prevTerminalUrl = terminal.url;
			(async () => {
				const cwd = await getCwd(terminal.url, terminal.key);
				const dir = cwd ? (cwd.endsWith('/') ? cwd : cwd + '/') : '/';
				savedPath = dir;
				loadDir(dir);
			})();
		}
	}

	// ── Helpers ──────────────────────────────────────────────────────────
	const IMAGE_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico', 'avif']);
	const isImage = (path: string) => IMAGE_EXTS.has(path.split('.').pop()?.toLowerCase() ?? '');
	const isPdf = (path: string) => path.split('.').pop()?.toLowerCase() === 'pdf';

	const buildBreadcrumbs = (path: string) =>
		path
			.split('/')
			.filter(Boolean)
			.reduce(
				(acc, part) => {
					const prev = acc[acc.length - 1];
					acc.push({ label: part, path: `${prev.path}${part}/` });
					return acc;
				},
				[{ label: '/', path: '/' }]
			);

	// ── File preview management ──────────────────────────────────────────
	const clearFilePreview = () => {
		fileContent = null;
		filePreviewRef?.disposePanzoom();
		if (fileImageUrl) {
			URL.revokeObjectURL(fileImageUrl);
			fileImageUrl = null;
		}
		filePdfData = null;
	};

	// ── Directory operations ─────────────────────────────────────────────
	const loadDir = async (path: string) => {
		const terminal = selectedTerminal;
		if (!terminal) return;

		loading = true;
		error = null;
		selectedFile = null;
		clearFilePreview();
		currentPath = path;
		savedPath = path;

		const result = await listFiles(terminal.url, terminal.key, path);
		loading = false;

		// Set working directory on the terminal server (fire-and-forget)
		setCwd(terminal.url, terminal.key, path);

		if (result === null) {
			error =
				'Failed to load directory. Check your Terminal connection in Settings → Integrations.';
			entries = [];
		} else {
			entries = result.sort((a, b) => {
				if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
				return a.name.localeCompare(b.name);
			});
		}
	};

	const openEntry = async (entry: FileEntry) => {
		if (entry.type === 'directory') {
			await loadDir(`${currentPath}${entry.name}/`);
			return;
		}

		const terminal = selectedTerminal;
		if (!terminal) return;

		const filePath = `${currentPath}${entry.name}`;
		selectedFile = filePath;
		fileLoading = true;
		clearFilePreview();

		if (isImage(filePath)) {
			const result = await downloadFileBlob(terminal.url, terminal.key, filePath);
			if (result) fileImageUrl = URL.createObjectURL(result.blob);
		} else if (isPdf(filePath)) {
			const result = await downloadFileBlob(terminal.url, terminal.key, filePath);
			if (result) filePdfData = await result.blob.arrayBuffer();
		} else {
			fileContent = await readFile(terminal.url, terminal.key, filePath);
		}
		fileLoading = false;
	};

	const downloadFile = async (path: string) => {
		const terminal = selectedTerminal;
		if (!terminal) return;

		const result = await downloadFileBlob(terminal.url, terminal.key, path);
		if (!result) return;
		const url = URL.createObjectURL(result.blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = result.filename;
		a.click();
		URL.revokeObjectURL(url);
	};

	// ── Drag-and-drop upload ─────────────────────────────────────────────
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

		const terminal = selectedTerminal;
		if (selectedFile || !terminal) return;

		const droppedFiles = Array.from(e.dataTransfer?.files ?? []);
		if (!droppedFiles.length) return;

		uploading = true;
		for (const file of droppedFiles) {
			await uploadToTerminal(terminal.url, terminal.key, currentPath, file);
		}
		uploading = false;
		await loadDir(currentPath);
	};

	const handleUploadFiles = async (files: File[]) => {
		const terminal = selectedTerminal;
		if (!files.length || !terminal) return;

		uploading = true;
		for (const file of files) {
			await uploadToTerminal(terminal.url, terminal.key, currentPath, file);
		}
		uploading = false;
		await loadDir(currentPath);
	};

	// ── Folder creation ──────────────────────────────────────────────────
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

		const terminal = selectedTerminal;
		if (!terminal) return;

		const result = await createDirectory(terminal.url, terminal.key, `${currentPath}${name}`);
		toast[result ? 'success' : 'error'](
			$i18n.t(result ? 'Folder created' : 'Failed to create folder')
		);
		await loadDir(currentPath);
	};

	// ── File creation ────────────────────────────────────────────────────
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

		const terminal = selectedTerminal;
		if (!terminal) return;

		const emptyFile = new File([''], name, { type: 'application/octet-stream' });
		const result = await uploadToTerminal(terminal.url, terminal.key, currentPath, emptyFile);
		toast[result ? 'success' : 'error'](
			$i18n.t(result ? 'File created' : 'Failed to create file')
		);
		await loadDir(currentPath);
	};

	// ── Delete ───────────────────────────────────────────────────────────
	const handleDelete = async (path: string, name: string) => {
		const terminal = selectedTerminal;
		if (!terminal) return;

		const result = await deleteEntry(terminal.url, terminal.key, path);
		toast[result ? 'success' : 'error'](
			$i18n.t(result ? '{{name}} deleted' : 'Failed to delete {{name}}', { name })
		);
		await loadDir(currentPath);
	};

	const requestDelete = (path: string, name: string) => {
		deleteTarget = { path, name };
		showDeleteConfirm = true;
	};

	// ── Lifecycle ────────────────────────────────────────────────────────
	onMount(async () => {
		const terminal = getTerminal();
		if (!terminal) return;

		let handledDisplayFile = false;

		const unsubFileNav = showFileNavPath.subscribe(async (filePath) => {
			if (!filePath || !selectedTerminal) return;
			handledDisplayFile = true;
			showFileNavPath.set(null);

			const lastSlash = filePath.lastIndexOf('/');
			const dir = lastSlash > 0 ? filePath.substring(0, lastSlash + 1) : '/';
			const fileName = filePath.substring(lastSlash + 1);

			if (dir !== currentPath) {
				await loadDir(dir);
			}

			await tick();
			const entry = entries.find((e) => e.name === fileName);
			if (entry) await openEntry(entry);
		});

		if (!handledDisplayFile) {
			if (savedPath === '/') {
				const cwd = await getCwd(terminal.url, terminal.key);
				if (cwd) savedPath = cwd.endsWith('/') ? cwd : cwd + '/';
			}
			loadDir(savedPath);
		}

		const onKeyDown = (e: KeyboardEvent) => {
			if (e.key === 'Shift') shiftKey = true;
		};
		const onKeyUp = (e: KeyboardEvent) => {
			if (e.key === 'Shift') shiftKey = false;
		};
		const onBlur = () => (shiftKey = false);

		const onVisibilityChange = () => {
			if (document.visibilityState === 'visible' && !selectedFile && selectedTerminal && !loading) {
				loadDir(currentPath);
			}
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur', onBlur);
		document.addEventListener('visibilitychange', onVisibilityChange);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
			document.removeEventListener('visibilitychange', onVisibilityChange);
		};
	});

	onDestroy(() => {
		if (fileImageUrl) URL.revokeObjectURL(fileImageUrl);
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	on:confirm={() => {
		if (deleteTarget) {
			handleDelete(deleteTarget.path, deleteTarget.name);
			deleteTarget = null;
		}
	}}
/>

{#if !selectedTerminal}
	<div class="flex-1 flex flex-col items-center justify-center p-6 text-center gap-3">
		<Folder className="size-10 text-gray-300 dark:text-gray-600" />
		<div class="text-sm text-gray-500 dark:text-gray-400">
			{$i18n.t('No Terminal connection configured.')}
		</div>
		<div class="text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t('Add your Open Terminal URL and API key in Settings → Integrations.')}
		</div>
	</div>
{:else}
	<div
		class="flex flex-col h-full min-h-0 relative"
		on:dragover={handleDragOver}
		on:dragleave={() => (isDragOver = false)}
		on:drop={handleDrop}
		role="region"
		aria-label={$i18n.t('File browser')}
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
				<span class="text-xs text-gray-400 dark:text-gray-500">{currentPath}</span>
			</div>
		{/if}

		<FileNavToolbar
			breadcrumbs={buildBreadcrumbs(currentPath)}
			{selectedFile}
			{loading}
			onNavigate={loadDir}
			onRefresh={() => loadDir(currentPath)}
			onNewFolder={startNewFolder}
			onNewFile={startNewFile}
			onUploadFiles={handleUploadFiles}
		>
			{#if fileImageUrl !== null}
				<Tooltip content={$i18n.t('Reset view')}>
					<button
						class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
						on:click={() => filePreviewRef?.resetImageView()}
						aria-label={$i18n.t('Reset view')}
					>
						<Reset className="size-3.5" />
					</button>
				</Tooltip>
			{/if}
			{#if (isMarkdown || isCsv) && fileContent !== null}
				<Tooltip content={showRaw ? $i18n.t('Preview') : $i18n.t('Source')}>
					<button
						class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
						on:click={() => {
							if (editing) filePreviewRef?.cancelEdit();
							showRaw = !showRaw;
						}}
						aria-label={showRaw ? $i18n.t('Preview') : $i18n.t('Source')}
					>
						{#if showRaw}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="size-3.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
								<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
							</svg>
						{:else}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="size-3.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5" />
							</svg>
						{/if}
					</button>
				</Tooltip>
			{/if}
			{#if isTextFile}
				{#if editing}
					<Tooltip content={$i18n.t('Cancel')}>
						<button
							class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
							on:click={() => filePreviewRef?.cancelEdit()}
							aria-label={$i18n.t('Cancel')}
						>
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
								<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
							</svg>
						</button>
					</Tooltip>
					<Tooltip content={$i18n.t('Save')}>
						<button
							class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
							on:click={() => filePreviewRef?.saveEdit()}
							disabled={saving}
							aria-label={$i18n.t('Save')}
						>
							{#if saving}
								<Spinner className="size-3.5" />
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-3.5">
									<path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z" clip-rule="evenodd" />
								</svg>
							{/if}
						</button>
					</Tooltip>
				{:else}
					<Tooltip content={$i18n.t('Edit')}>
						<button
							class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
							on:click={() => filePreviewRef?.startEdit()}
							aria-label={$i18n.t('Edit')}
						>
							<PenAlt className="size-3.5" />
						</button>
					</Tooltip>
				{/if}
			{/if}
			<Tooltip content={$i18n.t('Download')}>
				<button
					class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
					on:click={() => downloadFile(selectedFile)}
					aria-label={$i18n.t('Download')}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="size-3.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
					</svg>
				</button>
			</Tooltip>
		</FileNavToolbar>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto min-h-0">
			{#if selectedFile !== null}
				<FilePreview
					bind:this={filePreviewRef}
					bind:editing
					bind:showRaw
					bind:saving
					{selectedFile}
					{fileLoading}
					{fileImageUrl}
					{filePdfData}
					{fileContent}
					onSave={async (content) => {
						const terminal = selectedTerminal;
						if (!terminal || !selectedFile) return;
						const fileName = selectedFile.split('/').pop() ?? 'file';
						const dir = selectedFile.substring(0, selectedFile.lastIndexOf('/') + 1) || '/';
						const file = new File([content], fileName, { type: 'text/plain' });
						const result = await uploadToTerminal(terminal.url, terminal.key, dir, file);
						toast[result ? 'success' : 'error'](
							$i18n.t(result ? 'File saved' : 'Failed to save file')
						);
						if (result) fileContent = content;
					}}
				/>
			{:else}
				{#if uploading}
					<div class="flex items-center justify-center gap-2 p-4 text-xs text-gray-500">
						<Spinner className="size-4" />
						{$i18n.t('Uploading...')}
					</div>
				{:else if loading}
					<div class="flex justify-center pt-8"><Spinner className="size-4" /></div>
				{:else if error}
					<div class="p-4 text-xs">{error}</div>
				{:else if entries.length === 0 && !creatingFolder && !creatingFile}
					<div class="flex flex-col items-center justify-center gap-1.5 py-12 text-center">
						<Folder className="size-6 text-gray-200 dark:text-gray-700" />
						<div class="text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('This folder is empty')}
						</div>
						<div class="text-[11px] text-gray-300 dark:text-gray-600">
							{$i18n.t('Drop files here to upload')}
						</div>
					</div>
				{/if}

				{#if !loading && !error && !uploading}
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
						<ul>
							{#each entries as entry}
								<FileEntryRow
									{entry}
									{currentPath}
									terminalUrl={selectedTerminal.url}
									terminalKey={selectedTerminal.key}
									onOpen={openEntry}
									onDownload={downloadFile}
									onDelete={requestDelete}
								/>
							{/each}
						</ul>
					{/if}
				{/if}
			{/if}
		</div>
	</div>
{/if}
