type NoteContent = {
	md?: string;
	html?: string;
	json?: unknown;
	[key: string]: unknown;
};

export const resolveNoteEventContent = (
	currentContent: NoteContent,
	incomingContent: NoteContent,
	renderMarkdown: (markdown: string) => string
) => {
	const md = incomingContent.md ?? currentContent.md ?? '';
	const html =
		incomingContent.html ??
		(incomingContent.md !== undefined ? renderMarkdown(md) : (currentContent.html ?? ''));

	return {
		...currentContent,
		...incomingContent,
		md,
		html,
		json: incomingContent.json ?? null
	};
};
