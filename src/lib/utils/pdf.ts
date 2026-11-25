const PAGE_WIDTH_MM = 210; // A4
const PAGE_HEIGHT_MM = 297; // A4

// Draws one page at a time so no canvas exceeds the browser's size limit.
// The element must be a direct child of the body.
export const saveElementPdf = async (
	element: HTMLElement,
	filename: string,
	{
		width = 800,
		windowWidth,
		windowHeight,
		pageBreakSelector
	}: {
		width?: number;
		windowWidth?: number;
		windowHeight?: number;
		pageBreakSelector?: string;
	} = {}
) => {
	const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
		import('jspdf'),
		import('html2canvas-pro')
	]);

	const isDarkMode = document.documentElement.classList.contains('dark');
	const pdf = new jsPDF('p', 'mm', 'a4');

	const pagePixelHeight = Math.floor((width * PAGE_HEIGHT_MM) / PAGE_WIDTH_MM);
	const { top: rootTop, height } = element.getBoundingClientRect();
	const contentHeight = Math.ceil(height);
	const pageBreaks = pageBreakSelector
		? Array.from(element.querySelectorAll(pageBreakSelector))
				.slice(1)
				.map((pageElement) => Math.floor(pageElement.getBoundingClientRect().top - rootTop))
		: [];

	const blocks: { element: Element; top: number; bottom: number }[] = [];
	const trackedElements = new Set<Element>();
	const collectBlocks = (current: Element) => {
		const children = Array.from(current.children);
		const splittable =
			children.length > 0 &&
			(getComputedStyle(current).display === 'contents' ||
				(current.getBoundingClientRect().height > pagePixelHeight / 4 &&
					!Array.from(current.childNodes).some(
						(childNode) => childNode.nodeType === Node.TEXT_NODE && childNode.textContent?.trim()
					) &&
					children.every((child) => !getComputedStyle(child).display.startsWith('inline'))));

		if (current !== element) trackedElements.add(current);

		if (splittable) {
			children.forEach(collectBlocks);
		} else {
			const { top, bottom } = current.getBoundingClientRect();
			blocks.push({ element: current, top: top - rootTop, bottom: bottom - rootTop });
		}
	};
	collectBlocks(element);

	element.setAttribute('data-pdf-root', '');

	let offsetY = 0;
	let page = 0;

	while (offsetY < contentHeight) {
		const nextPageBreak = pageBreaks.find((top) => top > offsetY) ?? contentHeight;
		const sliceHeight = Math.min(pagePixelHeight, nextPageBreak - offsetY);
		const sliceBlocks = blocks.filter(
			(block) => block.bottom > offsetY && block.top < offsetY + sliceHeight
		);

		const keptElements = new Set<Element>();
		for (const block of sliceBlocks) {
			for (
				let current: Element | null = block.element;
				current && current !== element;
				current = current.parentElement
			) {
				keptElements.add(current);
			}
		}

		const anchor = sliceBlocks.find((block) => block.bottom > block.top);
		anchor?.element.setAttribute('data-pdf-anchor', '');

		const canvas = await html2canvas(element, {
			backgroundColor: isDarkMode ? '#000' : '#fff',
			useCORS: true,
			logging: false,
			scale: 2, // increase resolution
			width,
			windowWidth,
			windowHeight,
			height: sliceHeight,
			y: offsetY,
			ignoreElements: (current) =>
				(current.parentElement === document.body &&
					current !== element &&
					!['STYLE', 'LINK'].includes(current.tagName)) ||
				(trackedElements.has(current) && !keptElements.has(current)),
			onclone: (clonedDocument) => {
				const clonedRoot = clonedDocument.querySelector('[data-pdf-root]');
				const clonedAnchor = clonedDocument.querySelector('[data-pdf-anchor]');
				if (!anchor || !clonedRoot || !clonedAnchor) return;

				const spacer = clonedDocument.createElement('div');
				clonedRoot.prepend(spacer);

				let spacerHeight = 0;
				for (let pass = 0; pass < 2; pass++) {
					spacerHeight +=
						anchor.top -
						(clonedAnchor.getBoundingClientRect().top - clonedRoot.getBoundingClientRect().top);
					spacer.style.height = `${spacerHeight}px`;
				}
			}
		});

		anchor?.element.removeAttribute('data-pdf-anchor');

		if (page > 0) pdf.addPage();

		if (isDarkMode) {
			pdf.setFillColor(0, 0, 0);
			pdf.rect(0, 0, PAGE_WIDTH_MM, PAGE_HEIGHT_MM, 'F'); // black bg
		}

		pdf.addImage(
			canvas.toDataURL('image/jpeg', 0.7),
			'JPEG',
			0,
			0,
			PAGE_WIDTH_MM,
			(sliceHeight * PAGE_WIDTH_MM) / width
		);

		offsetY += sliceHeight;
		page++;
	}

	pdf.save(filename);
};

// Resolves once the element has not changed for a second, or after 10 seconds.
const waitForRender = (element: HTMLElement) =>
	new Promise<void>((resolve) => {
		const done = () => {
			observer.disconnect();
			resolve();
		};
		let timer = setTimeout(done, 1000);
		const observer = new MutationObserver(() => {
			clearTimeout(timer);
			timer = setTimeout(done, 1000);
		});
		observer.observe(element, { childList: true, subtree: true });
		setTimeout(done, 10000);
	});

export const saveChatPdf = async (container: HTMLElement, filename: string) => {
	// Equations, diagrams, and multi-model responses render after the messages mount.
	await waitForRender(container);

	const element = container.cloneNode(true) as HTMLElement;
	element.classList.add('text-base-1000', 'dark:text-base-0');
	Object.assign(element.style, { width: '800px', position: 'absolute', left: '-9999px' });

	const setStyle = (selector: string, style: Partial<CSSStyleDeclaration>) =>
		element
			.querySelectorAll<HTMLElement>(selector)
			.forEach((child) => Object.assign(child.style, style));
	setStyle('.message-virtualized', { contentVisibility: 'visible' });
	setStyle('.buttons', { opacity: '0' });
	setStyle('pre code', { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' });
	setStyle('[id^="responses-container-"]', { flexDirection: 'column', paddingRight: '8px' });

	document.body.appendChild(element);
	try {
		await saveElementPdf(element, filename);
	} finally {
		element.remove();
	}
};

export const saveTextPdf = async (text: string, filename: string) => {
	const { default: jsPDF } = await import('jspdf');
	const doc = new jsPDF();

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
