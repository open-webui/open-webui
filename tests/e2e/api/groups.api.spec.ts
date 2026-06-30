import { test, expect } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';
import { adminCredentials, userCredentials, signIn, authHeaders } from '../helpers/auth';
import type { Session } from '../helpers/auth';

const GROUPS = '/api/v1/groups';
const uniqueName = (prefix = 'e2e-group') =>
	`${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e4)}`;

let admin: Session;

test.beforeAll(async ({ request }) => {
	admin = await signIn(request, adminCredentials());
	expect(admin.role).toBe('admin');
});

async function deleteGroup(request: APIRequestContext, token: string, id: string) {
	await request
		.delete(`${GROUPS}/id/${id}/delete`, { headers: authHeaders(token) })
		.catch(() => {});
}

test.describe('groups router - authentication', () => {
	test('rejects unauthenticated list', async ({ request }) => {
		const res = await request.get(`${GROUPS}/`, { headers: { Accept: 'application/json' } });
		expect(res.status()).toBe(403);
	});

	test('rejects unauthenticated create', async ({ request }) => {
		const res = await request.post(`${GROUPS}/create`, {
			data: { name: uniqueName(), description: 'x' }
		});
		expect(res.status()).toBe(403);
	});
});

test.describe('groups router - validation', () => {
	test('create requires name and description (422)', async ({ request }) => {
		const res = await request.post(`${GROUPS}/create`, {
			headers: authHeaders(admin.token),
			data: { description: 'missing name' }
		});
		expect(res.status()).toBe(422);
	});

	test('get by unknown id returns 401 not-found', async ({ request }) => {
		const res = await request.get(`${GROUPS}/id/does-not-exist-${Date.now()}`, {
			headers: authHeaders(admin.token)
		});
		expect(res.status()).toBe(401);
	});
});

test.describe('groups router - admin CRUD lifecycle', () => {
	const description = 'groups e2e suite';
	let name: string;
	let groupId: string;
	let created: Record<string, unknown>;

	test.beforeEach(async ({ request }) => {
		name = uniqueName();
		const res = await request.post(`${GROUPS}/create`, {
			headers: authHeaders(admin.token),
			data: { name, description }
		});
		expect(res.status(), await res.text()).toBe(200);
		created = await res.json();
		groupId = created.id as string;
	});

	test.afterEach(async ({ request }) => {
		if (groupId) {
			await deleteGroup(request, admin.token, groupId);
		}
	});

	test('create stamps ownership and defaults', async () => {
		expect(created.id).toBeTruthy();
		expect(created.name).toBe(name);
		expect(created.description).toBe(description);
		expect(created.created_by).toBe(admin.email);
		expect(created.user_id).toBe(admin.id);
		expect(created.user_ids).toEqual([]);
		expect(typeof created.created_at).toBe('number');
		expect(typeof created.updated_at).toBe('number');
	});

	test('new group appears in the list', async ({ request }) => {
		const res = await request.get(`${GROUPS}/`, { headers: authHeaders(admin.token) });
		expect(res.status()).toBe(200);

		const groups = await res.json();
		expect(Array.isArray(groups)).toBe(true);
		expect(groups.map((g: { id: string }) => g.id)).toContain(groupId);
	});

	test('fetch the group by id', async ({ request }) => {
		const res = await request.get(`${GROUPS}/id/${groupId}`, { headers: authHeaders(admin.token) });
		expect(res.status()).toBe(200);

		const group = await res.json();
		expect(group.id).toBe(groupId);
		expect(group.name).toBe(name);
	});

	test('update name, description and permissions', async ({ request }) => {
		const updatedName = `${name}-updated`;
		const permissions = { workspace: { models: true } };

		const res = await request.post(`${GROUPS}/id/${groupId}/update`, {
			headers: authHeaders(admin.token),
			data: { name: updatedName, description: 'updated description', permissions }
		});
		expect(res.status(), await res.text()).toBe(200);

		const group = await res.json();
		expect(group.name).toBe(updatedName);
		expect(group.description).toBe('updated description');
		expect(group.permissions).toMatchObject(permissions);
		expect(group.updated_at).toBeGreaterThanOrEqual(group.created_at);
	});

	test('update membership with valid users', async ({ request }) => {
		const res = await request.post(`${GROUPS}/id/${groupId}/update`, {
			headers: authHeaders(admin.token),
			data: { name, description, user_ids: [admin.id] }
		});
		expect(res.status(), await res.text()).toBe(200);

		const group = await res.json();
		expect(group.user_ids).toContain(admin.id);
	});

	test('invalid user_ids are filtered out on update', async ({ request }) => {
		const res = await request.post(`${GROUPS}/id/${groupId}/update`, {
			headers: authHeaders(admin.token),
			data: { name, description, user_ids: ['this-user-does-not-exist'] }
		});
		expect(res.status(), await res.text()).toBe(200);

		const group = await res.json();
		expect(group.user_ids).not.toContain('this-user-does-not-exist');
	});

	test('delete the group', async ({ request }) => {
		const res = await request.delete(`${GROUPS}/id/${groupId}/delete`, {
			headers: authHeaders(admin.token)
		});
		expect(res.status()).toBe(200);
		expect(await res.json()).toBe(true);

		const after = await request.get(`${GROUPS}/id/${groupId}`, {
			headers: authHeaders(admin.token)
		});
		expect(after.status()).toBe(401);

		groupId = '';
	});

	test('update of a non-existent group returns 400', async ({ request }) => {
		const res = await request.post(`${GROUPS}/id/missing-${Date.now()}/update`, {
			headers: authHeaders(admin.token),
			data: { name: 'x', description: 'y' }
		});
		expect(res.status()).toBe(400);
	});

	test('removing a member updates membership', async ({ request }) => {
		const add = await request.post(`${GROUPS}/id/${groupId}/update`, {
			headers: authHeaders(admin.token),
			data: { name, description, user_ids: [admin.id] }
		});
		expect(add.status(), await add.text()).toBe(200);
		expect((await add.json()).user_ids).toContain(admin.id);

		const remove = await request.post(`${GROUPS}/id/${groupId}/update`, {
			headers: authHeaders(admin.token),
			data: { name, description, user_ids: [] }
		});
		expect(remove.status(), await remove.text()).toBe(200);
		expect((await remove.json()).user_ids).toEqual([]);
	});

	test('changing permissions on a group with members succeeds', async ({ request }) => {
		const withMember = await request.post(`${GROUPS}/id/${groupId}/update`, {
			headers: authHeaders(admin.token),
			data: { name, description, user_ids: [admin.id] }
		});
		expect(withMember.status(), await withMember.text()).toBe(200);

		const permissions = { workspace: { models: true, knowledge: false } };
		const res = await request.post(`${GROUPS}/id/${groupId}/update`, {
			headers: authHeaders(admin.token),
			data: { name, description, permissions, user_ids: [admin.id] }
		});
		expect(res.status(), await res.text()).toBe(200);

		const group = await res.json();
		expect(group.permissions).toMatchObject(permissions);
		expect(group.user_ids).toContain(admin.id);
	});

	test('delete a group that has members', async ({ request }) => {
		const add = await request.post(`${GROUPS}/id/${groupId}/update`, {
			headers: authHeaders(admin.token),
			data: { name, description, user_ids: [admin.id] }
		});
		expect(add.status(), await add.text()).toBe(200);

		const res = await request.delete(`${GROUPS}/id/${groupId}/delete`, {
			headers: authHeaders(admin.token)
		});
		expect(res.status()).toBe(200);
		expect(await res.json()).toBe(true);

		const after = await request.get(`${GROUPS}/id/${groupId}`, {
			headers: authHeaders(admin.token)
		});
		expect(after.status()).toBe(401);

		groupId = '';
	});
});

test.describe('groups router - role enforcement (non-admin)', () => {
	const creds = userCredentials();
	test.skip(!creds, 'Set USER_EMAIL and USER_PASSWORD to run non-admin role tests.');

	let userToken: string;
	let adminGroupId: string;
	let userIsAdmin = false;

	test.beforeAll(async ({ request }) => {
		const session = await signIn(request, creds!);
		userToken = session.token;
		userIsAdmin = session.role === 'admin';
		if (userIsAdmin) return;

		const res = await request.post(`${GROUPS}/create`, {
			headers: authHeaders(admin.token),
			data: { name: uniqueName('e2e-rbac'), description: 'rbac target' }
		});
		expect(res.status()).toBe(200);
		adminGroupId = (await res.json()).id;
	});

	test.afterAll(async ({ request }) => {
		if (adminGroupId) {
			await deleteGroup(request, admin.token, adminGroupId);
		}
	});

	const skipIfAdmin = () =>
		test.skip(userIsAdmin, 'USER_EMAIL is an admin account; set a non-admin user to run this.');

	test('non-admin cannot create a group (401)', async ({ request }) => {
		skipIfAdmin();
		const res = await request.post(`${GROUPS}/create`, {
			headers: authHeaders(userToken),
			data: { name: uniqueName(), description: 'should be forbidden' }
		});
		expect(res.status()).toBe(401);
	});

	test('non-admin cannot fetch a group by id (401)', async ({ request }) => {
		skipIfAdmin();
		const res = await request.get(`${GROUPS}/id/${adminGroupId}`, {
			headers: authHeaders(userToken)
		});
		expect(res.status()).toBe(401);
	});

	test('non-admin cannot update a group (401)', async ({ request }) => {
		skipIfAdmin();
		const res = await request.post(`${GROUPS}/id/${adminGroupId}/update`, {
			headers: authHeaders(userToken),
			data: { name: 'hijack', description: 'nope' }
		});
		expect(res.status()).toBe(401);
	});

	test('non-admin cannot delete a group (401)', async ({ request }) => {
		skipIfAdmin();
		const res = await request.delete(`${GROUPS}/id/${adminGroupId}/delete`, {
			headers: authHeaders(userToken)
		});
		expect(res.status()).toBe(401);
	});

	test('non-admin list excludes groups they are not a member of', async ({ request }) => {
		skipIfAdmin();
		const res = await request.get(`${GROUPS}/`, { headers: authHeaders(userToken) });
		expect(res.status()).toBe(200);

		const groups = await res.json();
		expect(Array.isArray(groups)).toBe(true);
		expect(groups.map((g: { id: string }) => g.id)).not.toContain(adminGroupId);
	});
});
