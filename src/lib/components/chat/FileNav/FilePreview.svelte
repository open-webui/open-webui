<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import panzoom, { type PanZoom } from 'panzoom';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import Spinner from '../../common/Spinner.svelte';
	import PDFViewer from '../../common/PDFViewer.svelte';

	const i18n = getContext('i18n');

	export let selectedFile: string | null = null;
	export let fileLoading = false;
	export let fileImageUrl: string | null = null;
	export let filePdfData: ArrayBuffer | null = null;
	export let fileContent: string | null = null;

	export let onSave: ((content: string) => Promise<void>) | null = null;

	export let editing = false;
	let editContent = '';
	export let saving = false;
	let editTextarea: HTMLTextAreaElement;

	// Reset edit state when switching files
	$: selectedFile, resetEdit();

	const resetEdit = () => {
		editing = false;
		editContent = '';
		saving = false;
	};

	export const startEdit = async () => {
		editContent = fileContent ?? '';
		editing = true;
		showRaw = true;
		await tick();
		editTextarea?.focus();
	};

	export const saveEdit = async () => {
		if (!onSave) return;
		saving = true;
		await onSave(editContent);
		saving = false;
		editing = false;
	};

	export const cancelEdit = () => {
		editing = false;
		editContent = '';
	};

	$: isTextFile = fileContent !== null && fileImageUrl === null && filePdfData === null;

	const MD_EXTS = new Set(['md', 'markdown', 'mdx']);
	const CSV_EXTS = new Set(['csv', 'tsv']);
	const getExt = (path: string | null) => path?.split('.').pop()?.toLowerCase() ?? '';

	$: isMarkdown = MD_EXTS.has(getExt(selectedFile));
	$: isCsv = CSV_EXTS.has(getExt(selectedFile));
	$: csvDelimiter = getExt(selectedFile) === 'tsv' ? '\t' : ',';
	$: renderedHtml =
		isMarkdown && fileContent
			? DOMPurify.sanitize(marked.parse(fileContent, { async: false }) as string)
			: '';

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

	export let showRaw = false;
	$: selectedFile, (showRaw = false); // reset to preview mode when switching files

	let pzInstance: PanZoom | null = null;

	const initImagePanzoom = (node: HTMLElement) => {
		pzInstance = panzoom(node, {
			bounds: true,
			boundsPadding: 0.1,
			zoomSpeed: 0.065
		});
	};

	export const resetImageView = () => {
		if (pzInstance) {
			pzInstance.moveTo(0, 0);
			pzInstance.zoomAbs(0, 0, 1);
		}
	};

	export const disposePanzoom = () => {
		if (pzInstance) {
			pzInstance.dispose();
			pzInstance = null;
		}
	};

	onDestroy(() => {
		disposePanzoom();
	});
</script>

<div
	class="flex-1 {fileImageUrl !== null || filePdfData !== null
		? 'overflow-hidden'
		: 'overflow-y-auto'} min-h-0 relative h-full"
>
	<!-- File preview -->
	{#if fileLoading}
		<div class="flex items-center justify-center h-full"><Spinner className="size-4" /></div>
	{:else if fileImageUrl !== null}
		<div class="w-full h-full flex items-center justify-center" use:initImagePanzoom>
			<img
				src={fileImageUrl}
				alt={selectedFile?.split('/').pop()}
				class="max-w-full max-h-full object-contain p-3"
				draggable="false"
			/>
		</div>
	{:else if filePdfData !== null}
		<PDFViewer data={filePdfData} className="w-full h-full" />
	{:else if fileContent !== null}
		{#if isMarkdown && !showRaw}
			<div class="prose dark:prose-invert max-w-full text-sm p-3">
				{@html renderedHtml}
			</div>
		{:else if isCsv && !showRaw && csvRows.length > 0}
			<div class="overflow-auto h-full px-3 pb-3">
				<table class="csv-table w-full text-xs font-mono border-collapse">
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
		<div class="text-sm text-gray-400 text-center pt-8">
			{$i18n.t('Could not read file.')}
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
		padding: 4px 8px;
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
		padding-right: 6px !important;
	}
	:global(.dark) .csv-row-num {
		color: #6b7280;
	}
</style>
