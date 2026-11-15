<script lang="ts">
	import ExcelPreview from '$lib/components/common/ExcelPreview.svelte';
	import { getContext, tick } from 'svelte';
	import { downloadFileBlob } from '$lib/apis/terminal';
	import MarkdownFileEditor from './MarkdownFileEditor.svelte';
	import MarkdownDocument from './MarkdownDocument.svelte';
	import { settings, config } from '$lib/stores';
	import { injectCsp } from '$lib/utils/csp';
	import { sanitizeSvg } from '$lib/utils';
	import Spinner from '../../common/Spinner.svelte';
	import PdfPagesPreview from '../../common/PdfPagesPreview.svelte';
	import PanzoomContainer from '../../common/PanzoomContainer.svelte';
	import DocxPreview from '../../common/DocxPreview.svelte';
	import PptxPreview from '../../common/PptxPreview.svelte';
	import JsonTreeView from './JsonTreeView.svelte';
	import NotebookView from './NotebookView.svelte';
	import SqliteView from './SqliteView.svelte';
	import FileCodeEditor from './FileCodeEditor.svelte';

	let pdfPagesPreviewRef: PdfPagesPreview;
	let fileCodeEditorRef: FileCodeEditor;
	let markdownEditorRef: MarkdownFileEditor;

	const i18n: any = getContext('i18n');

	export let selectedFile: string | null = null;
	export let fileLoading = false;
	export let fileImageUrl: string | null = null;
	export let fileVideoUrl: string | null = null;
	export let fileAudioUrl: string | null = null;
	export let filePdfData: ArrayBuffer | null = null;
	export let fileSqliteData: ArrayBuffer | null = null;
	export let fileModelData: ArrayBuffer | null = null;
	export let fileDocxData: ArrayBuffer | null = null;
	export let fileContent: string | null = null;
	export let gitBaseContent: string | null = null;

	// Terminal connection for notebook execution
	export let baseUrl: string = '';
	export let apiKey: string = '';
	export let chatId: string | null = null;
	export let resourceVersion = 0;
	export let onLocalLink: (path: string) => void = () => {};
	export let dirty = false;
	let codeValue = '';
	let lastLoaded: string | null = null;
	let bufferPath: string | null = null;
	const syncContent = (content: string | null, path: string | null) => {
		if (bufferPath !== path || codeValue === (lastLoaded ?? '')) codeValue = content ?? '';
		bufferPath = path;
		lastLoaded = content;
	};
	$: syncContent(fileContent, selectedFile);
	$: dirty = codeValue !== (fileContent ?? '');
	export const getSelection = () =>
		isMarkdown && !showRaw && !searchTarget
			? markdownEditorRef?.getSelection()
			: fileCodeEditorRef?.getSelection();
	export const save = () => saveCodeFile();

	export const captureView = () => ({
		baseText: fileContent ?? '',
		text: codeValue,
		dirty,
		showRaw,
		editor: fileCodeEditorRef?.captureView()
	});
	export async function restoreView(view: any) {
		if (!view) return;
		showRaw = view.showRaw;
		codeValue = view.text;
		lastLoaded = fileContent;
		bufferPath = selectedFile;
		await tick();
		fileCodeEditorRef?.restoreView(view.editor);
	}

	// Office preview props
	export let fileOfficeHtml: string | null = null;
	export let fileOfficeSlides: string[] | null = null;
	export let currentSlide = 0;
	export let targetPage: number | null = null;
	export let excelSheetNames: string[] = [];
	export let selectedExcelSheet = '';
	export let onSheetChange: ((sheet: string) => void) | null = null;

	export let overlay = false;
	export let readOnly = false;
	export let allowScripts: boolean | undefined = undefined;

	export let onSave: ((content: string) => Promise<void>) | null = null;
	export let searchTarget: {
		line: number;
		column: number;
		length: number;
		requestId: number;
	} | null = null;

	export let saving = false;

	export const discard = () => {
		codeValue = fileContent ?? '';
		fileCodeEditorRef?.setValue(codeValue);
		dirty = false;
	};

	/** Save code file directly from CodeMirror */
	export const saveCodeFile = async () => {
		if (!onSave || readOnly) return;
		saving = true;
		try {
			if (isMarkdown && !showRaw && !searchTarget) await markdownEditorRef?.flushUploads();
			const content =
				isMarkdown && !showRaw && !searchTarget
					? codeValue
					: (fileCodeEditorRef?.getValue() ?? codeValue);
			await onSave(content);
		} finally {
			saving = false;
		}
	};

	$: isTextFile = fileContent !== null && fileImageUrl === null && filePdfData === null;

	const MD_EXTS = new Set(['md', 'markdown', 'mdx']);
	const CSV_EXTS = new Set(['csv', 'tsv']);
	const HTML_EXTS = new Set(['html', 'htm']);
	const JSON_EXTS = new Set(['json', 'jsonc', 'jsonl', 'json5']);
	const getExt = (path: string | null) => path?.split('.').pop()?.toLowerCase() ?? '';

	$: isMarkdown = MD_EXTS.has(getExt(selectedFile));
	$: isCsv = CSV_EXTS.has(getExt(selectedFile));
	$: isHtml = HTML_EXTS.has(getExt(selectedFile));
	$: isJson = JSON_EXTS.has(getExt(selectedFile));
	$: isSvg = getExt(selectedFile) === 'svg';
	$: isNotebook = getExt(selectedFile) === 'ipynb';
	$: csvDelimiter = getExt(selectedFile) === 'tsv' ? '\t' : ',';
	$: isPptx = getExt(selectedFile) === 'pptx';

	// For HTML files on system terminals (proxy URL), use path-based serving
	// so the iframe can resolve relative CSS/JS/image references via cookie auth.
	$: serveUrl =
		isHtml && selectedFile && baseUrl && baseUrl.includes('/api/v1/terminals/')
			? `${baseUrl}/files/serve/${selectedFile.replace(/^\//, '')}`
			: null;
	// Simple CSV parser that handles quoted fields
	const parseCsv = (text: string, delimiter: string): string[][] => {
		const rows: string[][] = [];
		let row: string[] = [];
		let field = '';
		let inQuotes = false;
		for (let i = 0; i < text.length; i++) {
			const ch = text[i];
			if (inQuotes) {
				if (ch === '"') {
					if (text[i + 1] === '"') {
						field += '"';
						i++;
					} else {
						inQuotes = false;
					}
				} else {
					field += ch;
				}
			} else if (ch === '"') {
				inQuotes = true;
			} else if (ch === delimiter) {
				row.push(field);
				field = '';
			} else if (ch === '\n' || (ch === '\r' && text[i + 1] === '\n')) {
				if (ch === '\r') i++;
				row.push(field);
				field = '';
				if (row.some((c) => c !== '')) rows.push(row);
				row = [];
			} else {
				field += ch;
			}
		}
		row.push(field);
		if (row.some((c) => c !== '')) rows.push(row);
		return rows;
	};

	$: csvRows = isCsv && fileContent ? parseCsv(fileContent, csvDelimiter) : [];
	$: csvHeader = csvRows.length > 0 ? csvRows[0] : [];
	$: csvBody = csvRows.length > 1 ? csvRows.slice(1) : [];

	// Retired errors: keep their translations.
	// $i18n.t('Invalid JSON')
	// $i18n.t('JSON parse error: {{error}}')
	// JSON parsing
	let parsedJson: unknown = undefined;

	$: if (isJson && fileContent !== null) {
		try {
			parsedJson = JSON.parse(fileContent);
		} catch (e) {
			parsedJson = undefined;
		}
	} else {
		parsedJson = undefined;
	}

	// Notebook parsing
	let parsedNotebook: Record<string, unknown> | null = null;

	$: if (isNotebook && fileContent !== null) {
		try {
			parsedNotebook = JSON.parse(fileContent);
		} catch {
			parsedNotebook = null;
		}
	} else {
		parsedNotebook = null;
	}

	export let showRaw = false;
	$: (selectedFile, (showRaw = false)); // reset to preview mode when switching files

	// Auto-switch to raw/editor mode for empty previewable files so the user
	// can start editing immediately instead of seeing a blank preview.
	$: if (fileContent !== null && fileContent.trim() === '' && (isCsv || isJson)) {
		showRaw = true;
	}

	let panzoomRef: PanzoomContainer;
	let pptxPreviewRef: PptxPreview;
	let imageZoomLevel = 1;
	$: svgPreview = isSvg && !showRaw && !searchTarget && !!fileContent;
	export const resetImageView = () => {
		panzoomRef?.reset();
		pptxPreviewRef?.resetView();
	};

	export const resetPdfView = () => {
		pdfPagesPreviewRef?.resetView();
	};
</script>

<div
	class="flex-1 {fileImageUrl !== null ||
	svgPreview ||
	fileVideoUrl !== null ||
	fileDocxData !== null ||
	fileModelData !== null ||
	filePdfData !== null ||
	(fileOfficeSlides !== null && fileOfficeSlides.length > 0)
		? 'overflow-hidden'
		: 'overflow-y-auto'} min-h-0 min-w-0 relative h-full"
>
	<!-- File preview -->
	{#if fileLoading}
		<div class="flex items-center justify-center h-full">
			<Spinner className="size-3.5 text-gray-400 dark:text-gray-500" />
		</div>
	{:else if fileImageUrl !== null}
		<PanzoomContainer
			bind:this={panzoomRef}
			bind:zoomLevel={imageZoomLevel}
			className="w-full h-full flex items-center justify-center"
			options={{ zoomDoubleClickSpeed: 1 }}
		>
			<img
				src={fileImageUrl}
				alt={selectedFile?.split('/').pop()}
				class="max-w-full max-h-full object-contain p-3"
				draggable="false"
			/>
		</PanzoomContainer>
	{:else if fileVideoUrl !== null}
		<div class="w-full h-full flex items-center justify-center bg-black">
			<!-- svelte-ignore a11y-media-has-caption -->
			<video src={fileVideoUrl} controls class="w-full h-full object-contain">
				{$i18n.t('Your browser does not support the video tag.')}
			</video>
		</div>
	{:else if fileAudioUrl !== null}
		<div class="w-full h-full flex items-center justify-center p-6">
			<audio src={fileAudioUrl} controls class="w-full max-w-md">
				{$i18n.t('Your browser does not support the audio tag.')}
			</audio>
		</div>
	{:else if filePdfData !== null}
		<PdfPagesPreview
			bind:this={pdfPagesPreviewRef}
			data={filePdfData}
			bind:currentSlide
			{targetPage}
			singlePage={isPptx}
			itemLabel={isPptx ? 'Slide' : 'Page'}
			listLabel={isPptx ? 'Slides' : 'Pages'}
			className="w-full h-full"
		/>
	{:else if fileModelData !== null}
		{#key fileModelData}
			{#await import('../../common/ModelPreview.svelte')}
				<div class="flex h-full items-center justify-center">
					<Spinner className="size-3.5 text-gray-400 dark:text-gray-500" />
				</div>
			{:then { default: ModelPreview }}
				<ModelPreview
					data={fileModelData}
					path={selectedFile ?? ''}
					loadResource={baseUrl
						? async (path, signal) => {
								const result = await downloadFileBlob(
									baseUrl,
									apiKey,
									path,
									chatId ?? undefined,
									signal
								);
								if (!result) throw new Error('Could not load model resource.');
								return result.blob;
							}
						: undefined}
				/>
			{:catch}
				<div
					class="flex h-full items-center justify-center p-4 text-center text-sm text-gray-500 dark:text-gray-400"
				>
					{$i18n.t('Preview failed')}
				</div>
			{/await}
		{/key}
	{:else if fileSqliteData !== null}
		<SqliteView data={fileSqliteData} />
	{:else if fileDocxData !== null}
		<DocxPreview data={fileDocxData} {targetPage} className="w-full h-full" />
	{:else if fileOfficeHtml !== null}
		<ExcelPreview
			html={fileOfficeHtml}
			sheetNames={excelSheetNames}
			selectedSheet={selectedExcelSheet}
			{onSheetChange}
		/>
	{:else if fileOfficeSlides !== null && fileOfficeSlides.length > 0}
		<PptxPreview
			bind:this={pptxPreviewRef}
			slides={fileOfficeSlides}
			bind:currentSlide
			{targetPage}
			className="w-full h-full"
		/>
	{:else if fileContent !== null}
		{#if searchTarget || showRaw}
			<div class="absolute inset-0">
				<FileCodeEditor
					{gitBaseContent}
					readOnly={readOnly || !onSave}
					bind:this={fileCodeEditorRef}
					bind:value={codeValue}
					filePath={selectedFile}
					onSave={readOnly ? null : saveCodeFile}
					{searchTarget}
				/>
			</div>
		{:else if isHtml && !showRaw && serveUrl}
			{#if overlay}
				<div class="absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}
			<iframe
				src={serveUrl}
				sandbox="{(allowScripts ?? $settings?.iframeSandboxAllowScripts ?? true)
					? 'allow-scripts'
					: ''}{($settings?.iframeSandboxAllowDownloads ?? true)
					? ' allow-downloads'
					: ''}{($settings?.iframeSandboxAllowForms ?? true)
					? ' allow-forms'
					: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}"
				class="w-full h-full border-none bg-white"
				title={$i18n.t('HTML Preview')}
			/>
		{:else if isHtml && !showRaw}
			{#if overlay}
				<div class="absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}
			<iframe
				srcdoc={injectCsp(fileContent, $config?.ui?.iframe_csp ?? '')}
				sandbox="{(allowScripts ?? $settings?.iframeSandboxAllowScripts ?? true)
					? 'allow-scripts'
					: ''}{($settings?.iframeSandboxAllowDownloads ?? true)
					? ' allow-downloads'
					: ''}{($settings?.iframeSandboxAllowForms ?? true)
					? ' allow-forms'
					: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}"
				class="w-full h-full border-none bg-white"
				title={$i18n.t('HTML Preview')}
			/>
		{:else if isMarkdown && !showRaw && onSave && !readOnly}
			{#key selectedFile}
				<MarkdownFileEditor
					bind:this={markdownEditorRef}
					bind:value={codeValue}
					path={selectedFile ?? ''}
					{baseUrl}
					{apiKey}
					{chatId}
					{readOnly}
					onSave={readOnly ? null : saveCodeFile}
				/>
			{/key}
		{:else if isMarkdown && !showRaw}
			{#key selectedFile}
				<MarkdownDocument
					content={codeValue}
					id={`file-${selectedFile}`}
					path={selectedFile ?? ''}
					{baseUrl}
					{apiKey}
					{chatId}
					{resourceVersion}
					{onLocalLink}
				/>
			{/key}
		{:else if isCsv && !showRaw && csvRows.length > 0}
			<div class="absolute inset-0 overflow-auto px-3 pb-3">
				<table class="csv-table text-xs font-mono border-collapse">
					<thead>
						<tr>
							<th class="csv-row-num">#</th>
							{#each csvHeader as cell}
								<th>{cell}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each csvBody as row, i}
							<tr>
								<td class="csv-row-num">{i + 1}</td>
								{#each row as cell}
									<td>{cell}</td>
								{/each}
								<!-- Pad missing columns -->
								{#each Array(Math.max(0, csvHeader.length - row.length)) as _}
									<td></td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else if isNotebook && !showRaw && parsedNotebook}
			<div class="overflow-auto h-full">
				<NotebookView
					notebook={parsedNotebook}
					filePath={selectedFile ?? ''}
					{baseUrl}
					{apiKey}
					{readOnly}
				/>
			</div>
		{:else if isJson && !showRaw && parsedJson !== undefined}
			<div class="overflow-auto h-full">
				<JsonTreeView data={parsedJson} />
			</div>
		{:else if isSvg && !showRaw && fileContent}
			{#key selectedFile}
				<PanzoomContainer
					bind:this={panzoomRef}
					bind:zoomLevel={imageZoomLevel}
					className="svg-preview w-full h-full flex items-center justify-center p-3"
					options={{ zoomDoubleClickSpeed: 1 }}
				>
					{@html sanitizeSvg(fileContent)}
				</PanzoomContainer>
			{/key}
		{:else}
			<div class="absolute inset-0">
				<FileCodeEditor
					{gitBaseContent}
					readOnly={readOnly || !onSave}
					bind:this={fileCodeEditorRef}
					bind:value={codeValue}
					filePath={selectedFile}
					onSave={readOnly ? null : saveCodeFile}
				/>
			</div>
		{/if}
	{:else}
		<div class="flex h-full items-center justify-center p-4 text-center text-xs text-gray-400">
			{$i18n.t('Could not read file.')}
		</div>
	{/if}

	{#if !fileLoading && (fileImageUrl !== null || svgPreview)}
		<div
			class="absolute bottom-3 left-1/2 z-10 flex -translate-x-1/2 items-center gap-0.5 rounded-lg border border-gray-200/60 bg-white/90 px-1 py-0.5 shadow-lg backdrop-blur-sm dark:border-gray-700/60 dark:bg-gray-850/90"
		>
			<!-- Pinch covers in/out on coarse pointers; reset has no gesture, so it stays -->
			<button
				type="button"
				class="inline-flex h-7 min-w-7 shrink-0 items-center justify-center rounded-md p-1.5 text-gray-500 transition hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 pointer-coarse:hidden"
				on:click={() => panzoomRef?.zoomOut()}
				aria-label={$i18n.t('Zoom out')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M4 10a.75.75 0 0 1 .75-.75h10.5a.75.75 0 0 1 0 1.5H4.75A.75.75 0 0 1 4 10Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<button
				type="button"
				class="h-7 min-w-12 shrink-0 rounded-md px-1.5 py-1 text-center text-[0.6875rem] font-normal tabular-nums text-gray-500 transition hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
				on:click={() => panzoomRef?.reset()}
				aria-label={$i18n.t('Reset zoom')}
			>
				{Math.round(imageZoomLevel * 100)}%
			</button>
			<button
				type="button"
				class="inline-flex h-7 min-w-7 shrink-0 items-center justify-center rounded-md p-1.5 text-gray-500 transition hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800 pointer-coarse:hidden"
				on:click={() => panzoomRef?.zoomIn()}
				aria-label={$i18n.t('Zoom in')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
					/>
				</svg>
			</button>
		</div>
	{/if}
</div>

<style>
	.csv-table {
		font-size: 0.7rem;
		line-height: 1.4;
	}
	.csv-table th,
	.csv-table td {
		padding: 0.25rem 0.5rem;
		text-align: left;
		white-space: nowrap;
		border: 1px solid rgba(128, 128, 128, 0.15);
	}
	.csv-table thead th {
		position: sticky;
		top: 0;
		background: rgba(243, 244, 246, 0.95);
		backdrop-filter: blur(4px);
		font-weight: 600;
		color: #374151;
		border-bottom: 2px solid rgba(128, 128, 128, 0.25);
		z-index: 1;
	}
	:global(.dark) .csv-table thead th {
		background: rgba(31, 41, 55, 0.95);
		color: #d1d5db;
	}
	.csv-table tbody tr:nth-child(even) {
		background: rgba(128, 128, 128, 0.04);
	}
	.csv-table tbody tr:hover {
		background: rgba(59, 130, 246, 0.06);
	}
	:global(.dark) .csv-table tbody tr:hover {
		background: rgba(59, 130, 246, 0.1);
	}
	.csv-table td {
		color: #374151;
	}
	:global(.dark) .csv-table td {
		color: #d1d5db;
	}
	.csv-row-num {
		color: #9ca3af;
		font-size: 0.6rem;
		text-align: right !important;
		user-select: none;
		width: 1px;
		padding-right: 0.375rem !important;
	}
	:global(.dark) .csv-row-num {
		color: #6b7280;
	}
	/* DOCX / generic office styles */
	:global(.office-preview img) {
		max-width: 100%;
		height: auto;
	}
	:global(.office-preview h1) {
		font-size: 1.5rem;
		font-weight: 700;
		margin: 0.75em 0 0.5em;
	}
	:global(.office-preview h2) {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0.75em 0 0.5em;
	}
	:global(.office-preview h3) {
		font-size: 1.1rem;
		font-weight: 600;
		margin: 0.5em 0 0.25em;
	}
	:global(.office-preview p) {
		margin: 0.25em 0;
	}
	:global(.office-preview ul),
	:global(.office-preview ol) {
		padding-left: 1.5em;
		margin: 0.5em 0;
	}
</style>
