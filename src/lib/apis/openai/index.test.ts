import { describe, expect, it, vi, afterEach } from 'vitest';

import {
	applyOpenAIWebAuthConnection,
	completeOpenAIWebAuth,
	createOpenAIWebAuthConfigUpdate,
	createOpenAIWebAuthConnectionConfig,
	disconnectOpenAIWebAuth,
	getSupportedOpenAIConnectionAuthTypes,
	getOpenAIWebAuthStatus,
	OPENAI_CODEX_WEB_AUTH_API_BASE_URL,
	OPENAI_CODEX_WEB_AUTH_TYPE,
	isEmptyNativeOpenAIBearerConnection,
	startOpenAIWebAuth
} from './index';

const mockFetch = (body: unknown, ok = true) => {
	const fetchMock = vi.fn().mockResolvedValue({
		ok,
		json: vi.fn().mockResolvedValue(body)
	});
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
};

afterEach(() => {
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
});

describe('OpenAI web auth API helpers', () => {
	it('fetches redacted status', async () => {
		const fetchMock = mockFetch({
			credential_type: 'web_auth',
			connected: true,
			has_credential: true,
			status: 'connected',
			expires_at: 1893456000,
			access_token: 'must-not-return',
			refresh_token: 'must-not-return',
			client_secret: 'must-not-return'
		});

		const status = await getOpenAIWebAuthStatus('test-token');

		expect(fetchMock).toHaveBeenCalledWith('/openai/web-auth/status', expect.any(Object));
		expect(status).toEqual({
			credential_type: 'web_auth',
			connected: true,
			has_credential: true,
			status: 'connected',
			expires_at: 1893456000
		});
		expect(JSON.stringify(status)).not.toMatch(
			/access_token|refresh_token|authorization_code|code_verifier|client_secret/i
		);
	});

	it('starts account authorization with safe browser fields', async () => {
		const fetchMock = mockFetch({
			verification_url: 'https://auth.openai.com/device',
			user_code: 'ABCD-EFGH',
			session_id: 'session-1',
			interval: 5,
			expires_at: 1893456000,
			device_auth_id: 'must-not-return',
			code_verifier: 'must-not-return',
			client_id: 'must-not-return'
		});

		const started = await startOpenAIWebAuth('test-token');

		expect(fetchMock).toHaveBeenCalledWith(
			'/openai/web-auth/start',
			expect.objectContaining({ method: 'POST' })
		);
		expect(started).toEqual({
			verification_url: 'https://auth.openai.com/device',
			user_code: 'ABCD-EFGH',
			session_id: 'session-1',
			interval: 5,
			expires_at: 1893456000
		});
		expect(JSON.stringify(started)).not.toMatch(
			/access_token|refresh_token|authorization_code|code_verifier|client_secret|client_id|device_auth_id/i
		);
	});

	it('builds the OpenAI account-auth runtime connection config without public secrets', () => {
		const config = createOpenAIWebAuthConnectionConfig({ tags: [{ name: 'native' }] });

		expect(config).toEqual({
			tags: [{ name: 'native' }],
			enable: true,
			auth_type: OPENAI_CODEX_WEB_AUTH_TYPE,
			connection_type: 'external'
		});
		expect(JSON.stringify(config)).not.toMatch(/api_key|access_token|refresh_token|client_secret/i);
	});

	it('does not expose account auth in the generic add-connection auth options', () => {
		const authTypes = getSupportedOpenAIConnectionAuthTypes();

		expect(authTypes.map(({ value }) => value)).toEqual(['none', 'bearer', 'session', 'system_oauth']);
		expect(authTypes.map(({ value }) => value)).not.toContain(OPENAI_CODEX_WEB_AUTH_TYPE);
	});

	it('converts an empty native OpenAI bearer connection to web auth', () => {
		expect(
			isEmptyNativeOpenAIBearerConnection('https://api.openai.com/v1', '', {
				auth_type: 'bearer'
			})
		).toBe(true);

		const result = applyOpenAIWebAuthConnection(['https://api.openai.com/v1'], [''], {
			0: { enable: true, auth_type: 'bearer' }
		});

		expect(result).toEqual({
			urls: [OPENAI_CODEX_WEB_AUTH_API_BASE_URL],
			keys: [''],
			configs: {
				0: { enable: true, auth_type: OPENAI_CODEX_WEB_AUTH_TYPE, connection_type: 'external' }
			}
		});
	});

	it('preserves native OpenAI API-key connection and adds separate web auth connection', () => {
		const result = applyOpenAIWebAuthConnection(['https://api.openai.com/v1'], ['sk-existing'], {
			0: { enable: true, auth_type: 'bearer' }
		});

		expect(result.urls).toEqual(['https://api.openai.com/v1', OPENAI_CODEX_WEB_AUTH_API_BASE_URL]);
		expect(result.keys).toEqual(['sk-existing', '']);
		expect(result.configs[0]).toEqual({ enable: true, auth_type: 'bearer' });
		expect(result.configs[1]).toEqual({
			enable: true,
			auth_type: OPENAI_CODEX_WEB_AUTH_TYPE,
			connection_type: 'external'
		});
	});

	it('creates an enabled config update for auto-use after successful account auth completion', () => {
		const result = createOpenAIWebAuthConfigUpdate({
			ENABLE_OPENAI_API: false,
			OPENAI_API_BASE_URLS: ['https://api.openai.com/v1'],
			OPENAI_API_KEYS: ['sk-existing'],
			OPENAI_API_CONFIGS: { 0: { enable: true, auth_type: 'bearer' } }
		});

		expect(result.ENABLE_OPENAI_API).toBe(true);
		expect(result.OPENAI_API_BASE_URLS).toEqual([
			'https://api.openai.com/v1',
			OPENAI_CODEX_WEB_AUTH_API_BASE_URL
		]);
		expect(result.OPENAI_API_KEYS).toEqual(['sk-existing', '']);
		expect(result.OPENAI_API_CONFIGS[0]).toEqual({ enable: true, auth_type: 'bearer' });
		expect(result.OPENAI_API_CONFIGS[1]).toEqual({
			enable: true,
			auth_type: OPENAI_CODEX_WEB_AUTH_TYPE,
			connection_type: 'external'
		});
	});

	it('removes duplicate empty native bearer entry when web auth already exists', () => {
		const result = applyOpenAIWebAuthConnection(
			['https://api.openai.com/v1', OPENAI_CODEX_WEB_AUTH_API_BASE_URL],
			['', ''],
			{
				0: { enable: true, auth_type: 'bearer' },
				1: { enable: true, auth_type: OPENAI_CODEX_WEB_AUTH_TYPE }
			}
		);

		expect(result.urls).toEqual([OPENAI_CODEX_WEB_AUTH_API_BASE_URL]);
		expect(result.keys).toEqual(['']);
		expect(result.configs[0]).toEqual({
			enable: true,
			auth_type: OPENAI_CODEX_WEB_AUTH_TYPE,
			connection_type: 'external'
		});
	});

	it('completes with session id and returns redacted status', async () => {
		const fetchMock = mockFetch({
			credential_type: 'web_auth',
			connected: true,
			has_credential: true,
			status: 'connected'
		});

		const status = await completeOpenAIWebAuth('test-token', 'session-1');

		expect(fetchMock).toHaveBeenCalledWith(
			'/openai/web-auth/complete',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ session_id: 'session-1' })
			})
		);
		expect(status.connected).toBe(true);
		expect(JSON.stringify(status)).not.toMatch(
			/access_token|refresh_token|authorization_code|code_verifier|client_secret/i
		);
	});

	it('disconnects and returns not connected status', async () => {
		const fetchMock = mockFetch({
			credential_type: 'none',
			connected: false,
			has_credential: false,
			status: 'not_configured'
		});

		const status = await disconnectOpenAIWebAuth('test-token');

		expect(fetchMock).toHaveBeenCalledWith(
			'/openai/web-auth/disconnect',
			expect.objectContaining({ method: 'POST' })
		);
		expect(status.connected).toBe(false);
		expect(status.has_credential).toBe(false);
	});
});
