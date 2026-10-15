import { WEBUI_API_BASE_URL } from '$lib/constants';

export type SearchKind = 'chat' | 'message' | 'note';
export type SearchResult = {
	id: string;
	kind: SearchKind;
	title: string;
	context: string;
	snippet: string;
	preview: string;
	url: string;
	updated_at: number;
	shared: boolean;
	pinned: boolean;
};
export type SearchScope = { id: string; name: string; kind: 'folder' | 'channel' };
export type SearchResponse = {
	items: SearchResult[];
	has_more: boolean;
	scopes: SearchScope[];
	kinds: SearchKind[];
};

export const searchWorkspace = async (
	token: string,
	filters: { q: string; kind: string; sharing: string; scope: string; page: number },
	signal: AbortSignal
): Promise<SearchResponse> => {
	const params = new URLSearchParams({ ...filters, page: String(filters.page) });
	const response = await fetch(`${WEBUI_API_BASE_URL}/search?${params}`, {
		headers: { Authorization: `Bearer ${token}` },
		signal
	});
	if (!response.ok) throw new Error('Search is unavailable. Please try again.');
	return response.json();
};
