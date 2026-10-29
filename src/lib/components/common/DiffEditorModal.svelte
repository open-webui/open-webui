<script lang="ts">
	import '$lib/utils/codemirror';
	import { getContext } from 'svelte';
	import { copyToClipboard } from '$lib/utils';
	import { basicSetup, EditorView } from 'codemirror';
	import { Compartment, EditorState, type Text } from '@codemirror/state';
	import { keymap, type ViewUpdate } from '@codemirror/view';
	import { indentWithTab, isolateHistory, undo } from '@codemirror/commands';
	import { DiffUndoHistory } from './diffEditorHistory';
	import { LanguageDescription, indentUnit } from '@codemirror/language';
	import { languages } from '@codemirror/language-data';
	import { oneDark } from '@codemirror/theme-one-dark';
	import type { Chunk } from '@codemirror/merge';
	import Dropdown from './Dropdown.svelte';
	import DropdownMenu from './DropdownMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Italic from '$lib/components/icons/Italic.svelte';
	import LineSpaceSmaller from '$lib/components/icons/LineSpaceSmaller.svelte';

	import Modal from './Modal.svelte';
	import Tooltip from './Tooltip.svelte';
	import ConfirmDialog from './ConfirmDialog.svelte';
	import FileCodeEditor from '$lib/components/chat/FileNav/FileCodeEditor.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import {
		lineAlignment,
		alignChangedLines,
		clearLineAlignment,
		alignmentGeometryChanged
	} from './diffEditorAlignment';
	import {
		diffPresentation,
		setDiffPresentation,
		visibleDiffChunks,
		unchangedRanges,
		presentationDecorations,
		type CollapsedPair,
		copyChunk,
		keepBothChunk,
		selectedChunk,
		chunkOverview,
		changedLineCounts,
		nearestOverviewChunk,
		DiffEditorView,
		type MergeDirection
	} from './diffEditor';

	type FileLabel = { name: string; path: string };
	type ComparisonTexts = { initialContent: string; proposedContent: string };
	export let mode: 'edit' | 'review' = 'edit';
	export let leftFile: FileLabel | undefined = undefined;
	export let rightFile: FileLabel | undefined = undefined;
	export let onRefresh: (() => Promise<ComparisonTexts>) | undefined = undefined;
	export let show = false;
	export let initialContent = '';
	export let proposedContent: string | undefined = undefined;
	export let filePath: string | null = null;
	export let title = '';
	export let applyLabel: string | null = null;
	export let applyDescription: string | null = null;
	export let discardMessage: string | null = null;
	export let onApply: (content: string) => void = () => {};
	export let onClose: () => void = () => {};

	const i18n = getContext<any>('i18n');
	let session: {
		original: string;
		proposal: string;
		path: string | null;
		title: string;
		mode: 'edit' | 'review';
		hasProposal: boolean;
		leftFile?: FileLabel;
		rightFile?: FileLabel;
		onRefresh?: () => Promise<ComparisonTexts>;
	} | null = null;
	let working = '';
	let proposal = '';
	let comparing = false;
	let merge: DiffEditorView | null = null;
	let visibleChunks: readonly Chunk[] = [];
	let showOptions = false;
	let optionsDropdown: Dropdown;
	let ignoreWhitespace = false;
	let ignoreEmphasis = false;
	let onlyChanges = false;
	let updatePresentation: ((reset?: boolean) => void) | null = null;
	let activeChunk = 0;
	let canKeepBoth = false;
	let undoSide: 'a' | 'b' | null = null;
	let overview: ReturnType<typeof chunkOverview> = [];
	let chunkCount = 0;
	let lineNumberDigits = 1;
	let lineChanges = { removed: 0, added: 0 };
	let copied: { side: 'a' | 'b'; text: string } | null = null;
	let approximate = false;
	let loading = false;
	let error = '';
	let confirmDiscard = false;

	let swapped = false;
	let refreshing = false;
	let editorRevision = 0;
	const paneFile = (side: string) =>
		(side === 'a') !== swapped ? session?.leftFile : session?.rightFile;
	const paneLabel = (side: string) =>
		paneFile(side)?.name ?? (side === 'a' ? $i18n.t('Original') : $i18n.t('Proposed revision'));

	const begin = () => {
		session = {
			original: initialContent,
			proposal: proposedContent ?? '',
			path: filePath,
			title,
			mode,
			hasProposal: proposedContent !== undefined,
			leftFile: leftFile && { ...leftFile },
			rightFile: rightFile && { ...rightFile },
			onRefresh
		};
		swapped = refreshing = false;
		editorRevision++;
		working = session.original;
		proposal = session.proposal;
		comparing = proposedContent !== undefined;
		activeChunk = chunkCount = 0;
		canKeepBoth = false;
		undoSide = null;
		overview = [];
		lineChanges = { removed: 0, added: 0 };
		copied = null;
		loading = approximate = false;
		error =
			mode === 'review' && proposedContent === undefined
				? $i18n.t('Both files are required for comparison.')
				: '';
		confirmDiscard = false;
		showOptions = false;
	};
	$: if (show && !session) begin();
	$: if (!show && session) {
		session = null;
		confirmDiscard = false;
	}

	const close = () => {
		show = false;
		onClose();
	};
	const requestClose = () => {
		if (session?.mode === 'review') return close();
		if (session && (working !== session.original || proposal !== session.proposal))
			confirmDiscard = true;
		else close();
	};
	const apply = () => {
		if (session?.mode === 'review') return;
		try {
			onApply(proposal);
			close();
		} catch (cause) {
			error = cause instanceof Error ? cause.message : String(cause);
		}
	};
	const replaceReview = (texts: ComparisonTexts) => {
		working = swapped ? texts.proposedContent : texts.initialContent;
		proposal = swapped ? texts.initialContent : texts.proposedContent;
		activeChunk = 0;
		copied = null;
		editorRevision++;
	};
	const swap = () => {
		if (session?.mode !== 'review') return;
		swapped = !swapped;
		replaceReview({ initialContent: session.original, proposedContent: session.proposal });
	};
	const reload = async () => {
		const current = session;
		if (current?.mode !== 'review' || !current.onRefresh || refreshing) return;
		refreshing = true;
		error = '';
		try {
			const texts = await current.onRefresh();
			if (session !== current || !show) return;
			current.original = texts.initialContent;
			current.proposal = texts.proposedContent;
			replaceReview(texts);
		} catch (cause) {
			if (session === current && show)
				error = cause instanceof Error ? cause.message : String(cause);
		} finally {
			if (session === current) refreshing = false;
		}
	};
	const copyPane = async (side: 'a' | 'b') => {
		const text = side === 'a' ? working : proposal;
		const currentSession = session;
		const success = await copyToClipboard(text);
		if (session !== currentSession) return;
		if (success) {
			copied = { side, text };
			error = '';
		} else error = $i18n.t('Could not copy to clipboard. Please try again.');
	};
	const preventSave = (event: KeyboardEvent) => {
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
			event.preventDefault();
			event.stopPropagation();
		}
	};
	const refresh = (update?: ViewUpdate, side: 'a' | 'b' = 'a') => {
		if (!merge) return;
		if (!update || update.docChanged) {
			if (session?.mode !== 'review') {
				working = merge.a.state.doc.toString();
				proposal = merge.b.state.doc.toString();
			}
			visibleChunks = visibleDiffChunks(
				merge.a.state.doc,
				merge.b.state.doc,
				merge.chunks,
				ignoreWhitespace,
				ignoreEmphasis
			);
			chunkCount = visibleChunks.length;
			lineNumberDigits = String(Math.max(merge.a.state.doc.lines, merge.b.state.doc.lines)).length;
			lineChanges = changedLineCounts(merge.a.state.doc, merge.b.state.doc, visibleChunks);
			overview = chunkOverview(merge.a.state.doc, merge.b.state.doc, visibleChunks);
			approximate = merge.chunks.some((chunk) => !chunk.precise);
			updatePresentation?.();
		}
		if (update?.selectionSet) {
			const index = selectedChunk(visibleChunks, side, update.state.selection.main.head);
			if (index >= 0) activeChunk = index;
		}
		activeChunk = Math.max(0, Math.min(activeChunk, chunkCount - 1));
		const chunk = visibleChunks[activeChunk];
		canKeepBoth =
			session?.mode === 'edit' &&
			!!chunk &&
			keepBothChunk(merge.a.state.doc, merge.b.state.doc, chunk) !== null;
	};
	const reveal = (index: number) => {
		if (!merge || !chunkCount) return;
		activeChunk = Math.max(0, Math.min(index, chunkCount - 1));
		const chunk = visibleChunks[activeChunk];
		merge.scrollSource = chunk.toB > chunk.fromB ? merge.b : merge.a;
		for (const [view, start] of [
			[merge.a, chunk.fromA],
			[merge.b, chunk.fromB]
		] as const) {
			const position = Math.min(start, view.state.doc.length);
			view.dispatch({
				selection: { anchor: position },
				effects: EditorView.scrollIntoView(position, { y: 'start', yMargin: 0 })
			});
		}
		refresh();
	};
	const navigateOverview = (event: MouseEvent) => {
		const bounds =
			event.currentTarget instanceof HTMLElement && event.currentTarget.getBoundingClientRect();
		if (!bounds || !chunkCount) return;
		const side = event.clientX - bounds.left < bounds.width / 2 ? 'a' : 'b';
		reveal(nearestOverviewChunk(overview, side, (event.clientY - bounds.top) / bounds.height));
	};
	const overviewKeydown = (event: KeyboardEvent) => {
		const positions: Record<string, number> = {
			ArrowUp: activeChunk - 1,
			ArrowDown: activeChunk + 1,
			Home: 0,
			End: chunkCount - 1
		};
		const index = positions[event.key];
		if (index === undefined) return;
		event.preventDefault();
		event.stopPropagation();
		reveal(index);
	};

	const copy = (direction: MergeDirection) => {
		if (session?.mode === 'review' || !merge || !visibleChunks[activeChunk]) return;
		const destination = direction === 'to-working' ? merge.a : merge.b;
		destination.dispatch({
			changes: copyChunk(
				merge.a.state.doc,
				merge.b.state.doc,
				visibleChunks[activeChunk],
				direction
			),
			annotations: isolateHistory.of('full'),
			userEvent: 'input.merge'
		});
		refresh();
	};

	const undoLastChange = () => {
		if (session?.mode !== 'edit' || loading || !merge || !undoSide) return;
		const view = merge[undoSide];
		undo(view);
		view.focus();
	};

	const keepBoth = () => {
		if (session?.mode !== 'edit' || loading || !merge) return;
		const chunk = visibleChunks[activeChunk];
		if (!chunk) return;
		const changes = keepBothChunk(merge.a.state.doc, merge.b.state.doc, chunk);
		if (!changes) return;
		merge.b.dispatch({
			changes,
			annotations: isolateHistory.of('full'),
			userEvent: 'input.merge'
		});
		refresh();
		merge.b.focus();
	};

	const toggleDisplay = (option: 'whitespace' | 'emphasis' | 'unchanged') => {
		if (option === 'whitespace') ignoreWhitespace = !ignoreWhitespace;
		else if (option === 'emphasis') ignoreEmphasis = !ignoreEmphasis;
		else onlyChanges = !onlyChanges;
		activeChunk = 0;
		if (merge) {
			clearLineAlignment(merge.a, merge.b);
		}
		updatePresentation?.(true);
		refresh();
	};

	const mountMerge = (node: HTMLElement) => {
		let disposed = false;
		let view: DiffEditorView | null = null;
		let observer: MutationObserver | undefined;
		let alignmentFrame = 0;
		let presentationFrame = 0;
		let expanded: CollapsedPair[] = [];
		const schedulePresentation = (reset = false) => {
			if (reset) expanded = [];
			if (presentationFrame) return;
			presentationFrame = requestAnimationFrame(() => {
				presentationFrame = 0;
				if (disposed || !view) return;
				const folds = onlyChanges
					? unchangedRanges(view.a.state.doc, view.b.state.doc, visibleChunks).filter(
							(pair) =>
								!expanded.some((open) => open.a.from <= pair.a.to && open.a.to >= pair.a.from)
						)
					: [];
				for (const side of ['a', 'b'] as const) {
					view[side].dispatch({
						effects: setDiffPresentation.of(
							presentationDecorations(
								view[side].state.doc,
								side,
								visibleChunks,
								ignoreWhitespace,
								ignoreEmphasis,
								folds,
								(lines) => $i18n.t('Show {{count}} unchanged lines', { count: lines }),
								(pair) => {
									expanded.push(pair);
									schedulePresentation();
								}
							)
						)
					});
				}
			});
		};
		updatePresentation = schedulePresentation;
		let alignmentDocuments: readonly [Text, Text] | null = null;
		let alignmentGeometry: readonly number[] | null = null;
		const scheduleAlignment = () => {
			if (alignmentFrame || disposed) return;
			// Align after both virtualized editors have measured their visible lines.
			alignmentFrame = requestAnimationFrame(() => {
				alignmentFrame = 0;
				if (!disposed && view) {
					const documents = [view.a.state.doc, view.b.state.doc] as const;
					const geometry = [
						view.a.contentDOM.clientWidth,
						view.b.contentDOM.clientWidth,
						view.a.defaultLineHeight,
						view.b.defaultLineHeight
					];
					const resized =
						alignmentGeometry && alignmentGeometryChanged(alignmentGeometry, geometry);
					const reset =
						alignmentDocuments &&
						(alignmentDocuments[0] !== documents[0] ||
							alignmentDocuments[1] !== documents[1] ||
							resized);
					alignmentDocuments = documents;
					if (!alignmentGeometry || resized) alignmentGeometry = geometry;
					if (!reset || !clearLineAlignment(view.a, view.b))
						alignChangedLines(view.a, view.b, view.linePairs);
					view.syncScroll();
				}
			});
		};
		const themes = [new Compartment(), new Compartment()];
		const language = [new Compartment(), new Compartment()];
		const paths = ['a', 'b'].map((side) => paneFile(side)?.path ?? session?.path);
		const review = session?.mode === 'review';
		const undoHistory = new DiffUndoHistory();
		undoSide = null;
		loading = true;
		const extensions = (side: 'a' | 'b', index: number) => [
			basicSetup,
			undoHistory.extension(side),
			EditorState.readOnly.of(review),
			EditorView.editable.of(!review),
			lineAlignment,
			diffPresentation,
			keymap.of([indentWithTab, { key: 'Mod-s', run: () => true }]),
			indentUnit.of('    '),
			EditorView.lineWrapping,
			EditorView.contentAttributes.of({
				'aria-label': paneLabel(side),
				...(review ? { tabindex: '0', 'aria-readonly': 'true' } : {})
			}),
			themes[index].of(document.documentElement.classList.contains('dark') ? oneDark : []),
			language[index].of([]),
			EditorView.updateListener.of((update) => {
				for (const transaction of update.transactions) {
					if (transaction.docChanged) {
						for (const pair of expanded) {
							pair[side].from = transaction.changes.mapPos(pair[side].from);
							pair[side].to = transaction.changes.mapPos(pair[side].to, 1);
						}
					}
				}
				for (const transaction of update.transactions) undoHistory.record(side, transaction);
				undoSide = undoHistory.nextSide;
				if (update.docChanged || update.selectionSet) refresh(update, side);
				if (
					(update.geometryChanged ||
						update.viewportChanged ||
						update.transactions.some((tr) => tr.effects.length)) &&
					!alignmentFrame
				) {
					scheduleAlignment();
				}
			}),
			EditorView.theme({
				'&': { fontSize: '0.75rem', height: '100%' },
				'.cm-scroller': { overflowY: 'auto' },
				'.cm-content': { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' },
				'&.cm-focused': { outline: 'none' }
			})
		];
		void (async () => {
			try {
				if (disposed) return;
				view = new DiffEditorView({
					a: { doc: working, extensions: extensions('a', 0) },
					b: { doc: proposal, extensions: extensions('b', 1) },
					parent: node
				});
				merge = view;
				refresh();
				loading = false;
				observer = new MutationObserver(() => {
					const theme = document.documentElement.classList.contains('dark') ? oneDark : [];
					view?.a.dispatch({ effects: themes[0].reconfigure(theme) });
					view?.b.dispatch({ effects: themes[1].reconfigure(theme) });
				});
				observer.observe(document.documentElement, {
					attributes: true,
					attributeFilter: ['class']
				});
				await Promise.all(
					paths.map(async (path, index) => {
						const match = path && LanguageDescription.matchFilename(languages, path);
						if (!match) return;
						const support = await match.load();
						if (!disposed)
							(index === 0 ? view!.a : view!.b).dispatch({
								effects: language[index].reconfigure(support)
							});
					})
				);
			} catch (cause) {
				if (!disposed) {
					error = cause instanceof Error ? cause.message : String(cause);
					loading = false;
				}
			}
		})();
		return {
			destroy: () => {
				disposed = true;
				cancelAnimationFrame(alignmentFrame);
				cancelAnimationFrame(presentationFrame);
				if (updatePresentation === schedulePresentation) updatePresentation = null;
				observer?.disconnect();
				view?.destroy();
				if (merge === view) merge = null;
			}
		};
	};
</script>

{#if show && session}
	<Modal
		{show}
		ariaLabel={session.title || $i18n.t('Compare revision')}
		size="full"
		containerClassName="p-2 sm:p-4"
		className="h-[calc(100dvh-2rem)] overflow-hidden rounded-2xl bg-white dark:bg-gray-900 !border-0"
		onRequestClose={requestClose}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="diff-editor flex h-full min-h-0 flex-col text-xs"
			on:keydown|capture={preventSave}
			on:keydown={(event) => {
				if (
					event.key === 'Escape' &&
					event.target instanceof Element &&
					event.target.closest('.cm-editor')
				) {
					event.stopPropagation();
				}
			}}
		>
			<header class="flex shrink-0 flex-wrap items-center gap-2 px-5 pt-4 pb-2">
				<div class="min-w-0 flex-1">
					<Tooltip content={session.path ?? ''} allowHTML={false} className="min-w-0">
						<h2 class="truncate font-medium">{session.title || $i18n.t('Compare revision')}</h2>
					</Tooltip>
				</div>
				{#if !comparing && session.mode === 'edit'}
					<button type="button" class="primary" on:click={() => (comparing = true)}
						>{$i18n.t('Compare')}</button
					>
				{/if}
				{#if comparing}
					<div class="comparison-controls flex flex-wrap items-center gap-1.5">
						<div class="mr-1 flex items-center gap-1.5">
							<span class="whitespace-nowrap text-gray-500" role="status" aria-live="polite"
								>{loading
									? $i18n.t('Loading...')
									: chunkCount
										? $i18n.t('Change {{current}} of {{total}}', {
												current: activeChunk + 1,
												total: chunkCount
											})
										: $i18n.t('No differences')}</span
							>
							{#if approximate}<span
									role="img"
									class="text-gray-500"
									aria-label={$i18n.t('Approximate comparison')}
									title={$i18n.t(
										'Comparison reached its time limit; some changes are grouped together.'
									)}>≈</span
								>{/if}
						</div>
						<button
							type="button"
							class="secondary"
							aria-label={$i18n.t('Previous change')}
							title={$i18n.t('Previous change')}
							disabled={!chunkCount || activeChunk === 0}
							on:click={() => reveal(activeChunk - 1)}><span aria-hidden="true">↑</span></button
						>
						<button
							type="button"
							class="secondary"
							aria-label={$i18n.t('Next change')}
							title={$i18n.t('Next change')}
							disabled={!chunkCount || activeChunk === chunkCount - 1}
							on:click={() => reveal(activeChunk + 1)}><span aria-hidden="true">↓</span></button
						>
						{#if session.mode === 'edit'}
							<button
								type="button"
								class="secondary"
								disabled={loading || !undoSide}
								on:click={undoLastChange}>{$i18n.t('Undo')}</button
							>
							<button
								type="button"
								class="secondary"
								disabled={!chunkCount}
								aria-label={$i18n.t('Copy change to proposal')}
								title={$i18n.t('Copy change to proposal')}
								on:click={() => copy('to-proposal')}>{$i18n.t('Original')} →</button
							>
							<button
								type="button"
								class="secondary"
								disabled={!chunkCount}
								aria-label={$i18n.t('Copy change to original')}
								title={$i18n.t('Copy change to original')}
								on:click={() => copy('to-working')}>← {$i18n.t('Proposed revision')}</button
							>
							<button
								type="button"
								class="secondary"
								disabled={loading || !canKeepBoth}
								title={$i18n.t('Keep both versions in the proposed revision, original first.')}
								on:click={keepBoth}>{$i18n.t('Keep both')}</button
							>
						{:else}
							<button type="button" class="secondary" disabled={loading} on:click={swap}
								>{$i18n.t('Swap sides')}</button
							>
							{#if session.onRefresh}
								<button
									type="button"
									class="secondary"
									disabled={refreshing || loading}
									on:click={reload}
									>{refreshing
										? $i18n.t('Refreshing...')
										: error
											? $i18n.t('Retry')
											: $i18n.t('Refresh')}</button
								>
							{/if}
						{/if}
					</div>
				{/if}
				{#if comparing}
					<Dropdown bind:this={optionsDropdown} bind:show={showOptions} align="end">
						<button
							type="button"
							class="comparison-options shrink-0 text-gray-500 hover:text-gray-900 dark:hover:text-white"
							disabled={loading}
							aria-label={$i18n.t('Comparison options')}
							aria-haspopup="menu"
							aria-expanded={showOptions}
						>
							<EllipsisHorizontal className="size-4" />
						</button>
						<div
							slot="content"
							role="presentation"
							on:keydown={(event) => {
								if (event.key === 'Escape') {
									event.stopPropagation();
									optionsDropdown.close();
								}
							}}
						>
							<DropdownMenu className="min-w-48">
								<button
									type="button"
									role="menuitemcheckbox"
									aria-checked={ignoreWhitespace}
									on:click={() => toggleDisplay('whitespace')}
								>
									<svg
										class="size-3.5 shrink-0"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										aria-hidden="true"
										><path d="M4 9v6h16V9" stroke-linecap="round" stroke-linejoin="round" /></svg
									>
									<span class="flex-1 text-left">{$i18n.t('Ignore whitespace')}</span>
									<span class="size-3.5 shrink-0"
										>{#if ignoreWhitespace}<Check className="size-3.5" />{/if}</span
									>
								</button>
								<button
									type="button"
									role="menuitemcheckbox"
									aria-checked={ignoreEmphasis}
									on:click={() => toggleDisplay('emphasis')}
								>
									<Italic className="size-3.5 shrink-0" />
									<span class="flex-1 text-left">{$i18n.t('Ignore emphasis markers')}</span>
									<span class="size-3.5 shrink-0"
										>{#if ignoreEmphasis}<Check className="size-3.5" />{/if}</span
									>
								</button>
								<button
									type="button"
									role="menuitemcheckbox"
									aria-checked={onlyChanges}
									on:click={() => toggleDisplay('unchanged')}
								>
									<LineSpaceSmaller className="size-3.5 shrink-0" />
									<span class="flex-1 text-left">{$i18n.t('Only show changes')}</span>
									<span class="size-3.5 shrink-0"
										>{#if onlyChanges}<Check className="size-3.5" />{/if}</span
									>
								</button>
							</DropdownMenu>
						</div>
					</Dropdown>
				{/if}
				<button
					type="button"
					class="comparison-close shrink-0 text-gray-500 hover:text-gray-900 dark:hover:text-white"
					aria-label={$i18n.t('Close')}
					on:click|stopPropagation={requestClose}><XMark className="size-4" /></button
				>
			</header>
			{#if error}<p class="px-4 py-2 text-red-600" role="alert">{error}</p>{/if}
			{#if session.mode === 'edit' || session.hasProposal}
				<div class="relative flex min-h-0 flex-1">
					<div class="min-h-0 min-w-0 flex-1 overflow-x-auto px-4">
						<div class="flex h-full min-w-[640px] flex-col">
							<div class="grid shrink-0 grid-cols-2 gap-4 py-2">
								{#each ['a', 'b'] as side}
									{@const lines = (side === 'a' ? working : proposal).split(/\r\n|\r|\n/).length}
									{@const file = (side === 'a') !== swapped ? session.leftFile : session.rightFile}
									<div
										class="pane-header flex min-w-0 items-center gap-2 rounded-lg bg-gray-50/70 px-3 py-2 text-gray-500 dark:bg-white/[0.03]"
									>
										<Tooltip content={file?.path ?? ''} allowHTML={false} className="min-w-0">
											<span class="block truncate font-medium"
												>{file?.name ??
													(side === 'a' ? $i18n.t('Original') : $i18n.t('Proposed revision'))}</span
											>
										</Tooltip>
										{#if comparing && !loading}
											<span
												class="whitespace-nowrap"
												class:text-red-600={side === 'a'}
												class:dark:text-red-400={side === 'a'}
												class:text-teal-700={side === 'b'}
												class:dark:text-teal-400={side === 'b'}
												title={$i18n.t('Lines containing changed text')}
											>
												<span aria-hidden="true">{side === 'a' ? '−' : '+'}</span>
												{side === 'a'
													? $i18n.t(
															lineChanges.removed === 1
																? '{{count}} removal'
																: '{{count}} removals',
															{ count: lineChanges.removed }
														)
													: $i18n.t(
															lineChanges.added === 1
																? '{{count}} addition'
																: '{{count}} additions',
															{ count: lineChanges.added }
														)}
											</span>
										{/if}
										<span class="ml-auto whitespace-nowrap text-[11px]"
											>{$i18n.t(lines === 1 ? '{{count}} line' : '{{count}} lines', {
												count: lines
											})}</span
										>
										<button
											type="button"
											class="shrink-0 rounded px-1 hover:text-gray-900 dark:hover:text-white"
											aria-label={file
												? $i18n.t('Copy {{name}} to clipboard', { name: file.name })
												: side === 'a'
													? $i18n.t('Copy original to clipboard')
													: $i18n.t('Copy proposed revision to clipboard')}
											on:click={() => copyPane(side === 'a' ? 'a' : 'b')}
										>
											{copied?.side === side && copied.text === (side === 'a' ? working : proposal)
												? $i18n.t('Copied')
												: $i18n.t('Copy')}
										</button>
									</div>
								{/each}
							</div>
							{#if comparing}
								{#key editorRevision}
									<div
										class="merge-container min-h-0 flex-1"
										class:filtering-differences={ignoreWhitespace || ignoreEmphasis}
										style:--diff-line-digits={lineNumberDigits}
										use:mountMerge
									></div>
								{/key}
							{:else}
								<div class="grid min-h-0 flex-1 grid-cols-2 gap-4">
									<FileCodeEditor
										bind:value={working}
										filePath={session.path}
										ariaLabel={$i18n.t('Original')}
									/>
									<div class="min-h-0 min-w-0">
										<FileCodeEditor
											bind:value={proposal}
											filePath={session.path}
											ariaLabel={$i18n.t('Proposed revision')}
											placeholder={$i18n.t('Paste a proposed revision here...')}
										/>
									</div>
								</div>
							{/if}
						</div>
					</div>
					{#if comparing}
						<div
							class="diff-overview"
							role="slider"
							tabindex={chunkCount ? 0 : -1}
							aria-label={$i18n.t('Change overview')}
							aria-orientation="vertical"
							aria-valuemin={1}
							aria-valuemax={Math.max(1, chunkCount)}
							aria-valuenow={activeChunk + 1}
							aria-valuetext={chunkCount
								? $i18n.t('Change {{current}} of {{total}}', {
										current: activeChunk + 1,
										total: chunkCount
									})
								: $i18n.t('No differences')}
							aria-disabled={!chunkCount}
							on:click={navigateOverview}
							on:keydown={overviewKeydown}
							title={$i18n.t('Click to jump to a change. Use arrow keys to navigate.')}
						>
							<svg viewBox="0 0 20 1000" preserveAspectRatio="none" aria-hidden="true">
								<rect class="overview-track" x="2" y="0" width="6" height="1000" rx="3" />
								<rect class="overview-track" x="12" y="0" width="6" height="1000" rx="3" />
								{#each overview as range, index}
									<rect
										class="overview-removed"
										class:overview-active={index === activeChunk}
										x="2"
										y={Math.min(997, range.a.from * 1000)}
										width="6"
										height={Math.max(3, (range.a.to - range.a.from) * 1000)}
									/>
									<rect
										class="overview-added"
										class:overview-active={index === activeChunk}
										x="12"
										y={Math.min(997, range.b.from * 1000)}
										width="6"
										height={Math.max(3, (range.b.to - range.b.from) * 1000)}
									/>
								{/each}
							</svg>
						</div>
					{/if}
				</div>
			{/if}
			{#if session.mode === 'edit'}
				<footer class="flex shrink-0 flex-wrap items-center gap-2 px-5 py-3">
					<p class="mr-auto text-gray-500">
						{applyDescription ??
							$i18n.t('Apply uses the proposed revision on the right. Save your draft afterward.')}
					</p>
					<button type="button" class="secondary" on:click|stopPropagation={requestClose}
						>{$i18n.t('Cancel')}</button
					>
					<button type="button" class="primary" disabled={loading} on:click={apply}
						>{applyLabel ?? $i18n.t('Apply to draft')}</button
					>
				</footer>
			{/if}
		</div>
	</Modal>
	<ConfirmDialog
		bind:show={confirmDiscard}
		title={$i18n.t('Discard comparison changes?')}
		message={discardMessage ??
			$i18n.t(
				'Your changes in this comparison will be discarded. The original draft will stay unchanged.'
			)}
		confirmLabel={$i18n.t('Discard')}
		onConfirm={close}
	/>
{/if}

<style>
	.comparison-controls {
		margin-left: auto;
	}
	.diff-overview {
		flex: 0 0 20px;
		margin: 2.75rem 6px 0 -10px;
		cursor: pointer;
		border-radius: 4px;
	}
	.diff-overview:focus-visible {
		outline: 2px solid var(--color-gray-500);
		outline-offset: 2px;
	}
	.diff-overview svg {
		width: 100%;
		height: 100%;
		display: block;
	}
	.overview-track {
		fill: #94a3b81a;
	}
	.overview-removed {
		fill: #f0a394;
	}
	.overview-added {
		fill: #7dd3c5;
	}
	.overview-active.overview-removed {
		fill: #e4654c;
	}
	.overview-active.overview-added {
		fill: #0d9488;
	}
	@media (max-width: 900px) {
		.comparison-controls {
			order: 3;
			width: 100%;
		}
		.comparison-options,
		.comparison-close {
			order: 2;
		}
	}

	.secondary,
	.primary {
		display: inline-flex;
		height: 1.5rem;
		min-width: 1.5rem;
		flex-shrink: 0;
		align-items: center;
		justify-content: center;
		gap: 0.375rem;
		border-radius: 0.375rem;
		padding: 0 0.5rem;
		font-size: 0.75rem;
		font-weight: 400;
		transition:
			background-color 150ms,
			color 150ms;
	}
	.secondary {
		background: var(--color-gray-100);
		color: var(--color-gray-800);
	}
	.secondary:hover {
		background: color-mix(in oklab, var(--color-gray-100) 70%, transparent);
	}
	.primary {
		background: var(--color-gray-900);
		color: white;
	}
	.primary:hover {
		background: black;
	}
	button:disabled {
		opacity: 0.4;
	}
	.secondary:disabled,
	.primary:disabled {
		opacity: 0.6;
	}
	button:focus-visible {
		outline: 2px solid var(--color-gray-500);
		outline-offset: 2px;
	}
	:global(.dark) .secondary {
		background: var(--color-gray-850);
		color: white;
	}
	:global(.dark) .secondary:hover {
		background: color-mix(in oklab, var(--color-gray-850) 60%, transparent);
	}
	:global(.dark) .primary {
		background: var(--color-gray-100);
		color: var(--color-gray-900);
	}
	:global(.dark) .primary:hover {
		background: white;
	}
	.merge-container :global(.cm-mergeView) {
		height: 100%;
		overflow: hidden;
	}
	.merge-container :global(.cm-mergeViewEditor) {
		flex: 1 1 0;
		overflow: hidden;
		min-width: 0;
	}
	.merge-container :global(.cm-merge-a .cm-changedLine),
	.merge-container :global(.cm-merge-a .cm-visibleChangedLine) {
		background: #fce9e6;
	}
	.merge-container :global(.cm-merge-b .cm-changedLine),
	.merge-container :global(.cm-merge-b .cm-visibleChangedLine) {
		background: #e0f5f1;
	}
	.merge-container :global(.cm-merge-a .cm-changedText),
	.merge-container :global(.cm-merge-a .cm-visibleChangedText) {
		background: #f9b9ad;
	}
	.merge-container :global(.cm-merge-b .cm-changedText),
	.merge-container :global(.cm-merge-b .cm-visibleChangedText) {
		background: #a3e3d8;
	}
	.merge-container :global(.cm-changedText),
	.merge-container :global(.cm-visibleChangedText) {
		border-radius: 3px;
	}
	.merge-container :global(.cm-mergeSpacer) {
		background: repeating-linear-gradient(135deg, transparent 0 3px, #94a3b814 3px 4px);
	}
	:global(.dark) .merge-container :global(.cm-merge-a .cm-changedLine),
	:global(.dark) .merge-container :global(.cm-merge-a .cm-visibleChangedLine) {
		background: #3d1915;
		color: #f4d0c7;
	}
	:global(.dark) .merge-container :global(.cm-merge-b .cm-changedLine),
	:global(.dark) .merge-container :global(.cm-merge-b .cm-visibleChangedLine) {
		background: #0d302a;
		color: #a9e9dd;
	}
	:global(.dark) .merge-container :global(.cm-changedLine span),
	:global(.dark) .merge-container :global(.cm-visibleChangedLine span) {
		color: inherit;
	}
	:global(.dark) .merge-container :global(.cm-merge-a .cm-changedText),
	:global(.dark) .merge-container :global(.cm-merge-a .cm-visibleChangedText) {
		background: #77362c;
	}
	:global(.dark) .merge-container :global(.cm-merge-b .cm-changedText),
	:global(.dark) .merge-container :global(.cm-merge-b .cm-visibleChangedText) {
		background: #176456;
	}
	:global(.dark) .merge-container :global(.cm-merge-a .cm-changedLineGutter) {
		background: #9b5549;
	}
	:global(.dark) .merge-container :global(.cm-merge-b .cm-changedLineGutter) {
		background: #3e9c89;
	}
	:global(.dark) .merge-container :global(.cm-editor) {
		background: #101413;
	}
	:global(.dark) .merge-container :global(.cm-gutters) {
		background: #101413 !important;
	}
	.merge-container :global(.cm-mergeViewEditors) {
		height: 100%;
		display: flex;
		align-items: stretch;
		gap: 1rem;
	}
	.diff-editor :global(.cm-gutters) {
		border: 0;
		background: transparent;
	}
	.merge-container :global(.cm-lineNumbers) {
		/* Reserve the same gutter width, including padding and fractional glyph rounding. */
		min-width: calc(var(--diff-line-digits) * 1ch + 9px);
	}

	.filtering-differences :global(.cm-changedLine:not(.cm-visibleChangedLine)) {
		background: transparent !important;
		color: inherit !important;
	}
	.filtering-differences :global(.cm-changedText:not(.cm-visibleChangedText)) {
		background: transparent !important;
	}
</style>
