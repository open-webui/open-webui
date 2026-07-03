import { describe, expect, test, vi } from 'vitest';

import { executeToolRequest } from './executeTool';

describe('executeToolRequest', () => {
	test('returns an error callback when the tool server is missing', async () => {
		const cb = vi.fn();
		const executeToolServer = vi.fn();

		await executeToolRequest({
			data: {
				name: 'list_deals',
				params: {},
				server: { url: 'https://tools.example.test' }
			},
			chatId: 'chat-1',
			resolved: {
				toolServer: undefined,
				toolServerData: undefined,
				token: null
			},
			executeToolServer,
			cb,
			logger: {
				log: vi.fn(),
				error: vi.fn()
			}
		});

		expect(executeToolServer).not.toHaveBeenCalled();
		expect(cb).toHaveBeenCalledWith({ error: 'Tool Server Not Found' });
	});

	test('returns the tool server response on success', async () => {
		const cb = vi.fn();
		const executeToolServer = vi.fn().mockResolvedValue({ result: { ok: true } });

		await executeToolRequest({
			data: {
				name: 'list_deals',
				params: { limit: 10 },
				server: { url: 'https://tools.example.test' }
			},
			chatId: 'chat-1',
			resolved: {
				toolServer: {
					url: 'https://tools.example.test'
				},
				toolServerData: { openapi: {}, info: {}, specs: {} },
				token: 'token'
			},
			executeToolServer,
			cb,
			logger: {
				log: vi.fn(),
				error: vi.fn()
			}
		});

		expect(executeToolServer).toHaveBeenCalledWith(
			'token',
			'https://tools.example.test',
			'list_deals',
			{ limit: 10 },
			{ openapi: {}, info: {}, specs: {} },
			'chat-1'
		);
		expect(cb).toHaveBeenCalledWith({ result: { ok: true } });
	});

	test('returns an error callback when the tool server call throws', async () => {
		const cb = vi.fn();

		await executeToolRequest({
			data: {
				name: 'list_deals',
				params: {},
				server: { url: 'https://tools.example.test' }
			},
			chatId: 'chat-1',
			resolved: {
				toolServer: {
					url: 'https://tools.example.test'
				},
				toolServerData: undefined,
				token: 'token'
			},
			executeToolServer: vi.fn().mockRejectedValue(new Error('tool server unavailable')),
			cb,
			logger: {
				log: vi.fn(),
				error: vi.fn()
			}
		});

		expect(cb).toHaveBeenCalledWith({ error: 'tool server unavailable' });
	});
});
