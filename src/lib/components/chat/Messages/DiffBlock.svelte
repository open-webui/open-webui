<script lang="ts">
	import { parseDiffRows } from './diff';

	export let code = '';
	$: rows = parseDiffRows(code);
	$: showNumbers = rows.some((row) => row.oldNumber !== null || row.newNumber !== null);
	$: gutterWidth = `${rows.reduce((width, row) => Math.max(width, String(Math.max(row.oldNumber ?? 0, row.newNumber ?? 0)).length + 1), 3)}ch`;
</script>

<div class="diff-block text-sm" dir="ltr" style:--diff-gutter-width={gutterWidth}>
	<pre><code
			>{#each rows as row, index}<span class="diff-line {row.type}" class:numbered={showNumbers}
					>{#if showNumbers}<span
							class="line-number old-number"
							data-line-number={row.oldNumber ?? ''}
							aria-hidden="true"></span><span
							class="line-number new-number"
							data-line-number={row.newNumber ?? ''}
							aria-hidden="true"></span>{/if}<span class="line-prefix">{row.prefix}</span><span
						class="line-content"
						>{#each row.segments as segment}<span class:changed={segment.changed}
								>{segment.text}</span
							>{/each}{index < rows.length - 1 ? '\n' : ''}</span
					></span
				>{/each}</code
		></pre>
</div>

<style>
	.diff-block {
		overflow-x: auto;
		background: #ffffff;
		color: #24292f;
	}

	pre {
		margin: 0;
		padding: 0.5rem 0;
		min-width: 100%;
		width: max-content;
		border-radius: 0;
		background: transparent;
		color: inherit;
		font-size: inherit;
		line-height: 1.6;
		tab-size: 4;
	}

	code {
		display: block;
		padding: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		font-family: var(--font-mono, ui-monospace, monospace);
		font-weight: 400;
		white-space: pre;
	}

	.diff-line {
		display: grid;
		grid-template-columns: 1.75rem minmax(0, 1fr);
		min-height: 1.6em;
	}

	.diff-line.numbered {
		grid-template-columns: var(--diff-gutter-width) var(--diff-gutter-width) 1.75rem minmax(0, 1fr);
	}

	.line-number {
		padding: 0 0.5ch;
		text-align: right;
		color: #6e7781;
		border-inline-end: 1px solid #80808020;
		user-select: none;
	}

	.line-number::before {
		content: attr(data-line-number);
	}

	.line-prefix {
		text-align: center;
		font-weight: 700;
	}

	.line-content {
		padding: 0 1rem 0 0.25rem;
	}

	.addition {
		background: #dafbe1;
		color: #116329;
		box-shadow: inset 3px 0 0 #2da44e;
	}

	.deletion {
		background: #ffebe9;
		color: #a40e26;
		background-image: repeating-linear-gradient(
			-45deg,
			#cf222e 0,
			#cf222e 1px,
			transparent 1px,
			transparent 3px
		);
		background-position: left top;
		background-repeat: repeat-y;
		background-size: 3px 3px;
	}

	.hunk {
		background: #ddf4ff;
		color: #0550ae;
	}

	.file {
		background: #f6f8fa;
		color: #57606a;
		font-weight: 600;
	}

	.meta {
		color: #6e7781;
		font-style: italic;
	}

	:global(.dark) .diff-block {
		background: #0d1117;
		color: #c9d1d9;
	}

	:global(.dark) .addition {
		background: #12261e;
		color: #aff5b4;
		box-shadow: inset 3px 0 0 #3fb950;
	}

	:global(.dark) .deletion {
		background: #2d161b;
		color: #ffdcd7;
		background-image: repeating-linear-gradient(
			-45deg,
			#f85149 0,
			#f85149 1px,
			transparent 1px,
			transparent 3px
		);
		background-position: left top;
		background-repeat: repeat-y;
		background-size: 3px 3px;
	}

	:global(.dark) .hunk {
		background: #121f33;
		color: #79c0ff;
	}

	:global(.dark) .file {
		background: #161b22;
		color: #8b949e;
	}

	:global(.dark) .meta {
		color: #8b949e;
	}
	.changed {
		border-radius: 2px;
		font-weight: 700;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}

	.addition .changed {
		background: #16a34a40;
		box-shadow: inset 0 -2px 0 #15803d80;
	}

	.deletion .changed {
		background: #dc262630;
		box-shadow: inset 0 -2px 0 #b91c1c60;
	}

	:global(.dark) .addition .changed {
		background: #22c55e50;
		box-shadow: inset 0 -2px 0 #86efac80;
	}

	:global(.dark) .deletion .changed {
		background: #f8717150;
		box-shadow: inset 0 -2px 0 #fca5a580;
	}

	:global(.dark) .line-number {
		color: #8b949e;
	}
</style>
