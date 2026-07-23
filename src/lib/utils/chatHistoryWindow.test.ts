import { describe, expect, it } from 'vitest';
import {
	createMessagePatch,
	DEFAULT_CHAT_MESSAGE_WINDOW,
	getLoadedMessageIds,
	groupMessageIdsByModel,
	isChatMessageLoaded,
	mergeChatMessageEvent,
	mergeChatHistoryWindow,
	resolveLoadedCurrentMessageId,
	serializeChatForWindowSave,
	serializeMessageForPatch
} from './chatHistoryWindow';

describe('chatHistoryWindow', () => {
	it('uses a stable default window size', () => {
		expect(DEFAULT_CHAT_MESSAGE_WINDOW).toBe(32);
	});

	it('reads and deduplicates loaded IDs from message window metadata', () => {
		const history = {
			messages: {
				a: { id: 'a', content: 'A', __loaded: true },
				b: { id: 'b', __loaded: false }
			},
			messageWindow: { loadedIds: ['a', 'a', 'c'] }
		};

		expect(getLoadedMessageIds(history)).toEqual(['a', 'c']);
		expect(isChatMessageLoaded(history, 'a')).toBe(true);
		expect(isChatMessageLoaded(history, 'b')).toBe(false);
		expect(isChatMessageLoaded(history, 'missing')).toBe(false);
	});

	it('treats all messages in a legacy full history as loaded', () => {
		const history = {
			messages: { a: { id: 'a', content: 'A' }, b: { id: 'b', content: 'B' } }
		};

		expect(getLoadedMessageIds(history)).toEqual(['a', 'b']);
		expect(isChatMessageLoaded(history, 'b')).toBe(true);
	});

	it('keeps the loaded window current ID when the persisted column points to a stub', () => {
		const history = {
			currentId: 'latest',
			messages: {
				latest: { id: 'latest', content: 'latest response', __loaded: true },
				stale: { id: 'stale', role: 'assistant', __loaded: false }
			}
		};

		expect(resolveLoadedCurrentMessageId(history, 'stale')).toBe('latest');
	});

	it('uses a loaded persisted current ID only when the window has no loaded current ID', () => {
		const history = {
			currentId: null,
			messages: {
				persisted: { id: 'persisted', content: 'response', __loaded: true }
			}
		};

		expect(resolveLoadedCurrentMessageId(history, 'persisted')).toBe('persisted');
	});

	it('merges partial chat message events without clearing existing content', () => {
		const message = { id: 'assistant', content: 'kept', annotation: { rating: -1 } };

		expect(
			mergeChatMessageEvent(message, {
				chat_id: 'chat',
				message_id: 'assistant',
				annotation: { rating: 1 }
			})
		).toEqual({
			id: 'assistant',
			content: 'kept',
			annotation: { rating: 1 }
		});
		expect(mergeChatMessageEvent(message, { content: 'replaced' }, true)).toEqual({
			id: 'assistant',
			content: 'replaced',
			annotation: { rating: -1 }
		});
	});

	it('keeps unloaded multi-model siblings grouped and labelled by parent model order', () => {
		const parent = {
			id: 'user',
			models: ['model-a', 'model-b'],
			childrenIds: ['loaded-a', 'stub-b', 'retry-a']
		};
		const messages = {
			'loaded-a': { id: 'loaded-a', model: 'model-a', modelIdx: 0 },
			'stub-b': { id: 'stub-b', __loaded: false },
			'retry-a': { id: 'retry-a', model: 'model-a' }
		};

		expect(groupMessageIdsByModel(parent, messages)).toEqual({
			0: { messageIds: ['loaded-a', 'retry-a'] },
			1: { messageIds: ['stub-b'] }
		});
	});

	it('hydrates stubs, merges loaded IDs, and does not mutate either input', () => {
		const history = {
			currentId: 'b',
			messages: {
				a: {
					id: 'a',
					parentId: null,
					childrenIds: ['b'],
					content: 'A',
					__loaded: true
				},
				b: {
					id: 'b',
					parentId: 'a',
					childrenIds: ['c'],
					role: 'assistant',
					__loaded: false
				},
				d: { id: 'd', parentId: 'a', childrenIds: [], __loaded: false }
			},
			messageWindow: { loadedIds: ['a'], source: 'initial' }
		};
		const window = {
			messages: {
				b: { id: 'b', role: 'assistant', content: 'B' },
				c: { id: 'c', parentId: 'b', childrenIds: [], content: 'C' }
			},
			loadedIds: ['b', 'b'],
			hasMore: false,
			currentId: 'c'
		};
		const historySnapshot = structuredClone(history);
		const windowSnapshot = structuredClone(window);

		const merged = mergeChatHistoryWindow(history, window);

		expect(merged.messages?.b).toEqual({
			id: 'b',
			parentId: 'a',
			childrenIds: ['c'],
			role: 'assistant',
			content: 'B',
			__loaded: true
		});
		expect(merged.messages?.c).toEqual({ ...window.messages.c, __loaded: true });
		expect(merged.messages?.d?.__loaded).toBe(false);
		expect(merged.currentId).toBe('c');
		expect(merged.messageWindow).toEqual({
			loadedIds: ['a', 'b', 'c'],
			source: 'initial',
			hasMore: false,
			currentId: 'c'
		});
		expect(history).toEqual(historySnapshot);
		expect(window).toEqual(windowSnapshot);
	});

	it('saves hydrated and new messages, strips markers, and retains window metadata', () => {
		const chat = {
			title: 'Windowed chat',
			history: {
				currentId: 'stub',
				messages: {
					loaded: { id: 'loaded', content: '', role: 'user', __loaded: true },
					stub: {
						id: 'stub',
						parentId: 'loaded',
						childrenIds: [],
						__loaded: false
					},
					newMessage: { id: 'newMessage', content: 'new and not indexed yet' },
					hydrated: { id: 'hydrated', content: 'full', __loaded: true }
				},
				messageWindow: {
					loadedIds: ['loaded', 'stub', 'loaded'],
					hasMore: true
				}
			}
		};
		const snapshot = structuredClone(chat);

		const payload = serializeChatForWindowSave(chat);

		expect(payload.history?.messages).toEqual({
			loaded: { id: 'loaded', content: '', role: 'user' },
			newMessage: { id: 'newMessage', content: 'new and not indexed yet' },
			hydrated: { id: 'hydrated', content: 'full' }
		});
		expect(payload.history?.currentId).toBe('stub');
		expect(payload.history?.messageWindow).toEqual({
			loadedIds: ['loaded', 'stub'],
			hasMore: true
		});
		expect(chat).toEqual(snapshot);
	});

	it('serializes a single-message patch without topology or UI-only fields', () => {
		const message = {
			id: 'assistant',
			parentId: 'user',
			childrenIds: ['next'],
			role: 'assistant',
			timestamp: 123,
			content: 'edited',
			annotation: { rating: 1 },
			feedbackId: 'feedback',
			__loaded: true
		};

		expect(serializeMessageForPatch(message)).toEqual({
			content: 'edited',
			annotation: { rating: 1 },
			feedbackId: 'feedback'
		});
		expect(message).toHaveProperty('__loaded', true);
	});

	it('creates a minimal deep message patch and represents removed fields as null', () => {
		const previous = {
			id: 'assistant',
			content: 'a long response',
			annotation: { rating: -1 },
			files: [{ id: 'file' }],
			output: [{ type: 'message', content: 'unchanged' }]
		};
		const next = {
			...previous,
			annotation: { rating: 1 },
			files: undefined
		};

		expect(createMessagePatch(previous, next)).toEqual({
			annotation: { rating: 1 },
			files: null
		});
	});
});
