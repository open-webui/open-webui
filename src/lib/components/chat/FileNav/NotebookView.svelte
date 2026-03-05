<script lang="ts">
	import { getContext } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { highlightCode } from '$lib/utils/codeHighlight';

	const i18n = getContext('i18n');

	export let notebook: Record<string, unknown>;

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
		? ((notebook.metadata as Record<string, Record<string, string>>).kernelspec?.language ?? 'python')
		: 'python';

	const toStr = (s: string[] | string | undefined): string =>
		Array.isArray(s) ? s.join('') : s ?? '';

	// Highlight code cells with Shiki
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
			highlightedCells = highlightedCells; // trigger reactivity
		} catch {
			// fallback handled in template
		}
	};

	$: {
		highlightedCells = {};
		cells.forEach((cell, i) => {
			if (cell.cell_type === 'code') {
				highlightCell(i, toStr(cell.source), lang);
			}
		});
	}

	const renderMarkdown = (src: string): string =>
		DOMPurify.sanitize(marked.parse(src, { async: false }) as string);

	const stripAnsi = (s: string): string =>
		s.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');

	const getOutputImages = (output: NotebookOutput): string[] => {
		if (!output.data) return [];
		const images: string[] = [];
		for (const [mime, content] of Object.entries(output.data)) {
			if (mime.startsWith('image/')) {
				const raw = Array.isArray(content) ? content.join('') : content;
				if (raw.startsWith('data:')) {
					images.push(raw);
				} else {
					images.push(`data:${mime};base64,${raw}`);
				}
			}
		}
		return images;
	};

	const getOutputHtml = (output: NotebookOutput): string | null => {
		if (!output.data?.['text/html']) return null;
		const raw = toStr(output.data['text/html']);
		return DOMPurify.sanitize(raw);
	};

	const getOutputText = (output: NotebookOutput): string | null => {
		if (output.output_type === 'stream') return toStr(output.text);
		if (output.data?.['text/plain']) return toStr(output.data['text/plain']);
		return null;
	};
</script>

<div class="notebook-view">
	{#each cells as cell, i}
		<div class="nb-cell nb-cell-{cell.cell_type}">
			{#if cell.cell_type === 'markdown'}
				<div class="nb-markdown prose dark:prose-invert max-w-full text-sm">
					{@html renderMarkdown(toStr(cell.source))}
				</div>
			{:else if cell.cell_type === 'code'}
				<div class="nb-code-wrap">
					<div class="nb-cell-label">
						{#if cell.execution_count !== undefined && cell.execution_count !== null}
							[{cell.execution_count}]
						{:else}
							[ ]
						{/if}
					</div>
					<div class="nb-code-content">
						{#if highlightedCells[i]}
							<div class="nb-code-source shiki-preview">
								{@html highlightedCells[i]}
							</div>
						{:else}
							<pre class="nb-code-source-raw">{toStr(cell.source)}</pre>
						{/if}

						{#if cell.outputs && cell.outputs.length > 0}
							<div class="nb-outputs">
								{#each cell.outputs as output}
									{#if output.output_type === 'error'}
										<pre class="nb-error">{stripAnsi((output.traceback ?? []).join('\n') || `${output.ename}: ${output.evalue}`)}</pre>
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
		padding: 0.5rem 0;
		font-size: 0.8rem;
	}
	.nb-cell {
		padding: 0.25rem 0.75rem;
	}
	.nb-cell-markdown {
		padding-top: 0.5rem;
		padding-bottom: 0.5rem;
	}
	.nb-markdown :global(h1) { font-size: 1.4rem; }
	.nb-markdown :global(h2) { font-size: 1.2rem; }
	.nb-markdown :global(h3) { font-size: 1.05rem; }
	.nb-markdown :global(p) { margin: 0.4em 0; }
	.nb-markdown :global(pre) {
		background: rgba(128, 128, 128, 0.06);
		padding: 0.5rem 0.75rem;
		border-radius: 4px;
		font-size: 0.75rem;
	}
	.nb-code-wrap {
		display: flex;
		gap: 0.5rem;
	}
	.nb-cell-label {
		flex-shrink: 0;
		width: 2.5rem;
		text-align: right;
		color: #9ca3af;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		font-size: 0.65rem;
		padding-top: 0.5rem;
		user-select: none;
	}
	:global(.dark) .nb-cell-label {
		color: #4b5563;
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
	.nb-code-source :global(pre.shiki) {
		margin: 0;
		padding: 0.5rem 0.75rem;
		font-size: 0.75rem;
		line-height: 1.5;
		border-radius: 0;
	}
	/* Remove line numbers for notebook cells */
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
	/* Shiki dark mode for notebook cells */
	:global(.dark) .nb-code-source :global(.shiki),
	:global(.dark) .nb-code-source :global(.shiki span) {
		color: var(--shiki-dark) !important;
		background-color: var(--shiki-dark-bg) !important;
		font-style: var(--shiki-dark-font-style) !important;
		font-weight: var(--shiki-dark-font-weight) !important;
		text-decoration: var(--shiki-dark-text-decoration) !important;
	}
</style>
