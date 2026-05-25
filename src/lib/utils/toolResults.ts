export type ToolName = 'web_search' | 'web_fetch' | string;

export type DecodedToolArguments =
	| Record<string, unknown>
	| unknown[]
	| string
	| number
	| boolean
	| null;

export interface ToolCallSummary {
	kind: 'web_search' | 'web_fetch' | 'generic';
	title: string;
	subtitle?: string;
	badge?: string;
}

export interface WebSearchItem {
	index: number;
	title: string;
	url: string;
	domain: string;
	snippet: string;
}

export interface ParsedWebSearchResult {
	ok: boolean;
	query: string;
	declaredCount: number | null;
	results: WebSearchItem[];
	raw: string;
}

export interface WebFetchPage {
	index: number;
	title: string;
	url: string;
	domain: string;
	published: string;
	author: string;
	description: string;
	content: string;
	characters: number;
}

export interface ParsedWebFetchResult {
	ok: boolean;
	declaredCount: number | null;
	pages: WebFetchPage[];
	totalCharacters: number;
	raw: string;
}

const JSON_START_CHARS = new Set([
	'{',
	'[',
	'"',
	'-',
	'0',
	'1',
	'2',
	'3',
	'4',
	'5',
	'6',
	'7',
	'8',
	'9'
]);

const looksLikeJSON = (value: string) => {
	const trimmed = value.trim();
	if (!trimmed) return false;
	const first = trimmed[0];
	return JSON_START_CHARS.has(first) || first === 't' || first === 'f' || first === 'n';
};

export const decodePossiblyNestedJSON = (input: unknown, maxDepth = 4): unknown => {
	let value = input;

	for (let i = 0; i < maxDepth; i += 1) {
		if (typeof value !== 'string') break;

		const trimmed = value.trim();
		if (!looksLikeJSON(trimmed)) break;

		try {
			value = JSON.parse(trimmed);
		} catch {
			break;
		}
	}

	return value;
};

export const decodeToolArguments = (raw: unknown): DecodedToolArguments => {
	return decodePossiblyNestedJSON(raw) as DecodedToolArguments;
};

export const getToolArgumentsObject = (raw: unknown): Record<string, unknown> => {
	const decoded = decodeToolArguments(raw);
	return decoded && typeof decoded === 'object' && !Array.isArray(decoded)
		? (decoded as Record<string, unknown>)
		: {};
};

export const decodeToolResultText = (raw: unknown): string => {
	const decoded = decodePossiblyNestedJSON(raw);

	if (decoded == null) return '';
	if (typeof decoded === 'string') return decoded;
	if (typeof decoded === 'object') return JSON.stringify(decoded, null, 2);
	return String(decoded);
};

export const formatToolValue = (raw: unknown): string => {
	const decoded = decodePossiblyNestedJSON(raw);

	if (decoded == null) return '';
	if (typeof decoded === 'object') return JSON.stringify(decoded, null, 2);
	return String(decoded);
};

export const isWebToolName = (name: unknown): name is 'web_search' | 'web_fetch' => {
	return name === 'web_search' || name === 'web_fetch';
};

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const extractMarkdownField = (block: string, label: string) => {
	const fieldRegex = new RegExp(`^\\s*\\*\\*${escapeRegExp(label)}:\\*\\*\\s*(.*)$`, 'im');
	return block.match(fieldRegex)?.[1]?.trim() ?? '';
};

export const getDomain = (url: string) => {
	try {
		return new URL(url).hostname.replace(/^www\./i, '');
	} catch {
		return '';
	}
};

export const truncateMiddle = (value: string, max = 96) => {
	if (value.length <= max) return value;
	const keep = Math.max(8, Math.floor((max - 1) / 2));
	return `${value.slice(0, keep)}…${value.slice(value.length - keep)}`;
};

export const truncateEnd = (value: string, max = 120) => {
	if (value.length <= max) return value;
	return `${value.slice(0, Math.max(0, max - 1)).trimEnd()}…`;
};

export const compactWhitespace = (value: string) => value.replace(/\s+/g, ' ').trim();

export const previewText = (value: string, max = 900) => {
	// Previews are rendered for every fetched page card. Do not normalize an
	// entire 100k+ character page just to show the first few lines.
	const head = value.length > max * 4 ? value.slice(0, max * 4) : value;
	return truncateEnd(compactWhitespace(head), max);
};

export const formatCharacterCount = (count: number) => {
	if (!Number.isFinite(count) || count <= 0) return '0 chars';
	if (count < 1000) return `${count} chars`;
	if (count < 1000000) return `${(count / 1000).toFixed(count < 10000 ? 1 : 0)}k chars`;
	return `${(count / 1000000).toFixed(1)}m chars`;
};

export const formatCount = (count: number, singular: string, plural = `${singular}s`) => {
	return `${count} ${count === 1 ? singular : plural}`;
};

const parseDeclaredSearchCount = (text: string) => {
	const match = text.match(/\bFound\s+(\d+)\s+results?\b/i);
	return match ? Number.parseInt(match[1], 10) : null;
};

const parseDeclaredFetchCount = (text: string) => {
	const match = text.match(/\bRetrieved\s+content\s+from\s+(\d+)\s+URL\(s\)/i);
	return match ? Number.parseInt(match[1], 10) : null;
};

export const parseWebSearchResult = (
	rawResult: unknown,
	rawArgs?: unknown
): ParsedWebSearchResult => {
	const raw = decodeToolResultText(rawResult);
	const args = getToolArgumentsObject(rawArgs);
	const queryFromArgs = typeof args.query === 'string' ? args.query : '';
	const queryFromHeader = raw.match(/^##\s*Search Results for:\s*(.+?)\s*$/im)?.[1]?.trim() ?? '';
	const declaredCount = parseDeclaredSearchCount(raw);

	const results: WebSearchItem[] = [];
	const headingRegex = /^###\s*Result\s+(\d+)\b.*$/gim;
	const headings = [...raw.matchAll(headingRegex)];

	for (let i = 0; i < headings.length; i += 1) {
		const heading = headings[i];
		const nextHeading = headings[i + 1];
		const start = (heading.index ?? 0) + heading[0].length;
		const end = nextHeading?.index ?? raw.length;
		const block = raw.slice(start, end);

		const index = Number.parseInt(heading[1] ?? `${i + 1}`, 10) || i + 1;
		const title = extractMarkdownField(block, 'Title');
		const url = extractMarkdownField(block, 'URL');
		const snippet = extractMarkdownField(block, 'Snippet');

		if (!title && !url && !snippet) continue;

		results.push({
			index,
			title: title || url || `Result ${index}`,
			url,
			domain: getDomain(url),
			snippet
		});
	}

	return {
		ok: results.length > 0,
		query: queryFromArgs || queryFromHeader,
		declaredCount,
		results,
		raw
	};
};

export const parseWebFetchResult = (rawResult: unknown): ParsedWebFetchResult => {
	const raw = decodeToolResultText(rawResult);
	const declaredCount = parseDeclaredFetchCount(raw);
	const pages: WebFetchPage[] = [];
	const pageHeadingRegex = /^###\s*Page\s+(\d+)\s*:\s*(.*?)\s*$/gim;
	const allHeadings = [...raw.matchAll(pageHeadingRegex)];
	const headings = allHeadings.filter((heading, idx) => {
		if (idx === 0) return true;

		// Page headings generated by web_fetch are separated by a standalone
		// markdown rule. Fetched page bodies can themselves contain headings like
		// "### Page 2", so only treat subsequent matches as page boundaries when
		// they are immediately preceded by that generated separator.
		const position = heading.index ?? 0;
		const prefix = raw.slice(Math.max(0, position - 24), position);
		return /\n---\s*\n\s*$/.test(prefix);
	});

	for (let i = 0; i < headings.length; i += 1) {
		const heading = headings[i];
		const nextHeading = headings[i + 1];
		const start = (heading.index ?? 0) + heading[0].length;
		const end = nextHeading?.index ?? raw.length;
		let block = raw.slice(start, end).trim();

		// Remove the separator that web_fetch appends after each page while keeping
		// separators that may legitimately appear inside the fetched document body.
		block = block.replace(/\n---\s*$/, '').trim();

		const index = Number.parseInt(heading[1] ?? `${i + 1}`, 10) || i + 1;
		const title = heading[2]?.trim() || `Page ${index}`;
		const url = extractMarkdownField(block, 'URL');
		const published = extractMarkdownField(block, 'Published');
		const author = extractMarkdownField(block, 'Author');
		const description = extractMarkdownField(block, 'Description');

		const contentMarker = block.match(/\*\*Content:\*\*\s*/i);
		let content = '';
		if (contentMarker?.index != null) {
			content = block.slice(contentMarker.index + contentMarker[0].length).trim();
			content = content.replace(/\n---\s*$/, '').trim();
		}

		pages.push({
			index,
			title,
			url,
			domain: getDomain(url),
			published,
			author,
			description,
			content,
			characters: content.length
		});
	}

	return {
		ok: pages.length > 0,
		declaredCount,
		pages,
		totalCharacters: pages.reduce((sum, page) => sum + page.characters, 0),
		raw
	};
};

export const getToolCallSummary = (
	name: ToolName,
	rawArgs: unknown,
	rawResult: unknown,
	done: boolean
): ToolCallSummary => {
	// Keep the generic path intentionally cheap. Tool call rows render even when
	// collapsed, so only decode potentially huge result strings for the web tools
	// that actually use the richer summary metadata.
	if (name === 'web_search') {
		const args = getToolArgumentsObject(rawArgs);
		const rawResultString = typeof rawResult === 'string' ? rawResult : '';
		const queryFromArgs = typeof args.query === 'string' ? args.query.trim() : '';
		const decodedResultForFallback = done && !queryFromArgs ? decodeToolResultText(rawResult) : '';
		const query =
			queryFromArgs ||
			decodedResultForFallback.match(/^##\s*Search Results for:\s*(.+?)\s*$/im)?.[1]?.trim() ||
			'';
		const count = done
			? (parseDeclaredSearchCount(rawResultString) ??
				(decodedResultForFallback ? parseDeclaredSearchCount(decodedResultForFallback) : null))
			: null;

		return {
			kind: 'web_search',
			title: query ? `Search: “${truncateEnd(query, 72)}”` : 'web_search',
			subtitle: done
				? count != null
					? formatCount(count, 'result')
					: 'Search complete'
				: 'Searching…',
			badge: 'web'
		};
	}

	if (name === 'web_fetch') {
		const args = getToolArgumentsObject(rawArgs);
		const rawResultString = typeof rawResult === 'string' ? rawResult : '';
		const urlsArg = typeof args.urls === 'string' ? args.urls : '';
		const requestedUrls = urlsArg
			.split(/[\n,]+/)
			.map((url) => url.trim())
			.filter(Boolean);
		const count = done ? parseDeclaredFetchCount(rawResultString) : null;
		const charCount =
			rawResultString.length > 0 ? formatCharacterCount(rawResultString.length) : '';

		return {
			kind: 'web_fetch',
			title: done
				? `Fetched ${count != null ? formatCount(count, 'page') : 'web pages'}`
				: `Fetching ${requestedUrls.length ? formatCount(requestedUrls.length, 'URL') : 'web pages'}…`,
			subtitle: done ? charCount : requestedUrls.map((url) => getDomain(url) || url).join(', '),
			badge: 'web'
		};
	}

	return {
		kind: 'generic',
		title: `View Result from ${name}`
	};
};
