import { test, expect } from '@playwright/test';
import { createServer, type ViteDevServer } from 'vite';
import { svelte, vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'node:path';

let server: ViteDevServer;
let baseURL: string;

test.beforeAll(async () => {
	server = await createServer({
		configFile: false,
		optimizeDeps: {
			include: [
				'lowlight',
				'highlight.js/lib/core',
				'turndown',
				'dayjs',
				'file-saver',
				'paneforge',
				'@xyflow/svelte'
			]
		},
		define: { APP_VERSION: '"test"', APP_BUILD_HASH: '"test"' },
		resolve: { alias: { $lib: resolve('src/lib') } },
		server: { host: '127.0.0.1', port: 0, watch: null, hmr: false },
		plugins: [
			svelte({ configFile: false, preprocess: vitePreprocess() }),
			{
				name: 'keyboard-accessibility-fixture',
				resolveId(id) {
					if (id === '$app/environment') return '\0keyboard-environment';
					if (id === '$app/navigation') return '\0keyboard-navigation';
				},
				load(id) {
					if (id === '\0keyboard-environment')
						return 'export const browser = true; export const dev = false;';
					if (id === '\0keyboard-navigation')
						return 'export const goto = async () => {}; export const afterNavigate = () => {}; export const beforeNavigate = () => {};';
				},
				configureServer(server) {
					server.middlewares.use('/__keyboard', async (_request, response, next) => {
						try {
							response.setHeader('Content-Type', 'text/html');
							response.end(
								await server.transformIndexHtml(
									'/__keyboard',
									`<!doctype html>
								<html lang="en"><body><main id="fixture"></main><script type="module">
									import Fixture from '/playwright/fixtures/KeyboardAccessibility.svelte';
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
}, 60_000);

test.afterAll(async () => {
	server?.httpServer?.closeAllConnections();
	await server?.close();
});

test.beforeEach(async ({ page }) => {
	await page.route('**/api/v1/**', async (route) => {
		const path = new URL(route.request().url()).pathname;
		let data: unknown = {};
		if (path.endsWith('/pinned')) data = false;
		if (path.endsWith('/tags')) data = [];
		if (path === '/api/v1/folders/')
			data = [
				{ id: 'folder-a', name: 'Folder A', parent_id: null, is_expanded: false },
				{ id: 'folder-b', name: 'Folder B', parent_id: 'folder-a', is_expanded: false }
			];
		if (path === '/api/v1/folders/' && route.request().method() === 'POST') {
			data = { id: 'new-folder', name: 'New folder', parent_id: null, is_expanded: false };
		}
		await route.fulfill({ json: data });
	});
});

for (const locale of ['en-GB', 'fr-CA']) {
	test(`message navigation exposes old actions and timestamps without trapping focus in ${locale}`, async ({
		page
	}) => {
		await page.goto(`${baseURL}/__keyboard?locale=${locale}`);
		const messages = page.locator('[data-keyboard-message]');
		await expect(messages).toHaveCount(3, { timeout: 30_000 });
		await page.locator('#before').focus();
		await page.keyboard.press('Tab');
		await expect(messages.nth(0)).toBeFocused();
		await page.keyboard.press('ArrowDown');
		await expect(messages.nth(1)).toBeFocused();
		await expect(messages.nth(1).getByText('14/11/2023 at', { exact: false })).toBeVisible();
		await page.keyboard.press('Enter');
		const edit = messages
			.nth(1)
			.getByRole('button', { name: locale === 'fr-CA' ? 'Modifier' : 'Edit', exact: true });
		await expect(edit).toBeFocused();
		await page.keyboard.press('Enter');
		await expect(messages.nth(1).locator('textarea')).toBeFocused();
		await page.keyboard.press('Escape');
		await expect(messages.nth(1)).toBeFocused();
		await page.keyboard.press('Enter');
		await page.keyboard.press('ArrowRight');
		const copy = messages.nth(1).locator('.copy-response-button');
		await expect(copy).toBeFocused();
		await expect(copy).toBeVisible();
		await expect(copy).toHaveCSS('outline-style', 'solid');
		await page.keyboard.press('Escape');
		await expect(messages.nth(1)).toBeFocused();
		await page.keyboard.press('End');
		await expect(messages.nth(2)).toBeFocused();
		await page.keyboard.press('Tab');
		await expect(page.getByRole('button', { name: 'Remove', exact: true })).toBeFocused();
		await page.keyboard.press('Tab');
		const composer = page.getByRole('textbox', { name: 'Composer' });
		await expect(composer).toBeFocused();
		await page.keyboard.press('Shift+Tab');
		await expect(page.getByRole('button', { name: 'Remove', exact: true })).toBeFocused();
		await composer.focus();
		await page.keyboard.press('Alt+ArrowUp');
		await expect(messages.nth(2)).toBeFocused();
		await page.keyboard.press('Home');
		await page.keyboard.press('Shift+Tab');
		await expect(page.locator('#before')).toBeFocused();
	});
}

test('model popover allows Tab to reach temporary chat and Escape restores focus', async ({
	page
}) => {
	await page.goto(`${baseURL}/__keyboard`);
	const trigger = page.locator('#model-selector-test-button');
	await trigger.focus();
	await page.keyboard.press('Enter');
	const search = page.getByRole('combobox', { name: 'Search a model' });
	await expect(search).toBeFocused();
	await expect(search).toHaveAttribute('aria-expanded', 'true');
	await page.keyboard.press('ArrowDown');
	const option = page
		.getByRole('listbox', { name: 'Models' })
		.getByRole('option', { name: 'Test model', exact: true });
	await expect(option).toHaveAttribute('aria-selected', 'true');
	await expect(search).toHaveAttribute('aria-activedescendant', (await option.getAttribute('id'))!);
	await page.keyboard.press('Tab');
	await expect(page.getByRole('option', { name: 'Test model', exact: true })).toBeFocused();
	await page.keyboard.press('Tab');
	await expect(page.getByRole('switch', { name: 'Temporary Chat' })).toBeFocused();
	await page.keyboard.press('Escape');
	await expect(trigger).toBeFocused();
	await page.keyboard.press('Enter');
	await expect(page.getByRole('combobox', { name: 'Search a model' })).toBeFocused();
	await page.keyboard.press('Tab');
	await expect(page.getByRole('option', { name: 'Test model', exact: true })).toBeFocused();
	await page.keyboard.press('Tab');
	await expect(page.getByRole('switch', { name: 'Temporary Chat' })).toBeFocused();
	await page.keyboard.press('Space');
	await expect(trigger).toBeFocused();
});

test('model selection accepts Numpad Enter', async ({ page }) => {
	await page.goto(`${baseURL}/__keyboard`);
	const trigger = page.locator('#model-selector-test-button');
	await trigger.click();
	await expect(page.getByRole('combobox', { name: 'Search a model' })).toBeFocused();
	await page.keyboard.press('NumpadEnter');
	await expect(page.getByRole('combobox', { name: 'Search a model' })).toHaveCount(0);
	await expect(trigger).toBeFocused();
});

test('messages share help text and focus only reveals intended controls', async ({ page }) => {
	await page.setViewportSize({ width: 320, height: 800 });
	await page.goto(`${baseURL}/__keyboard`);
	const messages = page.locator('[data-keyboard-message]');
	await expect(messages).toHaveCount(3);
	await expect(page.locator('[id^="message-keyboard-help-"]')).toHaveCount(1);
	await messages.nth(1).evaluate((message) => {
		const placeholder = document.createElement('span');
		placeholder.id = 'hidden-placeholder';
		placeholder.className = 'invisible';
		placeholder.textContent = 'Not ready';
		message.append(placeholder);
	});
	await messages.nth(1).focus();
	await expect(messages.nth(1)).toHaveAccessibleDescription(
		'Use Up and Down to navigate messages, Enter for actions, Left and Right to navigate actions, and Escape to return to the message.'
	);
	await expect(page.locator('#hidden-placeholder')).toHaveCSS('visibility', 'hidden');
	await expect(messages.nth(1).locator('[data-reveal-on-focus]')).toHaveCSS(
		'visibility',
		'visible'
	);
	const actions = messages.nth(1).locator('[data-message-actions]');
	await expect(actions).toHaveCSS('overflow-x', 'auto');
	await expect(actions).toHaveCSS('padding-left', '4px');
	expect(
		await actions.evaluate((element) => element.getBoundingClientRect().right <= window.innerWidth)
	).toBe(true);
});

test('chat controls match hover capability and reveal on keyboard focus', async ({ page }) => {
	await page.goto(`${baseURL}/__keyboard`);
	await page.mouse.move(0, 0);
	const trigger = page.locator('#chat-menu-keyboard-chat');
	const controls = page.locator('div.opacity-0').filter({ has: trigger });
	const supportsHover = await page.evaluate(() => matchMedia('(hover: hover)').matches);
	await expect(controls).toHaveCSS('opacity', supportsHover ? '0' : '1');
	await expect(controls).toHaveCSS('pointer-events', supportsHover ? 'none' : 'auto');
	await trigger.focus();
	await expect(controls).toHaveCSS('opacity', '1');
	await expect(controls).toHaveCSS('pointer-events', 'auto');
});

test.describe('controls on devices without hover', () => {
	test.use({ hasTouch: true, viewport: { width: 390, height: 844 } });

	test('chat and folder menus are visible without hovering', async ({ page }) => {
		await page.goto(`${baseURL}/__keyboard`);
		expect(await page.evaluate(() => matchMedia('(hover: none)').matches)).toBe(true);
		for (const id of ['chat-menu-keyboard-chat', 'folder-a']) {
			const trigger = page.locator(`#${id}`);
			await expect(trigger).toHaveCount(1);
			const controls = page.locator('div.opacity-0').filter({ has: trigger });
			await expect(controls).toHaveCSS('opacity', '1');
			await expect(controls).toHaveCSS('pointer-events', 'auto');
		}
	});

	test('attachment, add, export and search controls are visible and tappable', async ({ page }) => {
		await page.goto(`${baseURL}/__keyboard?touch-controls`);
		await page.getByRole('button', { name: 'Search results' }).tap();
		for (const name of ['Add item', 'Export to CSV', 'Copy to clipboard', 'Remove']) {
			const button = page.getByRole('button', { name, exact: true });
			await expect(button).toBeVisible();
			expect(
				await button.evaluate((element) => {
					for (
						let ancestor: Element | null = element;
						ancestor;
						ancestor = ancestor.parentElement
					) {
						const style = getComputedStyle(ancestor);
						if (style.opacity === '0' || style.pointerEvents === 'none') return false;
					}
					return true;
				})
			).toBe(true);
		}
		await page.getByRole('button', { name: 'Remove', exact: true }).tap();
		await expect(page.getByRole('button', { name: 'Remove', exact: true })).toHaveCount(0);
	});
});

test('folder expansion and controls have visible keyboard focus and can be exited', async ({
	page
}) => {
	await page.goto(`${baseURL}/__keyboard`);
	const folder = page.locator('#folder-folder-a-button');
	await folder.focus();
	await page.keyboard.press('Space');
	await expect(folder).toHaveAttribute('aria-expanded', 'true');
	await page.keyboard.press('Enter');
	await expect(folder).toHaveAttribute('aria-expanded', 'false');
	await page.keyboard.press('ArrowRight');
	await expect(folder).toHaveAttribute('aria-expanded', 'true');
	await expect(page.getByRole('status', { name: 'Announcement' })).toHaveText('expanded');
	await page.keyboard.press('ArrowLeft');
	await expect(folder).toHaveAttribute('aria-expanded', 'false');
	await expect(page.getByRole('status', { name: 'Announcement' })).toHaveText('collapsed');
	await page.keyboard.press('Tab');
	await expect(page.getByRole('button', { name: 'Folder Menu' })).toBeFocused();
	const advanced = page.getByRole('button', { name: 'Advanced Params' });
	await advanced.focus();
	await page.keyboard.press('Enter');
	await page.keyboard.press('Tab');
	await expect(page.getByRole('button', { name: 'Default', exact: true })).toBeFocused();
	await expect(page.getByRole('button', { name: 'Default', exact: true })).toHaveCSS(
		'outline-style',
		'solid'
	);
	await page.keyboard.press('Tab');
	await expect(page.locator('#after')).toBeFocused();
});

test('chat menu offers a non-drag move to nested folders and new folders', async ({ page }) => {
	await page.goto(`${baseURL}/__keyboard`);
	const trigger = page.locator('#test-chat-menu');
	for (const createNew of [false, true]) {
		await trigger.focus();
		await page.keyboard.press('Enter');
		await expect(page.getByRole('menuitem', { name: 'Move to folder', exact: true })).toBeFocused();
		await page.keyboard.press('Enter');
		const dialog = page.getByRole('dialog', { name: 'Move to folder', exact: true });
		await expect(dialog).toHaveAttribute('aria-modal', 'true');
		await expect(dialog).toHaveAttribute('aria-labelledby', 'move-chat-title-test-chat');
		await expect(
			dialog.getByRole('heading', { name: 'Move to folder', exact: true })
		).toHaveAttribute('id', 'move-chat-title-test-chat');
		const select = dialog.getByLabel('Destination folder');
		await expect(select).toBeFocused();
		await expect(select.locator('option', { hasText: 'Folder A / Folder B' })).toHaveCount(1);
		if (createNew) {
			await page.keyboard.press('Tab');
			await page.keyboard.press('Space');
			await page.keyboard.press('Tab');
			await page.keyboard.type('New folder');
		} else {
			await page.keyboard.press('ArrowDown');
			await page.keyboard.press('ArrowDown');
		}
		const request = page.waitForRequest('**/api/v1/chats/test-chat/folder');
		await page.keyboard.press('Tab');
		if (!createNew) await page.keyboard.press('Tab');
		await page.keyboard.press('Tab');
		await page.keyboard.press('Enter');
		expect((await request).postDataJSON()).toEqual({
			folder_id: createNew ? 'new-folder' : 'folder-b'
		});
		await expect(trigger).toBeFocused();
	}
	await expect(page.getByRole('status', { name: 'Changes' })).toHaveText('2');
});

test('new folder validation stays visible and prevents empty or whitespace names', async ({
	page
}) => {
	await page.goto(`${baseURL}/__keyboard`);
	await page.locator('#test-chat-menu').click();
	await page.getByRole('menuitem', { name: 'Move to folder', exact: true }).click();
	const dialog = page.getByRole('dialog', { name: 'Move to folder', exact: true });
	await dialog.getByRole('checkbox', { name: 'Create new folder' }).check();
	const input = dialog.getByRole('textbox', { name: 'Folder name', exact: true });
	const move = dialog.getByRole('button', { name: 'Move', exact: true });
	let requests = 0;
	page.on('request', (request) => {
		if (request.method() === 'POST' && request.url().endsWith('/api/v1/folders/')) requests++;
	});
	for (const name of ['', '   ']) {
		await input.fill(name);
		await move.click();
		await expect(input).toHaveAttribute('required', '');
		await expect(input).toHaveAttribute('aria-invalid', 'true');
		await expect(input).toHaveAttribute('aria-describedby', 'folder-name-error-test-chat');
		await expect(input).toHaveAccessibleDescription('Folder name cannot be empty.');
		await expect(dialog.getByRole('alert')).toHaveText('Folder name cannot be empty.');
		await expect(input).toBeFocused();
		expect(requests).toBe(0);
	}
	await input.fill('New folder');
	await expect(input).toHaveAttribute('aria-invalid', 'false');
	await expect(dialog.getByRole('alert')).toHaveCount(0);
	await move.click();
	await expect(dialog).toHaveCount(0);
	expect(requests).toBe(1);
});

test('folder API failures show translated messages instead of raw errors', async ({ page }) => {
	await page.goto(`${baseURL}/__keyboard?locale=fr-CA`);
	const trigger = page.locator('#test-chat-menu');
	const errors: string[] = [];
	page.on('console', (message) => {
		if (message.type() === 'error') errors.push(message.text());
	});
	await page.route('**/api/v1/chats/test-chat/folder', (route) =>
		route.fulfill({ status: 500, json: { detail: 'Raw internal error' } })
	);
	await trigger.click();
	await page.getByRole('menuitem', { name: 'Déplacer vers un dossier', exact: true }).click();
	const dialog = page.getByRole('dialog', { name: 'Déplacer vers un dossier', exact: true });
	await dialog.getByRole('button', { name: 'Déplacer', exact: true }).click();
	await expect(page.getByText('Échec du déplacement du chat', { exact: true })).toBeVisible();
	await expect(page.getByText('Raw internal error', { exact: true })).toHaveCount(0);
	await expect(dialog).toBeVisible();
	expect(errors.some((error) => error.includes('Failed to move chat:'))).toBe(true);
	await page.keyboard.press('Escape');
	await page.route('**/api/v1/folders/', (route) =>
		route.fulfill({ status: 500, json: { detail: 'Raw internal error' } })
	);
	await trigger.click();
	await page.getByRole('menuitem', { name: 'Déplacer vers un dossier', exact: true }).click();
	await expect(page.getByText('Échec du chargement des dossiers', { exact: true })).toBeVisible();
	await expect(dialog).toHaveCount(0);
	expect(errors.some((error) => error.includes('Failed to load folders:'))).toBe(true);
});

test('tags can be added from the menu using only the keyboard and dialogs are escapable', async ({
	page
}) => {
	await page.goto(`${baseURL}/__keyboard`);
	const trigger = page.locator('#test-chat-menu');
	await trigger.focus();
	await page.keyboard.press('Enter');
	await expect(page.getByRole('menuitem', { name: 'Move to folder', exact: true })).toBeFocused();
	await page.keyboard.press('ArrowDown');
	await expect(page.getByRole('menuitem', { name: 'Tags', exact: true })).toBeFocused();
	await page.keyboard.press('Enter');
	const dialog = page.getByRole('dialog', { name: 'Tags', exact: true });
	await expect(dialog).toHaveAttribute('aria-modal', 'true');
	await expect(dialog).toHaveAttribute('aria-labelledby', 'chat-tags-title-test-chat');
	await expect(dialog.getByRole('heading', { name: 'Tags', exact: true })).toHaveAttribute(
		'id',
		'chat-tags-title-test-chat'
	);
	const add = dialog.getByRole('button', { name: 'Add Tag', exact: true });
	await expect(add).toBeFocused();
	await page.keyboard.press('Enter');
	await expect(page.getByRole('combobox', { name: 'Add a tag', exact: true })).toBeFocused();
	await page.keyboard.type('keyboard');
	const request = page.waitForRequest('**/api/v1/chats/test-chat/tags');
	await page.keyboard.press('Enter');
	await request;
	await expect(add).toBeFocused();
	await page.keyboard.press('Escape');
	await expect(dialog).toHaveCount(0);
	await expect(trigger).toBeFocused();
});

test('focusing a sidebar chat reveals its menu and rename retains keyboard focus', async ({
	page
}) => {
	await page.goto(`${baseURL}/__keyboard`);
	await page.getByRole('link', { name: 'Keyboard chat', exact: true }).focus();
	await page.keyboard.press('Tab');
	const trigger = page.locator('#chat-menu-keyboard-chat');
	await expect(trigger).toBeFocused();
	await expect(trigger).toBeVisible();
	await page.keyboard.press('Enter');
	await expect(page.getByRole('menuitem', { name: 'Move to folder', exact: true })).toBeFocused();
	await page.keyboard.press('Escape');
	await expect(trigger).toBeFocused();
	await page.keyboard.press('Enter');
	await expect(page.getByRole('menuitem', { name: 'Move to folder', exact: true })).toBeFocused();
	for (const label of ['Tags', 'Pin', 'Rename']) {
		await page.keyboard.press('ArrowDown');
		await expect(page.getByRole('menuitem', { name: label, exact: true })).toBeFocused();
	}
	await expect(page.getByRole('menuitem', { name: 'Rename', exact: true })).toBeFocused();
	await page.keyboard.press('Enter');
	await expect(page.locator('#chat-title-input-keyboard-chat')).toBeFocused();
});

test('the non-modal Chat Controls panel does not trap focus and returns it on close', async ({
	page
}) => {
	await page.goto(`${baseURL}/__keyboard?controls`);
	const opener = page.locator('#open-controls');
	await opener.focus();
	await page.keyboard.press('Enter');
	const close = page
		.locator('#chat-controls-container-wrapper')
		.getByRole('button', { name: 'Close', exact: true });
	await expect(close).toBeFocused();
	const outside = page.locator('#outside-controls');
	for (let index = 0; index < 3; index++) {
		await page.keyboard.press('Shift+Tab');
		if (await outside.evaluate((element) => element === document.activeElement)) break;
	}
	await expect(outside).toBeFocused();
	for (let index = 0; index < 3; index++) {
		await page.keyboard.press('Tab');
		if (await close.evaluate((element) => element === document.activeElement)) break;
	}
	await expect(close).toBeFocused();
	await page.keyboard.press('Tab');
	await page.keyboard.press('Tab');
	await page.keyboard.press('Tab');
	await page.keyboard.press('Tab');
	const panel = page.locator('#chat-controls-container-wrapper');
	await expect(panel.getByRole('button', { name: 'Advanced Params', exact: true })).toBeFocused();
	await page.keyboard.press('Enter');
	await page.keyboard.press('Tab');
	await page.keyboard.press('Tab');
	const seed = panel.locator('button[aria-describedby="tooltip-seed"]');
	await expect(seed).toBeFocused();
	await expect(seed).toHaveCSS('outline-style', 'solid');
	await expect(seed).toHaveCSS('outline-color', 'rgb(0, 94, 168)');
	await page.keyboard.press('Space');
	await page.keyboard.press('Tab');
	await expect(panel.getByRole('spinbutton').first()).toBeFocused();
	for (let index = 0; index < 7; index++) await page.keyboard.press('Shift+Tab');
	await expect(close).toBeFocused();
	await page.keyboard.press('Enter');
	await expect(opener).toBeFocused();
});

test('the Chat Controls drawer on small screens traps focus and Escape returns it', async ({
	page
}) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.goto(`${baseURL}/__keyboard?controls`);
	const opener = page.locator('#open-controls');
	await opener.focus();
	await page.keyboard.press('Enter');
	const dialog = page.getByRole('dialog', { name: 'Chat Controls' });
	await expect(dialog).toHaveAttribute('aria-modal', 'true');
	const close = dialog.getByRole('button', { name: 'Close', exact: true });
	await expect(close).toBeFocused();
	for (const key of ['Tab', 'Shift+Tab']) {
		for (let index = 0; index < 25; index++) {
			await page.keyboard.press(key);
			expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(
				true
			);
		}
	}
	await page.keyboard.press('Escape');
	await expect(dialog).toHaveCount(0);
	await expect(opener).toBeFocused();
});
