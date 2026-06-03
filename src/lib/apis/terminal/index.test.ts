import { afterEach, describe, expect, it, vi } from 'vitest';

import { getTerminalConfig, normalizeTerminalToken } from './index';

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
});
