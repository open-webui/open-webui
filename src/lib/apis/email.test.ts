import { afterEach, describe, expect, it, vi } from 'vitest';

import { addUser, userSignIn, userSignUp } from './auths';
import { updateUserById } from './users';

vi.mock('$lib/constants', () => ({ WEBUI_API_BASE_URL: '/api/v1' }));
vi.mock('$lib/utils', () => ({ getUserPosition: vi.fn() }));

afterEach(() => vi.unstubAllGlobals());

describe('account email submissions', () => {
	it.each(['a\u0308@a\u0308.a\u0308', 'ä@ä.ä', 'ascii@example.com', '用户@例子.中国'])(
		'submits NFC for %s without changing names or passwords',
		async (email) => {
			const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'user' }) });
			vi.stubGlobal('fetch', fetch);
			const name = 'Ame\u0301lie';
			const password = 'unchanged-e\u0301';

			await userSignIn(email, password);
			await userSignUp(name, email, password, '/user.png');
			// CSV import uses this same addUser function.
			await addUser('token', name, email, password, 'user');
			await updateUserById('token', 'user', {
				name,
				email,
				password,
				role: 'user',
				profile_image_url: '/user.png'
			});

			expect(fetch).toHaveBeenCalledTimes(4);
			for (const [, options] of fetch.mock.calls) {
				const body = JSON.parse(options.body);
				expect(body.email).toBe(email.normalize('NFC'));
				expect(body.password).toBe(password);
				if ('name' in body) expect(body.name).toBe(name);
			}
		}
	);
});
