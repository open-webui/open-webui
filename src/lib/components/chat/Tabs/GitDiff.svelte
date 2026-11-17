<script lang="ts">
	import { onDestroy } from 'svelte';
	import {
		diffFilePath,
		highlightDiffFile,
		type HighlightSegment
	} from '$lib/utils/gitDiffHighlight';
	import { versionDiffHunks, type VersionDiffLine } from '../../workspace/common/versionDiff';
	export let code = '';
	export let mode: 'unified' | 'split' = 'unified';
	export let hideWhitespace = false;
	$: files = code
		.split(/(?=^diff --git )/m)
		.filter(Boolean)
		.map((content) => ({
			path: diffFilePath(content),
			headers: content.match(/^@@.*$/gm) ?? [],
			hunks: versionDiffHunks(content)
		}));
	let highlighted = new Map<VersionDiffLine, HighlightSegment[]>();
	let highlightGeneration = 0;
	const highlight = async (entries: typeof files) => {
		const version = ++highlightGeneration;
		highlighted = new Map();
		const result = new Map<VersionDiffLine, HighlightSegment[]>();
		for (const file of entries) {
			if (version !== highlightGeneration) return;
			try {
				const tokens = await highlightDiffFile(file.path, file.hunks);
				if (version !== highlightGeneration) return;
				for (const [line, segments] of tokens) result.set(line, segments);
			} catch {
				// Unrecognized languages still display the complete diff without syntax colors.
			}
		}
		if (version === highlightGeneration) highlighted = result;
	};
	$: void highlight(files);
	onDestroy(() => {
		++highlightGeneration;
	});
</script>

{#snippet text(line: VersionDiffLine | null)}
	<code class="line-text"
		>{#if line}{#each (highlighted.get(line) ?? line.segments) as HighlightSegment[] as segment}<span
					class:changed={segment.changed}
					style:--diff-token-light={segment.light}
					style:--diff-token-dark={segment.dark}>{segment.text}</span
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
				class="sticky top-0 z-10 bg-white dark:bg-[var(--chat-tabs-dark-background,var(--color-gray-900))] px-2 py-1 text-[0.625rem] text-gray-500 dark:text-gray-400 border-b border-gray-100/50 dark:border-white/2"
			>
				{file.path}
			</div>{/if}
		{#each file.hunks as hunk, index}
			<div
				class="border-b border-gray-100/50 bg-gray-50 px-2 py-0.5 text-gray-400 dark:border-white/2 dark:bg-white/3 dark:text-gray-600"
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
		min-height: 1.125rem;
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
		border-left: 1px solid #8080800c;
	}
	.added {
		background-color: var(--color-green-100);
		color: var(--color-green-900);
	}
	.removed {
		background-color: var(--color-red-100);
		color: var(--color-gray-600);
	}
	.added .prefix {
		color: var(--color-green-600);
	}
	.removed .prefix {
		color: var(--color-gray-500);
	}
	.git-diff:not(.split) .added {
		box-shadow: inset 0.1875rem 0 0 #22c55e;
	}
	:global(.dark) .git-diff:not(.split) .added {
		box-shadow: inset 0.1875rem 0 0 #4ade80;
	}
	.git-diff:not(.split) .removed {
		background-image: repeating-linear-gradient(
			-45deg,
			#ef4444 0,
			#ef4444 1px,
			transparent 1px,
			transparent 0.1875rem
		);
		background-position: left top;
		background-repeat: repeat-y;
		background-size: 0.1875rem 0.1875rem;
	}
	.line-text span {
		color: var(--diff-token-light, inherit);
	}
	:global(.dark) .line-text span {
		color: var(--diff-token-dark, inherit);
	}
	.changed {
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}
	.added .changed {
		background: rgba(22, 163, 74, 0.38);
		box-shadow: inset 0 -0.125rem 0 rgba(21, 128, 61, 0.42);
	}
	.removed .changed {
		background: rgba(220, 38, 38, 0.32);
		box-shadow: inset 0 -0.125rem 0 rgba(185, 28, 28, 0.38);
	}
	:global(.dark) .added .changed {
		background: rgba(34, 197, 94, 0.42);
		box-shadow: inset 0 -0.125rem 0 rgba(134, 239, 172, 0.5);
	}
	:global(.dark) .removed .changed {
		background: rgba(248, 113, 113, 0.4);
		box-shadow: inset 0 -0.125rem 0 rgba(252, 165, 165, 0.48);
	}
	:global(.dark) .git-diff {
		color: var(--color-gray-400);
	}
	:global(.dark) .added {
		background-color: #22c55e26;
		color: var(--color-green-300);
	}
	:global(.dark) .removed {
		background-color: #ef444426;
		color: var(--color-gray-400);
	}
	:global(.dark) .added .prefix {
		color: var(--color-green-400);
	}
	:global(.dark) .removed .prefix {
		color: var(--color-gray-400);
	}
</style>
