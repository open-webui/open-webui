<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getFileById, getFileContentById } from '$lib/apis/files';
	import { quoteLines, quoteMarks } from '$lib/utils/comments/highlights';

	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';
	import PdfPagesPreview from '$lib/components/common/PdfPagesPreview.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import FilePreview from '$lib/components/chat/FileNav/FilePreview.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import RelevanceBadge from '$lib/components/chat/Messages/Citations/RelevanceBadge.svelte';

	// A cited or attached upload, shown at its cited page. PDFs also mark the cited text.
	let fileId = '';
	let fileLoading = false;
	let fileData: ArrayBuffer | null = null;
	let fileDocxData: ArrayBuffer | null = null;
	let fileSqliteData: ArrayBuffer | null = null;
	let fileModelData: ArrayBuffer | null = null;
	let fileImageUrl: string | null = null;
	let fileVideoUrl: string | null = null;
	let fileAudioUrl: string | null = null;
	let fileContent: string | null = null;
	// What was extracted from a file that cannot be drawn
	let fileText = '';
	let fileOfficeSlides: string[] | null = null;
	let excelWorkbook: import('xlsx').WorkBook | null = null;
	let selectedExcelSheet = '';
	$: fileName = String(embed?.title ?? '');
	$: fileExt = fileName.split('.').pop()?.toLowerCase() ?? '';

	const IMAGE_EXTS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'ico', 'avif']);
	const VIDEO_EXTS = new Set(['mp4', 'webm', 'mov', 'ogv', 'avi', 'mkv']);
	const AUDIO_EXTS = new Set(['mp3', 'wav', 'ogg', 'oga', 'flac', 'm4a', 'aac', 'wma', 'opus']);
	const SQLITE_EXTS = new Set(['db', 'sqlite', 'sqlite3', 'db3']);
	const MODEL_EXTS = new Set(['glb', 'gltf', 'stl', 'obj', 'ply']);
	const EXCEL_EXTS = new Set(['xlsx', 'xls']);
	const LAID_OUT_EXTS = new Set(['pdf', 'docx', 'pptx', ...EXCEL_EXTS]);
	// Text the preview draws as something other than its lines
	const DRAWN_TEXT_EXTS = new Set(
		'md markdown mdx csv tsv html htm json jsonc jsonl json5 svg ipynb'.split(' ')
	);

	const loadFile = async (id: string, ext: string) => {
		fileId = id;
		fileData = fileDocxData = fileSqliteData = fileModelData = null;
		fileImageUrl = fileVideoUrl = fileAudioUrl = null;
		fileContent = fileOfficeSlides = excelWorkbook = null;
		selectedExcelSheet = fileText = '';
		fileLoading = !!id;
		if (!id) return;
		try {
			const url = `${WEBUI_API_BASE_URL}/files/${id}/content`;
			if (IMAGE_EXTS.has(ext)) fileImageUrl = url;
			else if (VIDEO_EXTS.has(ext)) fileVideoUrl = url;
			else if (AUDIO_EXTS.has(ext)) fileAudioUrl = url;
			if (fileImageUrl || fileVideoUrl || fileAudioUrl) return;

			const data = await getFileContentById(id);
			if (fileId !== id || !data) return;
			if (ext === 'pdf') fileData = data;
			else if (ext === 'docx') fileDocxData = data;
			else if (SQLITE_EXTS.has(ext)) fileSqliteData = data;
			else if (MODEL_EXTS.has(ext)) fileModelData = data;
			else if (ext === 'pptx') {
				const { pptxToImages } = await import('$lib/utils/pptxToHtml');
				const slides = (await pptxToImages(data)).images;
				if (fileId === id) fileOfficeSlides = slides;
			} else if (EXCEL_EXTS.has(ext)) {
				const { readExcelWorkbook } = await import('$lib/utils/excelToTable');
				const workbook = await readExcelWorkbook(data);
				if (fileId === id && workbook.SheetNames.length > 0) {
					selectedExcelSheet = workbook.SheetNames[0];
					excelWorkbook = workbook;
				}
			} else {
				// Anything that is not readable as text fails here
				const text = new TextDecoder('utf-8', { fatal: true }).decode(data);
				if (text.includes('\0')) throw new Error('The file is not text');
				if (fileId === id) fileContent = text;
			}
		} catch (e) {
			console.error(e);
			const file = await getFileById(localStorage.token, id).catch(() => null);
			if (fileId === id) fileText = file?.data?.content ?? '';
		} finally {
			if (fileId === id) fileLoading = false;
		}
	};
	$: hasPreview =
		fileDocxData ||
		fileSqliteData ||
		fileModelData ||
		fileImageUrl ||
		fileVideoUrl ||
		fileAudioUrl ||
		fileContent !== null ||
		fileOfficeSlides ||
		excelWorkbook;
	$: if ((embed?.file?.id ?? '') !== fileId) loadFile(embed?.file?.id ?? '', fileExt);
	$: isPlainText = !DRAWN_TEXT_EXTS.has(fileExt) && !LAID_OUT_EXTS.has(fileExt);
	// Code and plain text are drawn as they are, so the lines are matched as they are
	const textLines = (passage: string) => [
		...new Set(
			passage
				.split('\n')
				.map((line) => line.trim())
				.filter((line) => line.length >= 6)
		)
	];
	// Only the lines in view are drawn, so the first cited one is scrolled to
	let textTargetId = 0;
	const getTextTarget = (content: string, passages: { text: string }[]) => {
		for (const { text } of passages) {
			const passage = (text ?? '').trim();
			const quote = [passage, ...textLines(passage)].find(
				(quote) => quote && content.includes(quote)
			);
			if (!quote) continue;

			const before = content.slice(0, content.indexOf(quote)).split(/\r\n?|\n/);
			return {
				line: before.length,
				column: before[before.length - 1].length + 1,
				length: quote.split('\n')[0].length,
				requestId: ++textTargetId
			};
		}
		return null;
	};
	$: textTarget =
		fileContent !== null && isPlainText
			? getTextTarget(fileContent, embed?.file?.passages ?? [])
			: null;
	let filePage: number | null = null;
	let fileQuotes: string[] = [];
	// Hovering a mark shows the retrieved passage it came from.
	let fileQuoteTexts: { text: string; page: number | null; distance?: number | null }[] = [];
	let hoveredText: {
		text: string;
		page: number | null;
		distance?: number | null;
		left: number;
		top: number;
		above: boolean;
	} | null = null;
	const CARD_WIDTH = 352;
	// The card stays while the pointer travels from the mark onto it, so it can be scrolled and selected.
	let closeTimer: ReturnType<typeof setTimeout> | null = null;
	const keepQuoteText = () => {
		if (closeTimer) clearTimeout(closeTimer);
		closeTimer = null;
	};
	const closeQuoteText = (delay = 300) => {
		keepQuoteText();
		closeTimer = setTimeout(() => (hoveredText = null), delay);
	};
	const showQuoteText = (index: number | null, rect: DOMRect | null) => {
		const passage = index === null ? null : fileQuoteTexts[index];
		if (!passage || !rect) return closeQuoteText();
		// Plain text already reads as its passage does, so only its relevance is worth showing
		if (isPlainText && typeof passage.distance !== 'number') return closeQuoteText();
		keepQuoteText();
		// Below the mark, or above it when there is more room there
		const above = rect.bottom > window.innerHeight / 2;
		hoveredText = {
			...passage,
			left: Math.max(12, Math.min(rect.left, window.innerWidth - CARD_WIDTH - 12)),
			top: above ? rect.top - 6 : rect.bottom + 6,
			above
		};
	};
	onDestroy(keepQuoteText);
	// The marks can be put away to read the page undisturbed
	let showQuotes = true;
	const NO_QUOTES: string[] = [];
	$: shownQuotes = showQuotes ? fileQuotes : NO_QUOTES;
	$: if (!showQuotes) hoveredText = null;
	let fileSource: any = null;
	$: if (embed?.file !== fileSource) {
		fileSource = embed?.file ?? null;
		filePage = fileSource?.page ?? null;
		// The cited passages are marked on the pages they appear on
		// Overlapping passages share lines; each line is marked once, for its most relevant passage
		const seen = new Set<string>();
		const quotes = [...(fileSource?.passages ?? [])]
			.sort((a, b) => (b.distance ?? -Infinity) - (a.distance ?? -Infinity) || 0)
			.flatMap((passage) =>
				(isPlainText ? textLines : quoteLines)(passage.text ?? '').map((quote) => ({
					quote,
					passage
				}))
			)
			.filter(({ quote }) => !seen.has(quote) && seen.add(quote));
		fileQuotes = quotes.map(({ quote }) => quote);
		fileQuoteTexts = quotes.map(({ passage }) => passage);
		hoveredText = null;
	}

	const i18n = getContext<any>('i18n');

	/** The cited source this tab shows. */
	export let embed: any;
	export let overlay = false;
	// Preserve the former embed close label for i18n extraction.
	// t('Close embed')

	const getSrcUrl = (url: string, chatId?: string, messageId?: string, sourceId: string) => {
		try {
			const parsed = new URL(url);

			if (chatId) {
				parsed.searchParams.set('chat_id', chatId);
			}

			if (messageId) {
				parsed.searchParams.set('message_id', messageId);
			}

			if (sourceId) {
				parsed.searchParams.set('source_id', sourceId);
			}

			return parsed.toString();
		} catch {
			// Fallback for relative URLs or invalid input
			const hasQuery = url.includes('?');
			const parts = [];

			if (chatId) parts.push(`chat_id=${encodeURIComponent(chatId)}`);
			if (messageId) parts.push(`message_id=${encodeURIComponent(messageId)}`);
			if (sourceId) parts.push(`source_id=${encodeURIComponent(sourceId)}`);

			if (parts.length === 0) return url;

			return url + (hasQuery ? '&' : '?') + parts.join('&');
		}
	};
</script>

{#if embed}
	<div class="h-full w-full flex flex-col">
		<!-- A cited file is named by its tab, like other file tabs -->
		{#if !embed?.file}
			<div
				class="pointer-events-auto z-20 flex justify-between items-center pb-3 px-2 font-primar text-base-900 dark:text-base-0 flex-shrink-0"
			>
				<div class="flex-1 flex items-center justify-between pl-2">
					<a
						class="flex items-center space-x-2 hover:underline"
						href={embed?.url}
						target="_blank"
						rel="noopener noreferrer"
					>
						{embed?.title ?? 'Embedded Content'}
					</a>
				</div>
			</div>
		{/if}

		<div class="w-full flex-1 min-h-0 relative">
			{#if overlay}
				<div class=" absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}

			{#if embed?.file}
				{#if fileData}
					{#key fileSource}
						<PdfPagesPreview
							data={fileData}
							targetPage={filePage}
							highlightQuotes={shownQuotes}
							onQuoteHover={showQuoteText}
							className="w-full h-full"
						>
							<svelte:fragment slot="toolbar">
								{#if fileQuotes.length}
									<Tooltip
										content={showQuotes ? $i18n.t('Hide highlights') : $i18n.t('Show highlights')}
									>
										<button
											type="button"
											class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md transition {showQuotes
												? 'bg-base-100 text-base-900 dark:bg-base-800 dark:text-base-0'
												: 'text-base-500 hover:bg-base-100 dark:text-base-400 dark:hover:bg-base-800'}"
											aria-label={showQuotes
												? $i18n.t('Hide highlights')
												: $i18n.t('Show highlights')}
											aria-pressed={showQuotes}
											on:click={() => (showQuotes = !showQuotes)}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.75"
												stroke-linecap="round"
												stroke-linejoin="round"
												class="size-3.5"
											>
												<path d="m9 11-6 6v3h9l3-3" />
												<path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4" />
											</svg>
										</button>
									</Tooltip>
								{/if}
							</svelte:fragment>
						</PdfPagesPreview>
					{/key}
				{:else if hasPreview}
					<!-- Previews drawn as real text get the cited passages marked too -->
					<div
						class="flex h-full min-h-0 flex-col"
						use:quoteMarks={{
							quotes: shownQuotes,
							onHover: showQuoteText
						}}
					>
						<FilePreview
							selectedFile={fileName}
							fileLoading={false}
							{fileDocxData}
							{fileContent}
							{fileSqliteData}
							{fileModelData}
							{fileImageUrl}
							{fileVideoUrl}
							{fileAudioUrl}
							searchTarget={textTarget}
							wrapLines={true}
							allowScripts={false}
							{fileOfficeSlides}
							{excelWorkbook}
							bind:selectedExcelSheet
							currentSlide={Math.max(0, (filePage ?? 1) - 1)}
							targetPage={filePage}
							target={null}
							readOnly={true}
						>
							<svelte:fragment slot="toolbar">
								{#if fileQuotes.length}
									<Tooltip
										content={showQuotes ? $i18n.t('Hide highlights') : $i18n.t('Show highlights')}
									>
										<button
											type="button"
											class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md transition {showQuotes
												? 'bg-base-100 text-base-900 dark:bg-base-800 dark:text-base-0'
												: 'text-base-500 hover:bg-base-100 dark:text-base-400 dark:hover:bg-base-800'}"
											aria-label={showQuotes
												? $i18n.t('Hide highlights')
												: $i18n.t('Show highlights')}
											aria-pressed={showQuotes}
											on:click={() => (showQuotes = !showQuotes)}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.75"
												stroke-linecap="round"
												stroke-linejoin="round"
												class="size-3.5"
											>
												<path d="m9 11-6 6v3h9l3-3" />
												<path d="m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4" />
											</svg>
										</button>
									</Tooltip>
								{/if}
							</svelte:fragment>
						</FilePreview>
					</div>
				{:else if !fileLoading && fileSource?.passages?.length}
					<!-- The file itself cannot be shown, but what was retrieved from it can -->
					<FilePreview
						selectedFile={isPlainText ? fileName : `${fileName}.md`}
						fileContent={fileSource.passages.map((passage) => passage.text ?? '').join('\n\n')}
						wrapLines={true}
						readOnly={true}
					/>
				{:else if !fileLoading && (fileText || fileSource?.content)}
					<FilePreview
						selectedFile={`${fileName}.md`}
						fileContent={fileText || fileSource.content}
						wrapLines={true}
						readOnly={true}
					/>
				{:else}
					<div
						class="flex h-full flex-col items-center justify-center gap-1 text-xs text-base-500 dark:text-base-400"
					>
						{#if fileLoading}
							<Spinner className="size-3.5 text-base-400 dark:text-base-500" />
						{:else}
							{$i18n.t('Preview failed')}
							{#if fileId}
								<a
									class="underline"
									href={`${WEBUI_API_BASE_URL}/files/${fileId}/content`}
									target="_blank"
									rel="noopener noreferrer">{$i18n.t('Open file')}</a
								>
							{/if}
						{/if}
					</div>
				{/if}
				{#if hoveredText}
					{@const hasRelevance = typeof hoveredText.distance === 'number'}
					{@const hasLabel = hoveredText.page || hasRelevance}
					<!-- Styled as the file and chat hover previews are -->
					<div
						role="tooltip"
						class="fixed z-[9999] flex max-h-[min(17.5rem,calc(100vh-1.5rem))] {isPlainText
							? 'pointer-events-none w-fit'
							: 'w-[22rem]'} max-w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-2xl bg-base-0 font-normal text-base-900 shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-base-1000/5 dark:bg-base-850 dark:text-base-100 dark:ring-base-0/10"
						style:left={`${hoveredText.left}px`}
						style:top={`${hoveredText.top}px`}
						style:transform={hoveredText.above ? 'translateY(-100%)' : ''}
						on:mouseenter={keepQuoteText}
						on:mouseleave={() => closeQuoteText(150)}
					>
						<!-- Labelled as the comment popover on a file is: one quiet line above the text -->
						{#if hasLabel}
							<div
								class="flex shrink-0 items-center gap-3 px-3 pt-2 {isPlainText
									? 'pb-2'
									: 'pb-1'} text-[0.6875rem] leading-4 text-base-500 dark:text-base-400"
							>
								{#if hoveredText.page}
									<span>{$i18n.t('Page')} {hoveredText.page}</span>
								{/if}
								{#if hasRelevance}
									<span class="flex items-center gap-1.5">
										{$i18n.t('Relevance')}
										<RelevanceBadge
											distance={hoveredText.distance}
											showPercentage={embed.file.showPercentage}
										/>
									</span>
								{/if}
							</div>
						{/if}
						{#if !isPlainText}
							<!-- Everything at the small preview size, headings and tables included -->
							<div
								class="markdown-prose-xs min-h-0 min-w-full max-w-full flex-1 overflow-auto scrollbar-thin px-3 pb-2 {hasLabel
									? 'pt-1'
									: 'pt-2'} !leading-snug text-base-800 dark:text-base-200 [&_*]:!text-xs [&_*]:!leading-snug [&_:is(h1,h2,h3,h4,h5,h6)]:!my-1 [&_:is(h1,h2,h3,h4,h5,h6)]:!font-medium [&_:is(td,th)]:!px-1.5 [&_:is(td,th)]:!py-0.5 [&_:is(td,th)]:!text-[0.6875rem] [&_strong]:!font-medium"
							>
								<Markdown
									content={hoveredText.text.trim().replace(/\n\n+/g, '\n\n')}
									id="cited-passage"
								/>
							</div>
						{/if}
					</div>
				{/if}
			{:else}
				<FullHeightIframe
					src={getSrcUrl(embed?.url ?? '', embed?.chatId, embed?.messageId, embed?.sourceId)}
					payload={embed?.source ?? null}
					iframeClassName="w-full h-full"
				/>
			{/if}
		</div>
	</div>
{/if}
