import { test, expect } from '@playwright/test';

const TEST_EMAIL = process.env.TEST_EMAIL || '';
const TEST_PASSWORD = process.env.TEST_PASSWORD || '';
const API_KEY = process.env.OPENWEBUI_API_KEY || '';

test.describe('OpenWebUI API', () => {
	test('GET /api/config returns basic info', async ({ request }) => {
		const r = await request.get('/api/config');
		expect(r.status()).toBe(200);
		const body = await r.json();
		expect(body).toHaveProperty('status', true);
		expect(body).toHaveProperty('name');
		expect(body).toHaveProperty('version');
		expect(body).toHaveProperty('features');
	});

	test('POST /api/v1/auths/signin returns token with valid creds', async ({ request }) => {
		test.skip(!TEST_EMAIL || !TEST_PASSWORD, 'TEST_EMAIL/TEST_PASSWORD not provided');
		const r = await request.post('/api/v1/auths/signin', {
			data: { email: TEST_EMAIL, password: TEST_PASSWORD }
		});
		expect(r.status()).toBe(200);
		const body = await r.json();
		expect(body).toHaveProperty('token');
		expect(body).toHaveProperty('token_type');
	});

	test('GET /api/v1/models returns data array with API key', async ({ request }) => {
		test.skip(!API_KEY, 'OPENWEBUI_API_KEY not provided');
		const r = await request.get('/api/v1/models', {
			headers: { Authorization: `Bearer ${API_KEY}` }
		});
		expect(r.status()).toBe(200);
		const body = await r.json();
		expect(body).toHaveProperty('data');
		expect(Array.isArray(body.data)).toBeTruthy();
	});

	test('POST /api/v1/chat/completions returns choices or is skipped if no models', async ({
		request
	}) => {
		test.skip(!API_KEY, 'OPENWEBUI_API_KEY not provided');

		const modelsRes = await request.get('/api/v1/models', {
			headers: { Authorization: `Bearer ${API_KEY}` }
		});
		expect(modelsRes.status()).toBe(200);
		const modelsBody = await modelsRes.json();
		const models = modelsBody.data || [];
		if (!models || models.length === 0) {
			test.skip(true, 'no models available to test chat completions');
			return;
		}

		const modelId = models[0].id || models[0].model || models[0].name;
		test.skip(!modelId, 'no model id found');

		const res = await request.post('/api/v1/chat/completions', {
			headers: { Authorization: `Bearer ${API_KEY}` },
			data: { model: modelId, messages: [{ role: 'user', content: 'Hello' }], stream: false }
		});
		expect(res.status()).toBe(200);
		const body = await res.json();
		expect(body).toHaveProperty('choices');
		expect(Array.isArray(body.choices)).toBeTruthy();
	});
});
