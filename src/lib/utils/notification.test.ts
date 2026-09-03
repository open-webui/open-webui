import { describe, expect, it } from 'vitest';

import { cleanNotificationText, containsUserMention } from './index';

describe('cleanNotificationText', () => {
	it('removes serialized user mentions from notification text', () => {
		expect(cleanNotificationText('<@U:13c44bd0|Jonathan Flower> sup')).toBe('sup');
	});

	it('does not expose an internal ID when a mention has no label', () => {
		expect(cleanNotificationText('<@U:13c44bd0> hello')).toBe('hello');
	});

	it('removes markdown while preserving ordinary notification text', () => {
		expect(cleanNotificationText('**Hello** `there`')).toBe('Hello there');
	});
});

describe('containsUserMention', () => {
	it('matches only the requested encoded user mention', () => {
		expect(containsUserMention('<@U:user-1|Ada> hello', 'user-1')).toBe(true);
		expect(containsUserMention('<@U:user-10|Grace> hello', 'user-1')).toBe(false);
	});

	it('accepts mentions without a display label', () => {
		expect(containsUserMention('<@U:user-1> hello', 'user-1')).toBe(true);
	});

	it('does not match when the user ID is unavailable', () => {
		expect(containsUserMention('<@U:> hello', '')).toBe(false);
	});
});
