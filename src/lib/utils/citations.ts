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
				if (distance !== undefined) existing.distances.push(distance);
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
				distances: distance !== undefined ? [distance] : []
			});
		});
	}

	return citations;
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
						citation_ids: [number]
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
