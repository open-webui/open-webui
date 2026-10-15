export type CommentLocation =
	| { kind: 'word'; anchor: string; quote?: string }
	| { kind: 'cell'; sheet: string; cell: string }
	| {
			kind: 'slide';
			slide: number;
			hidden: boolean;
			pdfPage?: number;
			width?: number;
			height?: number;
			x?: number;
			y?: number;
	  }
	| { kind: 'pdf'; page: number; rect: number[]; quads?: number[] };

export interface FileComment {
	id: string;
	parentId?: string;
	text: string;
	author?: string;
	date?: string;
	status?: 'open' | 'resolved';
	location?: CommentLocation;
}
export interface CommentResult {
	comments: FileComment[];
	warnings: string[];
}
export type CommentState = 'loading' | 'ready' | 'partial' | 'error';
export const supportsComments = (path: string | null) =>
	/\.(docx|xlsx|xls|pptx|pdf)$/i.test(path ?? '');

/** Broken parent links must not make a comment disappear from the thread list. */
export function commentThreads(comments: FileComment[]): FileComment[][] {
	const byId = new Map(comments.map((c) => [c.id, c]));
	const groups = new Map<string, FileComment[]>();
	for (const comment of comments) {
		let root = comment;
		const visited = new Set([root.id]);
		while (root.parentId && byId.has(root.parentId)) {
			if (visited.has(root.parentId)) {
				root = comment;
				break;
			}
			root = byId.get(root.parentId)!;
			visited.add(root.id);
		}
		const group = groups.get(root.id) ?? [];
		group.push(comment);
		groups.set(root.id, group);
	}
	return [...groups].map(([id, group]) =>
		group.sort((a, b) => (a.id === id ? -1 : b.id === id ? 1 : 0))
	);
}

export function commentLocation(
	comment: FileComment,
	comments: FileComment[]
): CommentLocation | undefined {
	const seen = new Set<string>();
	let current: FileComment | undefined = comment;
	while (current && !seen.has(current.id)) {
		if (current.location) return current.location;
		seen.add(current.id);
		current = comments.find((c) => c.id === current?.parentId);
	}
}
