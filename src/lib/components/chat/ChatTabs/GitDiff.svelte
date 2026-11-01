<script lang="ts">
	import { versionDiffHunks, type VersionDiffLine } from '../../workspace/common/versionDiff';
	export let code = '';
	export let mode: 'unified' | 'split' = 'unified';
	export let hideWhitespace = false;
	$: files = code
		.split(/(?=^diff --git )/m)
		.filter(Boolean)
		.map((content) => ({
			path: content.match(/^\+\+\+ (?:b\/)?(.+)$/m)?.[1] ?? '',
			headers: content.match(/^@@.*$/gm) ?? [],
			hunks: versionDiffHunks(content)
		}));
</script>

{#snippet text(line: VersionDiffLine | null)}
	<code class="line-text"
		>{#if line}{#each line.segments as segment}<span class:changed={segment.changed}
					>{segment.text}</span
				>{/each}{#if line.noNewline}<span class="opacity-40" title="No newline at end of file">
					↵</span
				>{/if}{:else}{' '}{/if}</code
	>
{/snippet}

{#snippet cell(line: VersionDiffLine | null)}
	<div
		class="line"
		class:added={line?.type === 'addition'}
		class:removed={line?.type === 'deletion'}
	>
		<span class="prefix" aria-hidden="true">{line?.prefix || ' '}</span>{@render text(line)}
	</div>
{/snippet}

<div class="git-diff font-mono text-[0.6875rem] leading-[1.125rem]" class:split={mode === 'split'}>
	{#each files as file}
		{#if files.length > 1}<div
				class="px-2 py-1 text-[0.625rem] text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-white/4"
			>
				{file.path}
			</div>{/if}
		{#each file.hunks as hunk, index}
			<div
				class="border-b border-gray-100 bg-gray-50 px-2 py-0.5 text-gray-400 dark:border-white/4 dark:bg-white/3 dark:text-gray-600"
			>
				{file.headers[index]}
			</div>
			{#each hunk.rows as row}
				{#if !(hideWhitespace && row.before?.type === 'deletion' && row.after?.type === 'addition' && row.before.content.replace(/\s/g, '') === row.after.content.replace(/\s/g, ''))}
					{#if mode === 'split'}<div class="split-row">
							{@render cell(row.before)}{@render cell(row.after)}
						</div>
					{:else if row.before?.type === 'context'}{@render cell(row.before)}
					{:else}{#if row.before}{@render cell(row.before)}{/if}{#if row.after}{@render cell(
								row.after
							)}{/if}{/if}
				{/if}
			{/each}
		{/each}
	{/each}
</div>

<style>
	.git-diff {
		min-width: 100%;
		width: max-content;
		color: var(--color-gray-600);
	}
	.git-diff.split {
		width: 100%;
	}
	.line {
		display: flex;
		min-width: 0;
	}
	.prefix {
		width: 1.25rem;
		flex-shrink: 0;
		text-align: center;
		user-select: none;
		color: var(--color-gray-400);
	}
	.line-text {
		white-space: pre;
		padding: 0 0.5rem;
		font: inherit;
		tab-size: 4;
	}
	.split-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	}
	.split-row .line-text {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.split-row > .line + .line {
		border-left: 1px solid #80808018;
	}
	.added {
		background: var(--color-green-100);
		color: var(--color-green-900);
	}
	.removed {
		background: var(--color-red-100);
		color: var(--color-red-900);
	}
	.added .prefix {
		color: var(--color-green-600);
	}
	.removed .prefix {
		color: var(--color-red-500);
	}
	.added .changed {
		background: #16a34a35;
	}
	.removed .changed {
		background: #dc262630;
	}
	:global(.dark) .git-diff {
		color: var(--color-gray-400);
	}
	:global(.dark) .added {
		background: #22c55e26;
		color: var(--color-green-300);
	}
	:global(.dark) .removed {
		background: #ef444426;
		color: var(--color-red-300);
	}
</style>
