import type { CommentResult, FileComment } from './types';

type Annotation = {
	id: string;
	subtype?: string;
	contentsObj?: { str?: string };
	titleObj?: { str?: string };
	contents?: string;
	creationDate?: string;
	modificationDate?: string;
	inReplyTo?: string;
	replyType?: string;
	state?: string;
	stateModel?: string;
	rect?: number[];
	quadPoints?: number[] | Float32Array;
};
const markup = new Set([
	'Text',
	'FreeText',
	'Highlight',
	'Underline',
	'Squiggly',
	'StrikeOut',
	'Stamp',
	'Caret',
	'Ink',
	'Line',
	'Square',
	'Circle',
	'Polygon',
	'PolyLine',
	'FileAttachment',
	'Redact'
]);

export function pdfComments(
	pages: Array<{ page: number; annotations: Annotation[] }>
): CommentResult {
	const comments: FileComment[] = [];
	const states: Annotation[] = [];
	for (const { page, annotations } of pages)
		for (const a of annotations) {
			if (!markup.has(a.subtype ?? '') || a.replyType === 'Group') continue;
			if (a.inReplyTo && a.stateModel && !a.contentsObj?.str && !a.contents) {
				states.push(a);
				continue;
			}
			comments.push({
				id: a.id,
				parentId: a.inReplyTo || undefined,
				text: a.contentsObj?.str ?? a.contents ?? '',
				author: a.titleObj?.str,
				date: a.creationDate || a.modificationDate,
				status:
					a.state === 'Completed' || a.state === 'Accepted'
						? 'resolved'
						: a.state === 'None'
							? 'open'
							: undefined,
				location: {
					kind: 'pdf',
					page,
					rect: a.rect ?? [],
					quads: a.quadPoints ? Array.from(a.quadPoints) : undefined
				}
			});
		}
	for (const a of states) {
		const parent = comments.find((c) => c.id === a.inReplyTo);
		if (parent)
			parent.status = ['Completed', 'Accepted'].includes(a.state ?? '')
				? 'resolved'
				: a.state === 'None'
					? 'open'
					: parent.status;
	}
	return { comments, warnings: [] };
}

export async function readPdfComments(
	doc: import('pdfjs-dist').PDFDocumentProxy,
	cancelled: () => boolean
): Promise<CommentResult> {
	const pages: Array<{ page: number; annotations: Annotation[] }> = [];
	const warnings: string[] = [];
	for (let page = 1; page <= doc.numPages; page++) {
		if (cancelled()) return { comments: [], warnings: [] };
		try {
			pages.push({ page, annotations: await (await doc.getPage(page)).getAnnotations() });
		} catch {
			warnings.push(`Could not read comments on page ${page}`);
		}
	}
	return { ...pdfComments(pages), warnings };
}
