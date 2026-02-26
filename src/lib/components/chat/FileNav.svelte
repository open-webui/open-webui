<script context="module">
	// Persists across mount/unmount cycles (module-level, not per-instance)
	let savedPath = '/';
</script>

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import { settings } from '$lib/stores';
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
	import Spinner from '../common/Spinner.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';

	import FileNavToolbar from './FileNav/FileNavToolbar.svelte';
	import FilePreview from './FileNav/FilePreview.svelte';
	import FileEntryRow from './FileNav/FileEntryRow.svelte';

	const i18n = getContext('i18n');

	export let onAttach: ((blob: Blob, name: string, contentType: string) => void) | null = null;

	let currentPath = savedPath;
	let entries: FileEntry[] = [];
	let loading = false;
	let error: string | null = null;

	let selectedFile: string | null = null;
	let fileContent: string | null = null;
	let fileImageUrl: string | null = null;
	let filePdfData: ArrayBuffer | null = null;
	let fileLoading = false;

	let filePreviewRef: FilePreview;

	const IMAGE_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico', 'avif']);
	const isImage = (path: string) => IMAGE_EXTS.has(path.split('.').pop()?.toLowerCase() ?? '');
	const isPdf = (path: string) => path.split('.').pop()?.toLowerCase() === 'pdf';

	let isDragOver = false;
	let uploading = false;

	let creatingFolder = false;
	let newFolderName = '';
	let newFolderInput: HTMLInputElement;

	let deleteTarget: { path: string; name: string } | null = null;
	let showDeleteConfirm = false;
	let shiftKey = false;

	$: activeTerminal = ($settings?.terminalServers ?? []).find((s) => s.enabled);
	$: terminalUrl = activeTerminal?.url ?? '';
	$: terminalKey = activeTerminal?.key ?? '';
	$: configured = !!terminalUrl;

	$: breadcrumbs = currentPath
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

	const clearFilePreview = () => {
		fileContent = null;
		filePreviewRef?.disposePanzoom();
		if (fileImageUrl) {
			URL.revokeObjectURL(fileImageUrl);
			fileImageUrl = null;
		}
		filePdfData = null;
	};

	const loadDir = async (path: string) => {
		if (!configured) return;
		loading = true;
		error = null;
		selectedFile = null;
		clearFilePreview();
		currentPath = path;
		savedPath = path;
		const result = await listFiles(terminalUrl, terminalKey, path);
		loading = false;

		// Set working directory on the terminal server (fire-and-forget)
		setCwd(terminalUrl, terminalKey, path);
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
		} else {
			const filePath = `${currentPath}${entry.name}`;
			selectedFile = filePath;
			fileLoading = true;
			clearFilePreview();
			if (isImage(filePath)) {
				const result = await downloadFileBlob(terminalUrl, terminalKey, filePath);
				if (result) fileImageUrl = URL.createObjectURL(result.blob);
			} else if (isPdf(filePath)) {
				const result = await downloadFileBlob(terminalUrl, terminalKey, filePath);
				if (result) filePdfData = await result.blob.arrayBuffer();
			} else {
				fileContent = await readFile(terminalUrl, terminalKey, filePath);
			}
			fileLoading = false;
		}
	};

	const downloadFile = async (path: string) => {
		const result = await downloadFileBlob(terminalUrl, terminalKey, path);
		if (!result) return;
		const url = URL.createObjectURL(result.blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = result.filename;
		a.click();
		URL.revokeObjectURL(url);
	};

	const formatSize = (bytes?: number) => {
		if (bytes === undefined) return '';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
	};

	const handleDragOver = (e: DragEvent) => {
		if (selectedFile) return;
		if (!e.dataTransfer?.types.includes('Files')) return;
		e.preventDefault();
		e.stopPropagation();
		isDragOver = true;
	};

	const handleDragLeave = () => {
		isDragOver = false;
	};

	const handleDrop = async (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		isDragOver = false;
		if (selectedFile) return;
		const droppedFiles = Array.from(e.dataTransfer?.files ?? []);
		if (!droppedFiles.length || !configured) return;

		uploading = true;
		for (const file of droppedFiles) {
			await uploadToTerminal(terminalUrl, terminalKey, currentPath, file);
		}
		uploading = false;
		await loadDir(currentPath);
	};

	const handleUploadFiles = async (files: File[]) => {
		if (!files.length || !configured) return;
		uploading = true;
		for (const file of files) {
			await uploadToTerminal(terminalUrl, terminalKey, currentPath, file);
		}
		uploading = false;
		await loadDir(currentPath);
	};

	const startNewFolder = () => {
		creatingFolder = true;
		newFolderName = '';
		tick().then(() => newFolderInput?.focus());
	};

	const submitNewFolder = async () => {
		const name = newFolderName.trim();
		creatingFolder = false;
		newFolderName = '';
		if (!name) return;
		const result = await createDirectory(terminalUrl, terminalKey, `${currentPath}${name}`);
		if (result) {
			toast.success($i18n.t('Folder created'));
		} else {
			toast.error($i18n.t('Failed to create folder'));
		}
		await loadDir(currentPath);
	};

	const handleDelete = async (path: string, name: string) => {
		const result = await deleteEntry(terminalUrl, terminalKey, path);
		if (result) {
			toast.success($i18n.t('{{name}} deleted', { name }));
		} else {
			toast.error($i18n.t('Failed to delete {{name}}', { name }));
		}
		await loadDir(currentPath);
	};

	const requestDelete = (path: string, name: string) => {
		deleteTarget = { path, name };
		showDeleteConfirm = true;
	};

	onMount(async () => {
		if (!configured) return;
		// On first ever open, resolve the server's CWD instead of defaulting to /
		if (savedPath === '/') {
			const cwd = await getCwd(terminalUrl, terminalKey);
			if (cwd) savedPath = cwd.endsWith('/') ? cwd : cwd + '/';
		}
		loadDir(savedPath);

		const onKeyDown = (e: KeyboardEvent) => {
			if (e.key === 'Shift') shiftKey = true;
		};
		const onKeyUp = (e: KeyboardEvent) => {
			if (e.key === 'Shift') shiftKey = false;
		};
		const onBlur = () => (shiftKey = false);

		// Auto-reload directory when the browser tab regains focus
		const onVisibilityChange = () => {
			if (document.visibilityState === 'visible' && !selectedFile && configured && !loading) {
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

{#if !configured}
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
		on:dragleave={handleDragLeave}
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
			{breadcrumbs}
			{selectedFile}
			{loading}
			onNavigate={loadDir}
			onRefresh={() => loadDir(currentPath)}
			onNewFolder={startNewFolder}
			onUploadFiles={handleUploadFiles}
		/>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto min-h-0">
			{#if selectedFile !== null}
				<FilePreview
					bind:this={filePreviewRef}
					{selectedFile}
					{fileLoading}
					{fileImageUrl}
					{filePdfData}
					{fileContent}
					onDownload={() => downloadFile(selectedFile)}
				/>
			{:else}
				<!-- Directory listing -->
				{#if uploading}
					<div class="flex items-center justify-center gap-2 p-4 text-xs text-gray-500">
						<Spinner className="size-4" />
						{$i18n.t('Uploading...')}
					</div>
				{:else if loading}
					<div class="flex justify-center pt-8"><Spinner className="size-4" /></div>
				{:else if error}
					<div class="p-4 text-xs text-red-500 dark:text-red-400">{error}</div>
				{:else if entries.length === 0 && !creatingFolder}
					<div class="p-4 text-xs text-gray-400 text-center">
						{$i18n.t('Empty — drop files here to upload')}
					</div>
				{/if}

				{#if !loading && !error && !uploading && !selectedFile}
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

					{#if entries.length > 0 || creatingFolder}
						<ul>
							{#each entries as entry}
								<FileEntryRow
									{entry}
									{currentPath}
									{terminalUrl}
									{terminalKey}
									onOpen={openEntry}
									onDownload={downloadFile}
									onDelete={requestDelete}
									{formatSize}
								/>
							{/each}
						</ul>
					{/if}
				{/if}
			{/if}
		</div>
	</div>
{/if}
