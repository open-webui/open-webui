import DOMPurify from 'dompurify';
import type JSPDF from 'jspdf';

// ==================== Type Definitions ====================

/**
 * Options for rendering element to canvas
 */
interface RenderCanvasOptions {
	/** Virtual height for rendering */
	virtualHeight?: number;
	/** Window width for rendering */
	windowWidth?: number;
	/** Window height for rendering */
	windowHeight?: number;
}

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
}

// ==================== Shared Constants ====================

/** A4 page width in millimeters */
const A4_PAGE_WIDTH_MM = 210;
/** A4 page height in millimeters */
const A4_PAGE_HEIGHT_MM = 297;
/** Default virtual width in pixels for cloned element */
const DEFAULT_VIRTUAL_WIDTH = 800;
/** Canvas scale factor for increased resolution */
const CANVAS_SCALE = 2;
/** JPEG quality for image compression (0.0 to 1.0) */
const JPEG_QUALITY = 0.95;

// ==================== Shared Utility Functions ====================

/**
 * Check if dark mode is enabled in the document
 * @returns True if dark mode is enabled, false otherwise
 */
const isDarkMode = (): boolean => {
	return document.documentElement.classList.contains('dark');
};

/**
 * Create a new A4 PDF document
 * @returns New jsPDF instance configured for A4 portrait orientation
 */
const createPdfDocument = async () => {
	const { jsPDF } = await import('jspdf');
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
};

/**
 * Render DOM element to canvas using html2canvas
 * @param element - DOM element to render
 * @param virtualWidth - Virtual width in pixels
 * @param options - Optional rendering options
 * @returns Promise that resolves to a canvas element
 */
const renderElementToCanvas = async (
	element: HTMLElement,
	virtualWidth: number,
	options?: RenderCanvasOptions
): Promise<HTMLCanvasElement> => {
	const { default: html2canvas } = await import('html2canvas-pro');

	const isDark = isDarkMode();
	const canvasOptions: Record<string, unknown> = {
		useCORS: true,
		backgroundColor: isDark ? '#000' : '#fff',
		scale: CANVAS_SCALE,
		width: virtualWidth
	};

	// Add optional window dimensions for Note rendering
	if (options?.windowWidth !== undefined) {
		canvasOptions.windowWidth = options.windowWidth;
	}
	if (options?.windowHeight !== undefined) {
		canvasOptions.windowHeight = options.windowHeight;
	}

	return await html2canvas(element, canvasOptions);
};

/**
 * Convert canvas to PDF with proper pagination using slice-based method
 * This is the more accurate pagination method that slices the canvas into page-sized chunks
 * @param pdf - jsPDF instance
 * @param canvas - Canvas element containing the rendered content
 * @param virtualWidth - Virtual width in pixels used for rendering
 * @param pageWidthMM - Page width in millimeters
 * @param pageHeightMM - Page height in millimeters
 */
const canvasToPdfWithSlicing = (
	pdf: JSPDF,
	canvas: HTMLCanvasElement,
	virtualWidth: number,
	pageWidthMM: number,
	pageHeightMM: number
): void => {
	// Convert page height in mm to px on canvas scale for cropping
	// Calculate scale factor from px/mm:
	// virtualWidth px corresponds directly to 210mm in PDF, so pxPerMM:
	const pxPerPDFMM = canvas.width / pageWidthMM; // canvas px per PDF mm

	// Height in px for one page slice:
	const pagePixelHeight = Math.floor(pxPerPDFMM * pageHeightMM);

	let offsetY = 0;
	let page = 0;

	while (offsetY < canvas.height) {
		// Height of slice
		const sliceHeight = Math.min(pagePixelHeight, canvas.height - offsetY);

		// Create temp canvas for slice
		const pageCanvas = document.createElement('canvas');
		pageCanvas.width = canvas.width;
		pageCanvas.height = sliceHeight;

		const ctx = pageCanvas.getContext('2d');
		if (!ctx) {
			throw new Error('Failed to get canvas context');
		}

		// Draw the slice of original canvas onto pageCanvas
		ctx.drawImage(canvas, 0, offsetY, canvas.width, sliceHeight, 0, 0, canvas.width, sliceHeight);

		const imgData = pageCanvas.toDataURL('image/jpeg', JPEG_QUALITY);

		// Calculate image height in PDF units keeping aspect ratio
		const imgHeightMM = (sliceHeight * pageWidthMM) / canvas.width;

		if (page > 0) pdf.addPage();

		applyDarkModeBackground(pdf, pageWidthMM, pageHeightMM);

		pdf.addImage(imgData, 'JPEG', 0, 0, pageWidthMM, imgHeightMM);

		offsetY += sliceHeight;
		page++;
	}
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

	console.log(node);
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

// ==================== Public API Functions ====================

/**
 * Download PDF from HTML content (for notes)
 * Creates a PDF from note content including title and HTML body.
 * Uses slice-based pagination for accurate page breaks.
 * @param note - Note object with title and data.content.html
 * @throws Error if PDF generation fails
 */
export const downloadNotePdf = async (note: NoteData): Promise<void> => {
	// Define a fixed virtual screen size
	const virtualWidth = 1024; // Fixed width (adjust as needed)
	const virtualHeight = 1400; // Fixed height (adjust as needed)

	// Create DOM node from note content
	const node = createNoteNode(note, DEFAULT_VIRTUAL_WIDTH);
	const htmlContent = note.data?.content?.html;
	const shouldRemoveNode = !(
		htmlContent &&
		typeof htmlContent === 'object' &&
		htmlContent instanceof HTMLElement
	);

	try {
		// Render to canvas
		const [canvas, pdf] = await Promise.all([
			renderElementToCanvas(node, virtualWidth, {
				windowWidth: virtualWidth,
				windowHeight: virtualHeight
			}),
			createPdfDocument()
		]);

		canvasToPdfWithSlicing(pdf, canvas, virtualWidth, A4_PAGE_WIDTH_MM, A4_PAGE_HEIGHT_MM);

		pdf.save(`${note.title}.pdf`);
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
	console.log('Downloading PDF', options);

	if ((options.stylizedPdfExport ?? true) && options.containerElementId) {
		await options.onBeforeRender?.();

		const containerElement = document.getElementById(options.containerElementId);
		try {
			if (containerElement) {
				const virtualWidth = DEFAULT_VIRTUAL_WIDTH;

				// Clone and style element for rendering
				const clonedElement = cloneElementForRendering(containerElement, virtualWidth);

				// Wait for DOM update/layout
				await new Promise((r) => setTimeout(r, 100));

				// Render entire content once
				const [canvas, pdf] = await Promise.all([
					renderElementToCanvas(clonedElement, virtualWidth),
					createPdfDocument()
				]);

				// Clean up cloned element
				document.body.removeChild(clonedElement);

				// Create PDF and convert canvas
				canvasToPdfWithSlicing(pdf, canvas, virtualWidth, A4_PAGE_WIDTH_MM, A4_PAGE_HEIGHT_MM);

				pdf.save(`chat-${options.title}.pdf`);
			}
		} finally {
			await options.onAfterRender?.();
		}

		return;
	}

	if (options.chatText) {
		await exportPlainTextToPdf(options.chatText, `chat-${options.title}.pdf`);
		return;
	}

	throw new Error('Either containerElementId or chatText is required');
};
