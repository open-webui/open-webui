import { WEBUI_API_BASE_URL } from '$lib/constants';

export type CommentResource = {
	resource_type:
		| 'model'
		| 'knowledge'
		| 'prompt'
		| 'skill'
		| 'tool'
		| 'note'
		| 'chat';
	resource_id: string;
};
export type CommentAnchor = {
	quote: string;
	prefix: string;
	suffix: string;
	start: number;
	end: number;
	surface_id: string;
	source: string;
	content_hash: string;
};
export type CommentTarget = {
	target_type?: 'note_page' | 'chat_message';
	target_id?: string;
	anchor?: CommentAnchor;
};
export type ResourceComment = CommentResource & {
	id: string;
	parent_id: string | null;
	reply_to_id: string | null;
	content: string;
	target_type: string | null;
	target_id: string | null;
	meta: { anchor?: CommentAnchor } | null;
	user: { id: string; name: string; profile_image_url?: string } | null;
	created_at: number;
	updated_at: number;
	deleted_at: number | null;
	etag: string;
	reply_count: number;
	latest_reply_at?: number;
	can_edit: boolean;
	can_delete: boolean;
	reactions: { name: string; count: number; reacted: boolean }[];
};
export class CommentError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}
export async function commentsRequest<T>(
	path: string,
	method = 'GET',
	body?: unknown,
	signal?: AbortSignal
): Promise<T> {
	const response = await fetch(`${WEBUI_API_BASE_URL}/comments${path}`, {
		method,
		signal,
		headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.token}` },
		...(body === undefined ? {} : { body: JSON.stringify(body) })
	});
	const data = await response.json();
	if (!response.ok)
		throw new CommentError(
			response.status,
			typeof data.detail === 'string' ? data.detail : 'Unable to load comments'
		);
	return data;
}
export const resourceQuery = (resource: CommentResource) =>
	new URLSearchParams({
		resource_type: resource.resource_type,
		resource_id: resource.resource_id
	}).toString();
export const getComments = (resource: CommentResource, cursor?: string) =>
	commentsRequest<{ items: ResourceComment[]; next_cursor: string | null; total: number }>(
		`/?${resourceQuery(resource)}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`
	);
