import { test, expect, type Locator, type Page } from '@playwright/test';
import { createServer, type ViteDevServer } from 'vite';
import { svelte, vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { readdirSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import fr from '../../../../src/lib/i18n/locales/fr-CA/translation.json' with { type: 'json' };

let server: ViteDevServer;
let baseURL: string;
let cacheDir: string | undefined;

const t = (locale: string, key: keyof typeof fr) => (locale === 'fr-CA' ? fr[key] || key : key);

test.describe.configure({ mode: 'default' });

test.beforeAll(async () => {
	test.setTimeout(60_000);
	cacheDir = await mkdtemp(join(tmpdir(), 'canchat-reflow-vite-'));
	server = await createServer({
		configFile: false,
		cacheDir,
		optimizeDeps: {
			noDiscovery: true,
			holdUntilCrawlEnd: false,
			include: [
				'lowlight',
				'highlight.js/lib/core',
				'turndown',
				'dayjs',
				'dayjs/plugin/duration',
				'dayjs/plugin/isToday',
				'dayjs/plugin/isYesterday',
				'dayjs/plugin/relativeTime',
				...readdirSync(resolve('node_modules/dayjs/locale'))
					.filter((name) => name.endsWith('.js'))
					.map((name) => `dayjs/locale/${name.slice(0, -3)}`),
				'file-saver',
				'@braintree/sanitize-url',
				'js-sha256',
				'panzoom',
				'sanitize-html'
			]
		},
		define: { APP_VERSION: '"test"', APP_BUILD_HASH: '"test"' },
		resolve: { alias: { $lib: resolve('src/lib') } },
		server: { host: '127.0.0.1', port: 0, watch: null, hmr: false },
		plugins: [
			svelte({ configFile: false, preprocess: vitePreprocess() }),
			{
				name: 'reflow-fixture',
				resolveId(id) {
					if (id === '$app/environment') return '\0reflow-environment';
				},
				load(id) {
					if (id === '\0reflow-environment')
						return 'export const browser = true; export const dev = false;';
				},
				configureServer(server) {
					server.middlewares.use('/__reflow', async (_request, response, next) => {
						try {
							response.setHeader('Content-Type', 'text/html');
							response.end(
								await server.transformIndexHtml(
									'/__reflow',
									`<!doctype html><html lang="en"><head>
									<meta name="viewport" content="width=device-width, initial-scale=1" />
									</head><body><div id="fixture"></div><script type="module">
										import Fixture from '/playwright/fixtures/Reflow.svelte';
										import '/src/tailwind.css?import';
										import '/src/app.css?import';
										new Fixture({ target: document.getElementById('fixture') });
									</script></body></html>`
								)
							);
						} catch (error) {
							next(error);
						}
					});
				}
			}
		]
	});
	await server.listen();
	const address = server.httpServer?.address();
	if (!address || typeof address === 'string') throw new Error('Expected a TCP fixture server');
	baseURL = `http://127.0.0.1:${address.port}`;
});

test.afterAll(async () => {
	try {
		const httpServer = server?.httpServer;
		if (httpServer && 'closeAllConnections' in httpServer) {
			httpServer.closeAllConnections();
		}
		await server?.close();
	} finally {
		if (cacheDir) await rm(cacheDir, { recursive: true, force: true });
	}
});

async function expectNoHorizontalScroll(page: Page) {
	const dimensions = await page.evaluate(() => ({
		viewportWidth: window.innerWidth,
		width: document.documentElement.clientWidth,
		scrollWidth: document.documentElement.scrollWidth
	}));
	expect(dimensions.viewportWidth).toBe(page.viewportSize()?.width);
	expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.width);
}

async function expectControlsFit(container: Locator) {
	const overflow = await container.evaluate((element) => {
		const bounds = element.getBoundingClientRect();
		return {
			scrollWidth: element.scrollWidth,
			width: element.clientWidth,
			clipped: Array.from(element.querySelectorAll('button')).flatMap((button) => {
				const rect = button.getBoundingClientRect();
				return rect.left < bounds.left - 1 || rect.right > bounds.right + 1
					? [button.getAttribute('aria-label') || button.textContent || button.id]
					: [];
			})
		};
	});
	expect(overflow.clipped).toEqual([]);
	expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.width + 1);
}

for (const locale of ['en-GB', 'fr-CA']) {
	for (const width of [320, 1280]) {
		test(`message actions reflow at ${width}px in ${locale}`, async ({ page }) => {
			await page.setViewportSize({ width, height: 800 });
			await page.goto(`${baseURL}/__reflow?locale=${locale}`);
			const actions = page.locator('#message-response .buttons');
			const regenerate = actions.getByRole('button', {
				name: t(locale, 'Regenerate'),
				exact: true
			});
			await expect(regenerate).toBeVisible({ timeout: 30_000 });
			await expect(page.locator('html')).toHaveAttribute('lang', locale);
			await expectControlsFit(actions);
			await expectNoHorizontalScroll(page);
			const rows = await actions.evaluate((element) => {
				const buttons = Array.from(element.querySelectorAll('button'), (button) =>
					button.getBoundingClientRect()
				)
					.filter((rect) => rect.width > 0 && rect.height > 0)
					.sort((a, b) => a.top - b.top);
				let rows = 0;
				let rowBottom = -Infinity;
				// Buttons of different heights can share a row despite having different top positions.
				for (const rect of buttons) {
					if (rect.top >= rowBottom) {
						rows++;
						rowBottom = rect.bottom;
					} else {
						rowBottom = Math.min(rowBottom, rect.bottom);
					}
				}
				return rows;
			});
			if (width === 320) expect(rows).toBeGreaterThan(1);
			else expect(rows).toBe(1);
			await regenerate.click();
			await expect(page.getByRole('status', { name: 'Regenerations' })).toHaveText('1');
			expect(await page.evaluate(() => window.scrollX)).toBe(0);
		});

		for (const bubbles of [true, false]) {
			test(`message edit controls fit at ${width}px in ${locale} with bubbles ${bubbles}`, async ({
				page
			}) => {
				await page.setViewportSize({ width, height: 800 });
				await page.goto(`${baseURL}/__reflow?locale=${locale}${bubbles ? '' : '&no-bubbles'}`);
				const response = page.locator('#message-response');
				await response.getByRole('button', { name: t(locale, 'Edit'), exact: true }).click();
				await expect(response.locator('textarea')).toBeVisible();
				await expectControlsFit(response.locator('textarea').locator('..'));
				await expectNoHorizontalScroll(page);
				await response.locator('#close-edit-message-button').click();
				const prompt = page.locator('#message-prompt');
				await prompt.hover();
				await prompt.getByRole('button', { name: t(locale, 'Edit'), exact: true }).click();
				await expect(prompt.locator('textarea')).toBeVisible();
				await expectControlsFit(prompt.locator('textarea').locator('../..'));
				await expectNoHorizontalScroll(page);
			});
		}
	}

	test(`multiple model responses stack without horizontal scrolling at 320px in ${locale}`, async ({
		page
	}) => {
		await page.setViewportSize({ width: 320, height: 800 });
		await page.goto(`${baseURL}/__reflow?locale=${locale}&multi`);
		const responses = page.locator('[id^="responses-container-"]');
		await expect(responses.locator('.buttons')).toHaveCount(2, { timeout: 30_000 });
		expect(await responses.evaluate((element) => element.scrollWidth)).toBeLessThanOrEqual(
			await responses.evaluate((element) => element.clientWidth)
		);
		for (const actions of await responses.locator('.buttons').all())
			await expectControlsFit(actions);
		const first = await page.locator('#message-response').boundingBox();
		const second = await page.locator('#message-alternative').boundingBox();
		if (!first || !second) throw new Error('Expected both model responses to have a layout');
		expect(second.y).toBeGreaterThanOrEqual(first.y + first.height);
		await expectNoHorizontalScroll(page);
		await page
			.locator('#message-response')
			.getByRole('button', {
				name: t(locale, 'Edit'),
				exact: true
			})
			.click();
		const editor = page.locator('#message-response textarea');
		await expect(editor).toBeVisible();
		await expectControlsFit(editor.locator('..'));
		await expectNoHorizontalScroll(page);
	});

	test(`multiple model responses remain side by side on desktop in ${locale}`, async ({ page }) => {
		await page.setViewportSize({ width: 1280, height: 800 });
		await page.goto(`${baseURL}/__reflow?locale=${locale}&multi`);
		await expect(page.locator('[id^="responses-container-"] .buttons')).toHaveCount(2, {
			timeout: 30_000
		});
		const first = await page.locator('#message-response').boundingBox();
		const second = await page.locator('#message-alternative').boundingBox();
		if (!first || !second) throw new Error('Expected both model responses to have a layout');
		expect(second.x).toBeGreaterThan(first.x);
		expect(Math.abs(second.y - first.y)).toBeLessThan(1);
		await expectNoHorizontalScroll(page);
	});
}

test('fixture defaults to English document language', async ({ page }) => {
	await page.goto(`${baseURL}/__reflow`);
	await expect(page.locator('html')).toHaveAttribute('lang', 'en-GB', { timeout: 30_000 });
});

test('multiple response cards adapt across responsive breakpoints', async ({ page }) => {
	await page.setViewportSize({ width: 639, height: 800 });
	await page.goto(`${baseURL}/__reflow?multi`);
	const responses = page.locator('[id^="responses-container-"]');
	const cards = responses.locator(':scope > div');
	await expect(cards).toHaveCount(2, { timeout: 30_000 });
	await expect(responses).toHaveCSS('flex-direction', 'column');

	for (const width of [640, 767]) {
		await page.setViewportSize({ width, height: 800 });
		await expect(responses).toHaveCSS('flex-direction', 'row');
		await expect
			.poll(async () =>
				responses.evaluate((element) => {
					const card = element.firstElementChild;
					if (!card) throw new Error('Expected a response card');
					return Math.abs(card.getBoundingClientRect().width - element.clientWidth);
				})
			)
			.toBeLessThan(1);
	}

	await page.setViewportSize({ width: 768, height: 800 });
	await expect
		.poll(async () =>
			responses.evaluate((element) => {
				const card = element.firstElementChild;
				if (!card) throw new Error('Expected a response card');
				return card.getBoundingClientRect().width < element.clientWidth - 1;
			})
		)
		.toBe(true);
});
