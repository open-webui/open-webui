<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import {
		settings,
		selectedTerminalId,
		showControls,
		showFileNavPath,
		terminalServers
	} from '$lib/stores';
	import { downloadFileBlob, downloadFilePreview, readFile } from '$lib/apis/terminal';
	import FilePreview from '$lib/components/chat/FileNav/FilePreview.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import { fileIconName } from '$lib/components/chat/FileNav/fileIcon';
	import { normalizeDocumentTargetPage } from '$lib/utils/documentPreview';

	export let item: any;
	export let chatId = '';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let expanded = true;
	let loading = false;
	let loadedKey = '';
	let error = '';
	let objectUrls: string[] = [];

	let fileImageUrl: string | null = null;
	let fileVideoUrl: string | null = null;
	let fileAudioUrl: string | null = null;
	let filePdfData: ArrayBuffer | null = null;
	let fileSqliteData: ArrayBuffer | null = null;
	let fileDocxData: ArrayBuffer | null = null;
	let fileContent: string | null = null;
	let fileOfficeHtml: string | null = null;
	let fileOfficeSlides: string[] | null = null;
	let currentSlide = 0;
	let excelSheetNames: string[] = [];
	let selectedExcelSheet = '';
	let excelWorkbook: any = null;

	const IMAGE_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico', 'avif']);
	const VIDEO_EXTS = new Set(['mp4', 'webm', 'mov', 'ogv', 'avi', 'mkv']);
	const AUDIO_EXTS = new Set(['mp3', 'wav', 'ogg', 'oga', 'flac', 'm4a', 'aac', 'wma', 'opus']);
	const SQLITE_EXTS = new Set(['db', 'sqlite', 'sqlite3', 'db3']);
	const OFFICE_EXTS = new Set(['docx', 'xlsx', 'xls', 'pptx']);

	$: path = String(item?.full_path || item?.path || '');
	$: name = String(item?.name || path.split('/').filter(Boolean).at(-1) || 'file');
	$: targetPage = normalizeDocumentTargetPage(item?.page);
	$: selector = item?.terminal_selector;
	$: terminal = resolveTerminal();
	$: unavailable = !terminal;
	$: previewKey = terminal ? `${terminal.url}|${terminal.key}|${path}|${chatId}` : '';
	$: previewClass = isImage(path)
		? 'h-[22rem]'
		: isPdf(path) ||
			  isOffice(path) ||
			  getExt(path) === 'html' ||
			  getExt(path) === 'htm' ||
			  getExt(path) === 'svg'
			? 'h-96'
			: 'h-72';
	$: if (expanded && terminal && path && previewKey !== loadedKey && !loading) {
		void loadPreview(previewKey);
	}

	const getExt = (value: string) => value.split('.').pop()?.toLowerCase() ?? '';
	const isImage = (value: string) => IMAGE_EXTS.has(getExt(value));
	const isVideo = (value: string) => VIDEO_EXTS.has(getExt(value));
	const isAudio = (value: string) => AUDIO_EXTS.has(getExt(value));
	const isSqlite = (value: string) => SQLITE_EXTS.has(getExt(value));
	const isPdf = (value: string) => getExt(value) === 'pdf';
	const isOffice = (value: string) => OFFICE_EXTS.has(getExt(value));

	const t = (key: string, vars?: Record<string, unknown>) => $i18n?.t?.(key, vars) ?? key;

	function resolveTerminal(): { url: string; key: string } | null {
		if (!selector || $selectedTerminalId !== selector) return null;

		const systemTerminal = ($terminalServers ?? []).find((server: any) => server.id === selector);
		if (systemTerminal?.url) {
			return { url: systemTerminal.url, key: localStorage.token };
		}

		const directTerminal = (($settings as any)?.terminalServers ?? []).find(
			(server: any) => server.url === selector && server.enabled
		);
		if (directTerminal?.url) {
			return { url: directTerminal.url, key: directTerminal.key ?? '' };
		}

		return null;
	}

	function clearPreview() {
		for (const url of objectUrls) URL.revokeObjectURL(url);
		objectUrls = [];
		fileImageUrl = null;
		fileVideoUrl = null;
		fileAudioUrl = null;
		filePdfData = null;
		fileSqliteData = null;
		fileDocxData = null;
		fileContent = null;
		fileOfficeHtml = null;
		fileOfficeSlides = null;
		currentSlide = 0;
		excelSheetNames = [];
		selectedExcelSheet = '';
		excelWorkbook = null;
	}

	async function blobForPreview() {
		if (!terminal) return null;
		return downloadFileBlob(terminal.url, terminal.key, path, chatId || undefined);
	}

	async function loadExcelSheet(sheet: string) {
		if (!excelWorkbook) return;
		selectedExcelSheet = sheet;
		const { excelToTable } = await import('$lib/utils/excelToTable');
		const result = await excelToTable(excelWorkbook.Sheets[selectedExcelSheet]);
		const DOMPurify = (await import('dompurify')).default;
		fileOfficeHtml = DOMPurify.sanitize(result.html);
	}

	async function loadPreview(key: string) {
		loadedKey = key;
		loading = true;
		error = '';
		clearPreview();

		try {
			if (isImage(path) || isVideo(path) || isAudio(path)) {
				const result = await blobForPreview();
				if (!result) throw new Error(t('Preview failed'));
				const url = URL.createObjectURL(result.blob);
				objectUrls = [...objectUrls, url];
				if (isImage(path)) fileImageUrl = url;
				else if (isVideo(path)) fileVideoUrl = url;
				else fileAudioUrl = url;
			} else if (isPdf(path) || isSqlite(path) || isOffice(path)) {
				const ext = getExt(path);

				if (isPdf(path)) {
					const result = await blobForPreview();
					if (!result) throw new Error(t('Preview failed'));
					const arrayBuffer = await result.blob.arrayBuffer();
					filePdfData = arrayBuffer;
				} else if (isSqlite(path)) {
					const result = await blobForPreview();
					if (!result) throw new Error(t('Preview failed'));
					const arrayBuffer = await result.blob.arrayBuffer();
					fileSqliteData = arrayBuffer;
				} else if (ext === 'docx') {
					const preview = await downloadFilePreview(
						terminal.url,
						terminal.key,
						path,
						chatId || undefined
					);
					if (preview) {
						filePdfData = await preview.blob.arrayBuffer();
					} else {
						const result = await blobForPreview();
						if (!result) throw new Error(t('Preview failed'));
						fileDocxData = await result.blob.arrayBuffer();
					}
				} else if (ext === 'xlsx' || ext === 'xls') {
					const result = await blobForPreview();
					if (!result) throw new Error(t('Preview failed'));
					const arrayBuffer = await result.blob.arrayBuffer();
					const XLSX = await import('xlsx');
					excelWorkbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
					excelSheetNames = excelWorkbook.SheetNames;
					if (excelSheetNames.length > 0) {
						await loadExcelSheet(excelSheetNames[0]);
					}
				} else if (ext === 'pptx') {
					const preview = await downloadFilePreview(
						terminal.url,
						terminal.key,
						path,
						chatId || undefined
					);
					if (preview) {
						filePdfData = await preview.blob.arrayBuffer();
					} else {
						const result = await blobForPreview();
						if (!result) throw new Error(t('Preview failed'));
						const arrayBuffer = await result.blob.arrayBuffer();
						const { pptxToImages } = await import('$lib/utils/pptxToHtml');
						const resultImages = await pptxToImages(arrayBuffer);
						fileOfficeSlides = resultImages.images;
					}
				}
			} else if (terminal) {
				fileContent = await readFile(terminal.url, terminal.key, path, chatId || undefined);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : t('Preview failed');
		} finally {
			loading = false;
		}
	}

	function openInFiles() {
		if (unavailable || !path) return;
		showControls.set(true);
		showFileNavPath.set(targetPage ? { path, page: targetPage } : path);
	}

	async function downloadFile() {
		if (!terminal || !path) return;
		const result = await downloadFileBlob(terminal.url, terminal.key, path, chatId || undefined);
		if (!result) {
			toast.error(t('Download failed'));
			return;
		}

		const url = URL.createObjectURL(result.blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = result.filename;
		a.click();
		URL.revokeObjectURL(url);
	}

	onDestroy(clearPreview);
</script>

<div
	class="my-2 w-full overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/8 dark:bg-gray-950/20"
>
	<div
		class="flex h-8 items-center {expanded ? 'border-b border-gray-100 dark:border-white/8' : ''}"
	>
		<button
			type="button"
			class="flex h-full min-w-0 flex-1 items-center gap-2 px-2.5 text-left"
			on:click={() => (expanded = !expanded)}
			aria-expanded={expanded}
		>
			<div
				class="flex size-5 shrink-0 items-center justify-center text-gray-500 dark:text-gray-400"
			>
				<Icon name={fileIconName(name || path || '', 'file')} size={14} />
			</div>
			<div class="min-w-0 flex-1 truncate text-xs font-medium text-gray-800 dark:text-gray-100">
				{name}
			</div>
		</button>

		<button
			type="button"
			class="mr-1 flex size-6 shrink-0 items-center justify-center rounded text-gray-400 transition-colors hover:text-gray-700 disabled:opacity-40 disabled:hover:text-gray-400 dark:text-gray-500 dark:hover:text-gray-200 dark:disabled:hover:text-gray-500"
			disabled={unavailable}
			on:click|stopPropagation={downloadFile}
			aria-label={t('Download')}
		>
			<Icon name="download" size={13} />
		</button>
		<button
			type="button"
			class="mr-1 flex size-6 shrink-0 items-center justify-center rounded text-gray-400 transition-colors hover:text-gray-700 disabled:opacity-40 disabled:hover:text-gray-400 dark:text-gray-500 dark:hover:text-gray-200 dark:disabled:hover:text-gray-500"
			disabled={unavailable}
			on:click|stopPropagation={openInFiles}
			aria-label={t('Open')}
		>
			<Icon name="external-link" size={13} />
		</button>
	</div>

	{#if expanded}
		{#if unavailable}
			<div class="px-4 py-3 text-xs text-gray-500 dark:text-gray-400">
				{t('Terminal unavailable')}
			</div>
		{:else if error}
			<div class="px-4 py-3 text-xs text-red-500 dark:text-red-400">{error}</div>
		{:else}
			<div
				class="{previewClass} max-h-[75vh] min-h-24 resize-y overflow-hidden bg-gray-50 dark:bg-gray-950"
			>
				<FilePreview
					selectedFile={path}
					fileLoading={loading}
					{fileImageUrl}
					{fileVideoUrl}
					{fileAudioUrl}
					{filePdfData}
					{fileSqliteData}
					{fileDocxData}
					{fileContent}
					baseUrl={terminal?.url ?? ''}
					apiKey={terminal?.key ?? ''}
					{fileOfficeHtml}
					{fileOfficeSlides}
					{currentSlide}
					{targetPage}
					{excelSheetNames}
					{selectedExcelSheet}
					onSheetChange={loadExcelSheet}
					readOnly={true}
				/>
				{#if !loading && fileImageUrl === null && fileVideoUrl === null && fileAudioUrl === null && filePdfData === null && fileSqliteData === null && fileDocxData === null && fileContent === null && fileOfficeHtml === null && fileOfficeSlides === null}
					<div
						class="flex h-full items-center justify-center px-3 text-xs text-gray-500 dark:text-gray-400"
					>
						{t('No preview available')}
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>
