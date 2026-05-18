import { describe, expect, it } from 'vitest';
import { hasAdminAccess, hasAnalyticsAccess, isAnalyticsOnlyUser } from './admin';

describe('admin access helpers', () => {
	it('grants analytics to admins regardless of permissions object', () => {
		expect(hasAnalyticsAccess({ role: 'admin' })).toBe(true);
		expect(hasAnalyticsAccess({ role: 'admin', permissions: { admin: { analytics: false } } })).toBe(
			true
		);
	});

	it('grants analytics to users with admin.analytics permission', () => {
		expect(
			hasAnalyticsAccess({
				role: 'user',
				permissions: { admin: { analytics: true } }
			})
		).toBe(true);
	});

	it('denies analytics for regular users without permission', () => {
		expect(hasAnalyticsAccess({ role: 'user' })).toBe(false);
		expect(
			hasAnalyticsAccess({
				role: 'user',
				permissions: { admin: { analytics: false } }
			})
		).toBe(false);
	});

	it('identifies analytics-only users', () => {
		expect(isAnalyticsOnlyUser({ role: 'user', permissions: { admin: { analytics: true } } })).toBe(
			true
		);
		expect(isAnalyticsOnlyUser({ role: 'admin' })).toBe(false);
	});

	it('hasAdminAccess matches admin role only', () => {
		expect(hasAdminAccess({ role: 'admin' })).toBe(true);
		expect(hasAdminAccess({ role: 'user', permissions: { admin: { analytics: true } } })).toBe(
			false
		);
	});
});
