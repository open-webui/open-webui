import { WEBUI_API_BASE_URL } from '$lib/constants';

export type SourceInfo = {
	id?: string;
	name?: string;
	display_name?: string;
	type?: string;
	url?: string;
	original_url?: string;
	embed_url?: string;
	citable?: boolean;
	fetched?: boolean;
	[key: string]: unknown;
};

export type SourceMetadata = {
	source?: string;
	name?: string;
	display_name?: string;
	title?: string;
	filename?: string;
	file_name?: string;
	url?: string;
	file_id?: string;
	page?: number;
	citation_id?: string;
	description?: string;
	thumbnail_url?: string;
	image_url?: string;
	image?: string;
	og_image_url?: string;
	'og:image'?: string;
	date_published?: string;
	author?: string[];
	publisher?: string[];
	display?: 'embedded' | 'external' | 'auto';
	provenance?: string;
	citable?: boolean;
	fetched?: boolean;
	[key: string]: unknown;
};

export type SourceEntry = {
	source?: SourceInfo;
	document?: string[];
	metadata?: SourceMetadata[];
	distances?: number[];
};

export type CitationEntry = {
	id: string;
	source: SourceInfo;
	document: string[];
	metadata: SourceMetadata[];
	distances: (number | undefined)[];
};

const NON_PUBLIC_SUFFIX = /\.(?:internal|local|localdomain|home\.arpa)$/i;
const DOCUMENT_EXTENSIONS = new Set([
	'pdf',
	'xls',
	'xlsx',
	'doc',
	'docx',
	'ppt',
	'pptx',
	'csv',
	'tsv',
	'txt',
	'md',
	'mdx',
	'markdown',
	'zip',
	'tar',
	'gz',
	'tgz',
	'bz2',
	'xz',
	'7z',
	'rar'
]);

const documentNameFromCandidate = (candidate: unknown, isUrl = false): string | null => {
	if (typeof candidate !== 'string') return null;
	let value = candidate.trim();
	if (!value) return null;

	if (isUrl) {
		try {
			value = decodeURIComponent(new URL(value).pathname.split('/').pop() ?? '');
		} catch {
			value = value.split(/[?#]/, 1)[0].split('/').pop() ?? '';
		}
	} else {
		value = value.split(/[?#]/, 1)[0].split(/[/\\]/).pop() ?? '';
	}

	const match = value.match(/\.([a-z0-9]+)$/i);
	return match && DOCUMENT_EXTENSIONS.has(match[1].toLowerCase()) ? value : null;
};

export const getCitationDocumentName = (
	source?: SourceInfo,
	metadata?: SourceMetadata
): string | null => {
	const namedCandidates = [
		metadata?.name,
		metadata?.filename,
		metadata?.file_name,
		metadata?.title,
		source?.name,
		source?.filename,
		source?.file_name,
		source?.title,
		metadata?.source
	];
	for (const candidate of namedCandidates) {
		const documentName = documentNameFromCandidate(candidate);
		if (documentName) return documentName;
	}

	for (const candidate of [metadata?.url, source?.original_url, source?.url]) {
		const documentName = documentNameFromCandidate(candidate, true);
		if (documentName) return documentName;
	}
	return null;
};

export const parseCitationIdentifier = (identifier: string | number) => {
	const [rawIndex, suffix] = String(identifier).split('#', 2);
	const parsedIndex = Number.parseInt(rawIndex, 10);
	return {
		sourceIndex: Number.isFinite(parsedIndex) ? parsedIndex - 1 : -1,
		suffix
	};
};

export const getCitationTitle = (source?: SourceInfo, metadata?: SourceMetadata): string =>
	metadata?.name || source?.name || metadata?.url || source?.url || metadata?.source || 'N/A';

export const getCitationDisplayName = (source?: SourceInfo, metadata?: SourceMetadata): string => {
	for (const candidate of [metadata?.display_name, source?.display_name]) {
		if (typeof candidate === 'string' && candidate.trim()) return candidate.trim();
	}
	return getCitationTitle(source, metadata);
};

export const getCitationListLabel = (source?: SourceInfo, metadata?: SourceMetadata): string => {
	const title = getCitationTitle(source, metadata).trim();
	const publisher = [metadata?.display_name, source?.display_name, ...(metadata?.publisher ?? [])]
		.find((candidate) => typeof candidate === 'string' && candidate.trim())
		?.trim();

	if (!publisher || publisher.localeCompare(title, undefined, { sensitivity: 'accent' }) === 0) {
		return title;
	}
	return `${publisher} | ${title}`;
};

export const buildCitationEntries = (sources: SourceEntry[] = []): CitationEntry[] => {
	const entries: CitationEntry[] = [];
	const entriesById = new Map<string, CitationEntry>();

	for (const sourceEntry of sources ?? []) {
		if (!sourceEntry || Object.keys(sourceEntry).length === 0) continue;

		for (let index = 0; index < (sourceEntry.document ?? []).length; index += 1) {
			const metadata = sourceEntry.metadata?.[index] ?? {};
			const distance = sourceEntry.distances?.[index];
			const id = metadata.source ?? sourceEntry.source?.id ?? 'N/A';
			const existing = entriesById.get(id);

			if (existing) {
				existing.document.push(sourceEntry.document?.[index] ?? '');
				existing.metadata.push(metadata);
				existing.distances.push(distance);
				continue;
			}

			const source: SourceInfo = {
				...(sourceEntry.source ?? {}),
				...(sourceEntry.source?.url && metadata.url && sourceEntry.source.url !== metadata.url
					? { original_url: sourceEntry.source.url }
					: {}),
				...(metadata.name ? { name: metadata.name } : {}),
				...(metadata.url ? { url: metadata.url } : {})
			};
			const entry = {
				id,
				source,
				document: [sourceEntry.document?.[index] ?? ''],
				metadata: [metadata],
				distances: [distance]
			};
			entriesById.set(id, entry);
			entries.push(entry);
		}
	}

	return entries;
};

export const buildCitableCitationEntries = (sources: SourceEntry[] = []): CitationEntry[] =>
	buildCitationEntries(
		sources.filter(
			(sourceEntry) =>
				sourceEntry?.source?.citable !== false &&
				!(sourceEntry?.metadata ?? []).some((metadata) => metadata?.citable === false)
		)
	);

export const selectCitationEntry = (
	entry: CitationEntry,
	identifier: string | number
): CitationEntry => {
	const { suffix } = parseCitationIdentifier(identifier);
	if (!suffix) return entry;

	const selectedIndex = entry.metadata.findIndex(
		(metadata) =>
			metadata.citation_id === suffix ||
			metadata.source === suffix ||
			metadata.source?.endsWith(`:${suffix}`)
	);
	if (selectedIndex < 0) return entry;

	return {
		...entry,
		document: [entry.document[selectedIndex] ?? ''],
		metadata: [entry.metadata[selectedIndex] ?? {}],
		distances: [entry.distances[selectedIndex]]
	};
};

const isPrivateIpv4 = (hostname: string): boolean => {
	const parts = hostname.split('.').map(Number);
	if (
		parts.length !== 4 ||
		parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)
	) {
		return false;
	}
	return (
		parts[0] === 10 ||
		parts[0] === 127 ||
		(parts[0] === 169 && parts[1] === 254) ||
		(parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) ||
		(parts[0] === 192 && parts[1] === 168) ||
		parts[0] === 0
	);
};

export const getSafeCitationUrl = (url?: string | null): string | null => {
	const candidate = url?.trim();
	if (!candidate) return null;
	try {
		const parsed = new URL(candidate);
		if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
			return null;
		}
		const hostname = parsed.hostname.toLowerCase().replace(/^\[|\]$/g, '');
		if (
			hostname === 'localhost' ||
			NON_PUBLIC_SUFFIX.test(hostname) ||
			isPrivateIpv4(hostname) ||
			hostname === '::1' ||
			hostname.startsWith('fc') ||
			hostname.startsWith('fd') ||
			hostname.startsWith('fe80:')
		) {
			return null;
		}
		return parsed.href;
	} catch {
		return null;
	}
};

export const isLinkableCitationUrl = (url?: string | null): boolean =>
	getSafeCitationUrl(url) !== null;

export const isSafeCitationUrl = (url?: string | null): boolean => getSafeCitationUrl(url) !== null;

const GOOGLE_FAVICON_SERVICE_URL = 'https://www.google.com/s2/favicons';

const isInternalCitationUrl = (url: URL, appOrigin?: string | null): boolean => {
	const normalizedAppOrigin =
		appOrigin ?? (typeof window !== 'undefined' ? window.location.origin : null);
	if (normalizedAppOrigin && url.origin === normalizedAppOrigin) return true;
	return /^\/(?:api\/(?:v1\/)?files|files\/[^/]+\/content)(?:\/|$)/i.test(url.pathname);
};

const getExternalCitationOrigin = (url?: string | null, appOrigin?: string | null): URL | null => {
	const safeUrl = getSafeCitationUrl(url);
	if (!safeUrl) return null;
	const parsed = new URL(safeUrl);
	if (isInternalCitationUrl(parsed, appOrigin)) return null;
	return parsed;
};

export const getCitationFaviconUrl = (
	url?: string | null,
	appOrigin?: string | null,
	size = 32
): string | null => {
	const parsed = getExternalCitationOrigin(url, appOrigin);
	if (!parsed) return null;

	const faviconUrl = new URL(GOOGLE_FAVICON_SERVICE_URL);
	faviconUrl.searchParams.set('domain_url', parsed.origin);
	faviconUrl.searchParams.set('sz', String(size));
	return faviconUrl.href;
};

export const getCitationIconInfo = (
	source?: SourceInfo,
	metadata?: SourceMetadata,
	appOrigin?: string | null,
	size = 32
): { documentName: string | null; faviconUrl: string | null } => {
	const documentName = getCitationDocumentName(source, metadata);
	if (documentName) return { documentName, faviconUrl: null };

	for (const candidate of [metadata?.url, source?.original_url, source?.url]) {
		const faviconUrl = getCitationFaviconUrl(candidate, appOrigin, size);
		if (faviconUrl) {
			return { documentName: null, faviconUrl };
		}
	}
	return { documentName: null, faviconUrl: null };
};

export const getCitationThumbnailUrl = (metadata?: SourceMetadata): string | null => {
	for (const candidate of [
		metadata?.thumbnail_url,
		metadata?.image_url,
		metadata?.image,
		metadata?.og_image_url,
		metadata?.['og:image']
	]) {
		const imageUrl = getSafeCitationUrl(candidate);
		if (imageUrl) return imageUrl;
	}
	return null;
};

export const formatCitationDate = (
	value?: string | null,
	locale?: string | null
): string | null => {
	const input = value?.trim();
	if (!input) return null;

	const dateOnly = input.match(/^(\d{4})-(\d{2})-(\d{2})$/);
	const monthOnly = input.match(/^(\d{4})-(\d{2})$/);
	const yearOnly = input.match(/^(\d{4})$/);
	let date: Date;
	let options: Intl.DateTimeFormatOptions;

	if (dateOnly) {
		const [, year, month, day] = dateOnly.map(Number);
		date = new Date(Date.UTC(year, month - 1, day));
		if (
			date.getUTCFullYear() !== year ||
			date.getUTCMonth() !== month - 1 ||
			date.getUTCDate() !== day
		) {
			return input;
		}
		options = { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' };
	} else if (monthOnly) {
		const [, year, month] = monthOnly.map(Number);
		if (month < 1 || month > 12) return input;
		date = new Date(Date.UTC(year, month - 1, 1));
		options = { year: 'numeric', month: 'long', timeZone: 'UTC' };
	} else if (yearOnly) {
		date = new Date(Date.UTC(Number(yearOnly[1]), 0, 1));
		options = { year: 'numeric', timeZone: 'UTC' };
	} else {
		date = new Date(input);
		if (Number.isNaN(date.getTime())) return input;
		options = { year: 'numeric', month: 'short', day: 'numeric' };
	}

	try {
		return new Intl.DateTimeFormat(locale || undefined, options).format(date);
	} catch {
		return new Intl.DateTimeFormat(undefined, options).format(date);
	}
};

export const buildTextFragmentUrl = ({
	source,
	metadata,
	document
}: {
	source?: SourceInfo;
	metadata?: SourceMetadata;
	document?: string;
}): string | null => {
	const page =
		typeof metadata?.page === 'number' && Number.isInteger(metadata.page)
			? `#page=${metadata.page + 1}`
			: '';
	const baseUrl = metadata?.file_id
		? `${WEBUI_API_BASE_URL}/files/${metadata.file_id}/content${page}`
		: ([metadata?.url, source?.url].map(getSafeCitationUrl).find(Boolean) ?? null);

	if (
		!baseUrl ||
		baseUrl.includes('#') ||
		!document?.trim() ||
		source?.citable === false ||
		metadata?.citable === false
	)
		return baseUrl;
	const words = document
		.trim()
		.split(/\s+/)
		.filter((word) => !/https?:\/\/|[\u{1F300}-\u{1F9FF}]/u.test(word))
		.map((word) => word.replace(/[^\p{L}\p{N}]/gu, ''))
		.filter(Boolean);
	if (words.length === 0) return baseUrl;

	const fragment = words.length === 1 ? words[0] : `${words[0]},${words.at(-1)}`;
	return `${baseUrl}#:~:text=${encodeURIComponent(fragment)}`;
};

export const findCitationEntryForLink = (
	entries: CitationEntry[],
	href?: string,
	text?: string,
	title?: string | null
): { entry: CitationEntry; identifier: number } | null => {
	const normalizedText = text?.trim().toLocaleLowerCase();
	const normalizedTitle = title?.trim().toLocaleLowerCase();
	const index = entries.findIndex((entry) =>
		entry.metadata.some(
			(metadata) =>
				(Boolean(href) && (metadata.url === href || entry.source.url === href)) ||
				(Boolean(normalizedText) &&
					(metadata.name?.toLocaleLowerCase() === normalizedText ||
						metadata.citation_id?.toLocaleLowerCase() === normalizedText)) ||
				(Boolean(normalizedTitle) && metadata.name?.toLocaleLowerCase() === normalizedTitle)
		)
	);
	return index >= 0 ? { entry: entries[index], identifier: index + 1 } : null;
};
