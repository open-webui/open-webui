import DOMPurify from 'dompurify';
import canvasSize from 'canvas-size';
import html2canvas, { type Options as Html2CanvasOptions } from 'html2canvas-pro';
import { jsPDF } from 'jspdf';
import type JSPDF from 'jspdf';
import { exportOverlay, type ExportOverlayStage } from '../stores';

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
export interface ExportPDFOptions {
	/** PDF filename */
	filename?: string;
	/** Optional title for the export (used in overlay) */
	title?: string;
	/** Optional callback before rendering (for showing full messages) */
	onBeforeRender?: () => Promise<void> | void;
	/** Optional callback after rendering (for hiding full messages) */
	onAfterRender?: () => Promise<void> | void;
	/** Optional callback for export progress updates */
	onProgress?: (progress: PdfExportProgress) => void;
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

interface PdfExportProgress {
	stage: ExportOverlayStage;
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
/** Step size used when probing canvas height fallback tests */
const CANVAS_PROBE_STEP_PX = 1024;

const canvasMaxHeightProbeCache = new Map<number, Promise<number | null>>();

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
 * @param element - DOM element to render (This is the cloned container)
 * @param virtualWidth - Virtual width in pixels
 * @returns Promise that resolves to a canvas element
 */
const renderElementToCanvas = async (
	element: HTMLElement,
	virtualWidth: number,
	options?: RenderElementToCanvasOptions
): Promise<HTMLCanvasElement> => {
	const isDark = isDarkMode();
	const cropY = options?.y ?? 0;
	// Use explicit height or fallback to scrollHeight/client logic
	const elementHeight =
			options?.elementHeight ??
			Math.max(1, Math.ceil(element.getBoundingClientRect().height), element.scrollHeight);
	const cropHeight = Math.max(1, Math.ceil(options?.height ?? elementHeight));
	const cropBottom = cropY + cropHeight;

	// =========================================================================
	// Optimization Phase 1: Clean up "Past" Elements (Already Rendered)
	// =========================================================================
	// Since 'element' is a dedicated clone for PDF generation, we can destructively
	// modify it. We replace elements fully above the current viewport with 
	// empty spacers. This progressively reduces the DOM weight for subsequent chunks.
	
	const children = Array.from(element.children) as HTMLElement[];
	for (const child of children) {
			// Optimization: Check if it's already a spacer to avoid re-processing
			if (child.getAttribute('data-pdf-spacer') === 'true') {
					continue;
			}

			// Use offsetTop/offsetHeight directly. Since 'element' is off-screen but 
			// attached to DOM, these values are computed correctly by the browser.
			const top = child.offsetTop;
			const height = child.offsetHeight;
			const bottom = top + height;

			// Rule 2: If fully rendered (above current chunk), replace with spacer
			// strictly < cropY ensures we don't remove elements intersecting the top edge
			if (bottom <= cropY) {
					const spacer = document.createElement('div');
					spacer.style.height = `${height}px`;
					spacer.style.width = '100%';
					spacer.setAttribute('data-pdf-spacer', 'true');
					// Replace the heavy content node with a lightweight spacer
					element.replaceChild(spacer, child);
			}
			
			// Optimization: If we reach an element that starts below the current chunk,
			// we can stop checking the "replace" logic (assuming children are sorted visually).
			// However, to be safe with absolute positioning/flexbox order, we iterate all.
	}

	// =========================================================================
	// Optimization Phase 2: Ignore "Future" Elements (Not Yet Rendered)
	// =========================================================================
	const windowHeight = Math.max(elementHeight, Math.ceil(cropY + cropHeight));

	const canvasOptions: Partial<Html2CanvasOptions> = {
			useCORS: true,
			allowTaint: true,
			backgroundColor: isDark ? '#000' : '#fff',
			scale: CANVAS_SCALE,
			windowWidth: virtualWidth,
			windowHeight,
			x: options?.x || 0,
			y: cropY,
			width: options?.width ?? virtualWidth,
			height: cropHeight,
			canvas: options?.canvas,
			onclone: options?.onclone,
			// Rule 3: Use ignoreElements to skip content below the viewport
			ignoreElements: (node) => {
					// Allow custom ignore logic to pass first
					if (options?.ignoreElements?.(node)) return true;

					// Ignore elements that are not part of the cloned container
					if (node.parentNode === document.body) {
						return (node as HTMLElement).dataset?.cloningElement !== 'true';
					}
					// Some browser plugin may add elements to the document.documentElement
					if (node.parentNode === document.documentElement && (node !== document.body && node !== document.head)) {
						return true;
					}

					// Only optimize based on the root container's direct children.
					// Checking every single DOM node's offsetTop is expensive and incorrect 
					// for nested elements (offsetTop is relative to offsetParent).
					if (node.parentElement === element && node instanceof HTMLElement) {
							const top = node.offsetTop;
							// If the element starts AFTER the current chunk ends, ignore it completely.
							// html2canvas won't traverse its children, saving massive time.
							if (top >= cropBottom) {
									return true;
							}
					}
					return false;
			},
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
	maxChunkHeightPx: number,
): ElementRenderChunk[] => {
	const totalHeight = element.getBoundingClientRect().height;

	const chunks: ElementRenderChunk[] = [];
	let offset = 0;
	while (offset < totalHeight) {
		const chunkHeight = Math.min(maxChunkHeightPx, totalHeight - offset);
		chunks.push({
			y: Math.max(0, Math.floor(offset)),
			height: Math.max(1, Math.ceil(chunkHeight))
		});
		offset += chunkHeight;
	}

	return chunks;
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
	chunkHeight: number,
	isDark: boolean,
): number => {
	const pxPerPdfMM = canvas.width / pageWidthMM;
	const pageSliceHeightPx = Math.max(1, Math.floor(pxPerPdfMM * pageHeightMM));
	const pageCanvas = document.createElement('canvas');
	pageCanvas.width = canvas.width;
	const pageCanvasContext = pageCanvas.getContext('2d');
	if (!pageCanvasContext) {
		throw new Error('Failed to get page canvas context');
	}
	let pagesAdded = 0;

	const actualChunkHeight = chunkHeight * CANVAS_SCALE;

	let offsetY = 0;
	while (offsetY < actualChunkHeight) {
		const sliceHeight = Math.min(pageSliceHeightPx, actualChunkHeight - offsetY);

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

	return pagesAdded;
};

/** Create a styled container element for rendering */
const processContainer = (container: HTMLElement, virtualWidth: number, title?: string, padding = '32px') => {
	if (container.dataset.exportPDFClonedContainer !== 'true') {
		container = container.cloneNode(true) as HTMLElement;
	}

	styleElementForRendering(container, virtualWidth);
	if (padding) {
		container.style.padding = padding;
	}
	if (title) {
		const titleNode = document.createElement('div');
		titleNode.className = 'text-3xl font-bold text-black dark:text-white leading-tight text-balance break-words mb-5';
		titleNode.textContent = title;
		container.insertBefore(titleNode, container.firstChild);
	}
	document.body.appendChild(container);

	return {
		element: container,
		cleanup() {
			document.body.removeChild(container);
		}
	};
};

// ==================== Export PDF Functions ====================

/**
 * Export plain text content to PDF
 * @param text - Plain text content to export
 * @param filename - Filename for the PDF file
 */
export const exportPlainTextToPdf = async (text: string, filename: string): Promise<void> => {
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

	let completedChunks = 0;
	for (let index = 0; index < chunks.length; index += 1) {
		throwIfAborted(signal);
		const chunk = chunks[index];
		const chunkCanvas = document.createElement('canvas');
		chunkCanvas.width = Math.max(1, Math.floor(virtualWidth * CANVAS_SCALE));
		chunkCanvas.height = Math.max(1, Math.floor(chunk.height * CANVAS_SCALE));

		const canvas = await renderElementToCanvas(element, virtualWidth, {
			canvas: chunkCanvas,
			x: 0,
			y: chunk.y,
			width: virtualWidth,
			height: chunk.height,
			elementHeight
		});
		throwIfAborted(signal);

		appendCanvasChunkToPdf(
			pdf,
			canvas,
			pdfState,
			A4_PAGE_WIDTH_MM,
			A4_PAGE_HEIGHT_MM,
			chunk.height,
			isDark,
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
 * Renders the element container as an image using html2canvas,
 * then converts it to PDF with proper pagination.
 *
 * @param containerElement - Selector or HTMLElement for the container to render
 * @param options - Configuration object
 * @throws Error if PDF generation fails or if chatText is missing in plain text mode
 */
export const exportPDF = async (containerElement: string | HTMLElement, options: ExportPDFOptions = {}): Promise<void> => {
	if (!containerElement) {
		throw new Error('containerElement is required for stylized PDF export');
	}

	const internalAbortController = new AbortController();
	const onAbortFromExternal = () => internalAbortController.abort();
	options.signal?.addEventListener('abort', onAbortFromExternal);
	const effectiveSignal = internalAbortController.signal;
	const exportStartedAt = Date.now();

	const updateOverlay = (progress: PdfExportProgress): void => {
		const estimatedRemainingMinutes = getEstimatedRemainingMinutes(exportStartedAt, progress.percent);
		exportOverlay.update((state) => ({
			...state,
			show: true,
			stage: progress.stage,
			progress: progress.percent,
			currentChunk: progress.currentChunk ?? state.currentChunk,
			totalChunks: progress.totalChunks ?? state.totalChunks,
			pagesGenerated: progress.pagesGenerated ?? state.pagesGenerated,
			estimatedRemainingMinutes,
			onCancel: () => internalAbortController.abort()
		}));
	};

	exportOverlay.set({
		show: true,
		stage: 'preparing',
		progress: 0,
		currentChunk: 0,
		totalChunks: 0,
		pagesGenerated: 0,
		estimatedRemainingMinutes: null,
		onCancel: () => internalAbortController.abort()
	});

	await new Promise((resolve) => setTimeout(resolve, 20));

	try {
		throwIfAborted(effectiveSignal);
		await options.onBeforeRender?.();

		if (typeof containerElement === 'string') {
			containerElement = document.querySelector(containerElement) as HTMLElement;
		}
		if (!containerElement) {
			throw new Error(`Container element not found for selector: ${containerElement}`);
		}

		try {
			// Clone and style element for rendering
			const { element, cleanup } = processContainer(containerElement, DEFAULT_VIRTUAL_WIDTH, options.title);

			try {
				await exportStyledElementToPdf(
					element,
					options.filename || `export-${options.title || Date.now()}.pdf`,
					DEFAULT_VIRTUAL_WIDTH,
					100,
					(progress) => {
						emitExportProgress(options.onProgress, progress);
						updateOverlay(progress);
					},
					effectiveSignal
				);
			} finally {
				cleanup();
			}
		} finally {
			await options.onAfterRender?.();
		}
	} catch (error) {
		if (error instanceof Error && error.name === 'AbortError') {
			return;
		}
		throw error;
	} finally {
		options.signal?.removeEventListener('abort', onAbortFromExternal);
		exportOverlay.set({
			show: false,
			stage: 'preparing',
			progress: 0,
			currentChunk: 0,
			totalChunks: 0,
			pagesGenerated: 0,
			estimatedRemainingMinutes: null,
			onCancel: undefined
		});
	}
};

/**
 * Create DOM node from note HTML content
 *
 * @param html - HTML content as string or HTMLElement
 * @param options - Configuration object
 * @returns DOM element ready for rendering
 */
export const exportPDFFromHTML = async (html: string, options: ExportPDFOptions = {}) => {
	const contentNode = document.createElement('div');
	contentNode.innerHTML = DOMPurify.sanitize(html);
	contentNode.dataset.exportPDFClonedContainer = 'true';
	await exportPDF(contentNode, options);
};
