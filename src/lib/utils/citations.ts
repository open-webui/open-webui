import { decodeString, isValidHttpUrl } from '$lib/utils';
import { QUOTE_CONTEXT_LENGTH, type TextQuoteSelector } from '$lib/utils/comments/highlights';

// A cited document is identified by its metadata source, falling back to the source id.
const getDocumentId = (source: any, index: number): string =>
	source?.metadata?.[index]?.source ?? source?.source?.id ?? 'N/A';

const getSavedNumber = (source: any, index: number): number | null => {
	const number = source?.citation_ids?.[index];
	return Number.isInteger(number) && number > 0 ? number : null;
};

/**
 * Groups a message's sources into one citation per document, each with the number the
 * model cites it by: the number saved with the source, or its position for sources saved
 * before numbers were shared across the chat.
 */
export const getCitations = (sources: any[] | null | undefined) => {
	const citations: any[] = [];

	for (const source of sources ?? []) {
		if (!source || Object.keys(source).length === 0) {
			continue;
		}

		(source.document ?? []).forEach((document: string, index: number) => {
			const metadata = source.metadata?.[index];
			const distance = source.distances?.[index];
			const id = getDocumentId(source, index);

			const existing = citations.find((citation) => citation.id === id);
			if (existing) {
				existing.document.push(document);
				existing.metadata.push(metadata);
				// Kept in step with the documents, as not every document has one
				existing.distances.push(distance);
				existing.paragraphs.push(source.paragraphs?.[index] ?? []);
				return;
			}

			const isUrl = id.startsWith('http://') || id.startsWith('https://');
			let _source = source.source;
			if (metadata?.name) {
				_source = { ..._source, name: metadata.name };
			}
			if (isUrl) {
				_source = { ..._source, name: metadata?.external ? _source?.name : id, url: id };
			}

			citations.push({
				id,
				number: getSavedNumber(source, index) ?? citations.length + 1,
				title: metadata?.name || (isUrl ? id : (source.source?.name ?? id)),
				source: _source,
				document: [document],
				metadata: metadata ? [metadata] : [],
				distances: [distance],
				// Each document's numbered paragraphs, cited as [number#paragraph]
				paragraphs: [source.paragraphs?.[index] ?? []]
			});
		});
	}

	return citations;
};

const PASSAGE_PREVIEW_LIMIT = 400;

const getPassagePreview = (passage: string, isHtml: boolean): string => {
	let text = passage ?? '';
	if (isHtml) {
		const body = new DOMParser().parseFromString(text, 'text/html').body;
		body.querySelectorAll('script, style').forEach((element) => element.remove());
		text = body.textContent ?? '';
	}

	return text
		.trim()
		.slice(0, PASSAGE_PREVIEW_LIMIT)
		.replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
		.replace(/^\s*(?:#{1,6}|>)\s+/gm, '')
		.replace(/\*\*(.+?)\*\*/g, '$1')
		.replace(/\s+/g, ' ');
};

/** The paragraph numbers in citation identifiers such as "1#3". */
export const getParagraphIds = (identifiers: string[]): number[] => [
	...new Set(
		identifiers
			.map((identifier) => /^\d+#(\d+)$/.exec(identifier)?.[1])
			.filter((id): id is string => !!id)
			.map(Number)
	)
];

/** A stretch of a cited document, by offsets, with that document's metadata and relevance. */
export type CitedSpan = {
	document: string;
	start: number;
	end: number;
	metadata: any;
	distance: any;
};

/** The paragraphs a citation such as [1#3][1#4] points at, in order. */
export const getCitedPassages = (citation: any, paragraphIds: number[]) => {
	const passages: (CitedSpan & { id: number })[] = [];
	(citation?.document ?? []).forEach((document: string, index: number) => {
		for (const paragraph of citation.paragraphs?.[index] ?? []) {
			if (typeof document === 'string' && paragraphIds.includes(paragraph?.id)) {
				passages.push({
					id: paragraph.id,
					document,
					start: paragraph.start,
					end: paragraph.end,
					metadata: citation.metadata?.[index],
					distance: citation.distances?.[index]
				});
			}
		}
	});
	return passages.sort((a, b) => a.id - b.id);
};

/** The W3C quote selector for a span, with the context on either side that comment anchors keep. */
export const getQuoteSelector = ({ document, start, end }: CitedSpan): TextQuoteSelector => ({
	type: 'TextQuoteSelector',
	exact: document.slice(start, end),
	prefix: document.slice(Math.max(0, start - QUOTE_CONTEXT_LENGTH), start),
	suffix: document.slice(end, end + QUOTE_CONTEXT_LENGTH)
});

const getWords = (text: string): string[] =>
	text
		.normalize('NFKC')
		.toLowerCase()
		.match(/[\p{L}\p{N}]+/gu) ?? [];

const countWords = (words: string[]) =>
	words.reduce(
		(counts, word) => counts.set(word, (counts.get(word) ?? 0) + 1),
		new Map<string, number>()
	);

/**
 * The sentences of the cited spans that support a claim, the answer text a citation follows,
 * in the order they appear. The claim is split into its sentences and clauses, and each part
 * takes the sentence most like it. Sentences follow Unicode sentence boundaries and are ranked
 * by cosine similarity of TF-IDF vectors, weighted as scikit-learn's TfidfVectorizer does by
 * default (smoothed idf, L2 norm). A part that shares no word with any sentence takes none, and
 * a sentence that holds no word of the claim the other sentences lack is left out, weakest first.
 */
export const getClaimSpans = (claim: string, spans: CitedSpan[]): CitedSpan[] => {
	const segmenter = new Intl.Segmenter(undefined, { granularity: 'sentence' });
	const sentences = spans.flatMap((span) =>
		[...segmenter.segment(span.document.slice(span.start, span.end))]
			.filter(({ segment }) => segment.trim())
			.map(({ segment, index }) => {
				const start = span.start + index + segment.length - segment.trimStart().length;
				const end = start + segment.trim().length;
				return { span: { ...span, start, end }, counts: countWords(getWords(segment)) };
			})
	);
	const frequency = new Map<string, number>();
	for (const { counts } of sentences) {
		for (const word of counts.keys()) frequency.set(word, (frequency.get(word) ?? 0) + 1);
	}
	const idf = (word: string) =>
		Math.log((1 + sentences.length) / (1 + (frequency.get(word) ?? 0))) + 1;

	// A part's own length is the same for every sentence, so it is left out of the cosine
	const matches = new Map<(typeof sentences)[number], number>();
	// Clauses end at a comma, semicolon or colon followed by a space, so 90,000 stays whole
	for (const { segment } of segmenter.segment(claim)) {
		for (const part of segment.split(/[,;:]\s/)) {
			const counts = countWords(getWords(part));
			let best: (typeof sentences)[number] | null = null;
			let bestScore = 0;
			for (const sentence of sentences) {
				let dot = 0;
				let norm = 0;
				for (const [word, count] of sentence.counts) {
					const weight = count * idf(word);
					norm += weight ** 2;
					dot += weight * (counts.get(word) ?? 0) * idf(word);
				}
				const score = norm ? dot / Math.sqrt(norm) : 0;
				if (score > bestScore) [best, bestScore] = [sentence, score];
			}
			if (best) matches.set(best, Math.max(matches.get(best) ?? 0, bestScore));
		}
	}

	const claimWords = new Set(getWords(claim));
	let kept = [...matches.keys()];
	for (const sentence of [...kept].sort((a, b) => matches.get(a)! - matches.get(b)!)) {
		const others = kept.filter((other) => other !== sentence);
		const words = [...sentence.counts.keys()].filter((word) => claimWords.has(word));
		if (others.length && words.every((word) => others.some((other) => other.counts.has(word)))) {
			kept = others;
		}
	}
	return sentences.filter((sentence) => kept.includes(sentence)).map(({ span }) => span);
};

/**
 * What a hovered citation shows: its title, and the cited paragraph or else the passage
 * the citation modal lists first.
 */
export const getCitationPreview = (citation: any, paragraphIds: number[] = []) => {
	const { document, metadata, distances } = citation;
	const isRanked =
		distances.length === document.length &&
		distances.every((distance: any) => typeof distance === 'number');
	const index = isRanked ? distances.indexOf(Math.max(...distances)) : 0;
	const [cited] = getCitedPassages(citation, paragraphIds);
	const passageMetadata = cited ? cited.metadata : metadata[index];

	const name = decodeString(citation.title);
	const url = isValidHttpUrl(citation.source?.url) ? citation.source.url : null;

	return {
		// A page is known by its title, or by its domain when it has none
		title: url
			? passageMetadata?.title || (isValidHttpUrl(name) ? new URL(url).hostname : name)
			: name,
		url,
		page: Number.isInteger(passageMetadata?.page) ? passageMetadata.page + 1 : null,
		passage: getPassagePreview(
			cited ? cited.document.slice(cited.start, cited.end) : document[index],
			!!passageMetadata?.html
		)
	};
};

// [1], [1, 2] or [1#page]; not a link label like [1](url)
const CITATION_PATTERN = /\[(\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\](?!\()/g;

const getCitedNumbers = (content: string) => {
	const numbers = new Set<number>();
	for (const segment of content.split(/(```[\s\S]*?```|`[\s\S]*?`)/)) {
		if (segment.startsWith('`')) {
			continue;
		}
		for (const match of segment.matchAll(CITATION_PATTERN)) {
			for (const part of match[1].split(',')) {
				numbers.add(parseInt(part, 10));
			}
		}
	}
	return numbers;
};

/**
 * Sources from earlier turns that a message cites without having them itself. The model is
 * shown earlier tool results again, so it can cite their sources without fetching them anew.
 */
export const getCarriedSources = (
	messages: Record<string, any> | null | undefined,
	message: any
) => {
	const content = message?.content;
	if (typeof content !== 'string' || !content.includes('[')) {
		return [];
	}

	const cited = getCitedNumbers(content);
	for (const citation of getCitations(message.sources ?? message.citations)) {
		cited.delete(citation.number);
	}
	if (cited.size === 0) {
		return [];
	}

	const ancestors: any[] = [];
	const visited = new Set<string>();
	let parentId = message.parentId;
	while (parentId && messages?.[parentId] && !visited.has(parentId)) {
		visited.add(parentId);
		ancestors.push(messages[parentId]);
		parentId = messages[parentId].parentId;
	}
	ancestors.reverse();

	// Number the chain the way the backend does: a saved number wins, anything else takes the next.
	const numbers = new Map<string, number>();
	const carried = new Map<number, any[]>();
	for (const ancestor of ancestors) {
		const found = new Map<number, any[]>();
		for (const source of ancestor.sources ?? []) {
			(source?.document ?? []).forEach((document: string, index: number) => {
				const id = getDocumentId(source, index);
				const saved = getSavedNumber(source, index);
				if (saved) {
					numbers.set(id, saved);
				} else if (!numbers.has(id)) {
					numbers.set(id, Math.max(0, ...numbers.values()) + 1);
				}

				const number = numbers.get(id) as number;
				if (!cited.has(number)) {
					return;
				}

				const metadata = source.metadata?.[index];
				const distance = source.distances?.[index];
				found.set(number, [
					...(found.get(number) ?? []),
					{
						source: source.source,
						document: [document],
						metadata: metadata ? [metadata] : [],
						distances: distance !== undefined ? [distance] : [],
						citation_ids: [number],
						paragraphs: [source.paragraphs?.[index] ?? []]
					}
				]);
			});
		}
		// When several turns hold a source, the latest is the copy the model saw last.
		for (const [number, sources] of found) {
			carried.set(number, sources);
		}
	}

	return [...carried.values()].flat();
};
