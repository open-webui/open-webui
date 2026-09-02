import { describe, expect, it } from 'vitest';

import { cleanNotificationText } from './index';

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
