<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { settings, config } from '$lib/stores';
	import { injectCsp } from '$lib/utils/csp';
	import { isCodeFile } from '$lib/utils/codeHighlight';
	import { initMermaid, renderMermaidDiagram } from '$lib/utils';
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

	const i18n = getContext('i18n');

	export let selectedFile: string | null = null;
	export let fileLoading = false;
	export let fileImageUrl: string | null = null;
	export let fileVideoUrl: string | null = null;
	export let fileAudioUrl: string | null = null;
	export let filePdfData: ArrayBuffer | null = null;
	export let fileSqliteData: ArrayBuffer | null = null;
	export let fileDocxData: ArrayBuffer | null = null;
	export let fileContent: string | null = null;

	// Terminal connection for notebook execution
	export let baseUrl: string = '';
	export let apiKey: string = '';

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

	export let onSave: ((content: string) => Promise<void>) | null = null;
	export let searchTarget: {
		line: number;
		column: number;
		length: number;
		requestId: number;
	} | null = null;

	export let editing = false;
	let editContent = '';
	export let saving = false;
	let editTextarea: HTMLTextAreaElement;

	// Reset edit state when switching files
	$: (selectedFile, resetEdit());

	const resetEdit = () => {
		editing = false;
		editContent = '';
		saving = false;
	};

	export const startEdit = async () => {
		if (readOnly) return;
		editContent = fileContent ?? '';
		editing = true;
		showRaw = true;
		await tick();
		editTextarea?.focus();
	};

	export const saveEdit = async () => {
		if (!onSave || readOnly) return;
		saving = true;
		await onSave(editContent);
		saving = false;
		editing = false;
	};

	export const cancelEdit = () => {
		editing = false;
		editContent = '';
	};

	/** Save code file directly from CodeMirror */
	export const saveCodeFile = async () => {
		if (!onSave || readOnly) return;
		saving = true;
		const content = fileCodeEditorRef?.getValue() ?? '';
		await onSave(content);
		saving = false;
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
	$: isCode = isCodeFile(selectedFile);
	$: csvDelimiter = getExt(selectedFile) === 'tsv' ? '\t' : ',';
	$: isPptx = getExt(selectedFile) === 'pptx';

	// For HTML files on system terminals (proxy URL), use path-based serving
	// so the iframe can resolve relative CSS/JS/image references via cookie auth.
	$: serveUrl =
		isHtml && selectedFile && baseUrl && baseUrl.includes('/api/v1/terminals/')
			? `${baseUrl}/files/serve/${selectedFile.replace(/^\//, '')}`
			: null;
	$: renderedHtml =
		isMarkdown && fileContent
			? DOMPurify.sanitize(marked.parse(fileContent, { async: false }) as string)
			: '';

	let markdownEl: HTMLDivElement;
	let mermaidInstance: any = null;

	const renderMermaidBlocks = async (el: HTMLDivElement) => {
		if (!el) return;
		const codeEls = el.querySelectorAll('code.language-mermaid');
		if (codeEls.length === 0) return;

		if (!mermaidInstance) {
			mermaidInstance = await initMermaid();
		}

		for (const codeEl of codeEls) {
			const pre = codeEl.parentElement;
			if (!pre || pre.tagName !== 'PRE' || pre.dataset.mermaidRendered) continue;
			pre.dataset.mermaidRendered = 'true';

			try {
				const svg = await renderMermaidDiagram(mermaidInstance, codeEl.textContent ?? '');
				if (svg) {
					const wrapper = document.createElement('div');
					wrapper.className = 'mermaid-diagram flex justify-center py-2';
					wrapper.innerHTML = svg;
					pre.replaceWith(wrapper);
				}
			} catch (e) {
				console.error('Mermaid render error:', e);
			}
		}
	};

	$: if (renderedHtml && markdownEl) {
		tick().then(() => renderMermaidBlocks(markdownEl));
	}

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

	// ── Shiki code highlighting (SVG only) ──────────────────────────────
	let highlightedHtml: string | null = null;
	let highlightingFile: string | null = null;

	$: if (isSvg && fileContent !== null && selectedFile) {
		const currentFile = selectedFile;
		highlightingFile = currentFile;
		import('shiki')
			.then(({ codeToHtml }) =>
				codeToHtml(fileContent!, {
					lang: 'xml',
					themes: { light: 'github-light', dark: 'github-dark' },
					defaultColor: 'light'
				})
			)
			.then((html) => {
				if (highlightingFile === currentFile) highlightedHtml = html;
			})
			.catch(() => {
				if (highlightingFile === currentFile) highlightedHtml = null;
			});
	} else {
		highlightedHtml = null;
	}

	// ── JSON parsing ────────────────────────────────────────────────────
	let parsedJson: unknown = undefined;
	let jsonError: string | null = null;

	$: if (isJson && fileContent !== null) {
		try {
			parsedJson = JSON.parse(fileContent);
			jsonError = null;
		} catch (e) {
			parsedJson = undefined;
			jsonError = e instanceof Error ? e.message : 'Invalid JSON';
		}
	} else {
		parsedJson = undefined;
		jsonError = null;
	}

	// ── Notebook parsing ─────────────────────────────────────────────────
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
	$: if (fileContent !== null && fileContent.trim() === '' && (isMarkdown || isCsv || isJson)) {
		showRaw = true;
	}

	let panzoomRef: PanzoomContainer;
	let pptxPreviewRef: PptxPreview;
	let imageZoomLevel = 1;
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
	fileDocxData !== null ||
	filePdfData !== null ||
	(fileOfficeSlides !== null && fileOfficeSlides.length > 0)
		? 'overflow-hidden'
		: 'overflow-y-auto'} min-h-0 min-w-0 relative h-full"
>
	<!-- File preview -->
	{#if fileLoading}
		<div class="flex items-center justify-center h-full"><Spinner className="size-4" /></div>
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
			<video src={fileVideoUrl} controls class="max-w-full max-h-full">
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
	{:else if fileSqliteData !== null}
		<SqliteView data={fileSqliteData} />
	{:else if fileDocxData !== null}
		<DocxPreview data={fileDocxData} {targetPage} className="w-full h-full" />
	{:else if fileOfficeHtml !== null}
		<div class="flex flex-col h-full">
			<div class="office-preview overflow-auto flex-1 min-h-0">
				{@html fileOfficeHtml}
			</div>
			{#if excelSheetNames.length > 1}
				<div
					class="flex items-center gap-1 py-1.5 px-3 border-t border-gray-100 dark:border-gray-800 overflow-x-auto"
				>
					{#each excelSheetNames as sheet}
						<button
							class="shrink-0 px-3 py-1 text-xs rounded-md transition-colors
								{selectedExcelSheet === sheet
								? 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 font-normal'
								: 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
							on:click={() => onSheetChange?.(sheet)}
						>
							{sheet}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{:else if fileOfficeSlides !== null && fileOfficeSlides.length > 0}
		<PptxPreview
			bind:this={pptxPreviewRef}
			slides={fileOfficeSlides}
			bind:currentSlide
			{targetPage}
			className="w-full h-full"
		/>
	{:else if fileContent !== null}
		{#if searchTarget}
			<div class="absolute inset-0">
				<FileCodeEditor
					bind:this={fileCodeEditorRef}
					value={fileContent ?? ''}
					filePath={selectedFile}
					onSave={readOnly ? null : onSave}
					{searchTarget}
				/>
			</div>
		{:else if isHtml && !showRaw && serveUrl}
			{#if overlay}
				<div class="absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}
			<iframe
				src={serveUrl}
				sandbox="{($settings?.iframeSandboxAllowScripts ?? true)
					? 'allow-scripts'
					: ''}{($settings?.iframeSandboxAllowDownloads ?? true)
					? ' allow-downloads'
					: ''}{($settings?.iframeSandboxAllowForms ?? true)
					? ' allow-forms'
					: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}"
				class="w-full h-full border-none bg-white"
				title="HTML Preview"
			/>
		{:else if isHtml && !showRaw}
			{#if overlay}
				<div class="absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}
			<iframe
				srcdoc={injectCsp(fileContent, $config?.ui?.iframe_csp ?? '')}
				sandbox="{($settings?.iframeSandboxAllowScripts ?? true)
					? 'allow-scripts'
					: ''}{($settings?.iframeSandboxAllowDownloads ?? true)
					? ' allow-downloads'
					: ''}{($settings?.iframeSandboxAllowForms ?? true)
					? ' allow-forms'
					: ''}{($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}"
				class="w-full h-full border-none bg-white"
				title="HTML Preview"
			/>
		{:else if isHtml && showRaw}
			<div class="absolute inset-0">
				<FileCodeEditor
					bind:this={fileCodeEditorRef}
					value={fileContent ?? ''}
					filePath={selectedFile}
					onSave={readOnly ? null : onSave}
				/>
			</div>
		{:else if isMarkdown && !showRaw}
			<div bind:this={markdownEl} class="prose dark:prose-invert max-w-full text-sm p-3">
				{@html renderedHtml}
			</div>
		{:else if isMarkdown && showRaw}
			<div class="absolute inset-0">
				<FileCodeEditor
					bind:this={fileCodeEditorRef}
					value={fileContent ?? ''}
					filePath={selectedFile}
					onSave={readOnly ? null : onSave}
				/>
			</div>
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
				<NotebookView notebook={parsedNotebook} filePath={selectedFile ?? ''} {baseUrl} {apiKey} />
			</div>
		{:else if isJson && !showRaw && parsedJson !== undefined}
			<div class="overflow-auto h-full">
				<JsonTreeView data={parsedJson} />
			</div>
		{:else if isJson && !showRaw && jsonError}
			<div class="p-3 text-xs">
				<div class="text-red-500 mb-2">JSON parse error: {jsonError}</div>
				<pre
					class="text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all leading-relaxed">{fileContent}</pre>
			</div>
		{:else if isSvg && !showRaw && fileContent}
			<div class="svg-preview w-full h-full flex items-center justify-center overflow-auto p-3">
				{@html DOMPurify.sanitize(fileContent, {
					USE_PROFILES: { svg: true, svgFilters: true },
					ADD_TAGS: ['use']
				})}
			</div>
		{:else if isCode && !showRaw}
			<div class="absolute inset-0">
				<FileCodeEditor
					bind:this={fileCodeEditorRef}
					value={fileContent ?? ''}
					filePath={selectedFile}
					onSave={readOnly ? null : onSave}
				/>
			</div>
		{:else if isSvg && highlightedHtml && !showRaw}
			<div class="shiki-preview overflow-auto h-full text-xs">
				{@html highlightedHtml}
			</div>
		{:else if editing}
			<textarea
				bind:this={editTextarea}
				bind:value={editContent}
				class="w-full h-full text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre break-all leading-relaxed p-3 bg-transparent border-none outline-none resize-none"
				spellcheck="false"
			/>
		{:else}
			<pre
				class="text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all leading-relaxed p-3">{fileContent}</pre>
		{/if}
	{:else}
		<div class="text-xs text-gray-400 text-center pt-8">
			{$i18n.t('Could not read file.')}
		</div>
	{/if}

	{#if !fileLoading && fileImageUrl !== null}
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
	/* ── Office preview styles ──────────────────────────────────────── */
	:global(.office-preview) {
		font-size: 0.875rem;
		line-height: 1.6;
		color: #1f2937;
		background: #fff;
		border-radius: 0.25rem;
	}
	:global(.dark .office-preview) {
		color: #e5e7eb;
		background: #1a1a2e;
	}
	:global(.office-preview table) {
		border-collapse: collapse;
		font-size: 0.75rem;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, monospace;
		line-height: 1.3;
	}
	:global(.office-preview table td),
	:global(.office-preview table th) {
		border: 1px solid rgba(200, 200, 200, 0.5);
		padding: 0.25rem 0.625rem;
		text-align: left;
		white-space: nowrap;
		user-select: text;
		cursor: cell;
		max-width: 18.75rem;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	:global(.dark .office-preview table td),
	:global(.dark .office-preview table th) {
		border-color: rgba(80, 80, 80, 0.5);
	}
	/* Column letter headers */
	:global(.office-preview table th.excel-col-hdr) {
		position: sticky;
		top: 0;
		z-index: 2;
		background: #f0f0f0;
		color: #666;
		font-weight: 500;
		font-size: 0.65rem;
		text-align: center;
		padding: 0.1875rem 0.625rem;
		border-bottom: 2px solid rgba(180, 180, 180, 0.6);
	}
	:global(.dark .office-preview table th.excel-col-hdr) {
		background: #2a2a3e;
		color: #888;
		border-bottom-color: rgba(100, 100, 100, 0.6);
	}
	/* Row number cells */
	:global(.office-preview .excel-row-num) {
		position: sticky;
		left: 0;
		z-index: 1;
		background: #f0f0f0;
		color: #999;
		font-size: 0.6rem;
		text-align: right !important;
		padding: 0.25rem 0.5rem 0.25rem 0.25rem !important;
		user-select: none;
		width: 1px;
		white-space: nowrap;
		border-right: 2px solid rgba(180, 180, 180, 0.6) !important;
	}
	:global(.dark .office-preview .excel-row-num) {
		background: #2a2a3e;
		color: #666;
		border-right-color: rgba(100, 100, 100, 0.6) !important;
	}
	/* Corner cell (intersection of row nums and col headers) */
	:global(.office-preview thead .excel-row-num) {
		z-index: 3;
	}
	/* Number cells right-aligned */
	:global(.office-preview .excel-num) {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	/* Row hover and selection */
	:global(.office-preview table tbody tr:nth-child(even) td:not(.excel-row-num)) {
		background: rgba(0, 0, 0, 0.015);
	}
	:global(.dark .office-preview table tbody tr:nth-child(even) td:not(.excel-row-num)) {
		background: rgba(255, 255, 255, 0.02);
	}
	:global(.office-preview table tbody tr:hover td:not(.excel-row-num)) {
		background: rgba(59, 130, 246, 0.06);
	}
	:global(.dark .office-preview table tbody tr:hover td:not(.excel-row-num)) {
		background: rgba(59, 130, 246, 0.1);
	}
	:global(.office-preview table td:focus) {
		outline: 2px solid rgba(59, 130, 246, 0.5);
		outline-offset: -2px;
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
	/* ── Shiki code highlighting ─────────────────────────────────── */
	.shiki-preview :global(pre.shiki) {
		margin: 0;
		padding: 0.75rem 1rem;
		font-size: 0.75rem;
		line-height: 1.6;
		border-radius: 0;
		overflow-x: auto;
		min-height: 100%;
	}
	.shiki-preview :global(pre.shiki code) {
		counter-reset: line;
	}
	.shiki-preview :global(pre.shiki code > .line) {
		counter-increment: line;
		display: inline-block;
		width: 100%;
		white-space: pre;
	}
	.shiki-preview :global(pre.shiki code > .line::before) {
		content: counter(line);
		display: inline-block;
		width: 2.5em;
		text-align: right;
		margin-right: 1em;
		color: #9ca3af;
		user-select: none;
		font-size: 0.65rem;
	}
	:global(.dark) .shiki-preview :global(pre.shiki code > .line::before) {
		color: #4b5563;
	}
	/* Shiki dual-theme: swap CSS variables in dark mode */
	:global(.dark) .shiki-preview :global(.shiki),
	:global(.dark) .shiki-preview :global(.shiki span) {
		color: var(--shiki-dark) !important;
		background-color: var(--shiki-dark-bg) !important;
		font-style: var(--shiki-dark-font-style) !important;
		font-weight: var(--shiki-dark-font-weight) !important;
		text-decoration: var(--shiki-dark-text-decoration) !important;
	}
</style>
