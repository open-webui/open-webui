import type { ComponentType } from 'svelte';

import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
import BookOpen from '$lib/components/icons/BookOpen.svelte';
import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
import ClockRotateRight from '$lib/components/icons/ClockRotateRight.svelte';
import CodeBracket from '$lib/components/icons/CodeBracket.svelte';
import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
import Note from '$lib/components/icons/Note.svelte';
import Photo from '$lib/components/icons/Photo.svelte';
import Search from '$lib/components/icons/Search.svelte';
import Sparkles from '$lib/components/icons/Sparkles.svelte';
import Users from '$lib/components/icons/Users.svelte';
import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';

type TranslateFn = (key: string, options?: Record<string, unknown>) => string;
type ToolAction = 'search' | 'open' | 'read' | 'list' | 'review' | 'save' | 'update' | 'delete';

export type ToolPresentationFamily =
	| 'time'
	| 'web'
	| 'media'
	| 'code'
	| 'memory'
	| 'notes'
	| 'chats'
	| 'channels'
	| 'knowledge'
	| 'skills'
	| 'generic';

export type ToolPresentationChip = {
	type: 'text' | 'host';
	label: string;
	url?: string;
	faviconUrl?: string;
};

export type ToolSourceGroupFavicon = {
	url: string;
	faviconUrl: string;
	hostname: string;
};

export type ToolSourceGroup = {
	favicons: ToolSourceGroupFavicon[];
	totalCount: number;
};

export type ToolPresentation = {
	family: ToolPresentationFamily;
	icon: ComponentType;
	pendingLabel: string;
	doneLabel: string;
	chips: ToolPresentationChip[];
	sourceGroup?: ToolSourceGroup;
	debugName: string;
};

/**
 * Keep tool activity copy intentionally small.
 * The repo extracts i18n keys from direct `t('...')` calls, so avoid hiding
 * translatable strings behind intermediate constants that the parser cannot see.
 */
const KNOWN_NATIVE_TOOLS = new Set([
	'get_current_timestamp',
	'calculate_timestamp',
	'search_web',
	'fetch_url',
	'generate_image',
	'edit_image',
	'execute_code',
	'search_memories',
	'add_memory',
	'replace_memory_content',
	'delete_memory',
	'list_memories',
	'search_notes',
	'view_note',
	'write_note',
	'replace_note_content',
	'search_chats',
	'view_chat',
	'search_channels',
	'search_channel_messages',
	'view_channel_message',
	'view_channel_thread',
	'list_knowledge_bases',
	'search_knowledge_bases',
	'search_knowledge_files',
	'view_file',
	'view_knowledge_file',
	'list_knowledge',
	'query_knowledge_files',
	'query_knowledge_bases',
	'view_skill'
]);

const FAMILY_ORDER: ToolPresentationFamily[] = [
	'web',
	'knowledge',
	'notes',
	'memory',
	'chats',
	'channels',
	'media',
	'code',
	'time',
	'skills',
	'generic'
];

const TOOL_ICONS: Record<ToolPresentationFamily, ComponentType> = {
	time: ClockRotateRight,
	web: GlobeAlt,
	media: Photo,
	code: CodeBracket,
	memory: ArchiveBox,
	notes: Note,
	chats: ChatBubbles,
	channels: Users,
	knowledge: BookOpen,
	skills: Sparkles,
	generic: WrenchSolid
};

const SEARCH_ICON = Search;
const MAX_CHIP_LABEL_LENGTH = 48;

const lowerCaseStart = (value: string) =>
	value.length > 0 ? `${value.charAt(0).toLowerCase()}${value.slice(1)}` : value;

const truncateLabel = (value: string, maxLength: number = MAX_CHIP_LABEL_LENGTH) =>
	value.length > maxLength ? `${value.slice(0, maxLength - 3)}...` : value;

const asRecord = (value: unknown): Record<string, unknown> | null => {
	if (!value || typeof value !== 'object' || Array.isArray(value)) {
		return null;
	}

	return value as Record<string, unknown>;
};

const asArray = (value: unknown): unknown[] => {
	if (Array.isArray(value)) {
		return value;
	}

	return [];
};

const asString = (value: unknown): string | null => {
	if (typeof value !== 'string') {
		return null;
	}

	const trimmed = value.trim();
	return trimmed.length > 0 ? trimmed : null;
};

const shortId = (value: unknown) => {
	const id = asString(value);
	return id ? id.slice(0, 8) : null;
};

const createTextChip = (label: string): ToolPresentationChip => ({
	type: 'text',
	label: truncateLabel(label)
});

const createHostChip = (url: string, label?: string): ToolPresentationChip | null => {
	const host = getHostname(url);

	if (!host) {
		return null;
	}

	return {
		type: 'host',
		label: truncateLabel(label ?? host),
		url,
		faviconUrl: getFaviconUrl(url)
	};
};

const uniqueChips = (chips: Array<ToolPresentationChip | null>) => {
	const seen = new Set<string>();

	return chips.filter((chip): chip is ToolPresentationChip => {
		if (!chip) {
			return false;
		}

		const key = `${chip.type}:${chip.label}:${chip.url ?? ''}`;
		if (seen.has(key)) {
			return false;
		}

		seen.add(key);
		return true;
	});
};

const buildPresentation = ({
	family,
	icon,
	pendingLabel,
	doneLabel,
	chips = [],
	sourceGroup,
	debugName
}: {
	family: ToolPresentationFamily;
	icon: ComponentType;
	pendingLabel: string;
	doneLabel: string;
	chips?: ToolPresentationChip[];
	sourceGroup?: ToolSourceGroup;
	debugName: string;
}): ToolPresentation => ({
	family,
	icon,
	pendingLabel,
	doneLabel,
	chips,
	sourceGroup,
	debugName
});

const buildFallbackPresentation = (toolName: string, translate: TranslateFn): ToolPresentation => {
	const t = translate;
	const humanized = humanizeToolName(toolName);

	return buildPresentation({
		family: 'generic',
		icon: TOOL_ICONS.generic,
		pendingLabel: t('Executing {{TOOL_NAME}}', { TOOL_NAME: humanized }),
		doneLabel: t('Viewed result from {{TOOL_NAME}}', { TOOL_NAME: humanized }),
		debugName: toolName
	});
};

const getToolFamily = (toolName: string): ToolPresentationFamily => {
	if (!KNOWN_NATIVE_TOOLS.has(toolName)) {
		return 'generic';
	}

	if (['get_current_timestamp', 'calculate_timestamp'].includes(toolName)) {
		return 'time';
	}

	if (['search_web', 'fetch_url'].includes(toolName)) {
		return 'web';
	}

	if (['generate_image', 'edit_image'].includes(toolName)) {
		return 'media';
	}

	if (toolName === 'execute_code') {
		return 'code';
	}

	if (
		[
			'search_memories',
			'add_memory',
			'replace_memory_content',
			'delete_memory',
			'list_memories'
		].includes(toolName)
	) {
		return 'memory';
	}

	if (['search_notes', 'view_note', 'write_note', 'replace_note_content'].includes(toolName)) {
		return 'notes';
	}

	if (['search_chats', 'view_chat'].includes(toolName)) {
		return 'chats';
	}

	if (
		[
			'search_channels',
			'search_channel_messages',
			'view_channel_message',
			'view_channel_thread'
		].includes(toolName)
	) {
		return 'channels';
	}

	if (
		[
			'list_knowledge_bases',
			'search_knowledge_bases',
			'search_knowledge_files',
			'view_file',
			'view_knowledge_file',
			'list_knowledge',
			'query_knowledge_files',
			'query_knowledge_bases'
		].includes(toolName)
	) {
		return 'knowledge';
	}

	if (toolName === 'view_skill') {
		return 'skills';
	}

	return 'generic';
};

const buildActionLabels = ({
	action,
	target,
	query,
	translate
}: {
	action: ToolAction;
	target: string;
	query?: string | null;
	translate: TranslateFn;
}) => {
	const t = translate;

	if (action === 'search') {
		if (query) {
			return {
				pendingLabel: t('Searching {{TARGET}} for "{{QUERY}}"', {
					TARGET: target,
					QUERY: query
				}),
				doneLabel: t('Searched {{TARGET}} for "{{QUERY}}"', {
					TARGET: target,
					QUERY: query
				})
			};
		}

		return {
			pendingLabel: t('Searching {{TARGET}}', { TARGET: target }),
			doneLabel: t('Searched {{TARGET}}', { TARGET: target })
		};
	}

	if (action === 'open') {
		return {
			pendingLabel: t('Opening {{TARGET}}', { TARGET: target }),
			doneLabel: t('Opened {{TARGET}}', { TARGET: target })
		};
	}

	if (action === 'read') {
		return {
			pendingLabel: t('Reading {{TARGET}}', { TARGET: target }),
			doneLabel: t('Read {{TARGET}}', { TARGET: target })
		};
	}

	if (action === 'list') {
		return {
			pendingLabel: t('Listing {{TARGET}}', { TARGET: target }),
			doneLabel: t('Listed {{TARGET}}', { TARGET: target })
		};
	}

	if (action === 'review') {
		return {
			pendingLabel: t('Reviewing {{TARGET}}', { TARGET: target }),
			doneLabel: t('Reviewed {{TARGET}}', { TARGET: target })
		};
	}

	if (action === 'save') {
		return {
			pendingLabel: t('Saving {{TARGET}}', { TARGET: target }),
			doneLabel: t('Saved {{TARGET}}', { TARGET: target })
		};
	}

	if (action === 'update') {
		return {
			pendingLabel: t('Updating {{TARGET}}', { TARGET: target }),
			doneLabel: t('Updated {{TARGET}}', { TARGET: target })
		};
	}

	return {
		pendingLabel: t('Deleting {{TARGET}}', { TARGET: target }),
		doneLabel: t('Deleted {{TARGET}}', { TARGET: target })
	};
};

const extractSourceGroup = (result: unknown): ToolSourceGroup | undefined => {
	const items = asArray(result)
		.map((item) => asRecord(item))
		.filter((item): item is Record<string, unknown> => item !== null);

	const links = items.map((item) => asString(item.link)).filter((link): link is string => !!link);

	if (links.length === 0) {
		return undefined;
	}

	const seenHosts = new Set<string>();
	const favicons: ToolSourceGroupFavicon[] = [];

	for (const link of links) {
		const hostname = getHostname(link);
		if (!hostname || seenHosts.has(hostname)) {
			continue;
		}
		seenHosts.add(hostname);
		favicons.push({
			url: link,
			faviconUrl: getFaviconUrl(link),
			hostname
		});
	}

	return {
		favicons,
		totalCount: links.length
	};
};

export const safeParseUrl = (value: unknown) => {
	const stringValue = asString(value);

	if (!stringValue) {
		return null;
	}

	try {
		return new URL(stringValue);
	} catch {
		return null;
	}
};

export const getHostname = (value: unknown) => safeParseUrl(value)?.hostname ?? null;

export const getFaviconUrl = (value: unknown) => {
	const host = getHostname(value);
	return host
		? `https://www.google.com/s2/favicons?sz=32&domain=${encodeURIComponent(host)}`
		: '/favicon.png';
};

export const humanizeToolName = (toolName: string) =>
	toolName
		.split('_')
		.filter(Boolean)
		.map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
		.join(' ');

const getFamilySummaryLabel = (
	family: ToolPresentationFamily,
	pending: boolean,
	translate: TranslateFn
) => {
	const t = translate;

	switch (family) {
		case 'web':
			return pending ? t('Exploring the web') : t('Explored the web');
		case 'knowledge':
			return pending ? t('Reviewing knowledge') : t('Reviewed knowledge');
		case 'notes':
			return pending ? t('Reviewing notes') : t('Reviewed notes');
		case 'memory':
			return pending ? t('Reviewing saved memories') : t('Reviewed saved memories');
		case 'media':
			return pending ? t('Generating media') : t('Generated media');
		case 'code':
			return pending ? t('Running analysis') : t('Ran {{COUNT}} analysis', { COUNT: 1 });
		case 'time':
			return pending ? t('Checking time') : t('Checked time');
		case 'chats':
			return pending
				? t('Reviewing {{TARGET}}', { TARGET: t('Chats') })
				: t('Reviewed {{TARGET}}', { TARGET: t('Chats') });
		case 'channels':
			return pending
				? t('Reviewing {{TARGET}}', { TARGET: t('Channels') })
				: t('Reviewed {{TARGET}}', { TARGET: t('Channels') });
		case 'skills':
			return pending
				? t('Reviewing {{TARGET}}', { TARGET: t('Skills') })
				: t('Reviewed {{TARGET}}', { TARGET: t('Skills') });
		default:
			return null;
	}
};

export const getToolFamilySummary = (
	toolNames: string[],
	pending: boolean,
	translate: TranslateFn
) => {
	const parts: string[] = [];
	const seenFamilies = new Set<ToolPresentationFamily>();
	const genericCounts = new Map<string, number>();

	for (const toolName of toolNames) {
		const family = getToolFamily(toolName);

		if (family === 'generic') {
			const humanized = humanizeToolName(toolName || 'tool');
			genericCounts.set(humanized, (genericCounts.get(humanized) ?? 0) + 1);
			continue;
		}

		if (!seenFamilies.has(family)) {
			seenFamilies.add(family);
		}
	}

	for (const family of FAMILY_ORDER) {
		if (!seenFamilies.has(family)) {
			continue;
		}

		const label = getFamilySummaryLabel(family, pending, translate);
		if (label) {
			parts.push(label);
		}
	}

	for (const [label, count] of genericCounts.entries()) {
		parts.push(count > 1 ? `${count} ${label}` : label);
	}

	if (parts.length <= 1) {
		return parts.join('');
	}

	return parts.map((part, index) => (index === 0 ? part : lowerCaseStart(part))).join(', ');
};

export const getToolPresentation = ({
	toolName,
	args,
	result,
	translate
}: {
	toolName: string;
	args?: unknown;
	result?: unknown;
	translate: TranslateFn;
}): ToolPresentation => {
	const t = translate;
	const normalizedToolName = toolName || 'tool';
	const argsRecord = asRecord(args);
	const family = getToolFamily(normalizedToolName);
	const fallback = buildFallbackPresentation(normalizedToolName, translate);

	if (family === 'generic') {
		return fallback;
	}

	const query = asString(argsRecord?.query);
	const url = asString(argsRecord?.url);
	const title = asString(argsRecord?.title);
	const noteId = shortId(argsRecord?.note_id);
	const memoryId = shortId(argsRecord?.memory_id);
	const chatId = shortId(argsRecord?.chat_id);
	const messageId = shortId(argsRecord?.message_id);
	const parentMessageId = shortId(argsRecord?.parent_message_id);
	const fileId = shortId(argsRecord?.file_id);
	const name = asString(argsRecord?.name);
	const prompt = asString(argsRecord?.prompt);
	const host = getHostname(url);

	switch (normalizedToolName) {
		case 'get_current_timestamp':
			return buildPresentation({
				family,
				icon: TOOL_ICONS.time,
				pendingLabel: t('Checking time'),
				doneLabel: t('Checked time'),
				debugName: normalizedToolName
			});
		case 'calculate_timestamp':
			return buildPresentation({
				family,
				icon: TOOL_ICONS.time,
				pendingLabel: t('Calculating a timestamp'),
				doneLabel: t('Calculated a timestamp'),
				debugName: normalizedToolName
			});
		case 'search_web':
			return buildPresentation({
				family,
				icon: SEARCH_ICON,
				pendingLabel: query
					? t('Searching for "{{QUERY}}"', { QUERY: query })
					: t('Searching the web'),
				doneLabel: query ? t('Searched for "{{QUERY}}"', { QUERY: query }) : t('Explored the web'),
				sourceGroup: extractSourceGroup(result),
				debugName: normalizedToolName
			});
		case 'fetch_url':
			return buildPresentation({
				family,
				icon: TOOL_ICONS.web,
				pendingLabel: host ? t('Browsing {{HOST}}', { HOST: host }) : t('Exploring the web'),
				doneLabel: host ? t('Browsed {{HOST}}', { HOST: host }) : t('Explored the web'),
				chips: uniqueChips([url ? createHostChip(url) : null]),
				debugName: normalizedToolName
			});
		case 'generate_image':
			return buildPresentation({
				family,
				icon: TOOL_ICONS.media,
				pendingLabel: t('Generating an image'),
				doneLabel: t('Generated an image'),
				chips: uniqueChips([prompt ? createTextChip(prompt) : null]),
				debugName: normalizedToolName
			});
		case 'edit_image':
			return buildPresentation({
				family,
				icon: TOOL_ICONS.media,
				pendingLabel: t('Editing an image'),
				doneLabel: t('Edited an image'),
				chips: uniqueChips([prompt ? createTextChip(prompt) : null]),
				debugName: normalizedToolName
			});
		case 'execute_code':
			return buildPresentation({
				family,
				icon: TOOL_ICONS.code,
				pendingLabel: t('Running analysis'),
				doneLabel: t('Ran {{COUNT}} analysis', { COUNT: 1 }),
				debugName: normalizedToolName
			});
		case 'search_memories': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Memories'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.memory,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'add_memory': {
			const labels = buildActionLabels({
				action: 'save',
				target: t('Memory'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.memory,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'replace_memory_content': {
			const labels = buildActionLabels({
				action: 'update',
				target: t('Memory'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.memory,
				...labels,
				chips: uniqueChips([memoryId ? createTextChip(`#${memoryId}`) : null]),
				debugName: normalizedToolName
			});
		}
		case 'delete_memory': {
			const labels = buildActionLabels({
				action: 'delete',
				target: t('Memory'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.memory,
				...labels,
				chips: uniqueChips([memoryId ? createTextChip(`#${memoryId}`) : null]),
				debugName: normalizedToolName
			});
		}
		case 'list_memories': {
			const labels = buildActionLabels({
				action: 'review',
				target: t('Memories'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.memory,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'search_notes': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Notes'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.notes,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'view_note': {
			const labels = buildActionLabels({
				action: 'open',
				target: t('Note'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.notes,
				...labels,
				chips: uniqueChips([noteId ? createTextChip(`#${noteId}`) : null]),
				debugName: normalizedToolName
			});
		}
		case 'write_note': {
			const labels = buildActionLabels({
				action: 'save',
				target: t('Note'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.notes,
				...labels,
				chips: uniqueChips([title ? createTextChip(title) : null]),
				debugName: normalizedToolName
			});
		}
		case 'replace_note_content': {
			const labels = buildActionLabels({
				action: 'update',
				target: t('Note'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.notes,
				...labels,
				chips: uniqueChips([
					title ? createTextChip(title) : null,
					noteId ? createTextChip(`#${noteId}`) : null
				]),
				debugName: normalizedToolName
			});
		}
		case 'search_chats': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Chats'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.chats,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'view_chat': {
			const labels = buildActionLabels({
				action: 'open',
				target: t('Chat'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.chats,
				...labels,
				chips: uniqueChips([chatId ? createTextChip(`#${chatId}`) : null]),
				debugName: normalizedToolName
			});
		}
		case 'search_channels': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Channels'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.channels,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'search_channel_messages': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Channel messages'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.channels,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'view_channel_message': {
			const labels = buildActionLabels({
				action: 'open',
				target: t('Channel message'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.channels,
				...labels,
				chips: uniqueChips([messageId ? createTextChip(`#${messageId}`) : null]),
				debugName: normalizedToolName
			});
		}
		case 'view_channel_thread': {
			const labels = buildActionLabels({
				action: 'open',
				target: t('Thread'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.channels,
				...labels,
				chips: uniqueChips([parentMessageId ? createTextChip(`#${parentMessageId}`) : null]),
				debugName: normalizedToolName
			});
		}
		case 'list_knowledge_bases': {
			const labels = buildActionLabels({
				action: 'list',
				target: t('Knowledge bases'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.knowledge,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'search_knowledge_bases': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Knowledge bases'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.knowledge,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'search_knowledge_files': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Knowledge files'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.knowledge,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'view_file': {
			const labels = buildActionLabels({
				action: 'read',
				target: t('File'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.knowledge,
				...labels,
				chips: uniqueChips([fileId ? createTextChip(`#${fileId}`) : null]),
				debugName: normalizedToolName
			});
		}
		case 'view_knowledge_file': {
			const labels = buildActionLabels({
				action: 'read',
				target: t('Knowledge file'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.knowledge,
				...labels,
				chips: uniqueChips([fileId ? createTextChip(`#${fileId}`) : null]),
				debugName: normalizedToolName
			});
		}
		case 'list_knowledge': {
			const labels = buildActionLabels({
				action: 'review',
				target: t('Knowledge'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.knowledge,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'query_knowledge_files': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Knowledge'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.knowledge,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'query_knowledge_bases': {
			const labels = buildActionLabels({
				action: 'search',
				target: t('Knowledge bases'),
				query,
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.knowledge,
				...labels,
				debugName: normalizedToolName
			});
		}
		case 'view_skill': {
			const labels = buildActionLabels({
				action: 'open',
				target: t('Skill'),
				translate
			});

			return buildPresentation({
				family,
				icon: TOOL_ICONS.skills,
				...labels,
				chips: uniqueChips([name ? createTextChip(name) : null]),
				debugName: normalizedToolName
			});
		}
		default:
			return buildPresentation({
				...fallback,
				family,
				icon: TOOL_ICONS[family] ?? TOOL_ICONS.generic
			});
	}
};
