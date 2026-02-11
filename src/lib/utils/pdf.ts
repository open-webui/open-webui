import DOMPurify from 'dompurify';
import canvasSize from 'canvas-size';
import html2canvas, { type Options as Html2CanvasOptions } from 'html2canvas-pro';
import { jsPDF } from 'jspdf';
import type JSPDF from 'jspdf';
import i18n from 'i18next';
import { writable } from 'svelte/store';

// ==================== Type Definitions ====================

/**
 * Note data structure
 */
interface NoteData {
	/** Note title */
	title: string;
	/** Note content data */
	data?: {
		/** Content object */
		content?: {
			/** HTML content (can be string or HTMLElement) */
			html?: string | HTMLElement;
		};
	};
}

/**
 * Options for downloading chat PDF
 */
interface ChatPdfOptions {
	/** ID of the container element to render (for stylized mode) */
	containerElementId?: string;
	/** Plain text content (for plain text mode) */
	chatText?: string;
	/** PDF filename (without .pdf extension) */
	title: string;
	/** Whether to use stylized PDF export (default: true) */
	stylizedPdfExport?: boolean;
	/** Optional callback before rendering (for showing full messages) */
	onBeforeRender?: () => Promise<void> | void;
	/** Optional callback after rendering (for hiding full messages) */
	onAfterRender?: () => Promise<void> | void;
	/** Optional callback for export progress updates */
	onProgress?: (progress: PdfExportProgress) => void;
	/** Optional chunk selector for stylized mode */
	chunkSelector?: string;
	/** Optional abort signal for cancellation */
	signal?: AbortSignal;
}

interface ElementRenderChunk {
	y: number;
	height: number;
}

interface PdfAppendState {
	pageCount: number;
}

interface AppendCanvasChunkOptions {
	stopWhenEncounteringEmptySlice?: boolean;
}

interface AppendCanvasChunkResult {
	pagesAdded: number;
	encounteredEmptySlice: boolean;
}

export type PdfExportOverlayState = {
	show: boolean;
	stage: PdfExportStage;
	title: string;
	stageText: string;
	progress: number;
	currentChunk: number;
	totalChunks: number;
	pagesGenerated: number;
	estimatedRemainingMinutes: number | null;
	onCancel?: () => void;
};

export const pdfExportOverlay = writable<PdfExportOverlayState>({
	show: false,
	stage: 'preparing',
	title: 'Exporting PDF',
	stageText: 'Preparing export...',
	progress: 0,
	currentChunk: 0,
	totalChunks: 0,
	pagesGenerated: 0,
	estimatedRemainingMinutes: null,
	onCancel: undefined
});

type PdfExportStage = 'preparing' | 'rendering' | 'saving' | 'done';

interface PdfExportProgress {
	stage: PdfExportStage;
	percent: number;
	currentChunk?: number;
	totalChunks?: number;
	pagesGenerated?: number;
}

interface RenderElementToCanvasOptions {
	canvas?: HTMLCanvasElement;
	x?: number;
	y?: number;
	width?: number;
	height?: number;
	elementHeight?: number;
	onclone?: (document: Document, element: HTMLElement) => void;
	ignoreElements?: (element: Element) => boolean;
	lastElementY?: number;
}

// ==================== Shared Constants ====================

/** A4 page width in millimeters */
const A4_PAGE_WIDTH_MM = 210;
/** A4 page height in millimeters */
const A4_PAGE_HEIGHT_MM = 297;
/** Default virtual width in pixels for cloned element */
const DEFAULT_VIRTUAL_WIDTH = 800;
/** Canvas scale factor for increased resolution */
const CANVAS_SCALE = window.devicePixelRatio || 2;
/** JPEG quality for canvas encoding before PDF embedding */
const JPEG_QUALITY = 0.95;
/** Conservative browser canvas edge limit in pixels */
const MAX_CANVAS_EDGE_PX = 16384;
/** Conservative browser canvas area limit in pixels */
const MAX_CANVAS_AREA_PX = 268_000_000;
/** Extra tail guard height to avoid clipping final content */
const RENDER_TAIL_GUARD_PX = 128;
/** Step size used when probing canvas height fallback tests */
const CANVAS_PROBE_STEP_PX = 1024;

const canvasMaxHeightProbeCache = new Map<number, Promise<number | null>>();
const sharedProbeCanvas = document.createElement('canvas');
let sharedProbeContext: CanvasRenderingContext2D | null = null;

/** Whether the current browser is little-endian */
const IS_LITTLE_ENDIAN = new Uint8Array(new Uint32Array([0x01020304]).buffer)[0] === 0x04;
const pixelDiffersFromBackground = IS_LITTLE_ENDIAN
	? (pixel: number, bg: number, tolerance: number): boolean => {
			const r = pixel & 0xff;
			const g = (pixel >>> 8) & 0xff;
			const b = (pixel >>> 16) & 0xff;
			return (
				Math.abs(r - bg) > tolerance ||
				Math.abs(g - bg) > tolerance ||
				Math.abs(b - bg) > tolerance
			);
		}
	: (pixel: number, bg: number, tolerance: number): boolean => {
			const r = (pixel >>> 24) & 0xff;
			const g = (pixel >>> 16) & 0xff;
			const b = (pixel >>> 8) & 0xff;
			return (
				Math.abs(r - bg) > tolerance ||
				Math.abs(g - bg) > tolerance ||
				Math.abs(b - bg) > tolerance
			);
		};

// ==================== Shared Utility Functions ====================

/**
 * Check if dark mode is enabled in the document
 * @returns True if dark mode is enabled, false otherwise
 */
const isDarkMode = (): boolean => {
	return document.documentElement.classList.contains('dark');
};

const createAbortError = (): Error => {
	const error = new Error('PDF export cancelled');
	error.name = 'AbortError';
	return error;
};

const throwIfAborted = (signal?: AbortSignal): void => {
	if (signal?.aborted) {
		throw createAbortError();
	}
};

const emitExportProgress = (
	callback: ((progress: PdfExportProgress) => void) | undefined,
	progress: PdfExportProgress
): void => {
	callback?.(progress);
};

const getStageText = (stage: PdfExportStage): string => {
	if (stage === 'preparing') return i18n.t('Preparing export...');
	if (stage === 'rendering') return i18n.t('Rendering content...');
	if (stage === 'saving') return i18n.t('Saving PDF...');
	return i18n.t('Completed');
};

const getEstimatedRemainingMinutes = (startedAt: number, progressPercent: number): number | null => {
	if (progressPercent <= 0 || progressPercent >= 100) {
		return null;
	}

	const elapsedMs = Date.now() - startedAt;
	if (elapsedMs <= 0) {
		return null;
	}

	const remainingMs = (elapsedMs * (100 - progressPercent)) / progressPercent;
	return Math.max(0, Math.ceil(remainingMs / 60_000));
};

/**
 * Create a new A4 PDF document
 * @returns New jsPDF instance configured for A4 portrait orientation
 */
const createPdfDocument = async () => {
	return new jsPDF('p', 'mm', 'a4');
};

/**
 * Apply dark mode background to PDF page if dark mode is enabled
 * @param pdf - jsPDF instance
 * @param pageWidthMM - Page width in millimeters
 * @param pageHeightMM - Page height in millimeters
 */
const applyDarkModeBackground = (pdf: JSPDF, pageWidthMM: number, pageHeightMM: number): void => {
	if (isDarkMode()) {
		pdf.setFillColor(0, 0, 0);
		pdf.rect(0, 0, pageWidthMM, pageHeightMM, 'F'); // black bg
	}
};

/**
 * Style a DOM element for PDF rendering (hidden, positioned off-screen)
 * @param element - DOM element to style
 * @param virtualWidth - Virtual width in pixels for the element
 */
const styleElementForRendering = (element: HTMLElement, virtualWidth: number): void => {
	element.classList.add('text-black');
	element.classList.add('dark:text-white');
	element.style.width = `${virtualWidth}px`;
	element.style.position = 'absolute';
	element.style.left = '-9999px';
	element.style.height = 'auto';
	element.dataset.cloningElement = 'true';
};

/**
 * Render DOM element to canvas using html2canvas
 * @param element - DOM element to render
 * @param virtualWidth - Virtual width in pixels
 * @returns Promise that resolves to a canvas element
 */
const renderElementToCanvas = async (
	element: HTMLElement,
	virtualWidth: number,
	options?: RenderElementToCanvasOptions,
	elmChunks?: { y: number; height: number }[]
): Promise<HTMLCanvasElement> => {
	const isDark = isDarkMode();
	const cropY = options?.y ?? 0;
	// 确保至少渲染1px
	const cropHeight = Math.max(1, Math.ceil(options?.height ?? 0));
	const currentChunkEndY = cropY + cropHeight;

	// 1. 计算当前的“基准 Y (Base Y)”
	// 基准 Y 指的是：在当前视口范围内，第一个“应该出现”的元素原本的 Y 坐标。
	// 因为我们移除了它上面的所有元素，它在克隆 DOM 里会跑到顶部。
	// 我们用这个基准 Y 来计算相对偏移量。
	
	let baseContentY = 0;
	
	// 为了快速判断，我们先处理 elmChunks（如果传了的话）
	// 找到第一个与当前视图 [cropY, currentChunkEndY] 相交的 chunk
	if (elmChunks && elmChunks.length > 0) {
		const firstVisibleChunk = elmChunks.find(chunk => {
			const chunkBottom = chunk.y + chunk.height;
			// 排除掉：完全在上面 (bottom <= cropY) 或 完全在下面 (y >= endY) 的
			return !(chunkBottom <= cropY || chunk.y >= currentChunkEndY);
		});
		
		if (firstVisibleChunk) {
			baseContentY = firstVisibleChunk.y;
		} else {
			// 如果没有找到相交的chunk（比如是纯空白区域），默认不对齐
			// 或者如果 cropY 超过了所有内容，就以 cropY 为准
			baseContentY = cropY; 
		}
	} else {
		// 如果没传 elmChunks（比如 tail 渲染阶段），我们只能保守一点，
		// 假设没有发生 DOM 塌缩，或者只能依赖 dataset 实时判断。
		// 但根据你的逻辑，这里我们主要处理“正文”部分的逻辑。
		// 如果不传 elmChunks，我们默认不进行坐标偏移（因为不知道原来在哪里），
		// 但为了兼容性，建议尽可能传入 elmChunks。
		baseContentY = 0; 
	}
	
	// 特殊情况：如果实际上我们是从 0 开始截取的，基准肯定也是 0
	if (cropY === 0) baseContentY = 0;

	// 2. 计算修正后的 captureY
	// 如果上面的元素被删了，当前内容跑到了 0 (或 padding 处)。
	// 我们原本想在 cropY 处截图，现在应该在 (cropY - baseContentY) 处截图。
	// 比如：想要截取 5000-6000。第一个元素从 4800 开始。
    // 删掉 4800 以前的。该元素变到了 0。
	// 我们需要截取该元素内部 200px 处开始的内容。即 5000 - 4800 = 200。
	const captureY = Math.max(0, cropY - baseContentY);

	const canvasOptions: Partial<Html2CanvasOptions> = {
		useCORS: true,
		allowTaint: true,
		backgroundColor: isDark ? '#000' : '#fff',
		scale: CANVAS_SCALE,
		windowWidth: virtualWidth,
		// 视口高度只需要覆盖我们要截取的部分即可，不用设太大，节省内存
		windowHeight: Math.max(captureY + cropHeight + 100, 1000), 
		x: options?.x || 0,
		y: captureY, // 关键：使用计算后的相对坐标
		width: options?.width ?? virtualWidth,
		height: cropHeight,
		canvas: options?.canvas,
		ignoreElements(elm) {
			// 1. 基础过滤
			if (options?.ignoreElements && options.ignoreElements(elm)) {
				return true;
			}
			if (elm.parentNode === document.body) {
				return (elm as HTMLElement).dataset?.cloningElement !== 'true';
			}

			// 2. 核心性能过滤逻辑
			if (elm instanceof HTMLElement) {
				const cloningHeightStr = elm.dataset.cloningHeight;
				const cloningYStr = elm.dataset.cloningY;

				// 只有当元素有明确的坐标标记（即主要内容块）时，确实执行过滤
				if (cloningHeightStr && cloningYStr) {
					const elmY = parseInt(cloningYStr, 10);
					const elmH = parseInt(cloningHeightStr, 10);
					const elmBottom = elmY + elmH;

					// 判断逻辑：
					// 1. 元素底部 <= cropY：说明元素完全在当前视窗上方 -> 忽略 (return true)
					// 2. 元素顶部 >= currentChunkEndY：说明元素完全在当前视窗下方 -> 忽略 (return true)
					if (elmBottom <= cropY || elmY >= currentChunkEndY) {
						return true; // 移除元素！性能极大提升
					}
				}
			}
			
			return false;
		}
	};

	const canvas = await html2canvas(element, canvasOptions);
	return canvas;
};

const getSafeRenderChunkHeightPxFallback = (virtualWidth: number, scale: number): number => {
	const canvasWidthPx = Math.max(1, Math.floor(virtualWidth * scale));
	const maxHeightByEdge = Math.floor(MAX_CANVAS_EDGE_PX / scale);
	const maxHeightByArea = Math.floor(MAX_CANVAS_AREA_PX / canvasWidthPx / scale);
	return Math.max(1, Math.min(maxHeightByEdge, maxHeightByArea));
};

const probeMaxCanvasHeightPx = async (canvasWidthPx: number): Promise<number | null> => {
	try {
		const [maxHeightResult, maxAreaResult] = await Promise.all([
			canvasSize.maxHeight({ useWorker: true, usePromise: true }),
			canvasSize.maxArea({ useWorker: true, usePromise: true })
		]);

		const maxHeightPx = Math.max(1, Math.floor(maxHeightResult.height || 1));
		const maxAreaPx = Math.max(1, Math.floor((maxAreaResult.width || 1) * (maxAreaResult.height || 1)));
		const maxHeightByAreaPx = Math.max(1, Math.floor(maxAreaPx / canvasWidthPx));
		let candidateHeightPx = Math.max(1, Math.min(maxHeightPx, maxHeightByAreaPx));

		const firstValidation = await canvasSize.test({
			width: canvasWidthPx,
			height: candidateHeightPx,
			useWorker: true,
			usePromise: true
		});
		if (firstValidation) {
			return candidateHeightPx;
		}

		while (candidateHeightPx > 1) {
			candidateHeightPx = Math.max(1, candidateHeightPx - CANVAS_PROBE_STEP_PX);
			const validation = await canvasSize.test({
				width: canvasWidthPx,
				height: candidateHeightPx,
				useWorker: true,
				usePromise: true
			});
			if (validation) {
				return candidateHeightPx;
			}
		}
	} catch (error) {
		console.warn('Failed to probe canvas size via canvas-size:', error);
	}

	return null;
};

/**
 * Compute a safe chunk height in CSS pixels based on browser canvas limits.
 */
const getSafeRenderChunkHeightPx = async (virtualWidth: number, scale: number): Promise<number> => {
	const canvasWidthPx = Math.max(1, Math.floor(virtualWidth * scale));
	const fallbackSafeHeightPx = getSafeRenderChunkHeightPxFallback(virtualWidth, scale);
	const probePromise = canvasMaxHeightProbeCache.get(canvasWidthPx) ?? probeMaxCanvasHeightPx(canvasWidthPx);
	canvasMaxHeightProbeCache.set(canvasWidthPx, probePromise);
	const probedMaxHeightPx = await probePromise;
	const safeHeight =
		probedMaxHeightPx && probedMaxHeightPx > 0
			? Math.max(1, Math.floor(probedMaxHeightPx / scale))
			: fallbackSafeHeightPx;
	const a4PageHeightPx = Math.max(
		1,
		Math.floor((A4_PAGE_HEIGHT_MM / A4_PAGE_WIDTH_MM) * virtualWidth)
	);

	// Prefer chunk size that is an integer multiple of one A4 page height.
	const a4PageMultiple = Math.floor(safeHeight / a4PageHeightPx);
	const safeHeightAlignedToA4 =
		a4PageMultiple > 0 ? a4PageMultiple * a4PageHeightPx : safeHeight;

	return safeHeightAlignedToA4;
};

/**
 * Build render chunks from element children, with canvas-safe chunking.
 * @param element - Root element used for rendering
 * @param maxChunkHeightPx - Max chunk height in CSS pixels
 * @returns Render chunks in CSS pixel coordinates
 */
const buildElementRenderChunks = (
	element: HTMLElement,
	maxChunkHeightPx: number
): ElementRenderChunk[] => {
	const splitRange = (startY: number, totalHeight: number): ElementRenderChunk[] => {
		const chunks: ElementRenderChunk[] = [];
		let offset = 0;
		while (offset < totalHeight) {
			const chunkHeight = Math.min(maxChunkHeightPx, totalHeight - offset);
			chunks.push({
				y: Math.max(0, Math.floor(startY + offset)),
				height: Math.max(1, Math.ceil(chunkHeight))
			});
			offset += chunkHeight;
		}
		return chunks;
	};

	const rootRect = element.getBoundingClientRect();
	const lastChildBottom =
		element.lastElementChild instanceof HTMLElement
			? Math.max(0, element.lastElementChild.getBoundingClientRect().bottom - rootRect.top)
			: 0;
	const fullHeight = Math.max(
		1,
		Math.ceil(
			Math.max(
				element.scrollHeight,
				element.getBoundingClientRect().height,
				element.offsetHeight,
				element.clientHeight,
				lastChildBottom
			) + RENDER_TAIL_GUARD_PX
		)
	);
	const fallbackChunks = splitRange(0, fullHeight);
	return fallbackChunks;
};

/**
 * Append one rendered canvas chunk to PDF by slicing it into A4-height pages.
 */
const appendCanvasChunkToPdf = (
	pdf: JSPDF,
	canvas: HTMLCanvasElement,
	state: PdfAppendState,
	pageWidthMM: number,
	pageHeightMM: number,
	isDark: boolean,
	options?: AppendCanvasChunkOptions
): AppendCanvasChunkResult => {
	const pxPerPdfMM = canvas.width / pageWidthMM;
	const pageSliceHeightPx = Math.max(1, Math.floor(pxPerPdfMM * pageHeightMM));
	const pageCanvas = document.createElement('canvas');
	pageCanvas.width = canvas.width;
	const pageCanvasContext = pageCanvas.getContext('2d');
	if (!pageCanvasContext) {
		throw new Error('Failed to get page canvas context');
	}
	let pagesAdded = 0;

	let offsetY = 0;
	while (offsetY < canvas.height) {
		const sliceHeight = Math.min(pageSliceHeightPx, canvas.height - offsetY);
		if (
			options?.stopWhenEncounteringEmptySlice &&
			!canvasRegionHasRenderableContent(canvas, 0, offsetY, canvas.width, sliceHeight, isDark)
		) {
			return { pagesAdded, encounteredEmptySlice: true };
		}

		pageCanvas.height = sliceHeight;
		pageCanvasContext.clearRect(0, 0, pageCanvas.width, pageCanvas.height);
		pageCanvasContext.drawImage(
			canvas,
			0,
			offsetY,
			canvas.width,
			sliceHeight,
			0,
			0,
			canvas.width,
			sliceHeight
		);

		if (state.pageCount > 0) {
			pdf.addPage();
		}
		if (isDark) {
			applyDarkModeBackground(pdf, pageWidthMM, pageHeightMM);
		}

		const imgHeightMM = (sliceHeight * pageWidthMM) / canvas.width;
		const imgData = pageCanvas.toDataURL('image/jpeg', JPEG_QUALITY);
		pdf.addImage(imgData, 'JPEG', 0, 0, pageWidthMM, imgHeightMM);
		state.pageCount += 1;
		pagesAdded += 1;
		offsetY += sliceHeight;
	}

	return { pagesAdded, encounteredEmptySlice: false };
};

/**
 * Check whether a rendered canvas contains non-background pixels.
 * Used to decide if we should continue rendering tail chunks.
 */
const canvasRegionHasRenderableContent = (
	canvas: HTMLCanvasElement,
	sourceX: number,
	sourceY: number,
	sourceWidth: number,
	sourceHeight: number,
	isDark: boolean
): boolean => {
	const clampedWidth = Math.max(0, Math.floor(sourceWidth));
	const clampedHeight = Math.max(0, Math.floor(sourceHeight));
	if (clampedWidth <= 0 || clampedHeight <= 0) {
		return false;
	}

	try {
		// Downsample first to avoid reading a huge pixel buffer from a large canvas.
		const probeMaxEdge = 128;
		const probeWidth = Math.max(1, Math.min(clampedWidth, probeMaxEdge));
		const probeHeight = Math.max(1, Math.min(clampedHeight, probeMaxEdge));
		if (sharedProbeCanvas.width !== probeWidth) {
			sharedProbeCanvas.width = probeWidth;
		}
		if (sharedProbeCanvas.height !== probeHeight) {
			sharedProbeCanvas.height = probeHeight;
		}
		if (!sharedProbeContext) {
			sharedProbeContext = sharedProbeCanvas.getContext('2d', { willReadFrequently: true });
		}
		const probeContext = sharedProbeContext;
		if (!probeContext) {
			return false;
		}

		probeContext.drawImage(
			canvas,
			Math.floor(sourceX),
			Math.floor(sourceY),
			clampedWidth,
			clampedHeight,
			0,
			0,
			probeWidth,
			probeHeight
		);
		const imageData = probeContext.getImageData(0, 0, probeWidth, probeHeight).data;
		const pixels = new Uint32Array(
			imageData.buffer,
			imageData.byteOffset,
			Math.floor(imageData.byteLength / 4)
		);
		const bg = isDark ? 0 : 255;
		const tolerance = 8;

		for (let i = 0; i < pixels.length; i += 1) {
			if (pixelDiffersFromBackground(pixels[i], bg, tolerance)) {
				return true;
			}
		}
	} catch (error) {
		// If pixels are unreadable (e.g. browser security edge cases),
		// keep existing behavior and avoid truncating by assuming content exists.
		console.warn('Failed to inspect canvas pixels for tail continuation:', error);
		return true;
	}

	return false;
};

/**
 * Create a styled container element for rendering
 * @param virtualWidth - Virtual width in pixels
 * @param padding - Optional padding CSS value (e.g., '40px 40px')
 * @returns Styled container element
 */
const createStyledContainer = (virtualWidth: number, padding?: string): HTMLElement => {
	const container = document.createElement('div');
	styleElementForRendering(container, virtualWidth);
	if (padding) {
		container.style.padding = padding;
	}
	return container;
};

// ==================== Note-specific Functions ====================

/**
 * Create DOM node from note HTML content
 * If the HTML is already an HTMLElement, returns it directly.
 * Otherwise, creates a new container with title and content nodes.
 * @param note - Note object containing title and HTML content
 * @param virtualWidth - Virtual width in pixels for the container
 * @returns DOM element ready for rendering
 */
const createNoteNode = (note: NoteData, virtualWidth: number): HTMLElement => {
	const htmlContent = note.data?.content?.html;
	const html = typeof htmlContent === 'string' ? DOMPurify.sanitize(htmlContent) : '';
	const isDark = isDarkMode();

	// If html is already an HTMLElement, return it
	if (htmlContent && typeof htmlContent === 'object' && htmlContent instanceof HTMLElement) {
		return htmlContent;
	}

	// Create container
	const node = createStyledContainer(virtualWidth, '40px 40px');

	// Create title node
	const titleNode = document.createElement('div');
	titleNode.textContent = note.title;
	titleNode.style.fontSize = '24px';
	titleNode.style.fontWeight = 'medium';
	titleNode.style.paddingBottom = '20px';
	titleNode.style.color = isDark ? 'white' : 'black';
	node.appendChild(titleNode);

	// Create content node
	const contentNode = document.createElement('div');
	contentNode.innerHTML = html;
	node.appendChild(contentNode);

	document.body.appendChild(node);

	return node;
};

// ==================== Chat-specific Functions ====================

/**
 * Clone and style an existing DOM element for PDF rendering
 * @param element - DOM element to clone
 * @param virtualWidth - Virtual width in pixels for the cloned element
 * @returns Cloned and styled element
 */
const cloneElementForRendering = (element: HTMLElement, virtualWidth: number): HTMLElement => {
	const clonedElement = element.cloneNode(true) as HTMLElement;
	styleElementForRendering(clonedElement, virtualWidth);
	document.body.appendChild(clonedElement);
	return clonedElement;
};

/**
 * Export plain text content to PDF
 * @param text - Plain text content to export
 * @param filename - Filename for the PDF file
 */
const exportPlainTextToPdf = async (text: string, filename: string): Promise<void> => {
	const doc = await createPdfDocument();

	// Margins
	const left = 15;
	const top = 20;
	const right = 15;
	const bottom = 20;

	const pageWidth = doc.internal.pageSize.getWidth();
	const pageHeight = doc.internal.pageSize.getHeight();
	const usableWidth = pageWidth - left - right;

	// Font size and line height
	const fontSize = 8;
	doc.setFontSize(fontSize);
	const lineHeight = fontSize * 1; // adjust if needed

	// Split the markdown into lines (handles \n)
	const paragraphs = text.split('\n');

	let y = top;

	for (const paragraph of paragraphs) {
		// Wrap each paragraph to fit the width
		const lines = doc.splitTextToSize(paragraph, usableWidth);

		for (const line of lines) {
			// If the line would overflow the bottom, add a new page
			if (y + lineHeight > pageHeight - bottom) {
				doc.addPage();
				y = top;
			}
			doc.text(line, left, y);
			y += lineHeight * 0.5;
		}
		// Add empty line at paragraph breaks
		y += lineHeight * 0.1;
	}

	doc.save(filename);
};

const applyChunkSelector = (element: HTMLElement, chunkSelector?: string) => {
	const chunks: { y: number, height: number }[] = [];
	if (chunkSelector) {
		element.querySelectorAll(chunkSelector).forEach((chunk) => {
			const size = chunk.getBoundingClientRect();
			(chunk as HTMLElement).dataset.cloningY = size.y.toString();
			(chunk as HTMLElement).dataset.cloningHeight = size.height.toString();
			chunks.push({
				y: size.y,
				height: size.height
			});
		});
	}
	return chunks;
};

/**
 * Export a styled DOM element to PDF using the shared canvas->slice pipeline.
 * Note and Chat stylized exports both use this path to keep behavior consistent.
 * @param element - DOM element to render
 * @param filename - Output PDF filename
 * @param virtualWidth - Virtual width used during html2canvas render
 * @param waitBeforeRenderMs - Optional wait to allow layout settling
 */
const exportStyledElementToPdf = async (
	element: HTMLElement,
	filename: string,
	chunkSelector?: string,
	virtualWidth: number = DEFAULT_VIRTUAL_WIDTH,
	waitBeforeRenderMs = 0,
	onProgress?: (progress: PdfExportProgress) => void,
	signal?: AbortSignal
): Promise<void> => {
	throwIfAborted(signal);
	emitExportProgress(onProgress, { stage: 'preparing', percent: 0 });

	if (waitBeforeRenderMs > 0) {
		await new Promise((resolve) => setTimeout(resolve, waitBeforeRenderMs));
	}

	throwIfAborted(signal);
	const pdf = await createPdfDocument();
	const isDark = isDarkMode();
	const elementHeight = Math.max(
		1,
		Math.ceil(element.getBoundingClientRect().height),
		element.scrollHeight
	);
	const safeRenderChunkHeightPx = await getSafeRenderChunkHeightPx(virtualWidth, CANVAS_SCALE);
	const chunks = buildElementRenderChunks(element, safeRenderChunkHeightPx);
	const pdfState: PdfAppendState = { pageCount: 0 };
	emitExportProgress(onProgress, {
		stage: 'rendering',
		percent: 5,
		currentChunk: 0,
		totalChunks: chunks.length,
		pagesGenerated: 0
	});

	const elmChunks = applyChunkSelector(element, chunkSelector);

	let completedChunks = 0;
	let shouldStopTailContinuation = false;
	for (let index = 0; index < chunks.length; index += 1) {
		throwIfAborted(signal);
		const chunk = chunks[index];
		const chunkCanvas = document.createElement('canvas');
		chunkCanvas.width = Math.max(1, Math.floor(virtualWidth * CANVAS_SCALE));
		chunkCanvas.height = Math.max(1, Math.floor(chunk.height * CANVAS_SCALE));

		const prevChunk = chunks[index - 1];

		const canvas = await renderElementToCanvas(element, virtualWidth, {
			canvas: chunkCanvas,
			x: 0,
			y: chunk.y,
			width: virtualWidth,
			height: chunk.height,
			elementHeight,
			lastElementY: prevChunk ? (prevChunk.y + prevChunk.height) : undefined
		}, elmChunks);
		throwIfAborted(signal);

		const appendResult = appendCanvasChunkToPdf(
			pdf,
			canvas,
			pdfState,
			A4_PAGE_WIDTH_MM,
			A4_PAGE_HEIGHT_MM,
			isDark,
			{
				stopWhenEncounteringEmptySlice: index === chunks.length - 1
			}
		);
		completedChunks += 1;
		const renderPercent = chunks.length > 0 ? 5 + (completedChunks / chunks.length) * 90 : 95;
		emitExportProgress(onProgress, {
			stage: 'rendering',
			percent: Math.min(95, Math.round(renderPercent)),
			currentChunk: completedChunks,
			totalChunks: chunks.length,
			pagesGenerated: pdfState.pageCount
		});

		if (appendResult.encounteredEmptySlice) {
			shouldStopTailContinuation = true;
			break;
		}
	}

	// Tail continuation: keep rendering forward while new chunks still contain content.
	if (!shouldStopTailContinuation) {
		let continuationY = chunks.length > 0 ? chunks[chunks.length - 1].y + chunks[chunks.length - 1].height : 0;
		const maxContinuationChunks = 512;
		for (let i = 0; i < maxContinuationChunks; i += 1) {
			throwIfAborted(signal);
			const chunkCanvas = document.createElement('canvas');
			chunkCanvas.width = Math.max(1, Math.floor(virtualWidth * CANVAS_SCALE));
			chunkCanvas.height = Math.max(1, Math.floor(safeRenderChunkHeightPx * CANVAS_SCALE));

			const tailCanvas = await renderElementToCanvas(element, virtualWidth, {
				canvas: chunkCanvas,
				x: 0,
				y: continuationY,
				width: virtualWidth,
				height: safeRenderChunkHeightPx,
				elementHeight
			}, elmChunks);

			throwIfAborted(signal);
			if (!canvasRegionHasRenderableContent(tailCanvas, 0, 0, tailCanvas.width, tailCanvas.height, isDark)) {
				break;
			}

			const appendResult = appendCanvasChunkToPdf(
				pdf,
				tailCanvas,
				pdfState,
				A4_PAGE_WIDTH_MM,
				A4_PAGE_HEIGHT_MM,
				isDark,
				{
					stopWhenEncounteringEmptySlice: true
				}
			);
			completedChunks += 1;
			continuationY += safeRenderChunkHeightPx;

			emitExportProgress(onProgress, {
				stage: 'rendering',
				percent: 95,
				currentChunk: completedChunks,
				totalChunks: chunks.length + i + 1,
				pagesGenerated: pdfState.pageCount
			});

			if (appendResult.encounteredEmptySlice) {
				break;
			}
		}
	}

	throwIfAborted(signal);
	emitExportProgress(onProgress, {
		stage: 'saving',
		percent: 98,
		currentChunk: chunks.length,
		totalChunks: chunks.length,
		pagesGenerated: pdfState.pageCount
	});
	pdf.save(filename);
	emitExportProgress(onProgress, {
		stage: 'done',
		percent: 100,
		currentChunk: chunks.length,
		totalChunks: chunks.length,
		pagesGenerated: pdfState.pageCount
	});
};

// ==================== Public API Functions ====================

/**
 * Download PDF from HTML content (for notes)
 * Creates a PDF from note content including title and HTML body.
 * Uses slice-based pagination for accurate page breaks.
 * @param note - Note object with title and data.content.html
 * @throws Error if PDF generation fails
 */
export const downloadNotePdf = async (note: NoteData): Promise<void> => {
	// Create DOM node from note content
	const node = createNoteNode(note, DEFAULT_VIRTUAL_WIDTH);
	const htmlContent = note.data?.content?.html;
	const shouldRemoveNode = !(
		htmlContent &&
		typeof htmlContent === 'object' &&
		htmlContent instanceof HTMLElement
	);

	try {
		await exportStyledElementToPdf(node, `${note.title}.pdf`, undefined, DEFAULT_VIRTUAL_WIDTH, 0);
	} finally {
		// Clean up: remove hidden node if needed
		if (shouldRemoveNode && node.parentNode) {
			document.body.removeChild(node);
		}
	}
};

/**
 * Download PDF from chat (supports stylized and plain text modes)
 *
 * Stylized mode: Renders the chat messages container as an image using html2canvas,
 * then converts it to PDF with proper pagination.
 *
 * Plain text mode: Exports chat content as plain text with basic formatting.
 *
 * @param options - Configuration object
 * @param options.containerElementId - ID of the container element to render (for stylized mode).
 * @param options.chatText - Plain text content (required for plain text mode)
 * @param options.title - PDF filename (without .pdf extension)
 * @param options.stylizedPdfExport - Whether to use stylized PDF export (default: true)
 * @param options.onBeforeRender - Optional callback before rendering (for showing full messages)
 * @param options.onAfterRender - Optional callback after rendering (for hiding full messages)
 * @throws Error if PDF generation fails or if chatText is missing in plain text mode
 */
export const downloadChatPdf = async (options: ChatPdfOptions): Promise<void> => {
	const internalAbortController = new AbortController();
	const onAbortFromExternal = () => internalAbortController.abort();
	options.signal?.addEventListener('abort', onAbortFromExternal);
	const effectiveSignal = internalAbortController.signal;
	const exportStartedAt = Date.now();

	const updateOverlay = (progress: PdfExportProgress): void => {
		const estimatedRemainingMinutes = getEstimatedRemainingMinutes(exportStartedAt, progress.percent);
		pdfExportOverlay.update((state) => ({
			...state,
			show: true,
			stage: progress.stage,
			title: 'Exporting PDF',
			stageText: getStageText(progress.stage),
			progress: progress.percent,
			currentChunk: progress.currentChunk ?? state.currentChunk,
			totalChunks: progress.totalChunks ?? state.totalChunks,
			pagesGenerated: progress.pagesGenerated ?? state.pagesGenerated,
			estimatedRemainingMinutes,
			onCancel: () => internalAbortController.abort()
		}));
	};

	pdfExportOverlay.set({
		show: true,
		stage: 'preparing',
		title: 'Exporting PDF',
		stageText: 'Preparing export...',
		progress: 0,
		currentChunk: 0,
		totalChunks: 0,
		pagesGenerated: 0,
		estimatedRemainingMinutes: null,
		onCancel: () => internalAbortController.abort()
	});

	try {
		if ((options.stylizedPdfExport ?? true) && options.containerElementId) {
			throwIfAborted(effectiveSignal);
			await options.onBeforeRender?.();

			const containerElement = document.getElementById(options.containerElementId);
			try {
				if (containerElement) {
					// Clone and style element for rendering
					const clonedElement = cloneElementForRendering(containerElement, DEFAULT_VIRTUAL_WIDTH);
					try {
						await exportStyledElementToPdf(
							clonedElement,
							`chat-${options.title}.pdf`,
							options.chunkSelector,
							DEFAULT_VIRTUAL_WIDTH,
							100,
							(progress) => {
								emitExportProgress(options.onProgress, progress);
								updateOverlay(progress);
							},
							effectiveSignal
						);
					} finally {
						// Clean up cloned element
						if (clonedElement.parentNode) {
							document.body.removeChild(clonedElement);
						}
					}
				}
			} finally {
				await options.onAfterRender?.();
			}

			return;
		}

		if (options.chatText) {
			throwIfAborted(effectiveSignal);
			const preparingProgress: PdfExportProgress = { stage: 'preparing', percent: 0 };
			emitExportProgress(options.onProgress, preparingProgress);
			updateOverlay(preparingProgress);
			await exportPlainTextToPdf(options.chatText, `chat-${options.title}.pdf`);
			const doneProgress: PdfExportProgress = { stage: 'done', percent: 100 };
			emitExportProgress(options.onProgress, doneProgress);
			updateOverlay(doneProgress);
			return;
		}

		throw new Error('Either containerElementId or chatText is required');
	} catch (error) {
		if (error instanceof Error && error.name === 'AbortError') {
			return;
		}
		throw error;
	} finally {
		options.signal?.removeEventListener('abort', onAbortFromExternal);
		pdfExportOverlay.set({
			show: false,
			stage: 'preparing',
			title: 'Exporting PDF',
			stageText: 'Preparing export...',
			progress: 0,
			currentChunk: 0,
			totalChunks: 0,
			pagesGenerated: 0,
			estimatedRemainingMinutes: null,
			onCancel: undefined
		});
	}
};
