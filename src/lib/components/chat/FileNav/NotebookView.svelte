<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { highlightCode } from '$lib/utils/codeHighlight';
	import {
		createNotebookSession,
		executeNotebookCell,
		stopNotebookSession
	} from '$lib/apis/terminal';
	import Spinner from '../../common/Spinner.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import CellEditor from './CellEditor.svelte';

	const i18n = getContext('i18n');

	export let notebook: Record<string, unknown>;
	export let filePath: string = '';
	export let baseUrl: string = '';
	export let apiKey: string = '';

	interface NotebookCell {
		cell_type: 'markdown' | 'code' | 'raw';
		source: string[] | string;
		outputs?: NotebookOutput[];
		execution_count?: number | null;
	}

	interface NotebookOutput {
		output_type: 'stream' | 'execute_result' | 'display_data' | 'error';
		text?: string[] | string;
		data?: Record<string, string[] | string>;
		name?: string;
		ename?: string;
		evalue?: string;
		traceback?: string[];
	}

	$: cells = (notebook?.cells as NotebookCell[]) ?? [];
	$: lang = (notebook?.metadata as Record<string, unknown>)?.kernelspec
		? ((notebook.metadata as Record<string, Record<string, string>>).kernelspec?.language ??
			'python')
		: 'python';

	const toStr = (s: string[] | string | undefined): string =>
		Array.isArray(s) ? s.join('') : (s ?? '');

	// ── Syntax highlighting ──────────────────────────────────────────────
	let highlightedCells: Record<number, string> = {};

	const highlightCell = async (index: number, code: string, language: string) => {
		try {
			const { codeToHtml } = await import('shiki');
			const html = await codeToHtml(code, {
				lang: language,
				themes: { light: 'github-light', dark: 'github-dark' },
				defaultColor: 'light'
			});
			highlightedCells[index] = html;
			highlightedCells = highlightedCells;
		} catch {
			// fallback handled in template
		}
	};

	$: {
		highlightedCells = {};
		cells.forEach((cell, i) => {
			if (cell.cell_type === 'code' && !editingCell[i]) {
				highlightCell(i, toStr(cell.source), lang);
			}
		});
	}

	// ── Markdown / output helpers ────────────────────────────────────────
	const renderMarkdown = (src: string): string =>
		DOMPurify.sanitize(marked.parse(src, { async: false }) as string);

	const stripAnsi = (s: string): string => s.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');

	const getOutputImages = (output: NotebookOutput): string[] => {
		if (!output.data) return [];
		const images: string[] = [];
		for (const [mime, content] of Object.entries(output.data)) {
			if (mime.startsWith('image/')) {
				const raw = Array.isArray(content) ? content.join('') : content;
				images.push(raw.startsWith('data:') ? raw : `data:${mime};base64,${raw}`);
			}
		}
		return images;
	};

	const getOutputHtml = (output: NotebookOutput): string | null => {
		if (!output.data?.['text/html']) return null;
		return DOMPurify.sanitize(toStr(output.data['text/html']));
	};

	const getOutputText = (output: NotebookOutput): string | null => {
		if (output.output_type === 'stream') return toStr(output.text);
		if (output.data?.['text/plain']) return toStr(output.data['text/plain']);
		return null;
	};

	// ── Cell editing ─────────────────────────────────────────────────────
	let editingCell: Record<number, boolean> = {};
	let editedSources: Record<number, string> = {};

	const startEditing = (index: number) => {
		editingCell[index] = true;
		editedSources[index] = toStr(cells[index].source);
		editingCell = editingCell;
	};

	const cancelEditing = (index: number) => {
		delete editingCell[index];
		delete editedSources[index];
		editingCell = editingCell;
		highlightCell(index, toStr(cells[index].source), lang);
	};

	// ── Session / kernel ─────────────────────────────────────────────────
	let sessionId: string | null = null;
	let kernelReady = false;
	let kernelStarting = false;
	let kernelError: string | null = null;
	let runningCell: number | null = null;
	let runAllActive = false;

	const canExecute = baseUrl && apiKey && filePath;

	const startSession = async (): Promise<boolean> => {
		if (!baseUrl || !apiKey || !filePath) return false;
		kernelStarting = true;
		kernelError = null;

		const result = await createNotebookSession(baseUrl, apiKey, filePath);

		if ('error' in result) {
			kernelStarting = false;
			kernelError = result.error;
			return false;
		}

		sessionId = result.id;
		kernelReady = true;
		kernelStarting = false;
		return true;
	};

	const stopSession = async () => {
		if (sessionId && baseUrl && apiKey) {
			await stopNotebookSession(baseUrl, apiKey, sessionId);
		}
		sessionId = null;
		kernelReady = false;
	};

	const runCell = async (index: number) => {
		if (runningCell !== null) return;
		if (!kernelReady && !(await startSession())) return;

		runningCell = index;
		const source = editedSources[index] ?? toStr(cells[index].source);

		// Apply edits
		if (editedSources[index] !== undefined) {
			cells[index].source = editedSources[index];
			delete editingCell[index];
			delete editedSources[index];
			editingCell = editingCell;
		}

		const result = await executeNotebookCell(baseUrl, apiKey, sessionId!, index, source);

		if ('error' in result) {
			cells[index].outputs = [
				{
					output_type: 'error',
					ename: 'ExecutionError',
					evalue: result.error,
					traceback: [result.error]
				}
			];
		} else {
			cells[index].outputs = result.outputs;
			if (result.execution_count !== undefined) {
				cells[index].execution_count = result.execution_count;
			}
		}

		cells = cells;
		runningCell = null;
		highlightCell(index, toStr(cells[index].source), lang);
	};

	const runAll = async () => {
		if (runAllActive) return;
		runAllActive = true;
		for (let i = 0; i < cells.length; i++) {
			if (cells[i].cell_type === 'code') {
				await runCell(i);
			}
		}
		runAllActive = false;
	};

	const autoResize = (e: Event) => {
		const ta = e.target as HTMLTextAreaElement;
		ta.style.height = 'auto';
		ta.style.height = ta.scrollHeight + 'px';
	};

	onDestroy(() => {
		if (sessionId) stopSession();
	});
</script>

<div class="notebook-view">
	<!-- Toolbar -->
	{#if baseUrl && apiKey && filePath}
		<div class="nb-toolbar flex items-center gap-1 px-2 py-0.5">
			<button
				class="nb-btn text-[0.6rem]"
				on:click={runAll}
				disabled={runAllActive || runningCell !== null}
			>
				{$i18n.t('Run All')}
			</button>
			{#if kernelReady}
				<button
					class="nb-btn text-[0.6rem]"
					on:click={async () => {
						await stopSession();
						await startSession();
					}}
				>
					{$i18n.t('Restart')}
				</button>
				<button class="nb-btn text-[0.6rem]" on:click={stopSession}>
					{$i18n.t('Stop')}
				</button>
			{/if}

			<div class="flex-1"></div>

			<div class="flex items-center select-none">
				{#if kernelStarting}
					<Tooltip content={$i18n.t('Starting kernel...')} placement="bottom"
						><Spinner className="size-2" /></Tooltip
					>
				{:else if runningCell !== null}
					<Tooltip content={$i18n.t('Running')} placement="bottom"
						><Spinner className="size-2" /></Tooltip
					>
				{:else if kernelReady}
					<Tooltip content="Jupyter" placement="bottom"
						><span class="size-1.5 rounded-full bg-green-500 inline-block"></span></Tooltip
					>
				{:else}
					<Tooltip content={$i18n.t('No kernel')} placement="bottom"
						><span class="size-1.5 rounded-full bg-gray-400 dark:bg-gray-600 inline-block"
						></span></Tooltip
					>
				{/if}
			</div>
		</div>

		{#if kernelError}
			<div
				class="px-2 py-1 text-[0.65rem] text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 whitespace-pre-wrap font-mono"
			>
				{kernelError}
			</div>
		{/if}
	{/if}

	<!-- Cells -->
	{#each cells as cell, i}
		<div class="nb-cell nb-cell-{cell.cell_type}">
			{#if cell.cell_type === 'markdown'}
				{#if editingCell[i]}
					<textarea
						class="nb-edit-textarea text-sm"
						bind:value={editedSources[i]}
						on:input={autoResize}
						on:blur={() => cancelEditing(i)}
						on:keydown={(e) => {
							if (e.key === 'Escape') cancelEditing(i);
						}}
					></textarea>
				{:else}
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<div
						class="nb-markdown prose dark:prose-invert max-w-full text-sm cursor-text"
						role="textbox"
						tabindex="0"
						on:dblclick={() => startEditing(i)}
					>
						{@html renderMarkdown(toStr(cell.source))}
					</div>
				{/if}
			{:else if cell.cell_type === 'code'}
				<div class="nb-code-wrap">
					<div class="nb-cell-gutter">
						{#if runningCell === i}
							<div class="nb-cell-label"><Spinner className="size-3" /></div>
						{:else if baseUrl && apiKey && filePath}
							<button
								class="nb-run-btn"
								on:click={() => runCell(i)}
								disabled={runningCell !== null}
								title="Run cell (⌘+Enter)"
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="2"
									stroke="currentColor"
									class="size-3"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"
									/>
								</svg>
							</button>
						{/if}
						<div class="nb-cell-label">
							{#if cell.execution_count !== undefined && cell.execution_count !== null}
								[{cell.execution_count}]
							{:else}
								[ ]
							{/if}
						</div>
					</div>
					<div class="nb-code-content">
						{#if editingCell[i]}
							<CellEditor
								value={editedSources[i]}
								{lang}
								on:change={(e) => {
									editedSources[i] = e.detail;
								}}
								on:run={() => runCell(i)}
								on:cancel={() => cancelEditing(i)}
							/>
						{:else}
							<!-- svelte-ignore a11y-click-events-have-key-events -->
							<div
								class="nb-code-source-clickable"
								role="textbox"
								tabindex="0"
								on:dblclick={() => startEditing(i)}
							>
								{#if highlightedCells[i]}
									<div class="nb-code-source shiki-preview">
										{@html highlightedCells[i]}
									</div>
								{:else}
									<pre class="nb-code-source-raw">{toStr(cell.source)}</pre>
								{/if}
							</div>
						{/if}

						{#if cell.outputs && cell.outputs.length > 0}
							<div class="nb-outputs">
								{#each cell.outputs as output}
									{#if output.output_type === 'error'}
										<pre class="nb-error">{stripAnsi(
												(output.traceback ?? []).join('\n') || `${output.ename}: ${output.evalue}`
											)}</pre>
									{:else}
										{@const html = getOutputHtml(output)}
										{@const images = getOutputImages(output)}
										{@const text = getOutputText(output)}
										{#if html}
											<div class="nb-output-html">{@html html}</div>
										{/if}
										{#each images as src}
											<img {src} alt="Output" class="nb-output-img" />
										{/each}
										{#if text}
											<pre class="nb-output-text">{text}</pre>
										{/if}
									{/if}
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{:else if cell.cell_type === 'raw'}
				<pre class="nb-raw">{toStr(cell.source)}</pre>
			{/if}
		</div>
	{/each}
</div>

<style>
	.notebook-view {
		padding: 0;
		font-size: 0.8rem;
	}
	.nb-toolbar {
		position: sticky;
		top: 0;
		z-index: 5;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(4px);
	}
	:global(.dark) .nb-toolbar {
		background: rgba(17, 24, 39, 0.95);
	}
	.nb-btn {
		font-size: 0.6rem;
		padding: 0.15rem 0.35rem;
		border-radius: 0.25rem;
		color: #6b7280;
		transition: all 0.15s;
	}
	.nb-btn:hover:not(:disabled) {
		background: rgba(128, 128, 128, 0.1);
		color: #374151;
	}
	:global(.dark) .nb-btn:hover:not(:disabled) {
		color: #d1d5db;
	}
	.nb-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.nb-cell {
		padding: 0.25rem 0.75rem;
	}
	.nb-cell-markdown {
		padding-top: 0.5rem;
		padding-bottom: 0.5rem;
	}
	.nb-markdown :global(h1) {
		font-size: 1.4rem;
	}
	.nb-markdown :global(h2) {
		font-size: 1.2rem;
	}
	.nb-markdown :global(h3) {
		font-size: 1.05rem;
	}
	.nb-markdown :global(p) {
		margin: 0.4em 0;
	}
	.nb-markdown :global(pre) {
		background: rgba(128, 128, 128, 0.06);
		padding: 0.5rem 0.75rem;
		border-radius: 4px;
		font-size: 0.75rem;
	}
	.nb-code-wrap {
		display: flex;
		gap: 0;
	}
	.nb-cell-gutter {
		flex-shrink: 0;
		width: 2.5rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		padding-top: 0.35rem;
		gap: 0.15rem;
	}
	.nb-cell-label {
		color: #9ca3af;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		font-size: 0.6rem;
		user-select: none;
		text-align: center;
	}
	:global(.dark) .nb-cell-label {
		color: #4b5563;
	}
	.nb-run-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.25rem;
		height: 1.25rem;
		border-radius: 0.25rem;
		color: #9ca3af;
		transition: all 0.15s;
	}
	.nb-run-btn:hover:not(:disabled) {
		color: #059669;
		background: rgba(5, 150, 105, 0.1);
	}
	:global(.dark) .nb-run-btn {
		color: #6b7280;
	}
	:global(.dark) .nb-run-btn:hover:not(:disabled) {
		color: #34d399;
		background: rgba(52, 211, 153, 0.15);
	}
	.nb-run-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}
	.nb-code-content {
		flex: 1;
		min-width: 0;
		border: 1px solid rgba(128, 128, 128, 0.15);
		border-radius: 4px;
		overflow: hidden;
	}
	:global(.dark) .nb-code-content {
		border-color: rgba(128, 128, 128, 0.25);
	}
	.nb-code-source-clickable {
		cursor: text;
	}
	.nb-code-source :global(pre.shiki) {
		margin: 0;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		line-height: 1.5;
		border-radius: 0;
	}
	.nb-code-source :global(pre.shiki code > .line::before) {
		display: none;
	}
	.nb-code-source-raw {
		margin: 0;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		line-height: 1.5;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		background: #f8f8f8;
		color: #1f2937;
	}
	:global(.dark) .nb-code-source-raw {
		background: #161b22;
		color: #e6edf3;
	}
	.nb-code-textarea,
	.nb-edit-textarea {
		width: 100%;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		line-height: 1.5;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		background: #fffef5;
		color: #1f2937;
		border: none;
		outline: none;
		resize: none;
		min-height: 2.5rem;
		overflow: hidden;
	}
	:global(.dark) .nb-code-textarea,
	:global(.dark) .nb-edit-textarea {
		background: #1a1d23;
		color: #e6edf3;
	}
	.nb-edit-textarea {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		font-size: 0.8rem;
		background: transparent;
		padding: 0.5rem 0.75rem;
		border: 1px dashed rgba(128, 128, 128, 0.3);
		border-radius: 4px;
	}
	.nb-outputs {
		border-top: 1px solid rgba(128, 128, 128, 0.15);
	}
	:global(.dark) .nb-outputs {
		border-top-color: rgba(128, 128, 128, 0.25);
	}
	.nb-output-text {
		margin: 0;
		padding: 0.5rem 0.75rem;
		font-size: 0.7rem;
		line-height: 1.5;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		color: #374151;
		white-space: pre-wrap;
		word-break: break-all;
	}
	:global(.dark) .nb-output-text {
		color: #d1d5db;
	}
	.nb-output-img {
		max-width: 100%;
		height: auto;
		padding: 0.5rem 0.75rem;
	}
	.nb-output-html {
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		overflow-x: auto;
	}
	.nb-output-html :global(table) {
		border-collapse: collapse;
		font-size: 0.7rem;
	}
	.nb-output-html :global(td),
	.nb-output-html :global(th) {
		border: 1px solid rgba(128, 128, 128, 0.2);
		padding: 3px 8px;
		text-align: left;
	}
	.nb-output-html :global(th) {
		background: rgba(128, 128, 128, 0.06);
		font-weight: 600;
	}
	.nb-error {
		margin: 0;
		padding: 0.5rem 0.75rem;
		font-size: 0.7rem;
		line-height: 1.5;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		background: rgba(239, 68, 68, 0.05);
		color: #dc2626;
		white-space: pre-wrap;
		word-break: break-all;
	}
	:global(.dark) .nb-error {
		background: rgba(239, 68, 68, 0.1);
		color: #f87171;
	}
	.nb-raw {
		margin: 0;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		line-height: 1.5;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		color: #6b7280;
		white-space: pre-wrap;
	}
	:global(.dark) .nb-code-source :global(.shiki),
	:global(.dark) .nb-code-source :global(.shiki span) {
		color: var(--shiki-dark) !important;
		background-color: var(--shiki-dark-bg) !important;
		font-style: var(--shiki-dark-font-style) !important;
		font-weight: var(--shiki-dark-font-weight) !important;
		text-decoration: var(--shiki-dark-text-decoration) !important;
	}
</style>
