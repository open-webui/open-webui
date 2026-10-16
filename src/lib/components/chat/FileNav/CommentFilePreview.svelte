<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import type { WorkBook } from 'xlsx';
	export let onReady = () => {};
	export let currentSlide = 0;
	let reportedReady = false;
	export let initialSheet = '';
	const reportReady = () => {
		if (!loading && !previewError && !reportedReady) {
			reportedReady = true;
			onReady();
		}
	};
	$: (loading, previewError, reportReady());

	import { downloadFileBlob, downloadFilePreview } from '$lib/apis/terminal';
	import { readOfficeComments } from '$lib/utils/comments/office';
	import {
		commentThreads,
		type FileComment,
		type CommentResult,
		type CommentState
	} from '$lib/utils/comments/types';
	import FilePreview from './FilePreview.svelte';
	import Icon from './Icon.svelte';
	import DocxPreview from '$lib/components/common/DocxPreview.svelte';
	import PdfPagesPreview from '$lib/components/common/PdfPagesPreview.svelte';
	import PptxPreview from '$lib/components/common/PptxPreview.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	const i18n: any = getContext('i18n');
	export let path: string;
	export let baseUrl: string;
	export let apiKey: string;
	export let chatId: string | null = null;
	export let targetPage: number | null = null;
	let comments: FileComment[] = [];
	let warnings: string[] = [];
	let commentState: CommentState = 'loading';
	let hoveredId: string | null = null;
	let pinned = false;
	let touchInteraction = false;
	let overHighlight = false;
	let popoverX = 0;
	let popoverY = 0;
	let closeTimer: ReturnType<typeof setTimeout>;
	let original: ArrayBuffer | null = null;
	let pdf: ArrayBuffer | null = null;
	let loading = true;
	let previewError = false;
	let slides: string[] = [];
	let workbook: WorkBook | null = null;
	export let sheet = '';
	let table: string | null = null;
	let root: HTMLDivElement;
	let popover: HTMLDivElement;
	let alive = true;
	let sheetToken = 0;
	let anchoredIds: string[] = [];
	const abort = new AbortController();
	const ext = path.split('.').pop()!.toLowerCase();
	$: threads = commentThreads(comments);
	$: hoveredThreads =
		hoveredId === '__unplaced'
			? threads.filter((thread) => !anchoredIds.includes(thread[0].id))
			: threads.filter((thread) => thread.some((c) => c.id === hoveredId));
	$: unplaced = threads.map((thread) => thread[0]).filter((c) => !anchoredIds.includes(c.id));
	const receiveAnchors = (ids: string[]) => {
		if (ids.length !== anchoredIds.length || ids.some((id, i) => id !== anchoredIds[i]))
			anchoredIds = ids;
	};
	const receiveComments = (result: CommentResult) => {
		if (!alive) return;
		comments = result.comments;
		warnings = result.warnings;
		commentState = warnings.length ? 'partial' : 'ready';
	};
	const setSheet = async (name: string) => {
		if (!workbook?.Sheets[name]) return;
		const token = ++sheetToken;
		sheet = name;
		const { excelToTable } = await import('$lib/utils/excelToTable');
		const result = await excelToTable(workbook.Sheets[name]);
		if (alive && token === sheetToken) {
			table = result.html;
			anchoredIds = comments
				.filter((c) => c.location?.kind === 'cell' && c.location.sheet === sheet)
				.map((c) => c.id);
		}
	};
	const keepOpen = () => clearTimeout(closeTimer);
	const closeLater = (event?: MouseEvent | FocusEvent) => {
		keepOpen();
		const next = event?.relatedTarget;
		if (
			next instanceof Element &&
			(popover?.contains(next) ||
				next.closest<HTMLElement>('[data-file-comment-id]')?.dataset.fileCommentId === hoveredId)
		)
			return;
		if (!pinned) closeTimer = setTimeout(() => (hoveredId = null), 100);
	};
	const reveal = (event: MouseEvent | FocusEvent, pin = false) => {
		overHighlight = false;
		if (event instanceof MouseEvent && (event.buttons || window.getSelection()?.type === 'Range')) {
			if (!pinned) {
				keepOpen();
				hoveredId = null;
			}
			return;
		}
		let element = (event.target as HTMLElement).closest<HTMLElement>(
			'[data-file-comment-id],[data-cell]'
		);
		// Highlights are pointer-transparent so dragging selects the document text.
		if (!element && event instanceof MouseEvent) {
			const page = (event.target as HTMLElement).closest('.pdf-page-wrapper');
			element =
				Array.from((page ?? root).querySelectorAll<HTMLElement>('[data-comment-highlight]')).find(
					(highlight) => {
						const rect = highlight.getBoundingClientRect();
						return (
							event.clientX >= rect.left &&
							event.clientX <= rect.right &&
							event.clientY >= rect.top &&
							event.clientY <= rect.bottom
						);
					}
				) ?? null;
		}
		if (!element) {
			closeLater();
			return;
		}
		overHighlight = event instanceof MouseEvent && !!element.dataset.commentHighlight;
		const id =
			element.dataset.fileCommentId ??
			comments.find(
				(c) =>
					c.location?.kind === 'cell' &&
					c.location.sheet === sheet &&
					c.location.cell === element.dataset.cell
			)?.id;
		if (!id) return;
		keepOpen();
		if (id === hoveredId) {
			if (pin) pinned = true;
			return;
		}
		hoveredId = id;
		pinned = pin;
		const rect = element.getBoundingClientRect();
		popoverX = Math.max(8, Math.min(window.innerWidth - 296, rect.left));
		popoverY = Math.max(8, Math.min(window.innerHeight - 260, rect.bottom + 10));
	};
	const displayDate = (value: string) => {
		const pdf = /^D:(\d{4})(\d{2})(\d{2})/.exec(value);
		const date = new Date(pdf ? `${pdf[1]}-${pdf[2]}-${pdf[3]}` : value);
		return Number.isNaN(date.getTime())
			? ''
			: date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
	};
	const portal = (node: HTMLElement) => {
		document.body.appendChild(node);
		const observer = new ResizeObserver(() => {
			const rect = node.getBoundingClientRect();
			popoverX = Math.max(8, Math.min(popoverX, window.innerWidth - rect.width - 8));
			popoverY = Math.max(8, Math.min(popoverY, window.innerHeight - rect.height - 8));
		});
		observer.observe(node);
		return {
			destroy: () => {
				observer.disconnect();
				node.remove();
			}
		};
	};
	async function load() {
		const previewPromise = ['docx', 'pptx'].includes(ext)
			? downloadFilePreview(baseUrl, apiKey, path, chatId ?? undefined, abort.signal)
					.then(async (r) => {
						if (r) {
							const bytes = await r.blob.arrayBuffer();
							if (alive) {
								pdf = bytes;
								loading = false;
							}
						}
					})
					.catch(() => undefined)
			: Promise.resolve();
		try {
			const raw = await downloadFileBlob(baseUrl, apiKey, path, chatId ?? undefined, abort.signal);
			if (!raw) throw new Error('Original file unavailable');
			const bytes = await raw.blob.arrayBuffer();
			if (!alive) return;
			original = bytes;
			if (ext === 'pdf') {
				pdf = bytes;
				loading = false;
				return;
			}
			if (ext === 'xlsx' || ext === 'xls') {
				const XLSX = await import('xlsx');
				if (!alive) return;
				workbook = XLSX.read(bytes, { type: 'array' });
				await setSheet(workbook.Sheets[initialSheet] ? initialSheet : workbook.SheetNames[0]);
				loading = false;
			}
			void readOfficeComments(bytes, ext, workbook ?? undefined)
				.then((result) => {
					receiveComments(result);
					if (workbook)
						anchoredIds = comments
							.filter((c) => c.location?.kind === 'cell' && c.location.sheet === sheet)
							.map((c) => c.id);
				})
				.catch(() => {
					if (alive) commentState = 'error';
				});
			await previewPromise;
			if (!alive) return;
			if (!pdf && ext === 'pptx') {
				const { pptxToImages } = await import('$lib/utils/pptxToHtml');
				const result = await pptxToImages(bytes);
				if (alive) slides = result.images;
			}
		} catch {
			if (alive) {
				commentState = 'error';
				previewError = true;
			}
		} finally {
			await previewPromise;
			if (alive) loading = false;
		}
	}
	onMount(() => {
		void load();
	});
	onDestroy(() => {
		alive = false;
		abort.abort();
		clearTimeout(closeTimer);
	});
</script>

<svelte:window
	on:click={(event) => {
		const target = event.target;
		if (target instanceof Node && !root?.contains(target) && !popover?.contains(target)) {
			keepOpen();
			pinned = false;
			hoveredId = null;
		}
	}}
	on:keydown={(event) => {
		if (event.key === 'Escape') {
			pinned = false;
			hoveredId = null;
		}
	}}
/>
<!-- Events are delegated from generated highlight buttons and focusable spreadsheet cells. -->
<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events a11y_mouse_events_have_key_events -->
<div
	bind:this={root}
	class="relative flex-1 h-full min-h-0 min-w-0 overflow-hidden"
	class:comment-hover={overHighlight}
	on:mouseover={reveal}
	on:mousemove={reveal}
	on:focusin={reveal}
	on:mouseout={closeLater}
	on:focusout={closeLater}
	on:pointerdown={(e) => {
		touchInteraction = e.pointerType === 'touch';
		if (!(e.target as HTMLElement).closest('[data-file-comment-id],[data-cell]')) {
			keepOpen();
			pinned = false;
			hoveredId = null;
		}
	}}
	on:click={(e) => reveal(e, touchInteraction || e.detail === 0)}
>
	{#if loading}<div class="flex h-full items-center justify-center"><Spinner /></div>
	{:else if pdf}
		<PdfPagesPreview
			bind:currentSlide
			data={pdf}
			{targetPage}
			singlePage={ext === 'pptx'}
			className="w-full h-full"
			sourceComments={ext !== 'pdf' ? comments : null}
			onAnchors={receiveAnchors}
			onComments={ext === 'pdf' ? receiveComments : null}
			onCommentsError={() => (commentState = 'error')}
		/>
	{:else if ext === 'docx' && original}
		<DocxPreview
			data={original}
			{targetPage}
			className="h-full"
			reviewComments={comments}
			onAnchors={receiveAnchors}
		/>
	{:else if ext === 'pptx' && slides.length}
		<PptxPreview bind:currentSlide {slides} {targetPage} className="h-full" {comments} />
	{:else if table !== null}
		<FilePreview
			selectedFile={path}
			fileOfficeHtml={table}
			excelSheetNames={workbook?.SheetNames ?? []}
			selectedExcelSheet={sheet}
			onSheetChange={setSheet}
		/>
	{:else if previewError}<p class="p-4 text-sm text-red-500">{$i18n.t('Preview failed')}</p>{/if}
	{#if unplaced.length || commentState === 'error' || commentState === 'partial'}
		<button
			type="button"
			data-file-comment-id="__unplaced"
			class="absolute right-3 top-3 z-10 flex h-6 items-center gap-1 rounded px-1.5 text-xs text-gray-400 dark:text-gray-500 bg-white/95 dark:bg-gray-850/95 hover:text-gray-600 dark:hover:text-gray-300 focus-visible:outline focus-visible:outline-2"
			aria-label={$i18n.t('Document comments')}
			aria-haspopup="dialog"
			><Icon name="chat-bubble" size={12} strokeWidth={1.5} />{unplaced.length || '!'}</button
		>
	{/if}
</div>
{#if hoveredId}
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		use:portal
		bind:this={popover}
		role="dialog"
		aria-label={$i18n.t('Comment')}
		tabindex="-1"
		class="file-comment-popover fixed z-[9999] w-72 max-w-[calc(100vw-1rem)] max-h-[50vh] overflow-y-auto rounded-2xl bg-white px-3 py-2 text-[0.8125rem] font-normal leading-5 text-gray-900 shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-black/5 dark:bg-gray-850 dark:text-gray-100 dark:ring-white/10"
		style:left={`${popoverX}px`}
		style:top={`${popoverY}px`}
		on:mouseenter={keepOpen}
		on:mouseleave={closeLater}
		on:focusin={keepOpen}
		on:focusout={closeLater}
	>
		<button
			type="button"
			class="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded text-gray-400 transition-colors duration-100 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 focus-visible:outline focus-visible:outline-2"
			aria-label={$i18n.t('Close comment')}
			on:click={() => {
				hoveredId = null;
				pinned = false;
			}}><Icon name="xmark" size={11} strokeWidth={1.5} /></button
		>
		{#if commentState === 'error'}<p>
				{$i18n.t('Could not read comments. Download the original file to review them.')}
			</p>{/if}
		{#each warnings as warning}<p class="text-xs text-amber-700">{warning}</p>{/each}
		{#each hoveredThreads as thread (thread[0].id)}
			<div class="comment-thread">
				{#if thread[0].status === 'resolved'}<span class="text-xs text-gray-500"
						>{$i18n.t('Resolved')}</span
					>{/if}
				{#each thread as comment (comment.id)}
					<div class="comment-message">
						<div class="pr-6 text-xs font-medium text-gray-900 dark:text-gray-100">
							{comment.author || $i18n.t('Unknown author')}
						</div>
						{#if comment.date}<div class="text-[11px] leading-4 text-gray-500 dark:text-gray-400">
								{displayDate(comment.date)}
							</div>{/if}
						<p class="mt-1.5 whitespace-pre-wrap break-words text-[0.8125rem] leading-5">
							{comment.text || $i18n.t('Annotation without text')}
						</p>
						{#if hoveredId === '__unplaced'}<p class="mt-1 text-xs text-gray-500">
								{comment.location?.kind === 'cell'
									? `${comment.location.sheet}!${comment.location.cell}`
									: comment.location?.kind === 'slide'
										? `${$i18n.t('Slide')} ${comment.location.slide}`
										: $i18n.t('Location unavailable')}
							</p>{/if}
					</div>
				{/each}
			</div>
		{/each}
	</div>
{/if}

<style>
	.comment-hover,
	.comment-hover :global(:hover) {
		cursor: help;
	}
	.comment-message {
		overflow-wrap: anywhere;
	}
	.comment-thread + .comment-thread,
	.comment-message + .comment-message {
		margin-top: 8px;
		padding-top: 8px;
		border-top: 1px solid rgb(0 0 0 / 5%);
	}
	:global(.dark) .comment-thread + .comment-thread,
	:global(.dark) .comment-message + .comment-message {
		border-color: rgb(255 255 255 / 10%);
	}
</style>
