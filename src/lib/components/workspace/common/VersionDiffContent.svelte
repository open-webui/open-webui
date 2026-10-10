<script lang="ts">
	import { getContext } from 'svelte';
	import { versionDiffHunks, type VersionDiffLine } from './versionDiff';
	export let code: string;
	export let mode: 'split' | 'unified' = 'split';
	const i18n = getContext<any>('i18n');
	$: hunks = versionDiffHunks(code);
</script>

{#snippet lineText(line: VersionDiffLine | null)}
	<span class="line-content"
		>{#if line}{#each line.segments as segment}<span class:changed={segment.changed}
					>{segment.text}</span
				>{/each}{#if line.noNewline}<span
					class="newline-marker"
					title={$i18n.t('No newline at end of file')}
					aria-label={$i18n.t('No newline at end of file')}>↵</span
				>{/if}{:else}{' '}{/if}</span
	>
{/snippet}

{#snippet cell(line: VersionDiffLine | null, side: 'before' | 'after')}
	<div
		class="diff-cell"
		class:addition={line?.type === 'addition'}
		class:deletion={line?.type === 'deletion'}
		class:empty={!line}
	>
		<span class="line-number" aria-hidden="true"
			>{(side === 'before' ? line?.oldNumber : line?.newNumber) ?? ''}</span
		>
		{@render lineText(line)}
	</div>
{/snippet}

{#snippet unifiedLine(line: VersionDiffLine)}
	<div
		class="diff-cell unified-row"
		class:addition={line.type === 'addition'}
		class:deletion={line.type === 'deletion'}
	>
		<span class="line-number" aria-hidden="true">{line.oldNumber ?? ''}</span>
		<span class="line-number" aria-hidden="true">{line.newNumber ?? ''}</span>
		<span class="select-none text-center" aria-hidden="true"
			>{line.type === 'addition' ? '+' : line.type === 'deletion' ? '−' : ''}</span
		>
		{@render lineText(line)}
	</div>
{/snippet}

<div class="version-diff-content font-mono text-xs leading-5" class:split={mode === 'split'}>
	{#each hunks as hunk, index}
		{#if index > 0 || hunk.beforeStart > 1 || hunk.afterStart > 1}
			<div class="hunk-gap" title={$i18n.t('Unchanged lines omitted')}>···</div>
		{/if}
		{#each hunk.rows as row}
			{#if mode === 'split'}
				<div class="split-row">
					{@render cell(row.before, 'before')}
					{@render cell(row.after, 'after')}
				</div>
			{:else if row.before?.type === 'context'}
				{@render unifiedLine(row.before)}
			{:else}
				{#if row.before}{@render unifiedLine(row.before)}{/if}
				{#if row.after}{@render unifiedLine(row.after)}{/if}
			{/if}
		{/each}
	{/each}
</div>

<style>
	.version-diff-content {
		color: var(--color-gray-700);
	}
	.split-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	}
	.diff-cell {
		display: grid;
		grid-template-columns: 2.5rem minmax(0, 1fr);
		min-width: 0;
		min-height: 1.25rem;
	}
	.diff-cell.unified-row {
		grid-template-columns: 2.5rem 2.5rem 1rem minmax(0, 1fr);
	}
	.split-row > .diff-cell + .diff-cell {
		border-left: 1px solid rgb(0 0 0 / 0.06);
	}
	.line-number {
		padding: 0 0.5rem;
		text-align: right;
		user-select: none;
		color: var(--color-gray-400);
		border-right: 1px solid rgb(0 0 0 / 0.04);
	}
	.line-content {
		padding: 0 0.5rem;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		tab-size: 4;
	}
	.addition {
		background: #dafbe1;
		color: #116329;
	}
	.deletion {
		background: #ffebe9;
		color: #a40e26;
	}
	.empty {
		background: rgb(0 0 0 / 0.025);
	}
	.changed {
		border-radius: 2px;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}
	.addition .changed {
		background: #16a34a35;
	}
	.deletion .changed {
		background: #dc262630;
	}
	.newline-marker {
		padding-left: 0.5rem;
		opacity: 0.45;
		user-select: none;
	}
	.hunk-gap {
		padding: 0.125rem 1rem;
		text-align: center;
		color: var(--color-gray-400);
		background: rgb(0 0 0 / 0.025);
	}
	:global(.dark) .version-diff-content {
		color: var(--color-gray-300);
	}
	:global(.dark) .addition {
		background: #12261e;
		color: #aff5b4;
	}
	:global(.dark) .deletion {
		background: #2d161b;
		color: #ffdcd7;
	}
	:global(.dark) .addition .changed {
		background: #22c55e40;
	}
	:global(.dark) .deletion .changed {
		background: #f8717140;
	}
	:global(.dark) .empty,
	:global(.dark) .hunk-gap {
		background: rgb(255 255 255 / 0.025);
	}
	:global(.dark) .line-number,
	:global(.dark) .split-row > .diff-cell + .diff-cell {
		border-color: rgb(255 255 255 / 0.06);
	}
	@media (max-width: 640px) {
		.diff-cell.unified-row {
			grid-template-columns: 1.75rem 1.75rem 1rem minmax(0, 1fr);
		}
		.diff-cell {
			grid-template-columns: 1.75rem minmax(0, 1fr);
		}
		.line-number {
			padding: 0 0.25rem;
		}
	}
</style>
