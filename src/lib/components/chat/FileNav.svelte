<script context="module">
	// Persists across mount/unmount cycles (module-level, not per-instance)
	let savedPath = '/';
</script>

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import {
		terminalServers,
		settings,
		showFileNavPath,
		showFileNavDir,
		selectedTerminalId
	} from '$lib/stores';
	import {
		getCwd,
		getTerminalConfig,
		listFiles,
		readFile,
		downloadFileBlob,
		archiveFromTerminal,
		uploadToTerminal,
		createDirectory,
		deleteEntry,
		moveEntry,
		setCwd,
		type FileEntry
	} from '$lib/apis/terminal';
	import { isCodeFile } from '$lib/utils/codeHighlight';
	import Folder from '../icons/Folder.svelte';
	import Document from '../icons/Document.svelte';
	import PenAlt from '../icons/PenAlt.svelte';
	import ZoomReset from '../icons/ZoomReset.svelte';

	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';

	import FileNavToolbar from './FileNav/FileNavToolbar.svelte';
	import FilePreview from './FileNav/FilePreview.svelte';
	import FileEntryRow from './FileNav/FileEntryRow.svelte';
	import BulkActionBar from './FileNav/BulkActionBar.svelte';
	import PortList from './FileNav/PortList.svelte';
	import PortPreview from './FileNav/PortPreview.svelte';
	import XTerminal from './XTerminal.svelte';

	const i18n = getContext('i18n');

	export let onAttach: ((blob: Blob, name: string, contentType: string) => void) | null = null;
	export let overlay = false;

	// ── Terminal panel state ────────────────────────────────────────────
	let terminalExpanded = false;
	let terminalHeight = 200; // px, default when expanded
	let isDraggingHandle = false;
	let containerEl: HTMLElement;
	let terminalConnected = false;
	let terminalConnecting = false;
	let terminalEnabled = true;

	const toggleTerminal = () => {
		terminalExpanded = !terminalExpanded;
	};

	const onHandleMouseDown = (e: MouseEvent) => {
		e.preventDefault();
		isDraggingHandle = true;
		const startY = e.clientY;
		const startHeight = terminalHeight;

		const onMouseMove = (ev: MouseEvent) => {
			const delta = startY - ev.clientY;
			const maxH = containerEl ? containerEl.clientHeight - 100 : 500;
			terminalHeight = Math.max(80, Math.min(maxH, startHeight + delta));
		};

		const onMouseUp = () => {
			isDraggingHandle = false;
			window.removeEventListener('mousemove', onMouseMove);
			window.removeEventListener('mouseup', onMouseUp);
		};

		window.addEventListener('mousemove', onMouseMove);
		window.addEventListener('mouseup', onMouseUp);
	};

	// ── Directory state ──────────────────────────────────────────────────
	let currentPath = savedPath;
	let entries: FileEntry[] = [];
	let loading = false;
	let error: string | null = null;

	// ── Navigation history ──────────────────────────────────────────────
	type NavEntry = { path: string; file: string | null };
	let navHistory: NavEntry[] = [];
	let navIndex = -1;
	let navigatingHistory = false;

	$: canGoBack = navIndex > 0;
	$: canGoForward = navIndex < navHistory.length - 1;

	const pushNavHistory = (path: string, file: string | null = null) => {
		if (navigatingHistory) return;
		// Skip if this is the same as the current entry
		const current = navHistory[navIndex];
		if (current && current.path === path && current.file === file) return;
		// Truncate forward history when navigating to a new location
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

	// ── File preview state ───────────────────────────────────────────────
	let selectedFile: string | null = null;
	let previewPort: number | null = null;
	let fileContent: string | null = null;
	let fileImageUrl: string | null = null;
	let fileVideoUrl: string | null = null;
	let fileAudioUrl: string | null = null;
	let filePdfData: ArrayBuffer | null = null;
	let fileSqliteData: ArrayBuffer | null = null;
	let fileLoading = false;
	let filePreviewRef: FilePreview;

	// ── Office preview state ────────────────────────────────────────────
	let fileOfficeHtml: string | null = null;
	let fileOfficeSlides: string[] | null = null;
	let currentSlide = 0;
	let excelSheetNames: string[] = [];
	let selectedExcelSheet = '';
	let excelWorkbook: import('xlsx').WorkBook | null = null;

	// ── File preview toolbar state (bound from FilePreview) ─────────────
	let editing = false;
	let showRaw = false;
	let saving = false;

	const MD_EXTS = new Set(['md', 'markdown', 'mdx']);
	const CSV_EXTS = new Set(['csv', 'tsv']);
	const HTML_EXTS = new Set(['html', 'htm']);
	const OFFICE_EXTS = new Set(['docx', 'xlsx', 'pptx']);
	const getFileExt = (path: string | null) => path?.split('.').pop()?.toLowerCase() ?? '';

	$: isMarkdown = MD_EXTS.has(getFileExt(selectedFile));
	$: isCsv = CSV_EXTS.has(getFileExt(selectedFile));
	$: isHtml = HTML_EXTS.has(getFileExt(selectedFile));
	$: isJson = ['json', 'jsonc', 'jsonl', 'json5'].includes(getFileExt(selectedFile));
	$: isSvg = getFileExt(selectedFile) === 'svg';
	$: isNotebook = getFileExt(selectedFile) === 'ipynb';
	$: isCode = isCodeFile(selectedFile);
	$: isOfficeFile = OFFICE_EXTS.has(getFileExt(selectedFile));
	$: isTextFile =
		fileContent !== null && fileImageUrl === null && filePdfData === null && !isOfficeFile;

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
		($selectedTerminalId, $terminalServers, $settings);
		const terminal = getTerminal();
		selectedTerminal = terminal;

		if (terminal && terminal.url !== prevTerminalUrl) {
			prevTerminalUrl = terminal.url;
			loading = true;
			error = null;
			entries = [];
			(async () => {
				// Discover server features (terminal enabled/disabled)
				const config = await getTerminalConfig(terminal.url, terminal.key);
				terminalEnabled = config?.features?.terminal !== false;

				const rawCwd = await getCwd(terminal.url, terminal.key);
				const cwd = rawCwd ? normalizePath(rawCwd) : null;
				const dir = cwd ? (cwd.endsWith('/') ? cwd : cwd + '/') : '/';
				savedPath = dir;
				loadDir(dir);
			})();
		}
	}

	// ── Helpers ──────────────────────────────────────────────────────────
	const IMAGE_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico', 'avif']);
	const VIDEO_EXTS = new Set(['mp4', 'webm', 'mov', 'ogv', 'avi', 'mkv']);
	const AUDIO_EXTS = new Set(['mp3', 'wav', 'ogg', 'oga', 'flac', 'm4a', 'aac', 'wma', 'opus']);
	const SQLITE_EXTS = new Set(['db', 'sqlite', 'sqlite3', 'db3']);
	const isImage = (path: string) => IMAGE_EXTS.has(path.split('.').pop()?.toLowerCase() ?? '');
	const isVideo = (path: string) => VIDEO_EXTS.has(path.split('.').pop()?.toLowerCase() ?? '');
	const isAudio = (path: string) => AUDIO_EXTS.has(path.split('.').pop()?.toLowerCase() ?? '');
	const isSqlite = (path: string) => SQLITE_EXTS.has(path.split('.').pop()?.toLowerCase() ?? '');
	const isPdf = (path: string) => path.split('.').pop()?.toLowerCase() === 'pdf';
	const isOffice = (path: string) => OFFICE_EXTS.has(path.split('.').pop()?.toLowerCase() ?? '');

	/** Normalize Windows backslashes to forward slashes. */
	const normalizePath = (p: string) => p.replace(/\\/g, '/');

	const buildBreadcrumbs = (path: string) => {
		const parts = path.split('/').filter(Boolean);
		const isDrive = /^[A-Za-z]:$/.test(parts[0] ?? '');
		const root = isDrive ? { label: parts[0], path: `${parts[0]}/` } : { label: '/', path: '/' };
		return (isDrive ? parts.slice(1) : parts).reduce(
			(acc, part) => {
				const prev = acc[acc.length - 1];
				acc.push({ label: part, path: `${prev.path}${part}/` });
				return acc;
			},
			[root]
		);
	};

	// ── File preview management ──────────────────────────────────────────
	const clearFilePreview = () => {
		fileContent = null;
		filePreviewRef?.disposePanzoom();
		if (fileImageUrl) {
			URL.revokeObjectURL(fileImageUrl);
			fileImageUrl = null;
		}
		if (fileVideoUrl) {
			URL.revokeObjectURL(fileVideoUrl);
			fileVideoUrl = null;
		}
		if (fileAudioUrl) {
			URL.revokeObjectURL(fileAudioUrl);
			fileAudioUrl = null;
		}
		filePdfData = null;
		fileSqliteData = null;
		fileOfficeHtml = null;
		fileOfficeSlides = null;
		currentSlide = 0;
		excelSheetNames = [];
		selectedExcelSheet = '';
		excelWorkbook = null;
	};

	// ── Directory operations ─────────────────────────────────────────────
	const loadDir = async (path: string) => {
		const terminal = selectedTerminal;
		if (!terminal) return;

		loading = true;
		error = null;
		selectedFile = null;
		previewPort = null;
		clearFilePreview();
		clearSelection();
		currentPath = path;
		savedPath = path;
		pushNavHistory(path);

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

		const filePath = `${currentPath}${entry.name}`;
		pushNavHistory(currentPath, filePath);

		const terminal = selectedTerminal;
		if (!terminal) return;

		selectedFile = filePath;
		fileLoading = true;
		clearFilePreview();

		if (isImage(filePath)) {
			const result = await downloadFileBlob(terminal.url, terminal.key, filePath);
			if (result) fileImageUrl = URL.createObjectURL(result.blob);
		} else if (isVideo(filePath)) {
			const result = await downloadFileBlob(terminal.url, terminal.key, filePath);
			if (result) fileVideoUrl = URL.createObjectURL(result.blob);
		} else if (isAudio(filePath)) {
			const result = await downloadFileBlob(terminal.url, terminal.key, filePath);
			if (result) fileAudioUrl = URL.createObjectURL(result.blob);
		} else if (isPdf(filePath)) {
			const result = await downloadFileBlob(terminal.url, terminal.key, filePath);
			if (result) filePdfData = await result.blob.arrayBuffer();
		} else if (isSqlite(filePath)) {
			const result = await downloadFileBlob(terminal.url, terminal.key, filePath);
			if (result) fileSqliteData = await result.blob.arrayBuffer();
		} else if (isOffice(filePath)) {
			const result = await downloadFileBlob(terminal.url, terminal.key, filePath);
			if (result) {
				const ext = getFileExt(filePath);
				const arrayBuffer = await result.blob.arrayBuffer();
				try {
					if (ext === 'docx') {
						const mammoth = await import('mammoth');
						const res = await mammoth.convertToHtml({ arrayBuffer });
						const DOMPurify = (await import('dompurify')).default;
						fileOfficeHtml = DOMPurify.sanitize(res.value);
					} else if (ext === 'xlsx') {
						const XLSX = await import('xlsx');
						const wb = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
						excelWorkbook = wb;
						excelSheetNames = wb.SheetNames;
						if (excelSheetNames.length > 0) {
							selectedExcelSheet = excelSheetNames[0];
							const { excelToTable } = await import('$lib/utils/excelToTable');
							const result = await excelToTable(wb.Sheets[selectedExcelSheet]);
							fileOfficeHtml = result.html;
						}
					} else if (ext === 'pptx') {
						const { pptxToImages } = await import('$lib/utils/pptxToHtml');
						const result = await pptxToImages(arrayBuffer);
						fileOfficeSlides = result.images;
						currentSlide = 0;
					}
				} catch (e) {
					console.error('Failed to render Office file:', e);
					fileContent = `Error previewing file: ${e instanceof Error ? e.message : 'Unknown error'}`;
				}
			}
		} else {
			fileContent = await readFile(terminal.url, terminal.key, filePath);
		}
		fileLoading = false;
	};

	const downloadFile = async (path: string) => {
		const terminal = selectedTerminal;
		if (!terminal) return;

		// Directories end with '/' — download as ZIP archive
		const isDir = path.endsWith('/');
		const result = isDir
			? await archiveFromTerminal(terminal.url, terminal.key, [path.replace(/\/$/, '')])
			: await downloadFileBlob(terminal.url, terminal.key, path);
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
		toast[result ? 'success' : 'error']($i18n.t(result ? 'File created' : 'Failed to create file'));
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

	// ── Move (drag-and-drop) ────────────────────────────────────────────
	const handleMove = async (source: string, destFolder: string) => {
		const terminal = selectedTerminal;
		if (!terminal) return;

		const fileName = source.split('/').pop() ?? '';
		const destination = `${destFolder}${fileName}`;

		if (source === destination) return;

		// Prevent moving a folder into itself or its own subtree
		const sourceDir = source.endsWith('/') ? source : source + '/';
		if (destFolder.startsWith(sourceDir)) return;

		const result = await moveEntry(terminal.url, terminal.key, source, destination);
		if ('error' in result) {
			toast.error(result.error);
		} else {
			toast.success($i18n.t('Moved {{name}}', { name: fileName }));
		}
		await loadDir(currentPath);
	};

	// ── Rename ──────────────────────────────────────────────────────────
	const handleRename = async (oldPath: string, newName: string) => {
		const terminal = selectedTerminal;
		if (!terminal || !newName) return;

		const dir = oldPath.substring(0, oldPath.lastIndexOf('/') + 1) || currentPath;
		const destination = `${dir}${newName}`;

		if (oldPath === destination) return;

		const result = await moveEntry(terminal.url, terminal.key, oldPath, destination);
		if ('error' in result) {
			toast.error(result.error);
		} else {
			toast.success($i18n.t('Renamed to {{name}}', { name: newName }));
		}
		await loadDir(currentPath);
	};

	// ── Multi-select ────────────────────────────────────────────────────
	let selectedEntries: Set<string> = new Set();
	let lastClickedIndex: number | null = null;
	let selectionMode = false;

	$: selectedCount = selectedEntries.size;
	$: hasSelectedFiles = [...selectedEntries].some((p) => !p.endsWith('/'));

	const clearSelection = () => {
		selectedEntries = new Set();
		lastClickedIndex = null;
		selectionMode = false;
	};

	const selectAll = () => {
		selectedEntries = new Set(
			entries.map((e) => {
				const p = `${currentPath}${e.name}`;
				return e.type === 'directory' ? p + '/' : p;
			})
		);
		selectedEntries = selectedEntries; // trigger reactivity
	};

	const handleSelect = (entry: FileEntry, event: MouseEvent) => {
		const path =
			entry.type === 'directory' ? `${currentPath}${entry.name}/` : `${currentPath}${entry.name}`;
		const idx = entries.indexOf(entry);

		if (event.shiftKey && lastClickedIndex !== null) {
			// Range select — replaces current selection with range
			const start = Math.min(lastClickedIndex, idx);
			const end = Math.max(lastClickedIndex, idx);
			const newSet = new Set<string>();
			for (let i = start; i <= end; i++) {
				const e = entries[i];
				const p = e.type === 'directory' ? `${currentPath}${e.name}/` : `${currentPath}${e.name}`;
				newSet.add(p);
			}
			selectedEntries = newSet;
		} else if (event.metaKey || event.ctrlKey) {
			// Toggle one
			if (selectedEntries.has(path)) {
				selectedEntries.delete(path);
			} else {
				selectedEntries.add(path);
			}
			selectedEntries = selectedEntries;
		} else {
			// In selection mode (touch), toggle
			if (selectedEntries.has(path)) {
				selectedEntries.delete(path);
			} else {
				selectedEntries.add(path);
			}
			selectedEntries = selectedEntries;
		}
		lastClickedIndex = idx;
	};

	const enterSelectionMode = () => {
		selectionMode = true;
	};

	const bulkDelete = async () => {
		const terminal = selectedTerminal;
		if (!terminal) return;

		const paths = [...selectedEntries];
		let ok = 0;
		for (const p of paths) {
			const result = await deleteEntry(terminal.url, terminal.key, p.replace(/\/$/, ''));
			if (result) ok++;
		}
		toast[ok > 0 ? 'success' : 'error'](
			$i18n.t('Deleted {{ok}} of {{total}} items', { ok, total: paths.length })
		);
		clearSelection();
		await loadDir(currentPath);
	};

	const bulkDownload = async () => {
		const terminal = selectedTerminal;
		if (!terminal) return;

		const paths = [...selectedEntries].map((p) => p.replace(/\/$/, ''));
		if (paths.length === 0) return;

		// Single file (not dir) — use the regular downloadFile path
		if (paths.length === 1 && ![...selectedEntries][0].endsWith('/')) {
			await downloadFile([...selectedEntries][0]);
			return;
		}

		// Archive everything into a single ZIP
		const result = await archiveFromTerminal(terminal.url, terminal.key, paths);
		if (!result) return;
		const url = URL.createObjectURL(result.blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = result.filename;
		a.click();
		URL.revokeObjectURL(url);
	};

	// Escape to clear selection
	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Escape' && selectedCount > 0) {
			e.preventDefault();
			clearSelection();
		}
	};

	// Click outside panel to clear selection
	const handleWindowClick = (e: MouseEvent) => {
		if (selectedCount > 0 && containerEl && !containerEl.contains(e.target as Node)) {
			clearSelection();
		}
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
			filePath = normalizePath(filePath);

			const lastSlash = filePath.lastIndexOf('/');
			const dir = lastSlash > 0 ? filePath.substring(0, lastSlash + 1) : '/';
			const fileName = filePath.substring(lastSlash + 1);

			// Always reload directory to ensure entries are fresh
			await loadDir(dir);
			await tick();

			const entry = entries.find((e) => e.name === fileName);
			if (entry) {
				await openEntry(entry);
			} else {
				// File may not be in listing; open it directly
				await openEntry({ name: fileName, type: 'file', size: 0 });
			}
		});

		const unsubFileNavDir = showFileNavDir.subscribe(async (filePath) => {
			if (!filePath || !selectedTerminal) return;
			showFileNavDir.set(null);
			filePath = normalizePath(filePath);

			const lastSlash = filePath.lastIndexOf('/');
			const dir = lastSlash > 0 ? filePath.substring(0, lastSlash + 1) : '/';

			if (selectedFile) {
				if (selectedFile === filePath || currentPath.startsWith(dir)) {
					const fileName = selectedFile.split('/').pop() ?? '';
					await openEntry({ name: fileName, type: 'file', size: 0 });
				}
			} else {
				if (currentPath.startsWith(dir) || dir.startsWith(currentPath)) {
					await loadDir(currentPath);
				}
			}
		});

		if (!handledDisplayFile) {
			loading = true;
			if (savedPath === '/') {
				const rawCwd = await getCwd(terminal.url, terminal.key);
				const cwd = rawCwd ? normalizePath(rawCwd) : null;
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
			unsubFileNav();
			unsubFileNavDir();
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
			document.removeEventListener('visibilitychange', onVisibilityChange);
		};
	});

	onDestroy(() => {
		if (fileImageUrl) URL.revokeObjectURL(fileImageUrl);
		if (fileVideoUrl) URL.revokeObjectURL(fileVideoUrl);
		if (fileAudioUrl) URL.revokeObjectURL(fileAudioUrl);
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	on:confirm={() => {
		if (deleteTarget) {
			if (deleteTarget.path === '__bulk__') {
				bulkDelete();
			} else {
				handleDelete(deleteTarget.path, deleteTarget.name);
			}
			deleteTarget = null;
		}
	}}
/>

<svelte:window on:keydown={handleKeydown} on:click={handleWindowClick} />

{#if !selectedTerminal}
	<div class="flex-1 flex flex-col items-center justify-center p-6 text-center">
		<Folder className="size-6 text-gray-300 dark:text-gray-600 mb-2" />
		<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">
			{$i18n.t('No Terminal connection configured.')}
		</div>
		<div class="text-[10px] text-gray-400 dark:text-gray-500">
			{$i18n.t('Add your Open Terminal URL and API key in Settings → Integrations.')}
		</div>
	</div>
{:else}
	<div
		bind:this={containerEl}
		class="flex flex-col h-full min-h-0 min-w-0 relative"
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

		{#if previewPort === null}
			<FileNavToolbar
				breadcrumbs={buildBreadcrumbs(currentPath)}
				{selectedFile}
				{loading}
				{canGoBack}
				{canGoForward}
				onGoBack={goBack}
				onGoForward={goForward}
				onNavigate={loadDir}
				onRefresh={() => {
					if (selectedFile) {
						const fileName = selectedFile.split('/').pop() ?? '';
						openEntry({ name: fileName, type: 'file', size: 0 });
					} else {
						loadDir(currentPath);
					}
				}}
				onNewFolder={startNewFolder}
				onNewFile={startNewFile}
				onUploadFiles={handleUploadFiles}
				onDownloadDir={() => downloadFile(currentPath)}
				onMove={handleMove}
			>
				{#if fileImageUrl !== null || (fileOfficeSlides !== null && fileOfficeSlides.length > 0)}
					<Tooltip content={$i18n.t('Reset view')}>
						<button
							class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
							on:click={() => filePreviewRef?.resetImageView()}
							aria-label={$i18n.t('Reset view')}
						>
							<ZoomReset className="size-3.5" />
						</button>
					</Tooltip>
				{/if}
				{#if filePdfData !== null}
					<Tooltip content={$i18n.t('Reset view')}>
						<button
							class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
							on:click={() => filePreviewRef?.resetPdfView()}
							aria-label={$i18n.t('Reset view')}
						>
							<ZoomReset className="size-3.5" />
						</button>
					</Tooltip>
				{/if}
				{#if (isMarkdown || isCsv || isHtml || isJson || isSvg || isNotebook) && fileContent !== null && !editing}
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
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									class="size-3.5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
									/>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
									/>
								</svg>
							{:else}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.5"
									class="size-3.5"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"
									/>
								</svg>
							{/if}
						</button>
					</Tooltip>
				{/if}
				{#if isTextFile}
					{#if isHtml && showRaw}
						<Tooltip content={$i18n.t('Save')}>
							<button
								class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
								on:click={() => filePreviewRef?.saveCodeFile()}
								disabled={saving}
								aria-label={$i18n.t('Save')}
							>
								{#if saving}
									<Spinner className="size-3.5" />
								{:else}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-3.5"
									>
										<path
											fill-rule="evenodd"
											d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
											clip-rule="evenodd"
										/>
									</svg>
								{/if}
							</button>
						</Tooltip>
					{:else if isHtml}
						<!-- HTML preview mode: no edit/save buttons -->
					{:else if isMarkdown && showRaw}
						<Tooltip content={$i18n.t('Save')}>
							<button
								class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
								on:click={() => filePreviewRef?.saveCodeFile()}
								disabled={saving}
								aria-label={$i18n.t('Save')}
							>
								{#if saving}
									<Spinner className="size-3.5" />
								{:else}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-3.5"
									>
										<path
											fill-rule="evenodd"
											d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
											clip-rule="evenodd"
										/>
									</svg>
								{/if}
							</button>
						</Tooltip>
					{:else if isMarkdown}
						<!-- Markdown preview mode: no edit/save buttons -->
					{:else if isCode}
						<Tooltip content={$i18n.t('Save')}>
							<button
								class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
								on:click={() => filePreviewRef?.saveCodeFile()}
								disabled={saving}
								aria-label={$i18n.t('Save')}
							>
								{#if saving}
									<Spinner className="size-3.5" />
								{:else}
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-3.5"
									>
										<path
											fill-rule="evenodd"
											d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
											clip-rule="evenodd"
										/>
									</svg>
								{/if}
							</button>
						</Tooltip>
					{:else if editing}
						<Tooltip content={$i18n.t('Cancel')}>
							<button
								class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
								on:click={() => filePreviewRef?.cancelEdit()}
								aria-label={$i18n.t('Cancel')}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="size-3.5"
								>
									<path
										d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
									/>
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
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-3.5"
									>
										<path
											fill-rule="evenodd"
											d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
											clip-rule="evenodd"
										/>
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

				{#if fileContent !== null}
					<Tooltip content={$i18n.t('Copy')}>
						<button
							class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
							on:click={async () => {
								await navigator.clipboard.writeText(fileContent ?? '');
								toast.success($i18n.t('Copied to clipboard'));
							}}
							aria-label={$i18n.t('Copy')}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.5"
								class="size-3.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9.75a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184"
								/>
							</svg>
						</button>
					</Tooltip>
				{/if}
				<Tooltip content={$i18n.t('Download')}>
					<button
						class="shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
						on:click={() => downloadFile(selectedFile)}
						aria-label={$i18n.t('Download')}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
							/>
						</svg>
					</button>
				</Tooltip>
			</FileNavToolbar>

			<!-- Bulk action bar -->
			{#if selectedCount > 0}
				<BulkActionBar
					count={selectedCount}
					hasFiles={hasSelectedFiles}
					onDelete={() => {
						deleteTarget = { path: '__bulk__', name: `${selectedCount} items` };
						showDeleteConfirm = true;
					}}
					onDownload={bulkDownload}
					onSelectAll={selectAll}
					onClear={clearSelection}
				/>
			{/if}
		{/if}

		<!-- Content -->
		<div
			class="flex-1 overflow-y-auto min-h-0 min-w-0"
			on:click={(e) => {
				if (e.target === e.currentTarget && selectedCount > 0) clearSelection();
			}}
		>
			{#if previewPort !== null}
				<PortPreview
					baseUrl={selectedTerminal?.url ?? ''}
					port={previewPort}
					overlay={overlay || isDraggingHandle}
					onClose={() => {
						previewPort = null;
					}}
				/>
			{:else if selectedFile !== null}
				<FilePreview
					bind:this={filePreviewRef}
					bind:editing
					bind:showRaw
					bind:saving
					bind:currentSlide
					{selectedFile}
					{fileLoading}
					{fileImageUrl}
					{fileVideoUrl}
					{fileAudioUrl}
					{filePdfData}
					{fileSqliteData}
					{fileContent}
					{fileOfficeHtml}
					{fileOfficeSlides}
					{excelSheetNames}
					{selectedExcelSheet}
					onSheetChange={async (sheet) => {
						if (!excelWorkbook) return;
						selectedExcelSheet = sheet;
						const { excelToTable } = await import('$lib/utils/excelToTable');
						const result = await excelToTable(excelWorkbook.Sheets[sheet]);
						fileOfficeHtml = result.html;
					}}
					baseUrl={selectedTerminal?.url ?? ''}
					apiKey={selectedTerminal?.key ?? ''}
					overlay={overlay || isDraggingHandle}
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
									selected={selectedEntries.has(
										entry.type === 'directory'
											? `${currentPath}${entry.name}/`
											: `${currentPath}${entry.name}`
									)}
									{selectionMode}
									selectedPaths={selectedEntries}
									onOpen={openEntry}
									onDownload={downloadFile}
									onDelete={requestDelete}
									onMove={handleMove}
									onRename={handleRename}
									onSelect={handleSelect}
									onLongPress={enterSelectionMode}
								/>
							{/each}
						</ul>
					{/if}
				{/if}
			{/if}
		</div>

		<!-- Port detection -->
		{#if selectedTerminal && !selectedFile && previewPort === null}
			<div class="shrink-0 border-t border-gray-100 dark:border-gray-800">
				<PortList
					baseUrl={selectedTerminal.url}
					apiKey={selectedTerminal.key}
					on:previewPort={(e) => {
						selectedFile = null;
						clearFilePreview();
						previewPort = e.detail;
					}}
				/>
			</div>
		{/if}

		<!-- Terminal bottom panel -->
		{#if terminalEnabled}
			<div class="shrink-0 border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850">
				{#if terminalExpanded}
					<!-- Drag handle (at top of panel) -->
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div class="relative cursor-row-resize group" on:mousedown={onHandleMouseDown}>
						<div
							class="h-px bg-transparent group-hover:bg-black/10 dark:group-hover:bg-white/10 transition"
						/>
						<div class="absolute inset-x-0 -top-1.5 -bottom-1.5" />
					</div>
				{/if}

				<!-- Toggle header (full-width button) -->
				<button
					class="w-full flex items-center gap-2 px-3 py-1 mb-0.5 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition"
					on:click={toggleTerminal}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3.5"
					>
						<path
							fill-rule="evenodd"
							d="M3.25 3A2.25 2.25 0 0 0 1 5.25v9.5A2.25 2.25 0 0 0 3.25 17h13.5A2.25 2.25 0 0 0 19 14.75v-9.5A2.25 2.25 0 0 0 16.75 3H3.25Zm.943 8.752a.75.75 0 0 1 .055-1.06L6.128 9l-1.88-1.693a.75.75 0 1 1 1.004-1.114l2.5 2.25a.75.75 0 0 1 0 1.114l-2.5 2.25a.75.75 0 0 1-1.06-.055ZM9.75 10.25a.75.75 0 0 0 0 1.5h2.5a.75.75 0 0 0 0-1.5h-2.5Z"
							clip-rule="evenodd"
						/>
					</svg>
					<span class="font-medium">{$i18n.t('Terminal')}</span>

					{#if terminalExpanded}
						<div
							class="w-1.5 h-1.5 rounded-full transition-colors {terminalConnected
								? 'bg-emerald-500'
								: terminalConnecting
									? 'bg-yellow-500 animate-pulse'
									: 'bg-gray-400'}"
						/>
					{/if}

					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3 ml-auto transition-transform {terminalExpanded ? 'rotate-180' : ''}"
					>
						<path
							fill-rule="evenodd"
							d="M9.47 6.47a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 1 1-1.06 1.06L10 8.06l-3.72 3.72a.75.75 0 0 1-1.06-1.06l4.25-4.25Z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>

				{#if terminalExpanded}
					<div style="height: {terminalHeight}px" class="min-h-0">
						<XTerminal
							overlay={overlay || isDraggingHandle}
							bind:connected={terminalConnected}
							bind:connecting={terminalConnecting}
						/>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
