import { afterEach, describe, expect, it, vi } from 'vitest';

import {
	createDirectory,
	getCwd,
	getTerminalConfig,
	getTerminalServers,
	normalizeTerminalToken
} from './index';

describe('terminal API token normalization', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('trims leading and trailing token whitespace', () => {
		expect(normalizeTerminalToken('  token-value \n')).toBe('token-value');
	});

	it('keeps an empty token empty', () => {
		expect(normalizeTerminalToken('')).toBe('');
		expect(normalizeTerminalToken('   ')).toBe('');
	});

	it('uses the normalized token in Authorization headers', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: vi.fn().mockResolvedValue({ features: { terminal: true } })
		});

		vi.stubGlobal('fetch', fetchMock);

		await getTerminalConfig('https://terminal.example/', '  secret-token  ');

		expect(fetchMock).toHaveBeenCalledWith('https://terminal.example/api/config', {
			headers: {
				Authorization: 'Bearer secret-token'
			}
		});
	});

	it('normalizes Open WebUI terminal server requests', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: vi.fn().mockResolvedValue([])
		});

		vi.stubGlobal('fetch', fetchMock);

		await getTerminalServers('\n webui-token ');

		expect(fetchMock).toHaveBeenCalledWith('/api/v1/terminals/', {
			headers: {
				Authorization: 'Bearer webui-token'
			}
		});
	});

	it('preserves session headers while normalizing terminal file requests', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: vi.fn().mockResolvedValue({ cwd: '/workspace' })
		});

		vi.stubGlobal('fetch', fetchMock);

		await getCwd('https://terminal.example/', '\tterminal-token\n', 'session-1');

		expect(fetchMock).toHaveBeenCalledWith('https://terminal.example/files/cwd', {
			headers: {
				Authorization: 'Bearer terminal-token',
				'X-Session-Id': 'session-1'
			}
		});
	});

	it('preserves JSON headers while normalizing terminal mutations', async () => {
		const fetchMock = vi.fn().mockResolvedValue({
			ok: true,
			json: vi.fn().mockResolvedValue({ path: '/workspace' })
		});

		vi.stubGlobal('fetch', fetchMock);

		await createDirectory(
			'https://terminal.example/',
			' terminal-token ',
			'/workspace',
			'session-2'
		);

		expect(fetchMock).toHaveBeenCalledWith('https://terminal.example/files/mkdir', {
			method: 'POST',
			headers: {
				Authorization: 'Bearer terminal-token',
				'Content-Type': 'application/json',
				'X-Session-Id': 'session-2'
			},
			body: JSON.stringify({ path: '/workspace' })
		});
	});
});
