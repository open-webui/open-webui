import type { FileComment } from './types';

export interface PdfTextRun {
	text: string;
	page: number;
	rect: number[];
}
const normalized = (text: string) => text.normalize('NFKC').replace(/\s/g, '');

/** Match only a unique saved passage. Ambiguous/absent matches remain document-level comments. */
export function mapWordComments(comments: FileComment[], runs: PdfTextRun[]): FileComment[] {
	const spans: Array<{ start: number; end: number; run: PdfTextRun }> = [];
	let documentText = '';
	for (const run of runs) {
		const start = documentText.length;
		documentText += normalized(run.text);
		spans.push({ start, end: documentText.length, run });
	}
	return comments.flatMap((comment) => {
		if (comment.parentId || comment.location?.kind !== 'word') return [];
		const quote = normalized(comment.location.quote ?? '');
		if (!quote) return [];
		const start = documentText.indexOf(quote);
		if (start < 0 || documentText.indexOf(quote, start + 1) >= 0) return [];
		const selected = spans.filter((s) => s.start < start + quote.length && s.end > start);
		if (!selected.length) return [];
		const first = selected[0].run;
		return [{ ...comment, location: { kind: 'pdf' as const, page: first.page, rect: first.rect } }];
	});
}
