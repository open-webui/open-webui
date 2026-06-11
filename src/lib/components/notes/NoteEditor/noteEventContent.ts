import { marked } from 'marked';

export type NoteContent = {
	json?: unknown | null;
	html?: string | null;
	md?: string | null;
};

const hasOwn = (value: object, key: string) => Object.prototype.hasOwnProperty.call(value, key);

export const resolveIncomingNoteContent = (
	currentContent: NoteContent | null | undefined,
	incomingContent: NoteContent
): Required<NoteContent> => {
	const hasMd = hasOwn(incomingContent, 'md');
	const hasHtml = hasOwn(incomingContent, 'html');
	const hasJson = hasOwn(incomingContent, 'json');

	const md = hasMd ? (incomingContent.md ?? '') : (currentContent?.md ?? '');
	const html = hasHtml
		? (incomingContent.html ?? '')
		: hasMd
			? String(marked.parse(md))
			: (currentContent?.html ?? '');
	const json = hasJson ? (incomingContent.json ?? null) : hasMd ? null : (currentContent?.json ?? null);

	return {
		json,
		html,
		md
	};
};
