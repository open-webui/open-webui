import type { ChatParticipant } from '$lib/apis/folders';
import { tagColors, type FolderTag, type TagColor } from './tags';

// Folder list and board views page through a folder's chats this many at a time.
export const FOLDER_PAGE_SIZE = 50;
export type FolderActivity = 'unread' | 'generating' | 'waiting_for_approval' | 'idle';

// Chats only have "No status" built in; every other status is defined per folder.
// A chat's status is null when it has none; 'none' is only the key for that group, column and filter.
export const NO_STATUS = 'none';
export const statusGlyphs = ['backlog', 'todo', 'in_progress', 'waiting', 'done'] as const;
export type StatusGlyph = (typeof statusGlyphs)[number];
export type FolderStatus = string;
// A status shows an emoji when `icon` is set, otherwise its glyph in its color.
export type CustomStatus = {
	id: string;
	name: string;
	glyph?: StatusGlyph;
	color?: TagColor;
	icon?: string;
};
export type StatusDef = CustomStatus & { custom: boolean };

// Ready-made statuses for folders that never set up their own; an empty list means none.
export const defaultStatuses: CustomStatus[] = [
	{ id: 'backlog', name: 'Backlog', glyph: 'backlog', color: 'gray' },
	{ id: 'todo', name: 'To do', glyph: 'todo', color: 'gray' },
	{ id: 'in_progress', name: 'In progress', glyph: 'in_progress', color: 'amber' },
	{ id: 'waiting', name: 'Waiting', glyph: 'waiting', color: 'blue' },
	{ id: 'done', name: 'Done', glyph: 'done', color: 'violet' }
];
const usesDefaultStatuses = (meta?: { statuses?: unknown } | null) => meta?.statuses == null;

export const customStatuses = (meta?: { statuses?: unknown } | null): CustomStatus[] => {
	if (usesDefaultStatuses(meta)) return defaultStatuses;
	const seen = new Set<string>([NO_STATUS]);
	return (Array.isArray(meta?.statuses) ? meta.statuses : [])
		.filter(
			(item) =>
				!!item &&
				typeof item.id === 'string' &&
				typeof item.name === 'string' &&
				!seen.has(item.id) &&
				!!seen.add(item.id)
		)
		.map((item) => ({
			id: item.id,
			name: item.name,
			glyph: statusGlyphs.includes(item.glyph) ? item.glyph : 'todo',
			color: tagColors.includes(item.color) ? item.color : 'gray',
			icon: typeof item.icon === 'string' && item.icon ? item.icon : undefined
		}));
};

// "No status" first, then the folder's statuses in its own order (matches the server).
export const statusDefs = (
	meta: { statuses?: unknown } | null | undefined,
	t: (key: string) => string
): StatusDef[] => [
	{ id: NO_STATUS, name: t('No status'), custom: false },
	...customStatuses(meta).map((item) => ({
		...item,
		name: usesDefaultStatuses(meta) ? t(item.name) : item.name,
		custom: true
	}))
];

export const newStatusId = () => `s_${Math.random().toString(36).slice(2, 10)}`;

export const glyphColor: Record<TagColor, string> = {
	gray: 'text-gray-400 dark:text-gray-500',
	blue: 'text-blue-500',
	violet: 'text-violet-500',
	pink: 'text-pink-500',
	red: 'text-red-500',
	amber: 'text-amber-500',
	green: 'text-green-500',
	teal: 'text-teal-500'
};

export type WorkspaceChat = {
	id: string;
	title: string;
	user_id: string;
	owner_name?: string;
	tags: FolderTag[];
	status: FolderStatus | null;
	/** When the chat would have entered its status if all its time there were one stretch (seconds); earlier stretches count, so going back doesn't reset it. Null for no status or older chats. */
	status_since?: number | null;
	/** When the current stretch in this status began (seconds). */
	status_entered_at?: number | null;
	/** Earlier time per status, in seconds, from before the current stretch. */
	status_durations?: Record<string, number>;
	can_edit_tags: boolean;
	can_edit_status: boolean;
	updated_at: number;
	created_at: number;
	last_read_at?: number | null;
	participants?: ChatParticipant[];
	active?: boolean;
	pending_approval?: boolean;
	search_snippet?: string | null;
	/** Set when an automation made this chat. */
	automation_id?: string | null;
};
export const statusKey = (status?: FolderStatus | null) => status ?? NO_STATUS;

export type WorkspacePage = { chats: WorkspaceChat[]; total: number; has_more: boolean };
export type FolderUser = { id: string; name: string; count: number };

export const isChatUnread = (chat: WorkspaceChat) =>
	(chat.last_read_at ?? 0) === 0 || chat.updated_at > (chat.last_read_at ?? 0);
