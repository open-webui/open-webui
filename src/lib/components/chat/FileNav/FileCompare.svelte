<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import type { Readable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { compareFiles, type TerminalComparison, type TerminalDiffLine } from '$lib/apis/terminal';
	import Icon from './Icon.svelte';
	import Spinner from '../../common/Spinner.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import Dropdown from '../../common/Dropdown.svelte';
	import DropdownMenu from '../../common/DropdownMenu.svelte';

	export let baseUrl: string;
	export let apiKey: string;
	export let chatId: string | null = null;
	export let paths: [string, string];
	export let onBack: () => void;

	const i18n = getContext<Readable<I18n>>('i18n');
	let original = paths[0];
	let revised = paths[1];
	let mode: 'unified' | 'split' = 'unified';
	let ignoreWhitespace = false;
	let result: TerminalComparison | null = null;
	let loading = true;
	let error = '';
	let controller: AbortController | null = null;
	let menu: Dropdown;
	let menuOpen = false;
	const name = (path: string) => path.split(/[\\/]/).pop() ?? path;

	async function run() {
		controller?.abort();
		const request = new AbortController();
		controller = request;
		loading = true;
		error = '';
		result = null;
		try {
			const response = await compareFiles(
				baseUrl,
				apiKey,
				{ original, revised, ignore_whitespace: ignoreWhitespace },
				chatId ?? undefined,
				request.signal
			);
			if (!request.signal.aborted) result = response;
		} catch (err) {
			if (!request.signal.aborted) error = err instanceof Error ? err.message : String(err);
		} finally {
			if (!request.signal.aborted) loading = false;
		}
	}

	function setMode(value: 'unified' | 'split') {
		mode = value;
		try {
			localStorage.setItem('fileCompare:mode', value);
		} catch {
			/* Storage can be disabled. */
		}
		menu.close();
	}

	function whitespaceChanged() {
		try {
			localStorage.setItem('fileCompare:ignoreWhitespace', String(ignoreWhitespace));
		} catch {
			/* Storage can be disabled. */
		}
		void run();
	}

	function splitRows(lines: TerminalDiffLine[]) {
		const rows: { original: TerminalDiffLine | null; revised: TerminalDiffLine | null }[] = [];
		let index = 0;
		while (index < lines.length) {
			if (lines[index].type === 'context') {
				const line = lines[index++];
				rows.push({
					original: line,
					revised: {
						...line,
						content: line.revisedContent ?? line.content,
						segments: [{ text: line.revisedContent ?? line.content, changed: false }]
					}
				});
				continue;
			}
			const removed: TerminalDiffLine[] = [];
			const added: TerminalDiffLine[] = [];
			while (index < lines.length && lines[index].type !== 'context') {
				const line = lines[index++];
				(line.type === 'removed' ? removed : added).push(line);
			}
			for (let i = 0; i < Math.max(removed.length, added.length); i++) {
				rows.push({ original: removed[i] ?? null, revised: added[i] ?? null });
			}
		}
		return rows;
	}

	onMount(() => {
		try {
			mode = localStorage.getItem('fileCompare:mode') === 'split' ? 'split' : 'unified';
			ignoreWhitespace = localStorage.getItem('fileCompare:ignoreWhitespace') === 'true';
		} catch {
			/* Use defaults when storage is disabled. */
		}
		void run();
	});
	onDestroy(() => controller?.abort());
</script>

<svelte:window
	on:keydown|capture={(event) => {
		if (event.key === 'Escape' && menuOpen) {
			event.stopPropagation();
			menu.close();
		}
	}}
/>

<div
	class="flex h-full min-h-0 flex-col bg-white text-[0.75em] font-normal text-gray-600 dark:bg-black dark:text-gray-400"
	aria-label={$i18n.t('Compare')}
>
	<div
		class="m-0 flex shrink-0 items-center gap-1 border-b border-gray-50 px-1 pt-0 pb-1.5 dark:border-gray-850/30"
	>
		<div class="flex shrink-0 items-center gap-0.5 px-1">
			<Tooltip content={$i18n.t('Back')}>
				<button
					class="flex h-5 min-w-6 shrink-0 items-center justify-center rounded px-1.5 text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
					on:click|stopPropagation={onBack}
					aria-label={$i18n.t('Back')}
					><Icon name="chevron-left" size={11} strokeWidth={1.5} /></button
				>
			</Tooltip>
		</div>
		<span class="min-w-0 flex-1 truncate font-normal">{$i18n.t('Compare')}</span>
		<Tooltip content={$i18n.t('Swap')}>
			<button
				class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
				on:click={() => {
					[original, revised] = [revised, original];
					void run();
				}}
				aria-label={$i18n.t('Swap')}><Icon name="swap" size={11} strokeWidth={1.4} /></button
			>
		</Tooltip>
		<Tooltip content={$i18n.t('Refresh')}>
			<button
				class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
				on:click={run}
				disabled={loading}
				aria-label={$i18n.t('Refresh')}
				><Icon
					name="refresh"
					size={11}
					strokeWidth={1.4}
					class={loading ? 'animate-spin' : ''}
				/></button
			>
		</Tooltip>
		<Dropdown bind:this={menu} bind:show={menuOpen} align="end" sideOffset={4}>
			<Tooltip content={$i18n.t('Diff settings')}>
				<button
					class="flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
					aria-label={$i18n.t('Diff settings')}
					><Icon
						name={mode === 'unified' ? 'list' : 'split-horizontal'}
						size={11}
						strokeWidth={1.4}
					/></button
				>
			</Tooltip>
			<div slot="content">
				<DropdownMenu className="min-w-[9.375rem] z-[9999999] font-normal">
					{#each ['unified', 'split'] as value}
						<button
							type="button"
							class="select-none font-normal transition"
							aria-pressed={mode === value}
							on:click={() => setMode(value as 'unified' | 'split')}
						>
							<Icon
								name={value === 'unified' ? 'list' : 'split-horizontal'}
								size={12}
								strokeWidth={1.4}
							/>
							<span class="flex-1 text-left"
								>{$i18n.t(value === 'unified' ? 'Unified' : 'Split')}</span
							>
							{#if mode === value}<Icon name="check" size={12} strokeWidth={1.4} />{/if}
						</button>
					{/each}
					<hr class="border-gray-100 dark:border-gray-800" />
					<button
						type="button"
						class="select-none font-normal transition"
						aria-pressed={ignoreWhitespace}
						on:click={() => {
							ignoreWhitespace = !ignoreWhitespace;
							whitespaceChanged();
						}}
					>
						<span class="flex-1 text-left">{$i18n.t('Hide whitespace')}</span>
						{#if ignoreWhitespace}<Icon name="check" size={12} strokeWidth={1.4} />{/if}
					</button>
				</DropdownMenu>
			</div>
		</Dropdown>
	</div>
	<div class="grid shrink-0 grid-cols-2 border-b border-black/5 dark:border-white/5">
		{#each [{ label: 'Original', path: original }, { label: 'Revised', path: revised }] as file}
			<div class="min-w-0 px-3 py-2" title={file.path}>
				<div class="text-[0.916667em] text-gray-400 dark:text-gray-500">{$i18n.t(file.label)}</div>
				<div class="truncate font-normal text-gray-700 dark:text-gray-300">{name(file.path)}</div>
			</div>
		{/each}
	</div>
	{#if loading}
		<div class="flex items-center gap-2 p-4" role="status">
			<Spinner className="size-3" />{$i18n.t('Extracting text and comparing…')}
		</div>
	{:else if error}
		<div class="p-4" role="alert">
			<p class="break-words">{error}</p>
			<button class="control mt-2" on:click={run}>{$i18n.t('Retry')}</button>
		</div>
	{:else if result}
		<div
			class="flex shrink-0 items-center gap-2 border-b border-black/5 px-3 py-1 dark:border-white/5"
			aria-live="polite"
		>
			<span
				class="text-green-600 dark:text-green-400"
				aria-label={$i18n.t('{{count}} added lines', { count: result.additions })}
				>+{result.additions}</span
			>
			<span
				class="text-red-500 dark:text-red-400"
				aria-label={$i18n.t('{{count}} removed lines', { count: result.deletions })}
				>−{result.deletions}</span
			>
			<span class="ml-auto text-[0.916667em] text-gray-400">{$i18n.t('Extracted text lines')}</span>
		</div>
		{#if result.hunks.length === 0}
			<p class="p-4" role="status">{$i18n.t('No text differences')}</p>
		{:else}
			<!-- Keyboard focus lets users scroll long comparisons without a pointer. -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<div
				class="diff-scroll min-h-0 flex-1 overflow-auto"
				tabindex="0"
				role="region"
				aria-label={$i18n.t('File differences')}
			>
				<div class="diff-content" class:split={mode === 'split'}>
					{#each result.hunks as hunk}
						<div
							class="hunk-header select-none bg-black/[0.025] px-3 text-gray-400 dark:bg-white/[0.025] dark:text-gray-600"
						>
							{hunk.header}
						</div>
						{#if mode === 'split'}
							{#each splitRows(hunk.lines) as row}
								<div class="split-row">
									{#each ['original', 'revised'] as side}
										{@const line = row[side as 'original' | 'revised']}
										<div class="split-cell {line?.type ?? ''}">
											<span class="number"
												>{(side === 'original' ? line?.oldNumber : line?.newNumber) ?? ''}</span
											>
											<span class="marker" aria-hidden="true"
												>{line?.type === 'added' ? '+' : line?.type === 'removed' ? '−' : ' '}</span
											>
											<span class="code"
												>{#if line}{#each line.segments as segment}<span
															class:changed={segment.changed}>{segment.text}</span
														>{/each}{:else}{' '}{/if}</span
											>
										</div>
									{/each}
								</div>
							{/each}
						{:else}
							{#each hunk.lines as line}
								<div class="unified-row {line.type}">
									<span class="number">{line.oldNumber ?? ''}</span><span class="number"
										>{line.newNumber ?? ''}</span
									>
									<span class="marker" aria-hidden="true"
										>{line.type === 'added' ? '+' : line.type === 'removed' ? '−' : ' '}</span
									>
									<span class="code"
										>{#each line.segments as segment}<span class:changed={segment.changed}
												>{segment.text}</span
											>{/each}</span
									>
								</div>
							{/each}
						{/if}
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	.control {
		display: inline-flex;
		min-height: 1.5rem;
		align-items: center;
		gap: 0.25rem;
		border-radius: 0.25rem;
		padding: 0.125rem 0.375rem;
		font-size: 1em;
	}
	.control:hover {
		background: rgb(0 0 0 / 0.05);
	}
	:global(.dark) .control:hover {
		background: rgb(255 255 255 / 0.06);
	}
	.control:disabled {
		opacity: 0.4;
	}
	.control:focus-visible,
	summary:focus-visible {
		outline: 2px solid currentColor;
		outline-offset: 2px;
	}
	.diff-scroll {
		font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace);
		font-size: 0.916667em;
		line-height: 1.636364;
	}
	.diff-content {
		width: max-content;
		min-width: 100%;
	}
	.diff-content.split {
		width: 100%;
	}
	.unified-row {
		display: grid;
		grid-template-columns: 2.75rem 2.75rem 1.25rem auto;
		min-height: 1.636364em;
	}
	.split-row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	}
	.split-cell {
		display: grid;
		grid-template-columns: 2.75rem 1.25rem minmax(0, 1fr);
		min-width: 0;
		min-height: 1.636364em;
	}
	.split-cell + .split-cell {
		border-left: 1px solid rgb(0 0 0 / 0.05);
	}
	.number {
		user-select: none;
		color: var(--color-gray-400);
		padding: 0 0.5rem;
		text-align: right;
		border-right: 1px solid rgb(0 0 0 / 0.05);
	}
	.marker {
		user-select: none;
		text-align: center;
		white-space: pre;
	}
	.code {
		white-space: pre;
		padding-right: 0.5rem;
	}
	.split .code {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.added {
		background-color: var(--color-green-100);
		color: var(--color-green-900);
		box-shadow: inset 0.1875rem 0 0 #22c55e;
	}
	.removed {
		background-color: var(--color-red-100);
		color: var(--color-red-900);
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
	.added .marker {
		color: var(--color-green-600);
	}
	.removed .marker {
		color: var(--color-red-500);
	}
	.added .changed {
		background: rgb(22 163 74 / 0.38);
		box-shadow: inset 0 -0.125rem 0 rgb(21 128 61 / 0.42);
	}
	.removed .changed {
		background: rgb(220 38 38 / 0.32);
		box-shadow: inset 0 -0.125rem 0 rgb(185 28 28 / 0.38);
	}
	:global(.dark) .added {
		background-color: color-mix(in oklab, var(--color-green-500) 15%, transparent);
		color: var(--color-green-300);
		box-shadow: inset 0.1875rem 0 0 #4ade80;
	}
	:global(.dark) .removed {
		background-color: color-mix(in oklab, var(--color-red-500) 15%, transparent);
		color: var(--color-red-300);
	}
	:global(.dark) .added .marker {
		color: var(--color-green-400);
	}
	:global(.dark) .removed .marker {
		color: var(--color-red-400);
	}
	:global(.dark) .number {
		color: var(--color-gray-600);
		border-color: rgb(255 255 255 / 0.04);
	}
	:global(.dark) .split-cell + .split-cell {
		border-color: rgb(255 255 255 / 0.04);
	}
	:global(.dark) .added .changed {
		background: rgb(34 197 94 / 0.42);
		box-shadow: inset 0 -0.125rem 0 rgb(134 239 172 / 0.5);
	}
	:global(.dark) .removed .changed {
		background: rgb(248 113 113 / 0.4);
		box-shadow: inset 0 -0.125rem 0 rgb(252 165 165 / 0.48);
	}
</style>
