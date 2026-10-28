import DOMPurify from 'dompurify';
import { toast } from 'svelte-sonner';

import { createNewNote } from '$lib/apis/notes';
import { safeImageUrl } from '$lib/utils/safeImageUrl';
import { marked } from 'marked';
// @ts-expect-error The installed file-saver package has no type declarations.
import fileSaver from 'file-saver';
import type { NoteContent, NotePage, NotePageOperation } from '$lib/apis/notes';

export const downloadNote = async (
	note: { title: string; data: { pages?: NotePage[]; content: NoteContent; files?: any[] } },
	format: string,
	pageId: string | null = null
) => {
	const pages = (
		note.data.pages ?? [
			{
				id: 'main',
				title: note.title,
				inherit_note_title: true,
				content: note.data.content,
				files: note.data.files
			}
		]
	).map((page) =>
		page.id === 'main' && page.inherit_note_title !== false ? { ...page, title: note.title } : page
	);
	const paths = new Map(tabRows(pages).map(({ page, path }) => [page.id, path]));
	const selected = pageId ? pages.filter((page) => page.id === pageId) : pages;
	if (!selected.length) throw new Error('Page no longer exists');
	const title = pageId && pageId !== 'main' ? `${note.title} - ${selected[0].title}` : note.title;
	const md =
		selected.length === 1
			? selected[0].content.md
			: selected.map((page) => `## ${paths.get(page.id)}\n\n${page.content.md}`).join('\n\n');
	if (format !== 'pdf') {
		fileSaver.saveAs(
			new Blob([md], { type: format === 'md' ? 'text/markdown' : 'text/plain' }),
			`${title}.${format}`
		);
		return;
	}
	const html = selected
		.map((page) => {
			const heading = document.createElement('h2');
			heading.textContent = paths.get(page.id) ?? page.title;
			return `<section data-note-page>${selected.length > 1 ? heading.outerHTML : ''}${page.content.html || marked.parse(page.content.md || '')}</section>`;
		})
		.join('');
	await downloadPdf({
		...note,
		title,
		data: {
			...note.data,
			content: { html, md }
		}
	});
};

export const downloadPdf = async (note) => {
	const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
		import('jspdf'),
		import('html2canvas-pro')
	]);

	// Define a fixed virtual screen size
	const virtualWidth = 1024; // Fixed width (adjust as needed)
	const virtualHeight = 1400; // Fixed height (adjust as needed)

	// STEP 1. Get a DOM node to render
	const html = DOMPurify.sanitize(note.data?.content?.html ?? '');
	const isDarkMode = document.documentElement.classList.contains('dark');

	let node;
	if (html instanceof HTMLElement) {
		node = html;
	} else {
		const virtualWidth = 800; // px, fixed width for cloned element

		// Clone and style
		node = document.createElement('div');

		// title node
		const titleNode = document.createElement('div');
		titleNode.textContent = note.title;
		titleNode.style.fontSize = '24px';
		titleNode.style.fontWeight = 'medium';
		titleNode.style.paddingBottom = '20px';
		titleNode.style.color = isDarkMode ? 'white' : 'black';
		node.appendChild(titleNode);

		const contentNode = document.createElement('div');

		contentNode.innerHTML = html;

		for (const img of contentNode.querySelectorAll('img[src^="data://"]')) {
			const fileId = img.getAttribute('src').replace('data://', '');
			const file = (note.data?.files ?? []).find((f) => f.id === fileId);
			if (file) {
				img.setAttribute('src', safeImageUrl(file.url || ''));
			}
		}

		node.appendChild(contentNode);

		node.classList.add('text-black');
		node.classList.add('dark:text-white');
		node.style.width = `${virtualWidth}px`;
		node.style.position = 'absolute';
		node.style.left = '-9999px';
		node.style.height = 'auto';
		node.style.padding = '40px 40px';

		console.log(node);
		document.body.appendChild(node);
	}

	await Promise.all(
		Array.from(node.querySelectorAll('img')).map((img) => img.decode().catch(() => {}))
	);

	// A4 page settings
	const pdf = new jsPDF('p', 'mm', 'a4');
	const pageWidthMM = 210; // A4 width in mm
	const pageHeightMM = 297; // A4 height in mm

	const pagePixelHeight = Math.floor((virtualWidth * pageHeightMM) / pageWidthMM);
	const rootTop = node.getBoundingClientRect().top;
	const contentHeight = Math.ceil(node.getBoundingClientRect().height);
	const pageBoundaries = Array.from(node.querySelectorAll('[data-note-page]'))
		.slice(1)
		.map((element) => Math.floor(element.getBoundingClientRect().top - rootTop));

	const blocks = [];
	const trackedElements = new Set();
	const collectBlocks = (element) => {
		const children = Array.from(element.children);
		const splittable =
			children.length > 0 &&
			(getComputedStyle(element).display === 'contents' ||
				(element.getBoundingClientRect().height > pagePixelHeight / 4 &&
					!Array.from(element.childNodes).some(
						(childNode) => childNode.nodeType === Node.TEXT_NODE && childNode.textContent?.trim()
					) &&
					children.every((child) => !getComputedStyle(child).display.startsWith('inline'))));

		if (element !== node) trackedElements.add(element);

		if (splittable) {
			children.forEach(collectBlocks);
		} else {
			const { top, bottom } = element.getBoundingClientRect();
			blocks.push({ element, top: top - rootTop, bottom: bottom - rootTop });
		}
	};
	collectBlocks(node);

	node.setAttribute('data-pdf-root', '');

	let offsetY = 0;
	let page = 0;

	while (offsetY < contentHeight) {
		const nextBoundary = pageBoundaries.find((top) => top > offsetY) ?? contentHeight;
		const sliceHeight = Math.min(pagePixelHeight, contentHeight - offsetY, nextBoundary - offsetY);
		const sliceBlocks = blocks.filter(
			(block) => block.bottom > offsetY && block.top < offsetY + sliceHeight
		);

		const keptElements = new Set();
		for (const { element } of sliceBlocks) {
			for (let current = element; current && current !== node; current = current.parentElement) {
				keptElements.add(current);
			}
		}

		const anchor = sliceBlocks.find((block) => block.bottom > block.top);
		anchor?.element.setAttribute('data-pdf-anchor', '');

		const canvas = await html2canvas(node, {
			useCORS: true,
			logging: false,
			backgroundColor: isDarkMode ? '#000' : '#fff',
			scale: 2, // Keep at 1x to avoid unexpected enlargements
			width: virtualWidth, // Set fixed virtual screen width
			windowWidth: virtualWidth, // Ensure consistent rendering
			windowHeight: virtualHeight,
			height: sliceHeight,
			y: offsetY,
			ignoreElements: (element) =>
				(element.parentElement === document.body &&
					element !== node &&
					!['STYLE', 'LINK'].includes(element.tagName)) ||
				(trackedElements.has(element) && !keptElements.has(element)),
			onclone: (clonedDocument) => {
				const clonedRoot = clonedDocument.querySelector('[data-pdf-root]');
				const clonedAnchor = clonedDocument.querySelector('[data-pdf-anchor]');
				if (!clonedRoot || !clonedAnchor) return;

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

		const imgData = canvas.toDataURL('image/jpeg', 0.7);
		const imgHeightMM = (sliceHeight * pageWidthMM) / virtualWidth;

		if (page > 0) pdf.addPage();

		if (isDarkMode) {
			pdf.setFillColor(0, 0, 0);
			pdf.rect(0, 0, pageWidthMM, pageHeightMM, 'F'); // black bg
		}

		pdf.addImage(imgData, 'JPEG', 0, 0, pageWidthMM, imgHeightMM);

		offsetY += sliceHeight;
		page++;
	}

	// Remove hidden node if needed
	if (!(html instanceof HTMLElement)) {
		document.body.removeChild(node);
	}

	pdf.save(`${note.title}.pdf`);
};

export const createNoteHandler = async (title: string, md?: string, html?: string) => {
	//  $i18n.t('New Note'),
	const res = await createNewNote(localStorage.token, {
		// YYYY-MM-DD
		title: title,
		data: {
			content: {
				json: null,
				html: html || md || '',
				md: md || ''
			}
		},
		meta: null,
		access_grants: []
	}).catch((error) => {
		toast.error(`${error}`);
		return null;
	});

	if (res) {
		return res;
	}
};

type Tab = Pick<NotePage, 'id' | 'title' | 'parent_id'>;

export function tabRows<T extends Tab>(pages: T[], collapsed = new Set<string>()) {
	const children = new Map<string | null, T[]>();
	for (const page of pages) {
		const parent = page.parent_id ?? null;
		if (!children.has(parent)) children.set(parent, []);
		children.get(parent)!.push(page);
	}
	const rows: {
		page: T;
		depth: number;
		path: string;
		hasChildren: boolean;
		position: number;
		siblings: number;
	}[] = [];
	const stack = (children.get(null) ?? [])
		.map((page, index, roots) => ({
			page,
			depth: 0,
			path: page.title,
			position: index + 1,
			siblings: roots.length
		}))
		.reverse();
	while (stack.length) {
		const row = stack.pop()!;
		const nested = children.get(row.page.id) ?? [];
		rows.push({ ...row, hasChildren: nested.length > 0 });
		if (!collapsed.has(row.page.id)) {
			stack.push(
				...nested
					.map((page, index) => ({
						page,
						depth: row.depth + 1,
						path: `${row.path} / ${page.title}`,
						position: index + 1,
						siblings: nested.length
					}))
					.reverse()
			);
		}
	}
	return rows;
}

export function tabAncestors(pages: Tab[], id: string) {
	const lookup = new Map(pages.map((page) => [page.id, page]));
	const ancestors: string[] = [];
	let parent = lookup.get(id)?.parent_id;
	while (parent && !ancestors.includes(parent)) {
		ancestors.unshift(parent);
		parent = lookup.get(parent)?.parent_id;
	}
	return ancestors;
}

export function tabBranchIds(pages: Tab[], id: string) {
	const children = new Map<string, string[]>();
	for (const page of pages) {
		if (page.parent_id) {
			if (!children.has(page.parent_id)) children.set(page.parent_id, []);
			children.get(page.parent_id)!.push(page.id);
		}
	}
	const ids = new Set<string>();
	const stack = [id];
	while (stack.length) {
		const next = stack.pop()!;
		if (ids.has(next)) continue;
		ids.add(next);
		stack.push(...(children.get(next) ?? []));
	}
	return ids;
}

export function siblingMove(
	pages: Tab[],
	id: string,
	direction: number
): Omit<NotePageOperation, 'revision'> | null {
	const page = pages.find((page) => page.id === id);
	if (!page || page.id === 'main') return null;
	const parent_id = page.parent_id ?? null;
	const siblings = pages.filter(
		(page) => page.id !== 'main' && (page.parent_id ?? null) === parent_id
	);
	const index = siblings.findIndex((page) => page.id === id);
	const next = index + direction;
	if (next < 0 || next >= siblings.length) return null;
	return {
		action: 'move',
		page_id: id,
		parent_id,
		before_id: siblings[direction < 0 ? next : next + 1]?.id ?? null
	};
}

export type PageDropPosition = 'before' | 'inside' | 'after';

export function pageDropMove(
	pages: Tab[],
	id: string,
	targetId: string,
	position: PageDropPosition
): Omit<NotePageOperation, 'revision'> | null {
	const target = pages.find((page) => page.id === targetId);
	if (
		id === 'main' ||
		!pages.some((page) => page.id === id) ||
		!target ||
		tabBranchIds(pages, id).has(targetId) ||
		(targetId === 'main' && position === 'before')
	)
		return null;
	const parent_id = position === 'inside' ? targetId : (target.parent_id ?? null);
	const siblings = pages.filter((page) => (page.parent_id ?? null) === parent_id && page.id !== id);
	return {
		action: 'move',
		page_id: id,
		parent_id,
		before_id:
			position === 'before'
				? targetId
				: position === 'after'
					? (siblings[siblings.findIndex((page) => page.id === targetId) + 1]?.id ?? null)
					: null
	};
}

export function contentFiles(content: NoteContent | undefined) {
	const files = new Map<string, { id: string; type: string; name: string; size: number }>();
	const stack = content?.json ? [content.json] : [];
	while (stack.length) {
		const node = stack.pop();
		if (node?.type === 'fileAttachment' && node.attrs?.id) {
			files.set(node.attrs.id, { ...node.attrs, type: 'file' });
		}
		stack.push(...(node?.content ?? []).slice().reverse());
	}
	return [...files.values()];
}
