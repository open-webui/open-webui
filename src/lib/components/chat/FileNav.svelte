<script context="module">
	// Persists across mount/unmount cycles (module-level, not per-instance)
	let savedPath = '/';
</script>

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy, tick, afterUpdate } from 'svelte';
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
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import Folder from '../icons/Folder.svelte';
	import NewFolderAlt from '../icons/NewFolderAlt.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	export let onAttach: ((blob: Blob, name: string, contentType: string) => void) | null = null;

	let currentPath = savedPath;
	let entries: FileEntry[] = [];
	let loading = false;
	let error: string | null = null;

	let selectedFile: string | null = null;
	let fileContent: string | null = null;
	let fileImageUrl: string | null = null;
	let filePdfUrl: string | null = null;
	let fileLoading = false;

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

	let breadcrumbEl: HTMLDivElement;

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

	// Scroll breadcrumb to the end after every DOM update
	afterUpdate(() => {
		if (breadcrumbEl) breadcrumbEl.scrollLeft = breadcrumbEl.scrollWidth;
	});

	const clearFilePreview = () => {
		fileContent = null;
		if (fileImageUrl) {
			URL.revokeObjectURL(fileImageUrl);
			fileImageUrl = null;
		}
		if (filePdfUrl) {
			URL.revokeObjectURL(filePdfUrl);
			filePdfUrl = null;
		}
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
				if (result)
					filePdfUrl = URL.createObjectURL(
						new Blob([await result.blob.arrayBuffer()], { type: 'application/pdf' })
					);
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

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});

	onDestroy(() => {
		if (fileImageUrl) URL.revokeObjectURL(fileImageUrl);
		if (filePdfUrl) URL.revokeObjectURL(filePdfUrl);
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

		<!-- Breadcrumb + actions — always visible, scrolls to end -->
		<div class="flex items-center px-2 pb-1.5 shrink-0 gap-1">
			<div
				bind:this={breadcrumbEl}
				class="flex items-center flex-1 min-w-0 overflow-x-auto scrollbar-none"
			>
				{#each breadcrumbs as crumb, i}
					{#if i > 1}
						<span class="text-gray-300 dark:text-gray-600 text-xs shrink-0 select-none mx-0.5"
							>/</span
						>
					{/if}
					<button
						class="text-xs shrink-0 px-1 py-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition
							{!selectedFile && i === breadcrumbs.length - 1
							? 'text-gray-700 dark:text-gray-300'
							: 'text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400'}"
						on:click={() => loadDir(crumb.path)}
					>
						{crumb.label}
					</button>
				{/each}
				{#if selectedFile}
					<span class="text-gray-300 dark:text-gray-600 text-xs shrink-0 select-none mx-0.5">/</span
					>
					<span
						class="text-xs shrink-0 px-1.5 py-0.5 text-gray-700 dark:text-gray-300 truncate max-w-[120px]"
					>
						{selectedFile.split('/').pop()}
					</span>
				{/if}
			</div>

			{#if !selectedFile}
				<Tooltip content={$i18n.t('New Folder')}>
					<button
						class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
						on:click={startNewFolder}
						aria-label={$i18n.t('New Folder')}
					>
						<NewFolderAlt className="size-3.5" />
					</button>
				</Tooltip>
			{/if}
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto min-h-0 relative">
			{#if selectedFile !== null}
				<!-- Floating download button -->
				<button
					class="absolute top-2 right-2 z-10 p-1.5 rounded-lg bg-white/80 dark:bg-gray-850/80 backdrop-blur-sm shadow-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
					on:click={() => downloadFile(selectedFile)}
					aria-label={$i18n.t('Download')}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.5"
						class="size-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
						/>
					</svg>
				</button>
				<!-- File preview -->
				{#if fileLoading}
					<div class="flex justify-center pt-8"><Spinner className="size-5" /></div>
				{:else if fileImageUrl !== null}
					<img
						src={fileImageUrl}
						alt={selectedFile?.split('/').pop()}
						class="w-full h-auto object-contain p-3"
					/>
				{:else if filePdfUrl !== null}
					<embed src={filePdfUrl} type="application/pdf" class="w-full h-full min-h-[400px]" />
				{:else if fileContent !== null}
					<pre
						class="text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all leading-relaxed p-3">{fileContent}</pre>
				{:else}
					<div class="text-sm text-gray-400 text-center pt-8">
						{$i18n.t('Could not read file.')}
					</div>
				{/if}
			{:else}
				<!-- Directory listing -->
				{#if uploading}
					<div class="flex items-center justify-center gap-2 p-4 text-xs text-gray-500">
						<Spinner className="size-4" />
						{$i18n.t('Uploading...')}
					</div>
				{:else if loading}
					<div class="flex justify-center pt-8"><Spinner className="size-5" /></div>
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
								<li class="group">
									<div
										class="w-full flex items-center hover:bg-gray-50 dark:hover:bg-gray-800 transition"
									>
										<button
											class="flex-1 flex items-center gap-2 px-3 py-1.5 text-left min-w-0"
											draggable={entry.type === 'file'}
											on:dragstart={(e) => {
												if (entry.type !== 'file') return;
												e.dataTransfer?.setData(
													'application/x-terminal-file',
													JSON.stringify({
														path: `${currentPath}${entry.name}`,
														name: entry.name,
														url: terminalUrl,
														key: terminalKey
													})
												);
											}}
											on:click={() => openEntry(entry)}
										>
											{#if entry.type === 'directory'}
												<Folder className="size-4 shrink-0 text-blue-400 dark:text-blue-300" />
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													stroke-width="1.5"
													class="size-4 shrink-0 text-gray-400"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
													/>
												</svg>
											{/if}
											<span class="flex-1 text-xs text-gray-800 dark:text-gray-200 truncate">
												{entry.name}
											</span>
											{#if entry.type === 'file' && entry.size !== undefined}
												<span class="text-xs text-gray-400 shrink-0">{formatSize(entry.size)}</span>
											{/if}
										</button>

										<DropdownMenu.Root>
											<DropdownMenu.Trigger
												class="shrink-0 p-0.5 mr-1 rounded-lg transition
													text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400
													hover:bg-gray-100 dark:hover:bg-gray-800"
												on:click={(e) => e.stopPropagation()}
												aria-label={$i18n.t('More')}
											>
												<EllipsisHorizontal className="size-3.5" />
											</DropdownMenu.Trigger>

											<DropdownMenu.Content
												strategy="fixed"
												class="w-full max-w-[150px] rounded-2xl p-1 z-[9999999] bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-100 dark:border-gray-800"
												sideOffset={4}
												side="bottom"
												align="end"
												transition={flyAndScale}
											>
												{#if entry.type !== "directory"}
												<DropdownMenu.Item
													type="button"
													class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
													on:click={(e) => {
														e.stopPropagation();
														downloadFile(`${currentPath}${entry.name}`);
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="size-4"
													>
														<path
															d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z"
														/>
														<path
															d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z"
														/>
													</svg>
													<div class="flex items-center">{$i18n.t('Download')}</div>
												</DropdownMenu.Item>
												{/if}

												<DropdownMenu.Item
													type="button"
													class="select-none flex rounded-xl py-1.5 px-3 w-full hover:bg-gray-50 dark:hover:bg-gray-800 transition items-center gap-2 text-sm"
													on:click={(e) => {
														e.stopPropagation();
														deleteTarget = {
															path: `${currentPath}${entry.name}`,
															name: entry.name
														};
														showDeleteConfirm = true;
													}}
												>
													<GarbageBin className="size-4" />
													<div class="flex items-center">{$i18n.t('Delete')}</div>
												</DropdownMenu.Item>
											</DropdownMenu.Content>
										</DropdownMenu.Root>
									</div>
								</li>
							{/each}
						</ul>
					{/if}
				{/if}
			{/if}
		</div>
	</div>
{/if}
