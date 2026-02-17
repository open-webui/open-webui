export type PinnedSnippet = {
	id: string;
	messageId: string;
	text: string;
	createdAt: number;
};

export const MAX_PINNED_SNIPPET_LENGTH = 500;
export const MAX_PINNED_SNIPPETS = 50;

const getPinnedStorageKey = (chatId: string) => `chat-pinned-snippets-${chatId}`;

const normalizePinnedSnippet = (value: unknown): PinnedSnippet | null => {
	if (!value || typeof value !== 'object') return null;

	const candidate = value as Record<string, unknown>;

	if (
		typeof candidate.id !== 'string' ||
		typeof candidate.messageId !== 'string' ||
		typeof candidate.text !== 'string'
	) {
		return null;
	}

	const id = candidate.id.trim();
	const messageId = candidate.messageId.trim();
	const text = candidate.text.trim().slice(0, MAX_PINNED_SNIPPET_LENGTH);
	if (!id || !messageId || !text) return null;

	const rawCreatedAt = candidate.createdAt;
	const createdAt =
		typeof rawCreatedAt === 'number' && Number.isFinite(rawCreatedAt) ? rawCreatedAt : Date.now();

	// Recreate as a plain object so storage prototypes/extra fields do not leak into state.
	return { id, messageId, text, createdAt };
};

export const loadPinnedSnippets = (chatId: string): PinnedSnippet[] => {
	if (!chatId) return [];

	try {
		const raw = localStorage.getItem(getPinnedStorageKey(chatId));
		if (!raw) return [];

		const parsed = JSON.parse(raw);
		if (!Array.isArray(parsed)) return [];

		return parsed
			.map(normalizePinnedSnippet)
			.filter((snippet): snippet is PinnedSnippet => snippet !== null)
			.slice(0, MAX_PINNED_SNIPPETS);
	} catch {
		return [];
	}
};

export const savePinnedSnippets = (chatId: string, snippets: PinnedSnippet[]): boolean => {
	if (!chatId) return false;

	try {
		localStorage.setItem(getPinnedStorageKey(chatId), JSON.stringify(snippets));
		return true;
	} catch {
		return false;
	}
};
