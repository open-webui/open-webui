import { searchUsers } from '$lib/apis/users';
import { getChannelMentionApps } from '$lib/apis/channels';

import type { Node } from '@tiptap/pm/model';
import type { EditorState } from '@tiptap/pm/state';

export type MentionItem = {
	type: 'user' | 'model' | 'app' | 'channel';
	id: string;
	label: string;
};

export const mentionAttributes = (item: MentionItem) => ({
	id: `${{ user: 'U', model: 'M', app: 'A', channel: 'C' }[item.type]}:${item.id}|${item.label}`,
	label: item.label,
	mentionSuggestionChar: item.type === 'channel' ? '#' : '@'
});

const mentionTextBlocks = (doc: Node) => {
	const blocks: { text: string; pos: number }[] = [];
	doc.descendants((node, pos) => {
		if (node.type.spec.code) return false;
		if (!node.isTextblock) return;
		let text = '';
		node.forEach((child) => {
			text +=
				child.type.name === 'hardBreak'
					? '\n'
					: child.isText &&
						  !child.marks.some((mark) => mark.type.spec.code || mark.type.name === 'link')
						? child.text
						: '\ufffc'.repeat(child.nodeSize);
		});
		blocks.push({ text, pos: pos + 1 });
		return false;
	});
	return blocks;
};

export const getMentionUserQueries = (doc: Node) => {
	const queries = new Set<string>();
	for (const { text } of mentionTextBlocks(doc)) {
		for (const match of text.matchAll(
			/<[@#$][^>]*>|(?:^|[\s([{])@([^\s@#<>.,!?;:()[\]{}\ufffc]+)/gu
		)) {
			if (match[1]) queries.add(match[1].toLowerCase());
		}
	}
	return [...queries];
};

export const resolveMentions = (state: EditorState, items: MentionItem[]) => {
	const tr = state.tr;
	const names = new Map<string, Map<string, MentionItem>>();
	for (const item of items) {
		if (!item.label || /[<>|\r\n]/.test(item.label)) continue;
		const attrs = mentionAttributes(item);
		for (const name of [item.label, item.id]) {
			const key = `${attrs.mentionSuggestionChar}${name}`.toLowerCase();
			if (!names.has(key)) names.set(key, new Map());
			names.get(key)!.set(attrs.id, item);
		}
	}
	if (!names.size || !state.schema.nodes.mention) return tr;

	const pattern = new RegExp(
		`<[@#$][^>]*>|(^|[\\s([{])(${[...names.keys()]
			.sort((a, b) => b.length - a.length)
			.map((name) => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
			.join('|')})(?=$|[\\s.,!?;:)\\]}])`,
		'giu'
	);
	for (const { text, pos } of mentionTextBlocks(state.doc)) {
		for (const match of text.matchAll(pattern)) {
			if (!match[2]) continue;
			const matches = names.get(match[2].toLowerCase())!;
			// Ambiguous names require an explicit selection from the menu.
			if (matches.size !== 1) continue;
			const item = [...matches.values()][0];
			const from = pos + match.index! + match[1].length;
			tr.replaceWith(
				tr.mapping.map(from),
				tr.mapping.map(from + match[2].length),
				state.schema.nodes.mention.create(
					mentionAttributes(item),
					null,
					state.doc.resolve(from).marks()
				)
			);
		}
	}
	return tr;
};

export const getChannelMentionCandidates = async (
	token: string,
	channelId: string,
	queries: string[],
	options: {
		users: boolean;
		apps: boolean;
		models: { id: string; name: string; direct?: boolean }[];
		channels: { id: string; name?: unknown; type?: string | null }[];
	}
): Promise<MentionItem[]> => {
	const [users, apps] = await Promise.all([
		options.users
			? Promise.all(
					queries.map(async (query) => {
						const users: { id: string; name: string }[] = [];
						for (let page = 1; ; page++) {
							const result = await searchUsers(token, query, 'name', 'asc', page);
							if (!result) throw new Error('Failed to load mention suggestions');
							users.push(...result.users);
							if (!result.users.length || users.length >= result.total) break;
						}
						return users;
					})
				).then((results) => results.flat())
			: [],
		options.apps && queries.length ? getChannelMentionApps(token, channelId) : []
	]);
	return [
		...users.map((u) => ({ type: 'user' as const, id: u.id, label: u.name })),
		...options.models
			.filter((m) => !m.direct)
			.map((m) => ({ type: 'model' as const, id: m.id, label: m.name })),
		...apps.map((a) => ({ type: 'app' as const, id: a.id, label: a.name })),
		...options.channels
			.filter((c) => c.type !== 'dm' && typeof c.name === 'string')
			.map((c) => ({ type: 'channel' as const, id: c.id, label: c.name as string }))
	];
};
