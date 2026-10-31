import { WEBUI_API_BASE_URL } from '$lib/constants';

export type InboxItem = {
	id: string;
	event_type: string;
	actor_type: 'user' | 'system';
	actor: { id: string; name: string } | null;
	resource_type: string | null;
	resource_id: string | null;
	object_type: string | null;
	object_id: string | null;
	title: string;
	preview: string;
	data: {
		message?: string;
		parent_id?: string;
		start_at?: number;
		target_type?: string;
		target_id?: string;
	};
	created_at: string;
	seen_at: string | null;
	read_at: string | null;
	is_new?: boolean;
};

export type InboxPage = {
	items: InboxItem[];
	next_cursor: string | null;
	count?: number;
	acknowledged_count?: number;
	acknowledged_at?: string;
};

export async function inboxRequest<T>(path: string, method = 'GET'): Promise<T> {
	const response = await fetch(`${WEBUI_API_BASE_URL}/notifications/inbox${path}`, {
		method,
		headers: { Authorization: `Bearer ${localStorage.token}`, Accept: 'application/json' }
	});
	if (!response.ok) {
		const error = await response.json().catch(() => ({}));
		throw new Error(error.detail || 'Could not load inbox');
	}
	return response.json();
}

export const inboxLabels: Record<string, string> = {
	'comment.created': '{{name}} commented',
	'comment.replied': '{{name}} replied',
	'comment.mentioned': '{{name}} mentioned you',
	'channel.mentioned': '{{name}} mentioned you',
	'channel.replied': '{{name}} replied',
	'calendar.alert': 'Upcoming event',
	'automation.run_failed': 'Automation failed',
	'system.announcement': 'Announcement'
};
