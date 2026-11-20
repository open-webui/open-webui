<script lang="ts">
	import { parseDiffRows, type DiffRow } from './diff';

	export let code = '';
	// Small, quiet variant for tool cards: the file path is shown above, so file headers are hidden.
	export let compact = false;

	$: rows = parseDiffRows(code).filter((row) => !compact || row.type !== 'file');
	$: showNumbers = rows.some((row) => row.oldNumber !== null || row.newNumber !== null);
	$: gutterWidth = `${rows.reduce((width, row) => Math.max(width, String(Math.max(row.oldNumber ?? 0, row.newNumber ?? 0)).length + 1), 3)}ch`;

	const ROW: Record<DiffRow['type'], string> = {
		addition:
			'bg-[#dafbe1] text-[#116329] shadow-[inset_3px_0_0_#2da44e] dark:bg-[#12261e] dark:text-[#aff5b4] dark:shadow-[inset_3px_0_0_#3fb950]',
		deletion:
			'bg-[#ffebe9] text-[#a40e26] shadow-[inset_3px_0_0_#cf222e] dark:bg-[#2d161b] dark:text-[#ffdcd7] dark:shadow-[inset_3px_0_0_#f85149]',
		hunk: 'bg-[#ddf4ff] text-[#0550ae] dark:bg-[#121f33] dark:text-[#79c0ff]',
		file: 'bg-[#f6f8fa] text-[#57606a] font-semibold dark:bg-[#161b22] dark:text-[#8b949e]',
		meta: 'italic text-[#6e7781] dark:text-[#8b949e]',
		context: ''
	};

	const COMPACT_ROW: Record<DiffRow['type'], string> = {
		addition: 'bg-green-500/8 text-green-700 dark:bg-green-500/10 dark:text-green-300',
		deletion: 'bg-red-500/7 text-red-700 dark:bg-red-500/10 dark:text-red-300',
		hunk: 'text-base-400 dark:text-base-500',
		file: '',
		meta: 'italic text-base-400 dark:text-base-500',
		context: ''
	};

	const CHANGED: Partial<Record<DiffRow['type'], string>> = {
		addition:
			'font-bold bg-green-600/25 shadow-[inset_0_-2px_0_#15803d80] dark:bg-green-500/30 dark:shadow-[inset_0_-2px_0_#86efac80]',
		deletion:
			'font-bold bg-red-600/20 shadow-[inset_0_-2px_0_#b91c1c60] dark:bg-red-400/30 dark:shadow-[inset_0_-2px_0_#fca5a580]'
	};

	const COMPACT_CHANGED: Partial<Record<DiffRow['type'], string>> = {
		addition: 'bg-green-500/18 dark:bg-green-500/20',
		deletion: 'bg-red-500/16 dark:bg-red-500/18'
	};

	$: rowClass = compact ? COMPACT_ROW : ROW;
	$: changedClass = compact ? COMPACT_CHANGED : CHANGED;
	$: columns = showNumbers
		? compact
			? 'grid-cols-[var(--diff-gutter-width)_var(--diff-gutter-width)_1.25rem_minmax(0,1fr)]'
			: 'grid-cols-[var(--diff-gutter-width)_var(--diff-gutter-width)_1.75rem_minmax(0,1fr)]'
		: compact
			? 'grid-cols-[1.25rem_minmax(0,1fr)]'
			: 'grid-cols-[1.75rem_minmax(0,1fr)]';
	$: numberClass = `px-[0.5ch] text-right select-none before:content-[attr(data-line-number)] ${
		compact
			? 'text-base-400 dark:text-base-500'
			: 'text-[#6e7781] dark:text-[#8b949e] border-e border-[#80808020]'
	}`;
</script>

<div
	class="overflow-x-auto {compact
		? 'text-xs bg-transparent text-inherit'
		: 'text-sm bg-white text-[#24292f] dark:bg-[#0d1117] dark:text-[#c9d1d9]'}"
	dir="ltr"
	style:--diff-gutter-width={gutterWidth}
>
	<pre
		class="m-0! min-w-full w-max rounded-none! bg-transparent! text-inherit! [font-size:inherit]! [tab-size:4] {compact
			? 'p-0! leading-normal'
			: 'py-2! px-0! leading-[1.6]'}"><code
			class="block p-0 bg-transparent text-inherit font-mono font-normal whitespace-pre [font-size:inherit]"
			>{#each rows as row, index}<span
					class="grid {columns} {compact ? 'min-h-[1.5em]' : 'min-h-[1.6em]'} {rowClass[row.type]}"
					>{#if showNumbers}<span
							class={numberClass}
							data-line-number={row.oldNumber ?? ''}
							aria-hidden="true"></span><span
							class={numberClass}
							data-line-number={row.newNumber ?? ''}
							aria-hidden="true"></span>{/if}<span
						class="text-center {compact ? 'font-normal' : 'font-bold'}">{row.prefix}</span
					><span class="pl-1 pr-4"
						>{#each row.segments as segment}<span
								class={segment.changed
									? `rounded-xs [box-decoration-break:clone] ${changedClass[row.type] ?? ''}`
									: ''}>{segment.text}</span
							>{/each}{index < rows.length - 1 ? '\n' : ''}</span
					></span
				>{/each}</code
		></pre>
</div>
