import { describe, expect, it } from 'vitest';
import { allGroupManagerRequestsDenied, isGroupManagerAuthorizationFailure } from './groupManager';

describe('group manager authorization state', () => {
	it('recognizes only 401 and 403 as authorization failures', () => {
		expect(isGroupManagerAuthorizationFailure({ status: 401 })).toBe(true);
		expect(isGroupManagerAuthorizationFailure({ status: 403 })).toBe(true);
		expect(isGroupManagerAuthorizationFailure({ status: 500 })).toBe(false);
		expect(isGroupManagerAuthorizationFailure(new Error('network'))).toBe(false);
	});

	it('requires every scoped request to be denied before showing access-required state', () => {
		expect(allGroupManagerRequestsDenied([{ status: 401 }, { status: 403 }])).toBe(true);
		expect(allGroupManagerRequestsDenied([{ status: 403 }, { status: 500 }])).toBe(false);
		expect(allGroupManagerRequestsDenied([new Error('offline'), { status: 503 }])).toBe(false);
	});
});
