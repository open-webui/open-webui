<script context="module">
	// Persists across mount/unmount cycles (module-level, not per-instance)
	let savedPath = '/';
	let savedFileRoot = null;
	/** @type {Map<string, string[]>} */
	const treeExpandedCache = new Map();
	/** @type {Map<string, [string, any[]][]>} */
	const treeContentsCache = new Map();
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
		getFileMatches,
		listFiles,
		readFile,
		downloadFileBlob,
		downloadFilePreview,
		archiveFromTerminal,
		uploadToTerminal,
		createDirectory,
		deleteEntry,
		moveEntry,
		setCwd,
		type FileEntry,
		type TerminalContentMatch,
		type TerminalFileMatch,
		type TerminalFileRoot,
		type TerminalCwd
	} from '$lib/apis/terminal';
	import { isCodeFile } from '$lib/utils/codeHighlight';
	import { isSavedChatId, isTemporaryChatId } from '$lib/utils/chatId';
	import { copyToClipboard } from '$lib/utils';
	import { normalizeDocumentTargetPage } from '$lib/utils/documentPreview';

	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import DropdownMenu from '../common/DropdownMenu.svelte';

	import FileNavToolbar from './FileNav/FileNavToolbar.svelte';
	import FilePreview from './FileNav/FilePreview.svelte';
	import FileEntryRow from './FileNav/FileEntryRow.svelte';
	import Icon from './FileNav/Icon.svelte';
	import FileTypeIcon from './FileNav/FileTypeIcon.svelte';
	import BulkActionBar from './FileNav/BulkActionBar.svelte';
	import PortList from './FileNav/PortList.svelte';
	import PortPreview from './FileNav/PortPreview.svelte';
	import XTerminal from './XTerminal.svelte';

	const i18n: any = getContext('i18n');

	export let overlay = false;
	export let chatId: string | null = null;

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
	let fileRoot: TerminalFileRoot | null = savedFileRoot;
	let entries: FileEntry[] = [];
	let currentWritable = true;
	let loading = false;
	let error: string | null = null;

	// ── Browser view state ──────────────────────────────────────────────
	type SortMode = 'name' | 'size' | 'date';
	type BrowserRow = FileEntry & {
		fullPath: string;
		parentPath: string;
		depth: number;
		rowIndex: number;
	};
	type FileSearchTarget = {
		line: number;
		column: number;
		length: number;
		requestId: number;
	};

	let sortBy: SortMode = 'name';
	let sortAsc = true;
	let showHidden = false;
	let visibleEntries: BrowserRow[] = [];
	let expandedDirs: Set<string> = new Set();
	let treeCache: Map<string, FileEntry[]> = new Map();
	let loadingDirs: Set<string> = new Set();
	let directoryMenu: { x: number; y: number } | null = null;
	let searchQuery = '';
	let matchResults: TerminalFileMatch[] | null = null;
	let matchLoading = false;
	let matchLoadingMore = false;
	let matchError: string | null = null;
	let matchLoadMoreError = false;
	let nextMatchOffset: number | null = null;
	let matchTimer: ReturnType<typeof setTimeout> | null = null;
	let matchController: AbortController | null = null;
	let matchRequestId = 0;
	let searchTargetRequestId = 0;

	$: searchText = searchQuery.trim();
	$: isSearching = Boolean(searchText);
	$: filenameMatches = matchResults?.filter((match) => match.name_match) ?? [];
	$: contentOnlyMatches = matchResults?.filter((match) => !match.name_match) ?? [];

	/** Normalize Windows backslashes and collapse duplicate separators. */
	const normalizePath = (path: string) => path.replace(/\\/g, '/').replace(/\/{2,}/g, '/');

	const cleanEntryName = (name: string) =>
		normalizePath(name).split('/').filter(Boolean).at(-1) ?? name.replace(/\/+$/, '');

	const normalizeEntries = (items: FileEntry[]) =>
		items.map((entry) => ({ ...entry, name: cleanEntryName(entry.name) }));

	const asDirectoryPath = (path: string) => {
		const normalized = normalizePath(path || '/');
		if (normalized === '/') return '/';
		return normalized.endsWith('/') ? normalized : `${normalized}/`;
	};

	const joinPath = (parentPath: string, name: string) => {
		const parent = asDirectoryPath(parentPath);
		const child = cleanEntryName(name);
		if (!child) return parent;
		return normalizePath(`${parent}${child}`);
	};

	const sortEntries = (items: FileEntry[], mode: SortMode, asc: boolean): FileEntry[] => {
		return [...items].sort((a, b) => {
			// Directories always first
			if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
			if (mode === 'date') {
				if (a.modified !== undefined && b.modified !== undefined) {
					return asc ? a.modified - b.modified : b.modified - a.modified;
				}
				const cmp = a.name.localeCompare(b.name);
				return asc ? cmp : -cmp;
			}
			if (mode === 'size') {
				if (a.size !== undefined && b.size !== undefined) {
					return asc ? a.size - b.size : b.size - a.size;
				}
				const cmp = a.name.localeCompare(b.name);
				return asc ? cmp : -cmp;
			}
			const cmp = a.name.localeCompare(b.name);
			return asc ? cmp : -cmp;
		});
	};

	const toggleSort = (mode: SortMode) => {
		if (sortBy === mode) {
			sortAsc = !sortAsc;
		} else {
			sortBy = mode;
			sortAsc = true;
		}
		void refreshBrowser();
	};

	const filterEntries = (items: FileEntry[], hiddenVisible: boolean) =>
		hiddenVisible ? items : items.filter((entry) => !entry.name.startsWith('.'));

	const entryPath = (parentPath: string, entry: FileEntry) =>
		entry.type === 'directory'
			? asDirectoryPath(joinPath(parentPath, entry.name))
			: joinPath(parentPath, entry.name);

	const withRowIndexes = (rows: Omit<BrowserRow, 'rowIndex'>[]): BrowserRow[] =>
		rows.map((row, rowIndex) => ({ ...row, rowIndex }));

	const buildVisibleRows = (
		items: FileEntry[],
		parentPath: string,
		expanded: Set<string>,
		cache: Map<string, FileEntry[]>,
		hiddenVisible: boolean,
		mode: SortMode,
		asc: boolean,
		depth = 0
	): Omit<BrowserRow, 'rowIndex'>[] =>
		sortEntries(filterEntries(items, hiddenVisible), mode, asc).flatMap((entry) => {
			const fullPath = entryPath(parentPath, entry);
			const row = { ...entry, fullPath, parentPath, depth };
			const children =
				entry.type === 'directory' && expanded.has(fullPath)
					? buildVisibleRows(
							cache.get(fullPath) ?? [],
							fullPath,
							expanded,
							cache,
							hiddenVisible,
							mode,
							asc,
							depth + 1
						)
					: [];
			return [row, ...children];
		});

	$: visibleEntries = withRowIndexes(
		buildVisibleRows(entries, currentPath, expandedDirs, treeCache, showHidden, sortBy, sortAsc)
	);

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
	let selectedFileWritable = true;
	let previewPort: number | null = null;
	let fileContent: string | null = null;
	let fileImageUrl: string | null = null;
	let fileVideoUrl: string | null = null;
	let fileAudioUrl: string | null = null;
	let filePdfData: ArrayBuffer | null = null;
	let fileSqliteData: ArrayBuffer | null = null;
	let fileDocxData: ArrayBuffer | null = null;
	let fileLoading = false;
	let filePreviewRef: FilePreview;
	let fileSearchTarget: FileSearchTarget | null = null;
	let documentTargetPage: number | null = null;

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
	let directoryUploadInput: HTMLInputElement;

	// ── Delete confirmation ──────────────────────────────────────────────
	let deleteTarget: { path: string; name: string } | null = null;
	let showDeleteConfirm = false;
	let shiftKey = false;

	// ── Terminal resolution ──────────────────────────────────────────────
	let selectedTerminal: { url: string; key: string } | null = null;
	let terminalChatContextPending = false;
	let terminalChatContextHidden = false;

	const chatContext = (terminal: any) => terminal?.contexts?.chat ?? {};

	const getTerminal = (): { url: string; key: string } | null => {
		const systemTerminal = $selectedTerminalId
			? (($terminalServers ?? []).find((t) => t.id === $selectedTerminalId) ?? null)
			: ($terminalServers?.[0] ?? null);
		const chatConfig = chatContext(systemTerminal);
		const chatScoped = !!systemTerminal && chatConfig?.context_id === 'chat_id';
		terminalChatContextHidden =
			!!systemTerminal && (chatConfig === false || (chatScoped && isTemporaryChatId(chatId)));
		terminalChatContextPending = chatScoped && !terminalChatContextHidden && !isSavedChatId(chatId);
		if (terminalChatContextHidden || terminalChatContextPending) return null;

		const settingsValue: any = $settings;
		const userTerminal = (settingsValue?.terminalServers ?? []).find(
			(s: any) => s.url === $selectedTerminalId
		);

		const isSystem = !!systemTerminal;
		const url = systemTerminal?.url ?? userTerminal?.url ?? '';
		const key = isSystem ? localStorage.token : (userTerminal?.key ?? '');

		return url ? { url, key } : null;
	};

	// Detect terminal or chat changes — the explicit store references ensure
	// Svelte re-runs this block when any of them update.
	// The `mounted` flag prevents the initial run from racing with onMount.
	let prevTerminalUrl = '';
	let prevChatId = chatId;
	let mounted = false;
	$: {
		($selectedTerminalId, $terminalServers, $settings);
		const terminal = getTerminal();
		selectedTerminal = terminal;

		const chatChanged = chatId !== prevChatId;
		const oldChatId = prevChatId;
		if (chatChanged) prevChatId = chatId;

		const terminalChanged = terminal && terminal.url !== prevTerminalUrl;
		if (terminalChanged) prevTerminalUrl = terminal.url;

		if (mounted && terminal) {
			if (chatChanged && chatId && !oldChatId) {
				// Chat just got created (null → real ID): persist the current
				// browsed path as the new session's cwd — don't re-fetch.
				setCwd(terminal.url, terminal.key, savedPath, chatId);
			} else if (terminalChanged || chatChanged) {
				// Terminal switched, new chat started, or switched between
				// existing chats — re-fetch the session cwd.
				loading = true;
				error = null;
				entries = [];
				resetTreeState();
				(async () => {
					if (terminalChanged) {
						const config = await getTerminalConfig(terminal.url, terminal.key);
						terminalEnabled = config?.features?.terminal !== false;
					}

					savedPath = applyCwd(await getCwd(terminal.url, terminal.key, chatId ?? undefined));
					loadDir(savedPath);
				})();
			}
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

	const resetTreeState = () => {
		expandedDirs = new Set();
		treeCache = new Map();
		loadingDirs = new Set();
	};

	const saveTreeState = () => {
		treeExpandedCache.set(currentPath, [...expandedDirs]);
		treeContentsCache.set(currentPath, [...treeCache.entries()]);
	};

	const restoreTreeState = (path: string) => {
		expandedDirs = new Set(treeExpandedCache.get(path) ?? []);
		treeCache = new Map(treeContentsCache.get(path) ?? []);
		loadingDirs = new Set();
	};

	const invalidateTreeCache = (...paths: string[]) => {
		const directories = paths.map(asDirectoryPath);
		const next = new Map(treeCache);
		for (const key of next.keys()) {
			if (directories.some((directory) => key === directory || key.startsWith(directory))) {
				next.delete(key);
			}
		}
		treeCache = next;
	};

	const toggleHidden = () => {
		showHidden = !showHidden;
		localStorage.setItem('fileNav:showHidden', String(showHidden));
		clearSelection();
		void refreshBrowser();
	};

	const closeDirectoryMenu = () => {
		directoryMenu = null;
	};

	const parentDirectoryPath = (path: string) => {
		const normalized = normalizePath(path);
		const slash = normalized.lastIndexOf('/');
		return slash > 0 ? asDirectoryPath(normalized.slice(0, slash)) : '/';
	};

	const relativeParentPath = (path: string) => {
		const slash = path.lastIndexOf('/');
		return slash === -1 ? '' : path.slice(0, slash);
	};

	const clearMatchRequest = () => {
		if (matchTimer) {
			clearTimeout(matchTimer);
			matchTimer = null;
		}
		matchController?.abort();
		matchController = null;
	};

	const resetMatches = () => {
		matchResults = null;
		matchLoading = false;
		matchLoadingMore = false;
		matchError = null;
		matchLoadMoreError = false;
		nextMatchOffset = null;
	};

	const queueFileSearch = (
		query: string,
		terminal: { url: string; key: string } | null,
		path: string,
		hiddenVisible: boolean,
		activeFile: string | null,
		activePort: number | null
	) => {
		clearMatchRequest();
		matchRequestId += 1;
		const requestId = matchRequestId;
		if (!query || !terminal || activeFile || activePort !== null) {
			resetMatches();
			return;
		}

		clearSelection();
		closeDirectoryMenu();
		creatingFolder = false;
		creatingFile = false;
		matchLoading = true;
		matchLoadingMore = false;
		matchError = null;
		matchLoadMoreError = false;
		nextMatchOffset = null;
		matchResults = null;
		const controller = new AbortController();
		matchController = controller;
		matchTimer = setTimeout(async () => {
			const data = await getFileMatches(
				terminal.url,
				terminal.key,
				query,
				path,
				hiddenVisible,
				0,
				chatId ?? undefined,
				controller.signal
			);
			if (requestId !== matchRequestId) return;
			if (data) {
				matchResults = data.results;
				nextMatchOffset = data.next_offset;
			} else if (!controller.signal.aborted) {
				matchError = $i18n.t('Failed to search files');
				matchResults = [];
			}
			matchLoading = false;
		}, 200);
	};

	$: queueFileSearch(
		searchText,
		selectedTerminal,
		currentPath,
		showHidden,
		selectedFile,
		previewPort
	);

	const loadMoreMatches = async () => {
		const offset = nextMatchOffset;
		if (offset === null || !isSearching || matchLoading || matchLoadingMore || matchLoadMoreError) {
			return;
		}
		const terminal = selectedTerminal;
		if (!terminal) return;

		const requestId = matchRequestId;
		matchLoadingMore = true;
		const controller = new AbortController();
		matchController = controller;
		const data = await getFileMatches(
			terminal.url,
			terminal.key,
			searchText,
			currentPath,
			showHidden,
			offset,
			chatId ?? undefined,
			controller.signal
		);
		if (requestId === matchRequestId) {
			if (data) {
				matchResults = [...(matchResults ?? []), ...data.results];
				nextMatchOffset = data.next_offset;
			} else if (!controller.signal.aborted) {
				matchLoadMoreError = true;
			}
			matchLoadingMore = false;
		}
	};

	const loadMoreOnVisible = (node: HTMLElement) => {
		const observer = new IntersectionObserver(
			([entry]) => {
				if (entry.isIntersecting) void loadMoreMatches();
			},
			{ rootMargin: '160px' }
		);
		observer.observe(node);
		return { destroy: () => observer.disconnect() };
	};

	const labelFromPath = (path: string) => {
		const parts = normalizePath(path).split('/').filter(Boolean);
		return parts.at(-1) ?? '/';
	};

	const setFileRoot = (root?: TerminalFileRoot) => {
		const previousRoot = fileRoot?.path ?? null;
		fileRoot = root?.path
			? {
					path: asDirectoryPath(root.path),
					label: root.label || labelFromPath(root.path)
				}
			: null;
		savedFileRoot = fileRoot;
		if ((fileRoot?.path ?? null) !== previousRoot) resetTreeState();
	};

	const isInsideFileRoot = (path: string) => {
		if (!fileRoot) return true;
		const directory = asDirectoryPath(path);
		return directory === fileRoot.path || directory.startsWith(fileRoot.path);
	};

	const clampToFileRoot = (path: string) => {
		if (!fileRoot) return asDirectoryPath(path);
		return isInsideFileRoot(path) ? asDirectoryPath(path) : fileRoot.path;
	};

	const rootFromCwd = (cwd: TerminalCwd | null) => {
		const rootPath = cwd?.root?.path ? asDirectoryPath(cwd.root.path) : null;
		return rootPath && rootPath !== '/' ? cwd?.root : undefined;
	};

	const applyCwd = (cwd: TerminalCwd | null) => {
		const cwdPath = cwd?.cwd ? asDirectoryPath(cwd.cwd) : null;
		setFileRoot(rootFromCwd(cwd));
		const path = cwdPath ?? fileRoot?.path ?? '/';
		return clampToFileRoot(path);
	};

	const buildBreadcrumbs = (path: string) => {
		if (fileRoot) {
			const directory = clampToFileRoot(path);
			const relative = directory === fileRoot.path ? '' : directory.slice(fileRoot.path.length);
			const parts = relative.split('/').filter(Boolean);
			return parts.reduce(
				(acc, part) => {
					const prev = acc[acc.length - 1];
					acc.push({ label: part, path: asDirectoryPath(joinPath(prev.path, part)) });
					return acc;
				},
				[{ label: fileRoot.label, path: fileRoot.path }]
			);
		}

		const parts = path.split('/').filter(Boolean);
		const isDrive = /^[A-Za-z]:$/.test(parts[0] ?? '');
		const root = isDrive ? { label: parts[0], path: `${parts[0]}/` } : { label: '/', path: '/' };
		return (isDrive ? parts.slice(1) : parts).reduce(
			(acc, part) => {
				const prev = acc[acc.length - 1];
				acc.push({ label: part, path: asDirectoryPath(joinPath(prev.path, part)) });
				return acc;
			},
			[root]
		);
	};

	// ── File preview management ──────────────────────────────────────────
	const clearFilePreview = () => {
		fileSearchTarget = null;
		documentTargetPage = null;
		fileContent = null;
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
		fileDocxData = null;
		fileOfficeHtml = null;
		fileOfficeSlides = null;
		currentSlide = 0;
		excelSheetNames = [];
		selectedExcelSheet = '';
		excelWorkbook = null;
	};

	// ── Directory operations ─────────────────────────────────────────────
	const loadDir = async (
		path: string,
		options: { preserveTree?: boolean; restoreTree?: boolean } = {}
	) => {
		const terminal = selectedTerminal;
		if (!terminal) return;
		const directory = clampToFileRoot(path);
		if (options.restoreTree) {
			restoreTreeState(directory);
		} else if (!options.preserveTree && directory !== currentPath) {
			resetTreeState();
		}

		loading = true;
		error = null;
		selectedFile = null;
		selectedFileWritable = true;
		previewPort = null;
		clearFilePreview();
		clearSelection();
		currentPath = directory;
		savedPath = directory;
		pushNavHistory(directory);

		const result = await listFiles(terminal.url, terminal.key, directory, chatId ?? undefined);
		loading = false;

		// Set working directory on the terminal server (fire-and-forget)
		setCwd(terminal.url, terminal.key, directory, chatId ?? undefined);

		if (result === null) {
			error =
				'Failed to load directory. Check your Terminal connection in Settings → Integrations.';
			entries = [];
		} else {
			currentWritable = result.writable !== false;
			entries = normalizeEntries(result.entries);
			treeCache = new Map(treeCache).set(directory, entries);
			saveTreeState();
		}
	};

	const fetchExpandedDir = async (path: string) => {
		const terminal = selectedTerminal;
		if (!terminal) return null;
		const directory = asDirectoryPath(path);
		loadingDirs = new Set(loadingDirs).add(directory);
		const result = await listFiles(terminal.url, terminal.key, directory, chatId ?? undefined);
		const nextLoading = new Set(loadingDirs);
		nextLoading.delete(directory);
		loadingDirs = nextLoading;
		if (result === null) return null;
		const normalizedEntries = normalizeEntries(result.entries);
		treeCache = new Map(treeCache).set(directory, normalizedEntries);
		saveTreeState();
		return normalizedEntries;
	};

	const refreshExpandedDirs = async () => {
		for (const directory of [...expandedDirs]) {
			await fetchExpandedDir(directory);
		}
	};

	const refreshBrowser = async () => {
		await loadDir(currentPath, { preserveTree: true });
		await refreshExpandedDirs();
	};

	const toggleExpand = async (path: string) => {
		const directory = asDirectoryPath(path);
		if (expandedDirs.has(directory)) {
			const next = new Set(expandedDirs);
			next.delete(directory);
			expandedDirs = next;
			saveTreeState();
			return;
		}

		expandedDirs = new Set(expandedDirs).add(directory);
		saveTreeState();

		const result = await fetchExpandedDir(directory);
		if (result === null) {
			const next = new Set(expandedDirs);
			next.delete(directory);
			expandedDirs = next;
			saveTreeState();
			toast.error($i18n.t('Failed to load folder'));
		} else {
			treeCache = new Map(treeCache);
		}
	};

	const openEntry = async (entry: FileEntry, options: { page?: unknown } = {}) => {
		const fullPath =
			'fullPath' in entry ? (entry as BrowserRow).fullPath : entryPath(currentPath, entry);
		const parentPath = 'parentPath' in entry ? (entry as BrowserRow).parentPath : currentPath;
		if (entry.type === 'directory') {
			await loadDir(fullPath);
			return;
		}

		const filePath = fullPath;
		if (parentPath !== currentPath) {
			await loadDir(parentPath);
		}
		selectedFileWritable = entry.writable !== false;
		pushNavHistory(parentPath, filePath);

		const terminal = selectedTerminal;
		if (!terminal) return;

		selectedFile = filePath;
		fileLoading = true;
		clearFilePreview();
		documentTargetPage = normalizeDocumentTargetPage(options.page);

		if (isImage(filePath)) {
			const result = await downloadFileBlob(
				terminal.url,
				terminal.key,
				filePath,
				chatId ?? undefined
			);
			if (result) fileImageUrl = URL.createObjectURL(result.blob);
		} else if (isVideo(filePath)) {
			const result = await downloadFileBlob(
				terminal.url,
				terminal.key,
				filePath,
				chatId ?? undefined
			);
			if (result) fileVideoUrl = URL.createObjectURL(result.blob);
		} else if (isAudio(filePath)) {
			const result = await downloadFileBlob(
				terminal.url,
				terminal.key,
				filePath,
				chatId ?? undefined
			);
			if (result) fileAudioUrl = URL.createObjectURL(result.blob);
		} else if (isPdf(filePath)) {
			const result = await downloadFileBlob(
				terminal.url,
				terminal.key,
				filePath,
				chatId ?? undefined
			);
			if (result) filePdfData = await result.blob.arrayBuffer();
		} else if (isSqlite(filePath)) {
			const result = await downloadFileBlob(
				terminal.url,
				terminal.key,
				filePath,
				chatId ?? undefined
			);
			if (result) fileSqliteData = await result.blob.arrayBuffer();
		} else if (isOffice(filePath)) {
			const ext = getFileExt(filePath);
			try {
				if (ext === 'docx') {
					const preview = await downloadFilePreview(
						terminal.url,
						terminal.key,
						filePath,
						chatId ?? undefined
					);
					if (preview) {
						filePdfData = await preview.blob.arrayBuffer();
					} else {
						const result = await downloadFileBlob(
							terminal.url,
							terminal.key,
							filePath,
							chatId ?? undefined
						);
						if (!result) throw new Error('Preview failed');
						const arrayBuffer = await result.blob.arrayBuffer();
						fileDocxData = arrayBuffer;
					}
				} else if (ext === 'xlsx') {
					const result = await downloadFileBlob(
						terminal.url,
						terminal.key,
						filePath,
						chatId ?? undefined
					);
					if (result) {
						const arrayBuffer = await result.blob.arrayBuffer();
						const XLSX = await import('xlsx');
						const wb = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
						excelWorkbook = wb;
						excelSheetNames = wb.SheetNames;
						if (excelSheetNames.length > 0) {
							selectedExcelSheet = excelSheetNames[0];
							const { excelToTable } = await import('$lib/utils/excelToTable');
							const result = await excelToTable(wb.Sheets[selectedExcelSheet]);
							const DOMPurify = (await import('dompurify')).default;
							fileOfficeHtml = DOMPurify.sanitize(result.html);
						}
					}
				} else if (ext === 'pptx') {
					const preview = await downloadFilePreview(
						terminal.url,
						terminal.key,
						filePath,
						chatId ?? undefined
					);
					if (preview) {
						filePdfData = await preview.blob.arrayBuffer();
					} else {
						const result = await downloadFileBlob(
							terminal.url,
							terminal.key,
							filePath,
							chatId ?? undefined
						);
						if (!result) throw new Error('Preview failed');
						const arrayBuffer = await result.blob.arrayBuffer();
						const { pptxToImages } = await import('$lib/utils/pptxToHtml');
						const fallback = await pptxToImages(arrayBuffer);
						fileOfficeSlides = fallback.images;
						currentSlide = 0;
					}
				}
			} catch (e) {
				console.error('Failed to render Office file:', e);
				fileContent = `Error previewing file: ${e instanceof Error ? e.message : 'Unknown error'}`;
			}
		} else {
			fileContent = await readFile(terminal.url, terminal.key, filePath, chatId ?? undefined);
		}
		fileLoading = false;
	};

	const openFileMatch = async (match: TerminalFileMatch) => {
		if (match.type === 'directory') {
			searchQuery = '';
			await loadDir(match.path);
			return;
		}
		await openEntry({
			name: match.name,
			type: 'file',
			size: 0,
			fullPath: match.path,
			parentPath: parentDirectoryPath(match.path),
			depth: 0,
			rowIndex: -1
		} as BrowserRow);
	};

	const openContentMatch = async (match: TerminalFileMatch, contentMatch: TerminalContentMatch) => {
		await openFileMatch(match);
		fileSearchTarget = {
			line: contentMatch.line,
			column: contentMatch.column,
			length: searchText.length,
			requestId: ++searchTargetRequestId
		};
	};

	let downloading = false;

	const downloadFile = async (path: string) => {
		const terminal = selectedTerminal;
		if (!terminal || downloading) return;

		downloading = true;
		const toastId = toast.loading($i18n.t('Preparing download...'));
		try {
			// Directories end with '/', downloaded as a ZIP archive
			const isDir = path.endsWith('/');
			const result = isDir
				? await archiveFromTerminal(terminal.url, terminal.key, [path.replace(/\/$/, '')])
				: await downloadFileBlob(terminal.url, terminal.key, path, chatId ?? undefined);
			if (!result) {
				toast.error($i18n.t('Download failed'));
				return;
			}
			const url = URL.createObjectURL(result.blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = result.filename;
			a.click();
			URL.revokeObjectURL(url);
		} finally {
			toast.dismiss(toastId);
			downloading = false;
		}
	};

	// ── Drag-and-drop upload ─────────────────────────────────────────────
	const handleDragOver = (e: DragEvent) => {
		if (selectedFile) return;
		if (!currentWritable) return;
		const types = e.dataTransfer?.types;
		if (!types?.includes('Files') && !types?.includes('application/x-terminal-file-move')) return;
		e.preventDefault();
		e.stopPropagation();
		isDragOver = types.includes('Files');
	};

	const handleDrop = async (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
		isDragOver = false;

		const terminal = selectedTerminal;
		if (selectedFile || !terminal || !currentWritable) return;

		const rawMove = e.dataTransfer?.getData('application/x-terminal-file-move');
		if (rawMove) {
			try {
				const data = JSON.parse(rawMove);
				const paths = (data.paths || (data.path ? [data.path] : [])) as string[];
				await handleMovePaths(paths, currentPath);
			} catch {}
			return;
		}

		const droppedFiles = Array.from(e.dataTransfer?.files ?? []);
		if (!droppedFiles.length) return;

		uploading = true;
		for (const file of droppedFiles) {
			await uploadToTerminal(terminal.url, terminal.key, currentPath, file, chatId ?? undefined);
		}
		uploading = false;
		invalidateTreeCache(currentPath);
		await loadDir(currentPath, { preserveTree: true });
	};

	const handleUploadFiles = async (files: File[]) => {
		const terminal = selectedTerminal;
		if (!files.length || !terminal || !currentWritable) return;

		uploading = true;
		for (const file of files) {
			await uploadToTerminal(terminal.url, terminal.key, currentPath, file, chatId ?? undefined);
		}
		uploading = false;
		invalidateTreeCache(currentPath);
		await loadDir(currentPath, { preserveTree: true });
	};

	// ── Folder creation ──────────────────────────────────────────────────
	const startNewFolder = async () => {
		if (!currentWritable) return;
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

		const result = await createDirectory(
			terminal.url,
			terminal.key,
			`${currentPath}${name}`,
			chatId ?? undefined
		);
		toast[result ? 'success' : 'error'](
			$i18n.t(result ? 'Folder created' : 'Failed to create folder')
		);
		invalidateTreeCache(currentPath);
		await loadDir(currentPath, { preserveTree: true });
	};

	// ── File creation ────────────────────────────────────────────────────
	const startNewFile = async () => {
		if (!currentWritable) return;
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
		invalidateTreeCache(currentPath);
		await loadDir(currentPath, { preserveTree: true });
	};

	// ── Delete ───────────────────────────────────────────────────────────
	const handleDelete = async (path: string, name: string) => {
		const terminal = selectedTerminal;
		if (!terminal || !currentWritable) return;

		const result = await deleteEntry(terminal.url, terminal.key, path, chatId ?? undefined);
		toast[result ? 'success' : 'error'](
			$i18n.t(result ? '{{name}} deleted' : 'Failed to delete {{name}}', { name })
		);
		invalidateTreeCache(currentPath, path);
		await loadDir(currentPath, { preserveTree: true });
	};

	const requestDelete = (path: string, name: string) => {
		if (!currentWritable) return;
		deleteTarget = { path, name };
		showDeleteConfirm = true;
	};

	// ── Move (drag-and-drop) ────────────────────────────────────────────
	const sourceParentPath = (source: string) => {
		const cleanSource = normalizePath(source).replace(/\/$/, '');
		const index = cleanSource.lastIndexOf('/');
		return asDirectoryPath(index >= 0 ? cleanSource.slice(0, index + 1) : currentPath);
	};

	const moveOne = async (source: string, destFolder: string) => {
		const terminal = selectedTerminal;
		if (!terminal || !currentWritable) return false;

		const cleanSource = normalizePath(source).replace(/\/$/, '');
		const fileName = cleanSource.split('/').pop() ?? '';
		const destination = joinPath(destFolder, fileName);

		if (!fileName || cleanSource === destination) return false;

		// Prevent moving a folder into itself or its own subtree
		const sourceDir = asDirectoryPath(cleanSource);
		if (asDirectoryPath(destFolder).startsWith(sourceDir)) return false;

		const result = await moveEntry(
			terminal.url,
			terminal.key,
			cleanSource,
			destination,
			chatId ?? undefined
		);
		if ('error' in result) {
			toast.error(result.error);
			return false;
		} else {
			toast.success($i18n.t('Moved {{name}}', { name: fileName }));
			return true;
		}
	};

	const refreshAfterMove = async (sources: string[], destFolder: string) => {
		invalidateTreeCache(currentPath, destFolder, ...sources, ...sources.map(sourceParentPath));
		clearSelection();
		await refreshBrowser();
	};

	const handleMovePaths = async (sources: string[], destFolder: string) => {
		const movedSources: string[] = [];
		for (const source of sources) {
			if (await moveOne(source, destFolder)) movedSources.push(source);
		}
		if (movedSources.length > 0) {
			await refreshAfterMove(movedSources, destFolder);
		}
	};

	// ── Rename ──────────────────────────────────────────────────────────
	const handleRename = async (oldPath: string, newName: string) => {
		const terminal = selectedTerminal;
		if (!terminal || !newName || !currentWritable) return;

		const dir = oldPath.substring(0, oldPath.lastIndexOf('/') + 1) || currentPath;
		const destination = `${dir}${newName}`;

		if (oldPath === destination) return;

		const result = await moveEntry(
			terminal.url,
			terminal.key,
			oldPath,
			destination,
			chatId ?? undefined
		);
		if ('error' in result) {
			toast.error(result.error);
		} else {
			toast.success($i18n.t('Renamed to {{name}}', { name: newName }));
		}
		invalidateTreeCache(currentPath, oldPath);
		await loadDir(currentPath, { preserveTree: true });
	};

	// ── Multi-select ────────────────────────────────────────────────────
	let selectedEntries: Set<string> = new Set();
	let lastClickedIndex: number | null = null;
	let selectionMode = false;

	$: selectedCount = selectedEntries.size;
	$: selectedEntriesWritable =
		currentWritable &&
		[...selectedEntries].every((path) => {
			const entry = visibleEntries.find((item) => item.fullPath === path);
			return entry?.writable !== false;
		});

	const clearSelection = () => {
		selectedEntries = new Set();
		lastClickedIndex = null;
		selectionMode = false;
	};

	const selectAll = () => {
		selectedEntries = new Set(visibleEntries.map((entry) => entry.fullPath));
		selectedEntries = selectedEntries; // trigger reactivity
	};

	const handleSelect = (entry: FileEntry, event: MouseEvent, path?: string, index?: number) => {
		const selectedPath = path ?? entryPath(currentPath, entry);
		const idx = index ?? visibleEntries.findIndex((row) => row.fullPath === selectedPath);
		if (idx < 0) return;
		if (event.shiftKey && lastClickedIndex !== null) {
			// Range select — replaces current selection with range
			const start = Math.min(lastClickedIndex, idx);
			const end = Math.max(lastClickedIndex, idx);
			const newSet = new Set<string>();
			for (let i = start; i <= end; i++) {
				const row = visibleEntries[i];
				if (row) newSet.add(row.fullPath);
			}
			selectedEntries = newSet;
		} else if (event.metaKey || event.ctrlKey) {
			// Toggle one
			if (selectedEntries.has(selectedPath)) {
				selectedEntries.delete(selectedPath);
			} else {
				selectedEntries.add(selectedPath);
			}
			selectedEntries = selectedEntries;
		} else {
			// In selection mode (touch), toggle
			if (selectedEntries.has(selectedPath)) {
				selectedEntries.delete(selectedPath);
			} else {
				selectedEntries.add(selectedPath);
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
		if (!terminal || !selectedEntriesWritable) return;

		const paths = [...selectedEntries];
		let ok = 0;
		for (const p of paths) {
			const result = await deleteEntry(terminal.url, terminal.key, p.replace(/\/$/, ''));
			if (result) ok++;
		}
		toast[ok > 0 ? 'success' : 'error'](
			$i18n.t('Deleted {{ok}} of {{total}} items', { ok, total: paths.length })
		);
		invalidateTreeCache(currentPath, ...paths);
		clearSelection();
		await loadDir(currentPath, { preserveTree: true });
	};

	const bulkDownload = async () => {
		const terminal = selectedTerminal;
		if (!terminal || downloading) return;

		const paths = [...selectedEntries].map((p) => p.replace(/\/$/, ''));
		if (paths.length === 0) return;

		// Single file (not dir) — use the regular downloadFile path
		if (paths.length === 1 && ![...selectedEntries][0].endsWith('/')) {
			await downloadFile([...selectedEntries][0]);
			return;
		}

		downloading = true;
		const toastId = toast.loading($i18n.t('Preparing download...'));
		try {
			// Archive everything into a single ZIP
			const result = await archiveFromTerminal(terminal.url, terminal.key, paths);
			if (!result) {
				toast.error($i18n.t('Download failed'));
				return;
			}
			const url = URL.createObjectURL(result.blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = result.filename;
			a.click();
			URL.revokeObjectURL(url);
		} finally {
			toast.dismiss(toastId);
			downloading = false;
		}
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
		if (directoryMenu) directoryMenu = null;
		if (selectedCount > 0 && containerEl && !containerEl.contains(e.target as Node)) {
			clearSelection();
		}
	};

	// ── Lifecycle ────────────────────────────────────────────────────────
	onMount(() => {
		showHidden = localStorage.getItem('fileNav:showHidden') === 'true';
		const terminal = getTerminal();

		let handledDisplayFile = false;

		const unsubFileNav = showFileNavPath.subscribe(async (request) => {
			if (!request || !selectedTerminal) return;
			handledDisplayFile = true;
			showFileNavPath.set(null);
			let filePath = typeof request === 'string' ? request : request.path;
			const targetPage = typeof request === 'string' ? null : request.page;
			filePath = normalizePath(filePath);
			if (!isInsideFileRoot(filePath)) {
				await loadDir(fileRoot?.path ?? '/');
				return;
			}

			const lastSlash = filePath.lastIndexOf('/');
			const dir = lastSlash > 0 ? filePath.substring(0, lastSlash + 1) : '/';
			const fileName = filePath.substring(lastSlash + 1);

			// Always reload directory to ensure entries are fresh
			await loadDir(dir);
			await tick();

			const entry = entries.find((e) => e.name === fileName);
			if (entry) {
				await openEntry(entry, { page: targetPage });
			} else {
				// File may not be in listing; open it directly
				await openEntry({ name: fileName, type: 'file', size: 0 }, { page: targetPage });
			}
		});

		const unsubFileNavDir = showFileNavDir.subscribe(async (filePath) => {
			if (!filePath || !selectedTerminal) return;
			showFileNavDir.set(null);
			filePath = normalizePath(filePath);
			if (!isInsideFileRoot(filePath)) {
				await loadDir(fileRoot?.path ?? '/');
				return;
			}

			const lastSlash = filePath.lastIndexOf('/');
			const dir = lastSlash > 0 ? filePath.substring(0, lastSlash + 1) : '/';
			invalidateTreeCache(dir);

			if (selectedFile) {
				if (selectedFile === filePath || currentPath.startsWith(dir)) {
					const fileName = selectedFile.split('/').pop() ?? '';
					await openEntry({ name: fileName, type: 'file', size: 0 });
				}
			} else {
				if (currentPath.startsWith(dir) || dir.startsWith(currentPath)) {
					await refreshBrowser();
				}
			}
		});

		if (!handledDisplayFile && terminal) {
			loading = true;

			void (async () => {
				// Discover server features on initial mount
				const config = await getTerminalConfig(terminal.url, terminal.key);
				terminalEnabled = config?.features?.terminal !== false;

				const serverCwd = await getCwd(terminal.url, terminal.key, chatId ?? undefined);
				const useServerPath = !!chatId || savedPath === '/';
				const serverPath = applyCwd(serverCwd);
				if (useServerPath) {
					// Fetch session-specific cwd from the server (or global default for new chats)
					savedPath = serverPath;
				}
				savedPath = clampToFileRoot(savedPath);
				loadDir(savedPath, { restoreTree: true });
			})();
		}

		mounted = true;

		const onKeyDown = (e: KeyboardEvent) => {
			if (e.key === 'Shift') shiftKey = true;
		};
		const onKeyUp = (e: KeyboardEvent) => {
			if (e.key === 'Shift') shiftKey = false;
		};
		const onBlur = () => (shiftKey = false);

		const onVisibilityChange = () => {
			if (
				document.visibilityState === 'visible' &&
				!selectedFile &&
				selectedTerminal &&
				!terminalChatContextPending &&
				!loading
			) {
				loadDir(currentPath, { preserveTree: true });
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
		clearMatchRequest();
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

{#if terminalChatContextHidden}
	<div class="hidden"></div>
{:else if terminalChatContextPending}
	<div class="flex-1 flex flex-col items-center justify-center p-6 text-center">
		<Icon
			name="terminal"
			size={24}
			strokeWidth={1.4}
			class="text-gray-300 dark:text-gray-600 mb-2"
		/>
		<div class="text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Start the chat to use this terminal.')}
		</div>
	</div>
{:else if !selectedTerminal}
	<div class="flex-1 flex flex-col items-center justify-center p-6 text-center">
		<Icon
			name="terminal"
			size={24}
			strokeWidth={1.4}
			class="text-gray-300 dark:text-gray-600 mb-2"
		/>
		<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">
			{$i18n.t('No Terminal connection configured.')}
		</div>
		<div class="text-[0.625rem] text-gray-400 dark:text-gray-500">
			{$i18n.t('Add your Open Terminal URL and API key in Settings → Integrations.')}
		</div>
	</div>
{:else}
	<div
		bind:this={containerEl}
		class="flex flex-col h-full min-h-0 min-w-0 relative"
		on:dragover={(e) => !isSearching && handleDragOver(e)}
		on:dragleave={() => (isDragOver = false)}
		on:drop={(e) => !isSearching && handleDrop(e)}
		role="region"
		aria-label={$i18n.t('File browser')}
	>
		{#if isDragOver && !isSearching}
			<div
				class="absolute inset-1 z-10 flex items-center justify-center rounded-lg border-2 border-dashed border-blue-400 bg-blue-500/10 dark:border-blue-500 pointer-events-none"
			>
				<span class="text-xs font-medium text-blue-500 dark:text-blue-400">
					{$i18n.t('Drop to upload')}
				</span>
			</div>
		{/if}

		{#if previewPort === null}
			<FileNavToolbar
				breadcrumbs={buildBreadcrumbs(currentPath)}
				{selectedFile}
				{loading}
				writable={currentWritable}
				{canGoBack}
				{canGoForward}
				{sortBy}
				{sortAsc}
				{showHidden}
				onGoBack={goBack}
				onGoForward={goForward}
				onNavigate={loadDir}
				onRefresh={() => {
					if (selectedFile) {
						const fileName = selectedFile.split('/').pop() ?? '';
						openEntry({ name: fileName, type: 'file', size: 0 });
					} else {
						refreshBrowser();
					}
				}}
				onNewFolder={startNewFolder}
				onNewFile={startNewFile}
				onUploadFiles={handleUploadFiles}
				onDownloadDir={() => downloadFile(currentPath)}
				onMove={handleMovePaths}
				onSort={toggleSort}
				onToggleHidden={toggleHidden}
			>
				{#if (isMarkdown || isCsv || isHtml || isJson || isSvg || isNotebook) && fileContent !== null && !editing}
					<Tooltip content={showRaw ? $i18n.t('Preview') : $i18n.t('Source')}>
						<button
							class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
							on:click={() => {
								if (editing) filePreviewRef?.cancelEdit();
								showRaw = !showRaw;
							}}
							aria-label={showRaw ? $i18n.t('Preview') : $i18n.t('Source')}
						>
							{#if showRaw}
								<Icon name="eye" size={11} strokeWidth={1.4} />
							{:else}
								<Icon name="code" size={11} strokeWidth={1.4} />
							{/if}
						</button>
					</Tooltip>
				{/if}
				{#if isTextFile}
					{#if isHtml && showRaw}
						<Tooltip content={$i18n.t('Save')}>
							<button
								class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:hover:bg-transparent"
								on:click={() => filePreviewRef?.saveCodeFile()}
								disabled={saving || !selectedFileWritable}
								aria-label={$i18n.t('Save')}
							>
								{#if saving}
									<Spinner className="size-3.5" />
								{:else}
									<Icon name="check" size={11} strokeWidth={1.7} />
								{/if}
							</button>
						</Tooltip>
					{:else if isHtml}
						<!-- HTML preview mode: no edit/save buttons -->
					{:else if isMarkdown && showRaw}
						<Tooltip content={$i18n.t('Save')}>
							<button
								class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:hover:bg-transparent"
								on:click={() => filePreviewRef?.saveCodeFile()}
								disabled={saving || !selectedFileWritable}
								aria-label={$i18n.t('Save')}
							>
								{#if saving}
									<Spinner className="size-3.5" />
								{:else}
									<Icon name="check" size={11} strokeWidth={1.7} />
								{/if}
							</button>
						</Tooltip>
					{:else if isMarkdown}
						<!-- Markdown preview mode: no edit/save buttons -->
					{:else if isCode}
						<Tooltip content={$i18n.t('Save')}>
							<button
								class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:hover:bg-transparent"
								on:click={() => filePreviewRef?.saveCodeFile()}
								disabled={saving || !selectedFileWritable}
								aria-label={$i18n.t('Save')}
							>
								{#if saving}
									<Spinner className="size-3.5" />
								{:else}
									<Icon name="check" size={11} strokeWidth={1.7} />
								{/if}
							</button>
						</Tooltip>
					{:else if editing}
						<Tooltip content={$i18n.t('Cancel')}>
							<button
								class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
								on:click={() => filePreviewRef?.cancelEdit()}
								aria-label={$i18n.t('Cancel')}
							>
								<Icon name="xmark" size={11} strokeWidth={1.7} />
							</button>
						</Tooltip>
						<Tooltip content={$i18n.t('Save')}>
							<button
								class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:hover:bg-transparent"
								on:click={() => filePreviewRef?.saveEdit()}
								disabled={saving || !selectedFileWritable}
								aria-label={$i18n.t('Save')}
							>
								{#if saving}
									<Spinner className="size-3.5" />
								{:else}
									<Icon name="check" size={11} strokeWidth={1.7} />
								{/if}
							</button>
						</Tooltip>
					{:else}
						<Tooltip content={$i18n.t('Edit')}>
							<button
								class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:hover:bg-transparent"
								on:click={() => filePreviewRef?.startEdit()}
								disabled={!selectedFileWritable}
								aria-label={$i18n.t('Edit')}
							>
								<Icon name="pencil" size={11} strokeWidth={1.4} />
							</button>
						</Tooltip>
					{/if}
				{/if}

				{#if fileContent !== null}
					<Tooltip content={$i18n.t('Copy')}>
						<button
							class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
							on:click={async () => {
								if (await copyToClipboard(fileContent ?? '')) {
									toast.success($i18n.t('Copied to clipboard'));
								}
							}}
							aria-label={$i18n.t('Copy')}
						>
							<Icon name="copy" size={11} strokeWidth={1.4} />
						</button>
					</Tooltip>
				{/if}
				<Tooltip content={$i18n.t('Download')}>
					<button
						class="shrink-0 flex h-5 w-5 items-center justify-center rounded transition-colors duration-100 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
						on:click={() => selectedFile && downloadFile(selectedFile)}
						aria-label={$i18n.t('Download')}
					>
						<Icon name="download" size={11} strokeWidth={1.4} />
					</button>
				</Tooltip>
			</FileNavToolbar>

			{#if !selectedFile}
				<div
					class="flex h-8 shrink-0 items-center gap-1.5 border-b border-gray-50 px-3 dark:border-gray-850/30"
				>
					<Icon name="search" size={13} strokeWidth={1.5} class="shrink-0 text-gray-400" />
					<input
						type="text"
						class="min-w-0 flex-1 border-none bg-transparent text-xs text-gray-800 outline-none placeholder:text-gray-400 dark:text-gray-200 dark:placeholder:text-gray-600"
						placeholder={$i18n.t('Search files and contents')}
						bind:value={searchQuery}
					/>
					{#if searchQuery}
						<button
							class="flex shrink-0 items-center text-gray-400 transition hover:text-gray-600 dark:hover:text-gray-300"
							on:click={() => (searchQuery = '')}
							aria-label={$i18n.t('Clear search')}
						>
							<Icon name="xmark" size={11} strokeWidth={1.5} />
						</button>
					{/if}
				</div>
			{/if}

			<!-- Bulk action bar -->
			{#if selectedCount > 0 && !isSearching}
				<BulkActionBar
					count={selectedCount}
					canDelete={selectedEntriesWritable}
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
				closeDirectoryMenu();
				if (e.target === e.currentTarget && selectedCount > 0) clearSelection();
			}}
			on:contextmenu={(e) => {
				if (selectedFile || previewPort !== null || isSearching) return;
				if ((e.target as HTMLElement)?.closest('[data-file-row]')) return;
				e.preventDefault();
				directoryMenu = { x: e.clientX, y: e.clientY };
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
					readOnly={!selectedFileWritable}
					{fileLoading}
					{fileImageUrl}
					{fileVideoUrl}
					{fileAudioUrl}
					{filePdfData}
					{fileSqliteData}
					{fileDocxData}
					{fileContent}
					{fileOfficeHtml}
					{fileOfficeSlides}
					targetPage={documentTargetPage}
					{excelSheetNames}
					{selectedExcelSheet}
					searchTarget={fileSearchTarget}
					onSheetChange={async (sheet) => {
						if (!excelWorkbook) return;
						selectedExcelSheet = sheet;
						const { excelToTable } = await import('$lib/utils/excelToTable');
						const result = await excelToTable(excelWorkbook.Sheets[sheet]);
						const DOMPurify = (await import('dompurify')).default;
						fileOfficeHtml = DOMPurify.sanitize(result.html);
					}}
					baseUrl={selectedTerminal?.url ?? ''}
					apiKey={selectedTerminal?.key ?? ''}
					overlay={overlay || isDraggingHandle}
					onSave={async (content) => {
						const terminal = selectedTerminal;
						if (!terminal || !selectedFile || !selectedFileWritable) return;
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
				{#if isSearching}
					{#if matchLoading}
						<div class="flex justify-center pt-8"><Spinner className="size-4" /></div>
					{:else if matchError}
						<div class="flex items-center justify-center py-12">
							<div class="text-xs text-gray-400 dark:text-gray-500">{matchError}</div>
						</div>
					{:else if !matchResults?.length}
						<div class="flex items-center justify-center py-12">
							<div class="text-xs text-gray-400 dark:text-gray-500">{$i18n.t('No matches')}</div>
						</div>
					{:else}
						{#if filenameMatches.length > 0}
							<div
								class="px-2 pt-1 pb-0.5 text-[0.625rem] font-medium uppercase tracking-wide text-gray-400 dark:text-gray-600"
							>
								{$i18n.t('Filename matches')}
							</div>
							{#each filenameMatches as match (match.path)}
								<button
									class="flex h-7 w-full items-center gap-2 rounded-lg px-2 text-left transition-colors duration-75 hover:bg-gray-50 dark:hover:bg-white/4"
									on:click={() => openFileMatch(match)}
								>
									<FileTypeIcon name={match.name} type={match.type} />
									<span class="min-w-0 flex-1 truncate text-xs text-gray-800 dark:text-gray-200">
										{match.name}
										{#if relativeParentPath(match.relative_path)}
											<span class="ml-1.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
												{relativeParentPath(match.relative_path)}
											</span>
										{/if}
									</span>
								</button>
								{#if match.content_matches.length > 0}
									{@const preview = match.content_matches[0]}
									<button
										class="flex h-6 w-full items-center gap-2 rounded-lg pl-8 pr-2 text-left transition-colors duration-75 hover:bg-gray-50 dark:hover:bg-white/4"
										on:click={() => openContentMatch(match, preview)}
									>
										<span
											class="w-6 shrink-0 text-right font-mono text-[0.625rem] text-gray-400 dark:text-gray-600"
											>{preview.line}</span
										>
										<span
											class="min-w-0 flex-1 truncate font-mono text-[0.6875rem] text-gray-500 dark:text-gray-500"
											>{preview.text}</span
										>
										{#if match.content_matches.length > 1}
											<span class="shrink-0 text-[0.625rem] text-gray-400 dark:text-gray-600">
												+{match.content_matches.length - 1}
											</span>
										{/if}
									</button>
								{/if}
							{/each}
						{/if}

						{#if contentOnlyMatches.length > 0}
							<div
								class="px-2 pt-2 pb-0.5 text-[0.625rem] font-medium uppercase tracking-wide text-gray-400 dark:text-gray-600"
							>
								{$i18n.t('Content matches')}
							</div>
							{#each contentOnlyMatches as match (match.path)}
								<button
									class="flex h-7 w-full items-center gap-2 rounded-lg px-2 text-left transition-colors duration-75 hover:bg-gray-50 dark:hover:bg-white/4"
									on:click={() => openFileMatch(match)}
								>
									<FileTypeIcon name={match.name} type={match.type} />
									<span class="min-w-0 flex-1 truncate text-xs text-gray-800 dark:text-gray-200">
										{match.name}
										{#if relativeParentPath(match.relative_path)}
											<span class="ml-1.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
												{relativeParentPath(match.relative_path)}
											</span>
										{/if}
									</span>
								</button>
								{#if match.content_matches.length > 0}
									{@const preview = match.content_matches[0]}
									<button
										class="flex h-6 w-full items-center gap-2 rounded-lg pl-8 pr-2 text-left transition-colors duration-75 hover:bg-gray-50 dark:hover:bg-white/4"
										on:click={() => openContentMatch(match, preview)}
									>
										<span
											class="w-6 shrink-0 text-right font-mono text-[0.625rem] text-gray-400 dark:text-gray-600"
											>{preview.line}</span
										>
										<span
											class="min-w-0 flex-1 truncate font-mono text-[0.6875rem] text-gray-500 dark:text-gray-500"
											>{preview.text}</span
										>
										{#if match.content_matches.length > 1}
											<span class="shrink-0 text-[0.625rem] text-gray-400 dark:text-gray-600">
												+{match.content_matches.length - 1}
											</span>
										{/if}
									</button>
								{/if}
							{/each}
						{/if}

						{#if nextMatchOffset !== null}
							<div use:loadMoreOnVisible class="flex h-8 items-center justify-center">
								{#if matchLoadingMore}
									<Spinner className="size-3" />
								{:else if matchLoadMoreError}
									<button
										class="text-[0.6875rem] text-gray-400 transition-colors duration-75 hover:text-gray-600 dark:text-gray-600 dark:hover:text-gray-400"
										on:click={() => {
											matchLoadMoreError = false;
											void loadMoreMatches();
										}}>{$i18n.t('Retry')}</button
									>
								{/if}
							</div>
						{/if}
					{/if}
				{:else if uploading}
					<div class="flex items-center justify-center gap-2 p-4 text-xs text-gray-500">
						<Spinner className="size-4" />
						{$i18n.t('Uploading...')}
					</div>
				{:else if loading || ($selectedTerminalId && $terminalServers === null)}
					<div class="flex justify-center pt-8"><Spinner className="size-4" /></div>
				{:else if error}
					<div class="p-4 text-xs">{error}</div>
				{:else if visibleEntries.length === 0 && !creatingFolder && !creatingFile}
					<div class="flex items-center justify-center py-12">
						<div class="text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('This folder is empty')}
						</div>
					</div>
				{/if}

				{#if !isSearching && !loading && !error && !uploading && !($selectedTerminalId && $terminalServers === null)}
					{#if creatingFolder}
						<div class="flex h-7 items-center gap-2 px-2">
							<FileTypeIcon name={newFolderName} type="directory" />
							<input
								bind:this={newFolderInput}
								bind:value={newFolderName}
								class="flex-1 text-xs bg-transparent border border-gray-100 dark:border-white/[0.06] rounded px-1.5 py-0.5 outline-none focus:border-blue-400 dark:focus:border-blue-500"
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
						<div class="flex h-7 items-center gap-2 px-2">
							<FileTypeIcon name={newFileName} type="file" />
							<input
								bind:this={newFileInput}
								bind:value={newFileName}
								class="flex-1 text-xs bg-transparent border border-gray-100 dark:border-white/[0.06] rounded px-1.5 py-0.5 outline-none focus:border-blue-400 dark:focus:border-blue-500"
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

					{#if visibleEntries.length > 0 || creatingFolder || creatingFile}
						<ul>
							{#each visibleEntries as entry (entry.fullPath)}
								<FileEntryRow
									{entry}
									currentPath={entry.parentPath}
									fullPath={entry.fullPath}
									depth={entry.depth}
									rowIndex={entry.rowIndex}
									expanded={expandedDirs.has(entry.fullPath)}
									loadingChildren={loadingDirs.has(entry.fullPath)}
									terminalUrl={selectedTerminal.url}
									terminalKey={selectedTerminal.key}
									selected={selectedEntries.has(entry.fullPath)}
									{selectionMode}
									selectedPaths={selectedEntries}
									onOpen={(row) =>
										openEntry({
											...row,
											fullPath: entry.fullPath,
											parentPath: entry.parentPath,
											depth: entry.depth,
											rowIndex: entry.rowIndex
										})}
									onDownload={downloadFile}
									onDelete={requestDelete}
									onMove={handleMovePaths}
									onRename={handleRename}
									onSelect={handleSelect}
									onLongPress={enterSelectionMode}
									onToggleExpand={toggleExpand}
									showDate={sortBy === 'date'}
									parentWritable={currentWritable}
								/>
							{/each}
						</ul>
					{/if}
				{/if}
			{/if}
		</div>

		<!-- Port detection -->
		{#if selectedTerminal && !selectedFile && previewPort === null && !isSearching}
			<div class="shrink-0 border-t border-gray-50 dark:border-gray-850/30">
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
			<div class="shrink-0 border-t border-gray-50 dark:border-gray-850/30">
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
					class="w-full flex items-center gap-2 px-2 py-1 mb-0.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-100"
					on:click={toggleTerminal}
				>
					<Icon name="terminal" size={14} strokeWidth={1.4} class="shrink-0" />
					<span class="font-normal">{$i18n.t('Terminal')}</span>

					{#if terminalExpanded}
						<div
							class="w-1.5 h-1.5 rounded-full transition-colors {terminalConnected
								? 'bg-emerald-500'
								: terminalConnecting
									? 'bg-yellow-500 animate-pulse'
									: 'bg-gray-400'}"
						/>
					{/if}

					<Icon
						name="chevron-up"
						size={12}
						strokeWidth={1.4}
						class="ml-auto transition-transform {terminalExpanded ? 'rotate-180' : ''}"
					/>
				</button>

				{#if terminalExpanded}
					<div style="height: {terminalHeight}px" class="min-h-0">
						<XTerminal
							overlay={overlay || isDraggingHandle}
							bind:connected={terminalConnected}
							bind:connecting={terminalConnecting}
							{chatId}
						/>
					</div>
				{/if}
			</div>
		{/if}

		<input
			bind:this={directoryUploadInput}
			type="file"
			multiple
			hidden
			on:change={async () => {
				if (!currentWritable || !directoryUploadInput?.files?.length) return;
				await handleUploadFiles(Array.from(directoryUploadInput.files));
				directoryUploadInput.value = '';
			}}
		/>

		{#if directoryMenu}
			<div
				class="fixed z-[9999999]"
				style="left: {directoryMenu.x}px; top: {directoryMenu.y}px;"
				on:click|stopPropagation
			>
				<DropdownMenu className="min-w-[9.375rem]">
					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition"
						on:click={() => {
							closeDirectoryMenu();
							refreshBrowser();
						}}
					>
						<Icon name="refresh" size={12} strokeWidth={1.4} />
						<span>{$i18n.t('Refresh')}</span>
					</button>
					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition disabled:opacity-40 disabled:hover:bg-transparent"
						disabled={!currentWritable}
						on:click={() => {
							closeDirectoryMenu();
							startNewFile();
						}}
					>
						<Icon name="empty-page" size={12} strokeWidth={1.4} />
						<span>{$i18n.t('New File')}</span>
					</button>
					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition disabled:opacity-40 disabled:hover:bg-transparent"
						disabled={!currentWritable}
						on:click={() => {
							closeDirectoryMenu();
							startNewFolder();
						}}
					>
						<Icon name="folder" size={12} strokeWidth={1.4} />
						<span>{$i18n.t('New Folder')}</span>
					</button>
					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition disabled:opacity-40 disabled:hover:bg-transparent"
						disabled={!currentWritable}
						on:click={() => {
							closeDirectoryMenu();
							directoryUploadInput?.click();
						}}
					>
						<Icon name="upload" size={12} strokeWidth={1.4} />
						<span>{$i18n.t('Upload')}</span>
					</button>
					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition"
						on:click={() => {
							closeDirectoryMenu();
							downloadFile(currentPath);
						}}
					>
						<Icon name="download" size={12} strokeWidth={1.4} />
						<span>{$i18n.t('Download')}</span>
					</button>
					<button
						type="button"
						class="select-none flex h-7 w-full items-center gap-2 rounded-lg px-2 text-xs hover:bg-gray-50/40 dark:hover:bg-white/4 transition"
						on:click={() => {
							closeDirectoryMenu();
							toggleHidden();
						}}
					>
						<Icon name="eye" size={12} strokeWidth={1.4} />
						<span>{showHidden ? $i18n.t('Hide Hidden Files') : $i18n.t('Show Hidden Files')}</span>
					</button>
				</DropdownMenu>
			</div>
		{/if}
	</div>
{/if}
