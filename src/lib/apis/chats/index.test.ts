import { afterEach, describe, expect, it, vi } from 'vitest';
import {
	deleteChatMessageById,
	getChatByIdWindow,
	getChatHistoryWindow,
	updateChatByIdWindow,
	updateChatMessageById
} from './index';

const jsonResponse = (body: unknown) =>
	Promise.resolve({
		ok: true,
		json: () => Promise.resolve(body)
	} as Response);

describe('windowed chat APIs', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('loads the initial chat window with a limit', async () => {
		const fetchMock = vi.fn(() => jsonResponse({ id: 'chat-id' }));
		vi.stubGlobal('fetch', fetchMock);

		await getChatByIdWindow('token', 'chat-id');

		expect(fetchMock).toHaveBeenCalledOnce();
		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toContain('/chats/chat-id/window?limit=32');
		expect(init).toMatchObject({ method: 'GET' });
		expect(init.headers.authorization).toBe('Bearer token');
	});

	it('anchors a chat window to a requested message', async () => {
		const fetchMock = vi.fn(() => jsonResponse({ id: 'chat-id' }));
		vi.stubGlobal('fetch', fetchMock);

		await getChatByIdWindow('token', 'chat-id', 24, 'rated-message');

		const [url] = fetchMock.mock.calls[0];
		expect(url).toContain('limit=24');
		expect(url).toContain('current_id=rated-message');
	});

	it('loads a history window and conditionally includes before_id', async () => {
		const fetchMock = vi.fn(() =>
			jsonResponse({ messages: {}, loadedIds: [], hasMore: false, currentId: 'current' })
		);
		vi.stubGlobal('fetch', fetchMock);

		await getChatHistoryWindow('token', 'chat-id', 'current', 16, 'before');

		const [url] = fetchMock.mock.calls[0];
		expect(url).toContain('/chats/chat-id/history/window?');
		expect(url).toContain('current_id=current');
		expect(url).toContain('limit=16');
		expect(url).toContain('before_id=before');
	});

	it('posts the chat payload to the windowed update endpoint', async () => {
		const fetchMock = vi.fn(() => jsonResponse({ id: 'chat-id' }));
		vi.stubGlobal('fetch', fetchMock);
		const chat = { history: { currentId: 'message-id' } };

		await updateChatByIdWindow('token', 'chat-id', chat);

		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toContain('/chats/chat-id/window');
		expect(init).toMatchObject({ method: 'POST' });
		expect(JSON.parse(init.body)).toEqual({ chat });
	});

	it('patches one message without posting the chat window', async () => {
		const fetchMock = vi.fn(() => jsonResponse({ id: 'message-id', content: 'edited' }));
		vi.stubGlobal('fetch', fetchMock);
		const message = { content: 'edited', annotation: { rating: 1 } };

		await updateChatMessageById('token', 'chat-id', 'message-id', message);

		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toContain('/chats/chat-id/messages/message-id');
		expect(init).toMatchObject({ method: 'PATCH' });
		expect(JSON.parse(init.body)).toEqual({ message });
	});

	it('requests a compact response when deleting a message', async () => {
		const fetchMock = vi.fn(() => jsonResponse({ id: 'chat-id' }));
		vi.stubGlobal('fetch', fetchMock);

		await deleteChatMessageById('token', 'chat-id', 'message-id');

		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toContain('/chats/chat-id/messages/message-id?compact=true');
		expect(init).toMatchObject({ method: 'DELETE' });
	});
});
