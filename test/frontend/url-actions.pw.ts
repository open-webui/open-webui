import { expect, test as base, type Request } from '@playwright/test';

const test = base.extend<{ actions: Request[] }>({
	actions: async ({ page, baseURL }, use) => {
		const actions: Request[] = [];
		const origin = new URL(baseURL!).origin;
		const user = {
			id: 'test-user',
			name: 'Test User',
			email: 'test@example.invalid',
			role: 'admin',
			profile_image_url: '/user.png'
		};
		let note: Record<string, unknown> | null = null;

		await page.context().addInitScript((appOrigin) => {
			if (window.location.origin !== appOrigin) {
				return;
			}
			localStorage.setItem(
				'token',
				`${btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }))}.${btoa(
					JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 })
				)}.test-signature`
			);
			localStorage.setItem('locale', 'en-US');
			localStorage.setItem('theme', 'light');
		}, origin);

		await page.context().routeWebSocket('**/ws/socket.io/**', (socket) => {
			socket.send(
				`0${JSON.stringify({
					sid: 'test-engine',
					upgrades: [],
					pingInterval: 25000,
					pingTimeout: 20000
				})}`
			);
			socket.onMessage((message) => {
				if (String(message).startsWith('40')) {
					socket.send('40{"sid":"test-socket"}');
				}
			});
		});

		await page.context().route('**/*', async (route) => {
			const request = route.request();
			const url = new URL(request.url());
			if (url.origin !== origin) {
				await route.abort();
				return;
			}
			if (!url.pathname.startsWith('/api/')) {
				await route.continue();
				return;
			}

			if (
				request.method() !== 'GET' &&
				/\/notes\/create|\/retrieval\/process\/(?:url|web)|\/chat\/completions|\/chats\/new|\/folders\/[^/]+\/update/.test(
					url.pathname
				)
			) {
				actions.push(request);
			}

			let response: unknown = [];
			if (url.pathname === '/api/config') {
				response = {
					name: 'Open WebUI',
					version: '0.11.3',
					default_models: 'safe-model',
					features: {
						auth: true,
						enable_websocket: true,
						enable_notes: true,
						enable_web_search: true,
						enable_image_generation: true,
						enable_code_interpreter: true
					}
				};
			} else if (url.pathname === '/api/v1/auths/') {
				response = user;
			} else if (url.pathname === '/api/v1/users/user/settings') {
				response = { ui: { models: ['safe-model'], showChangelog: false } };
			} else if (url.pathname === '/api/v1/tools/') {
				response = [{ id: 'test-tool', name: 'Test Tool', meta: {}, specs: [] }];
			} else if (url.pathname === '/api/models') {
				response = {
					data: [
						{ id: 'safe-model', name: 'Safe Model', owned_by: 'openai' },
						{ id: 'other-model', name: 'Other Model', owned_by: 'openai' }
					]
				};
			} else if (url.pathname === '/api/version') {
				response = { version: '0.11.3' };
			} else if (url.pathname === '/api/v1/notes/create') {
				note = {
					...request.postDataJSON(),
					id: 'test-note',
					user_id: user.id,
					created_at: 1,
					updated_at: 1
				};
				response = note;
			} else if (url.pathname === '/api/v1/notes/test-note') {
				response = note;
			} else if (url.pathname === '/api/v1/retrieval/process/url') {
				response = {
					type: 'text',
					name: 'Test page',
					content: 'Test content',
					collection_name: 'test-collection'
				};
			} else if (url.pathname === '/api/v1/chats/new') {
				response = { ...request.postDataJSON(), id: 'test-chat', user_id: user.id };
			} else if (url.pathname === '/api/chat/completions') {
				response = { task_id: 'test-task' };
			}
			await route.fulfill({ json: response });
		});

		await use(actions);
	}
});

test('note links wait for confirmation and cancel without creating a note', async ({
	page,
	actions
}, testInfo) => {
	const title = 'Review this note';
	const content = '<img src="https://example.invalid/image"> Untrusted content';
	await page.goto(`/notes/new?${new URLSearchParams({ title, content })}`);
	await page.waitForLoadState('networkidle');
	expect(actions).toHaveLength(0);
	const dialog = page.getByRole('dialog', { name: 'New Note' });
	await expect(dialog).toBeVisible();
	await expect(dialog).toContainText(title);
	await expect(dialog).toContainText(content);
	await expect(dialog.locator('img')).toHaveCount(0);
	await page.screenshot({ path: testInfo.outputPath('note-desktop.png') });

	await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
	await expect(page).toHaveURL(/\/notes$/);
	await page.waitForLoadState('networkidle');
	expect(actions).toHaveLength(0);
});

test('confirmed note links create exactly the previewed note', async ({ page, actions }) => {
	const title = 'Approved note';
	const content = 'Approved content';
	await page.goto(`/notes/new?${new URLSearchParams({ title, content })}`);
	const dialog = page.getByRole('dialog', { name: 'New Note' });
	await expect(dialog).toBeVisible();
	expect(actions).toHaveLength(0);
	await dialog.getByRole('button', { name: 'Create', exact: true }).click();
	await expect(page).toHaveURL(/\/notes\/test-note$/);
	expect(actions).toHaveLength(1);
	expect(actions[0].postDataJSON()).toMatchObject({
		title,
		data: { content: { md: content } }
	});
});

test('chat links do not apply or execute URL actions before confirmation', async ({
	page,
	actions
}, testInfo) => {
	const parameters = new URLSearchParams({
		model: 'other-model',
		youtube: 'test-video',
		'load-url': 'https://example.invalid/test-page',
		'web-search': 'true',
		'image-generation': 'true',
		'code-interpreter': 'true',
		tools: 'test-tool',
		call: 'true',
		q: 'Unapproved prompt',
		submit: 'true'
	});
	await page.goto(`/?${parameters}`);
	await page.waitForLoadState('networkidle');
	expect(actions).toHaveLength(0);
	const dialog = page.getByRole('dialog', { name: 'Confirm your action' });
	await expect(dialog).toBeVisible();
	for (const value of parameters.values()) {
		await expect(dialog).toContainText(value);
	}
	await page.screenshot({ path: testInfo.outputPath('chat-desktop.png') });
	await dialog.getByRole('button', { name: 'Cancel', exact: true }).click();
	await expect(dialog).not.toBeVisible();
	await expect(page.locator('#chat-input')).toBeVisible();
	await expect(page.locator('#chat-input')).toBeEmpty();
	await page.waitForLoadState('networkidle');
	expect(actions).toHaveLength(0);

	const completionRequest = page.waitForRequest('**/api/chat/completions');
	await page.locator('#chat-input').fill('My own prompt');
	await page.locator('#chat-input').press('Enter');
	const completion = (await completionRequest).postDataJSON();
	expect(completion).toMatchObject({
		model: 'safe-model',
		features: { voice: false, web_search: false, image_generation: false, code_interpreter: false },
		user_message: { content: 'My own prompt' }
	});
	expect(completion.tool_ids).toBeUndefined();
});

test('approved chat links preserve model, tool, feature and prompt parameters', async ({
	page,
	actions
}) => {
	const parameters = new URLSearchParams({
		model: 'other-model',
		tools: 'test-tool',
		'web-search': 'true',
		'image-generation': 'true',
		'code-interpreter': 'true',
		q: 'Approved prompt'
	});
	await page.goto(`/?${parameters}`);
	const dialog = page.getByRole('dialog', { name: 'Confirm your action' });
	await expect(dialog).toBeVisible();
	expect(actions).toHaveLength(0);
	const completionRequest = page.waitForRequest('**/api/chat/completions');
	await dialog.getByRole('button', { name: 'Send', exact: true }).click();
	expect((await completionRequest).postDataJSON()).toMatchObject({
		model: 'other-model',
		tool_ids: ['test-tool'],
		features: { web_search: true, image_generation: true, code_interpreter: true },
		user_message: { content: 'Approved prompt' }
	});
});

for (const [parameter, value, url] of [
	['load-url', 'https://example.invalid/test-page', 'https://example.invalid/test-page'],
	['youtube', 'test-video', 'https://www.youtube.com/watch?v=test-video']
]) {
	test(`${parameter} content is fetched only after confirmation`, async ({ page, actions }) => {
		await page.goto(`/?${new URLSearchParams({ [parameter]: value })}`);
		const dialog = page.getByRole('dialog', { name: 'Confirm your action' });
		await expect(dialog).toBeVisible();
		expect(actions).toHaveLength(0);
		const retrievalRequest = page.waitForRequest('**/api/v1/retrieval/process/url*');
		await dialog.getByRole('button', { name: 'Continue', exact: true }).click();
		expect((await retrievalRequest).postDataJSON()).toMatchObject({ url });
		await page.waitForLoadState('networkidle');
		expect(actions).toHaveLength(1);
	});
}

test('submit=false preserves an approved draft and model/tool aliases until manual submission', async ({
	page,
	actions
}) => {
	await page.goto(
		`/?${new URLSearchParams({
			models: 'other-model',
			'tool-ids': 'test-tool',
			q: 'Draft prompt',
			submit: 'false'
		})}`
	);
	const dialog = page.getByRole('dialog', { name: 'Confirm your action' });
	await dialog.getByRole('button', { name: 'Continue', exact: true }).click();
	await expect(page.locator('#chat-input')).toContainText('Draft prompt');
	await page.waitForLoadState('networkidle');
	expect(actions).toHaveLength(0);

	const completionRequest = page.waitForRequest('**/api/chat/completions');
	await page.locator('#chat-input').press('Enter');
	expect((await completionRequest).postDataJSON()).toMatchObject({
		model: 'other-model',
		tool_ids: ['test-tool'],
		user_message: { content: 'Draft prompt' }
	});
});

for (const [name, target, expectedPath] of [
	['note', '/notes/new?title=Framed&content=Unapproved', '/notes'],
	['chat', '/?model=other-model&load-url=https%3A%2F%2Fexample.invalid%2Fframed&q=Framed', '/']
]) {
	test(`cross-origin frames cannot authorize ${name} links`, async ({ page, baseURL, actions }) => {
		await page.context().grantPermissions(['local-network-access'], {
			origin: 'http://127.0.0.1:5178'
		});
		await page.route('http://127.0.0.1:5178/', (route) =>
			route.fulfill({ contentType: 'text/html', body: '<iframe title="linked app"></iframe>' })
		);
		await page.goto('http://127.0.0.1:5178/');
		await page.locator('iframe').evaluate((element, url) => {
			element.setAttribute('src', url);
		}, new URL(target, baseURL).href);
		const frame = page.frameLocator('iframe');
		await expect(frame.locator(name === 'chat' ? '#chat-input' : '.app')).toBeVisible();
		await expect
			.poll(() => {
				const child = page.frames().find((candidate) => candidate !== page.mainFrame());
				return child ? new URL(child.url()).pathname : '';
			})
			.toBe(expectedPath);
		await page.waitForLoadState('networkidle');
		await expect(frame.getByRole('dialog')).toHaveCount(0);
		expect(actions).toHaveLength(0);
		if (name === 'chat') {
			await expect(frame.locator('#chat-input')).toBeEmpty();
		}
	});
}

test('navigation replaces pending chat approval without executing the previous link', async ({
	page,
	actions
}) => {
	await page.goto('/?q=Previous%20prompt');
	const dialog = page.getByRole('dialog', { name: 'Confirm your action' });
	await expect(dialog).toContainText('Previous prompt');
	await dialog.evaluate((element) => {
		const link = document.createElement('a');
		link.href = '/?q=Current%20prompt';
		element.append(link);
		link.click();
		link.remove();
	});
	await expect(dialog).toContainText('Current prompt');
	await expect(dialog).not.toContainText('Previous prompt');
	expect(actions).toHaveLength(0);
	const completionRequest = page.waitForRequest('**/api/chat/completions');
	await dialog.getByRole('button', { name: 'Send', exact: true }).click();
	expect((await completionRequest).postDataJSON()).toMatchObject({
		user_message: { content: 'Current prompt' }
	});
});

test('ordinary navigation and unrelated query parameters need no approval', async ({
	page,
	actions
}) => {
	await page.goto('/?utm_source=test');
	await expect(page.locator('#chat-input')).toBeVisible();
	await page.waitForLoadState('networkidle');
	await expect(page.getByRole('dialog')).toHaveCount(0);
	expect(actions).toHaveLength(0);
});

test('bare note creation links also require approval', async ({ page, actions }) => {
	await page.goto('/notes/new');
	await expect(page.getByRole('dialog', { name: 'New Note' })).toBeVisible();
	await page.waitForLoadState('networkidle');
	expect(actions).toHaveLength(0);
});

test('mobile confirmation previews contain long untrusted values without horizontal overflow', async ({
	page,
	actions
}, testInfo) => {
	await page.setViewportSize({ width: 390, height: 844 });
	const longValue = `https://example.invalid/${'long-value'.repeat(50)}`;
	for (const [name, target, title] of [
		[
			'note',
			`/notes/new?${new URLSearchParams({ title: longValue, content: longValue })}`,
			'New Note'
		],
		[
			'chat',
			`/?${new URLSearchParams({ 'load-url': longValue, q: longValue })}`,
			'Confirm your action'
		]
	]) {
		await page.goto(target);
		const dialog = page.getByRole('dialog', { name: title });
		await expect(dialog).toBeVisible();
		const bounds = await dialog.boundingBox();
		expect(bounds!.x).toBeGreaterThanOrEqual(0);
		expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
		expect(await dialog.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(
			false
		);
		await page.screenshot({ path: testInfo.outputPath(`${name}-mobile.png`) });
		expect(actions).toHaveLength(0);
	}
});
