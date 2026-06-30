import { test, expect } from '@playwright/test';
import type { APIRequestContext, BrowserContext, Page } from '@playwright/test';
import { BASE_URL, adminCredentials, signIn, authHeaders } from '../helpers/auth';
import type { Session } from '../helpers/auth';

let admin: Session;
const createdGroupNames: string[] = [];

test.beforeAll(async ({ request }) => {
	admin = await signIn(request, adminCredentials());
});

test.afterAll(async ({ request }) => {
	const res = await request.get('/api/v1/groups/', { headers: authHeaders(admin.token) });
	if (!res.ok()) return;

	const groups: Array<{ id: string; name: string }> = await res.json();
	for (const group of groups) {
		if (createdGroupNames.includes(group.name)) {
			await request
				.delete(`/api/v1/groups/id/${group.id}/delete`, { headers: authHeaders(admin.token) })
				.catch(() => {});
		}
	}
});

async function seedAuth(context: BrowserContext, token: string) {
	await context.addCookies([{ name: 'token', value: token, url: BASE_URL }]);
	await context.addInitScript((t) => {
		window.localStorage.setItem('token', t);
	}, token);
}

async function gotoGroupsTab(page: Page) {
	await page.goto('/admin/users');
	await page.getByRole('button', { name: 'Groups', exact: true }).click();
	await expect(page.getByLabel('Create Group').first()).toBeVisible();
}

test.beforeEach(async ({ context }) => {
	await seedAuth(context, admin.token);
});

test('admin can create a group through the UI', async ({ page }) => {
	const name = `e2e-ui-${Date.now()}`;
	createdGroupNames.push(name);

	await gotoGroupsTab(page);

	await page.getByLabel('Create Group').first().click();
	await page.getByPlaceholder('Group Name').fill(name);
	await page.getByPlaceholder('Group Description').fill('groups ui smoke test');
	await page.getByRole('button', { name: 'Create', exact: true }).click();

	await expect(page.getByText(name, { exact: false })).toBeVisible();
});

test('a created group persists after reload', async ({ page, request }) => {
	const name = `e2e-ui-persist-${Date.now()}`;
	createdGroupNames.push(name);

	const res = await request.post('/api/v1/groups/create', {
		headers: authHeaders(admin.token),
		data: { name, description: 'persisted group' }
	});
	expect(res.status()).toBe(200);

	await gotoGroupsTab(page);
	await expect(page.getByText(name, { exact: false })).toBeVisible();
});

test('the create-group modal opens and can be dismissed', async ({ page }) => {
	await gotoGroupsTab(page);

	await page.getByLabel('Create Group').first().click();
	await expect(page.getByPlaceholder('Group Name')).toBeVisible();

	await page.keyboard.press('Escape');
	await expect(page.getByPlaceholder('Group Name')).toBeHidden();
});

async function seedGroup(request: APIRequestContext, name: string, description = 'seeded') {
	createdGroupNames.push(name);
	const res = await request.post('/api/v1/groups/create', {
		headers: authHeaders(admin.token),
		data: { name, description }
	});
	expect(res.status()).toBe(200);
}

test('search filters the group list by name', async ({ page, request }) => {
	const visibleName = `e2e-ui-search-${Date.now()}`;
	const hiddenName = `e2e-ui-other-${Date.now()}`;
	await seedGroup(request, visibleName);
	await seedGroup(request, hiddenName);

	await gotoGroupsTab(page);
	await expect(page.getByText(visibleName, { exact: true })).toBeVisible();

	// The groups search input is the last "Search" box (the first is the sidebar chat search).
	await page.getByPlaceholder('Search').last().fill(visibleName);
	await expect(page.getByText(visibleName, { exact: true })).toBeVisible();
	await expect(page.getByText(hiddenName, { exact: true })).toBeHidden();
});

test('searching for a non-existent group shows the empty state', async ({ page }) => {
	await gotoGroupsTab(page);

	await page.getByPlaceholder('Search').last().fill(`no-such-group-${Date.now()}`);
	await expect(page.getByText('Organize your users')).toBeVisible();
});

test('admin can edit a group name through the UI', async ({ page, request }) => {
	const name = `e2e-ui-edit-${Date.now()}`;
	const renamed = `${name}-renamed`;
	createdGroupNames.push(renamed);
	await seedGroup(request, name);

	await gotoGroupsTab(page);
	await page.getByText(name, { exact: true }).click();

	const nameInput = page.getByPlaceholder('Group Name');
	await expect(nameInput).toBeVisible();
	await nameInput.fill(renamed);
	await page.getByRole('button', { name: 'Save', exact: true }).click();

	await expect(page.getByText(renamed, { exact: true })).toBeVisible();
	await expect(page.getByText(name, { exact: true })).toBeHidden();
});

test('admin can delete a group through the UI', async ({ page, request }) => {
	const name = `e2e-ui-delete-${Date.now()}`;
	await seedGroup(request, name);

	await gotoGroupsTab(page);
	await page.getByText(name, { exact: true }).click();

	// Open the delete confirmation, then confirm. The dialog's confirm button is
	// also labelled "Delete", so it is the last matching button once the dialog opens.
	await page.getByRole('button', { name: 'Delete', exact: true }).click();
	await page.getByRole('button', { name: 'Delete', exact: true }).last().click();

	await expect(page.getByText(name, { exact: true })).toBeHidden();
});
